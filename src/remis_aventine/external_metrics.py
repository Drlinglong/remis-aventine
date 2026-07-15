"""Boundary between Aventine core and heavyweight automatic-metric runtimes."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from contextlib import ExitStack
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

from remis_aventine.validation import validate_document, validate_payload


class ExternalMetricError(RuntimeError):
    """Raised when an isolated metric runtime cannot produce valid evidence."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _require_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ExternalMetricError(f"{label} is not a file: {resolved}")
    return resolved


def _require_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise ExternalMetricError(f"{label} does not exist: {resolved}")
    return resolved


def _model_weight_file(model_path: Path) -> Path:
    if model_path.is_file():
        return model_path
    candidates = [
        model_path / "model.safetensors",
        model_path / "pytorch_model.bin",
    ]
    existing = [candidate for candidate in candidates if candidate.is_file()]
    if len(existing) != 1:
        raise ExternalMetricError(
            "Model directory must contain exactly one model.safetensors or pytorch_model.bin."
        )
    return existing[0]


def _sha256_model(model_path: Path) -> str:
    digest = hashlib.sha256()
    with _model_weight_file(model_path).open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_directory(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise ExternalMetricError(f"{label} is not a directory: {resolved}")
    return resolved


def _validate_cases(pack: dict[str, Any], mode: str, metric: str) -> None:
    ids = [case["id"] for case in pack["cases"]]
    if len(ids) != len(set(ids)):
        raise ExternalMetricError("Metric pack case ids must be unique.")
    if mode == "reference":
        missing = [case["id"] for case in pack["cases"] if not case.get("reference")]
        if missing:
            raise ExternalMetricError(
                "Reference mode requires a reference for every case; missing: " + ", ".join(missing)
            )
    if metric == "xcomet" and mode != "reference":
        raise ExternalMetricError("xCOMET-XL requires reference mode.")


def _worker_command(
    metric: str,
    python: Path,
    worker: Path,
    input_path: Path,
    output_path: Path,
    model_path: Path,
    mode: str,
    batch_size: int,
    *,
    tokenizer_path: Path | None,
    metricx_source: Path | None,
    hf_home: Path | None,
) -> list[str]:
    command = [
        str(python),
        str(worker),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--model",
        str(model_path),
        "--mode",
        mode,
        "--batch-size",
        str(batch_size),
    ]
    if metric == "metricx-24":
        if tokenizer_path is None or metricx_source is None:
            raise ExternalMetricError("MetricX requires both tokenizer_path and metricx_source.")
        command.extend(
            [
                "--tokenizer",
                str(_require_directory(tokenizer_path, "MetricX tokenizer")),
                "--metricx-source",
                str(_require_directory(metricx_source, "MetricX source checkout")),
            ]
        )
    elif hf_home is None:
        raise ExternalMetricError("xCOMET requires hf_home with its cached base model files.")
    else:
        command.extend(["--hf-home", str(_require_directory(hf_home, "Hugging Face cache"))])
    return command


def _read_worker_result(path: Path, expected_ids: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalMetricError(f"Metric worker did not write valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("runtime"), dict):
        raise ExternalMetricError("Metric worker result is missing runtime metadata.")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ExternalMetricError("Metric worker returned missing, reordered, or unexpected cases.")
    if (
        any(not isinstance(case, dict) for case in cases)
        or [case.get("id") for case in cases] != expected_ids
    ):
        raise ExternalMetricError("Metric worker returned missing, reordered, or unexpected cases.")
    if any(
        isinstance(case.get("score"), bool)
        or not isinstance(case.get("score"), int | float)
        or not math.isfinite(case["score"])
        for case in cases
    ):
        raise ExternalMetricError("Metric worker returned a non-numeric score.")
    return payload


def run_external_metric(
    input_path: Path,
    output_path: Path,
    *,
    metric: str,
    runtime_python: Path,
    model_path: Path,
    model_id: str,
    model_sha256: str,
    mode: str = "reference",
    batch_size: int = 1,
    timeout_seconds: int = 1800,
    tokenizer_path: Path | None = None,
    metricx_source: Path | None = None,
    hf_home: Path | None = None,
) -> dict[str, Any]:
    """Run one pinned metric in its own Python environment and validate the result."""
    if metric not in {"metricx-24", "xcomet"}:
        raise ExternalMetricError(f"Unsupported metric: {metric}")
    if mode not in {"qe", "reference"}:
        raise ExternalMetricError(f"Unsupported metric mode: {mode}")
    if batch_size < 1:
        raise ExternalMetricError("batch_size must be at least 1.")
    if timeout_seconds < 1:
        raise ExternalMetricError("timeout_seconds must be at least 1.")
    normalized_sha = model_sha256.lower()
    if len(normalized_sha) != 64 or any(char not in "0123456789abcdef" for char in normalized_sha):
        raise ExternalMetricError("model_sha256 must be 64 lowercase hexadecimal characters.")
    if not model_id.strip():
        raise ExternalMetricError("model_id must not be empty.")

    pack = validate_document(input_path, "metric-pack.schema.json")
    _validate_cases(pack, mode, metric)
    if metric == "metricx-24" and (tokenizer_path is None or metricx_source is None):
        raise ExternalMetricError("MetricX requires both tokenizer_path and metricx_source.")
    if metric == "xcomet" and hf_home is None:
        raise ExternalMetricError("xCOMET requires hf_home with its cached base model files.")
    python = _require_file(runtime_python, "Runtime Python")
    model = _require_path(model_path, "Metric model")
    actual_sha = _sha256_model(model)
    if actual_sha != normalized_sha:
        raise ExternalMetricError(
            f"Metric model SHA-256 mismatch: expected {normalized_sha}, received {actual_sha}."
        )
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()

    package = resources.files("remis_aventine.metric_workers")
    worker_name = "metricx.py" if metric == "metricx-24" else "xcomet.py"
    with ExitStack() as stack, tempfile.TemporaryDirectory(prefix="aventine-metric-") as temp:
        worker = stack.enter_context(resources.as_file(package.joinpath(worker_name)))
        raw_output = Path(temp) / "worker-result.json"
        command = _worker_command(
            metric,
            python,
            worker,
            input_path.resolve(),
            raw_output,
            model,
            mode,
            batch_size,
            tokenizer_path=tokenizer_path,
            metricx_source=metricx_source,
            hf_home=hf_home,
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExternalMetricError(
                f"{metric} exceeded the {timeout_seconds}-second runtime budget."
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-4000:]
            raise ExternalMetricError(
                f"{metric} worker exited with code {completed.returncode}: {detail}"
            )
        raw = _read_worker_result(raw_output, [case["id"] for case in pack["cases"]])

    scores = [float(case["score"]) for case in raw["cases"]]
    result = {
        "schema_version": 1,
        "pack_id": pack["id"],
        "metric": {
            "name": metric,
            "model_id": model_id,
            "model_sha256": normalized_sha,
            "mode": mode,
            "direction": "lower_is_better" if metric == "metricx-24" else "higher_is_better",
        },
        "runtime": raw["runtime"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "cases": raw["cases"],
        "summary": {
            "case_count": len(scores),
            "mean_score": sum(scores) / len(scores),
            "minimum_score": min(scores),
            "maximum_score": max(scores),
        },
    }
    validated = validate_payload(result, "metric-result.schema.json")
    output_path.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return validated

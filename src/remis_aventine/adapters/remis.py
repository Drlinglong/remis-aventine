"""Read-only conversion of Remis translation benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from remis_aventine.validation import validate_payload

ADAPTER_REVISION = "remis-translation-quality-v1"


class RemisCompatibilityError(ValueError):
    """Raised when a Remis artifact cannot be converted safely."""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_string(document: dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RemisCompatibilityError(f"Remis artifact requires a non-empty {key!r}.")
    return value


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RemisCompatibilityError(f"Invalid Remis created_at_utc: {value!r}.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _status(result: dict[str, Any]) -> str:
    if result.get("execution_failure"):
        return "execution_failure"
    score = result.get("score")
    if not isinstance(score, dict):
        return "structured_output_failure"
    if score.get("parsed") is not True or score.get("item_count_match") is not True:
        return "structured_output_failure"
    return "completed"


def _findings(score: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    items = score.get("items", [])
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            validations = item.get("validation", [])
            if isinstance(validations, list):
                for validation in validations:
                    finding = {"source": "remis_validation", "key": key}
                    if isinstance(validation, dict):
                        finding.update(validation)
                    else:
                        finding["detail"] = str(validation)
                    findings.append(finding)
            parity = item.get("token_parity")
            if isinstance(parity, dict) and parity.get("passed") is False:
                findings.append(
                    {
                        "source": "remis_token_parity",
                        "key": key,
                        "missing": parity.get("missing", []),
                        "extra": parity.get("extra", []),
                    }
                )
    if score.get("hard_pass") is False and not findings:
        findings.append(
            {
                "source": "remis_hard_validation",
                "code": "hard_validation_failed_without_structured_finding",
            }
        )
    return findings


def _automatic_metrics(result: dict[str, Any]) -> dict[str, Any]:
    score = result.get("score")
    metrics = {
        "elapsed_seconds": result.get("elapsed_seconds"),
    }
    if not isinstance(score, dict):
        return metrics
    for key, value in score.items():
        if key != "items":
            metrics[key] = value
    return metrics


def _convert_case(result: dict[str, Any]) -> dict[str, Any]:
    case_id = _required_string(result, "id")
    status = _status(result)
    score = result.get("score") if isinstance(result.get("score"), dict) else {}
    passed = score.get("hard_pass") if status == "completed" else None
    return {
        "id": case_id,
        "execution_status": status,
        "hard_validation": {
            "enabled": True,
            "passed": passed if isinstance(passed, bool) else None,
            "findings": _findings(score),
        },
        "automatic_metrics": _automatic_metrics(result),
        "judge": None,
        "track": result.get("track"),
        "source_metadata": {
            "source_file": result.get("source_file"),
            "source_sha256": result.get("source_sha256"),
            "prompt_sha256": result.get("prompt_sha256"),
            "source_language": result.get("source_lang"),
            "target_language": result.get("target_lang"),
            "focus": result.get("focus", []),
        },
        "candidate_outputs": result.get("outputs"),
    }


def convert_remis_result(
    document: dict[str, Any], *, recipe_id: str | None = None
) -> dict[str, Any]:
    """Convert one Remis benchmark JSON object into an Aventine run result."""
    if not isinstance(document, dict):
        raise RemisCompatibilityError("Remis artifact must be a JSON object.")
    if document.get("schema_version") != 1:
        raise RemisCompatibilityError("Only Remis benchmark schema_version 1 is supported.")
    results = document.get("results")
    if not isinstance(results, list):
        raise RemisCompatibilityError("Remis artifact results must be an array.")

    provider = _required_string(document, "provider")
    model_id = _required_string(document, "model_id")
    model_label = _required_string(document, "model_label")
    track = _required_string(document, "track")
    benchmark = _required_string(document, "benchmark")
    fixture_sha256 = _required_string(document, "fixture_sha256")
    finished = _timestamp(_required_string(document, "created_at_utc"))
    source_summary = document.get("summary")
    if not isinstance(source_summary, dict):
        raise RemisCompatibilityError("Remis artifact summary must be an object.")
    elapsed_seconds = source_summary.get("elapsed_seconds", 0)
    if not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
        raise RemisCompatibilityError("Remis summary elapsed_seconds must be non-negative.")
    started = finished - timedelta(seconds=float(elapsed_seconds))

    prompt_hashes = sorted(
        {
            value
            for result in results
            if isinstance(result, dict)
            and isinstance((value := result.get("prompt_sha256")), str)
            and value
        }
    )
    recipe_snapshot = {
        "adapter_revision": ADAPTER_REVISION,
        "provider": provider,
        "model_id": model_id,
        "model_label": model_label,
        "track": track,
        "prompt_sha256": prompt_hashes,
        "fixture_sha256": fixture_sha256,
        "policy": document.get("policy", {}),
    }
    resolved_recipe_id = recipe_id or f"remis.{_slug(provider)}.{_slug(model_id)}.{_slug(track)}"
    converted_cases = [_convert_case(result) for result in results if isinstance(result, dict)]
    if len(converted_cases) != len(results):
        raise RemisCompatibilityError("Every Remis result entry must be an object.")
    status_counts = {
        status: sum(case["execution_status"] == status for case in converted_cases)
        for status in ("completed", "execution_failure", "structured_output_failure")
    }

    converted = {
        "schema_version": 1,
        "run_id": f"remis-{finished.strftime('%Y%m%dT%H%M%SZ')}-{_slug(model_label)}",
        "suite": "remis",
        "recipe": {
            "id": resolved_recipe_id,
            "sha256": _canonical_sha256(recipe_snapshot),
            "provenance": "compatibility_snapshot",
            "snapshot": recipe_snapshot,
        },
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": finished.isoformat().replace("+00:00", "Z"),
        "environment": {
            "source_format": "remis_translation_quality_benchmark_v1",
            "adapter_revision": ADAPTER_REVISION,
            "benchmark": benchmark,
            "fixture_sha256": fixture_sha256,
            "provider": provider,
            "model_id": model_id,
            "model_label": model_label,
            "track": track,
        },
        "cases": converted_cases,
        "summary": {
            "case_count": len(converted_cases),
            "completed_count": status_counts["completed"],
            "execution_failure_count": status_counts["execution_failure"],
            "structured_output_failure_count": status_counts["structured_output_failure"],
            "hard_pass_count": sum(
                case["hard_validation"]["passed"] is True for case in converted_cases
            ),
            "elapsed_seconds": float(elapsed_seconds),
            "source_summary": source_summary,
        },
    }
    return validate_payload(converted, "run-result.schema.json")


def adapt_remis_result(
    input_path: Path, output_path: Path, *, recipe_id: str | None = None
) -> dict[str, Any]:
    """Read, convert, validate, and write one Remis benchmark artifact."""
    try:
        source = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RemisCompatibilityError(
            f"Invalid Remis JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    converted = convert_remis_result(source, recipe_id=recipe_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return converted

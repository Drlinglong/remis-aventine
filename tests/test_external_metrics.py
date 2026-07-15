from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import remis_aventine.external_metrics as external_metrics
from remis_aventine.external_metrics import ExternalMetricError, run_external_metric
from remis_aventine.validation import DocumentValidationError, validate_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PACK = PROJECT_ROOT / "examples" / "metrics" / "smoke-v1.json"


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    python = tmp_path / "python.exe"
    model = tmp_path / "model.bin"
    directory = tmp_path / "support"
    python.write_bytes(b"")
    model.write_bytes(b"")
    directory.mkdir()
    return python, model, directory


def _successful_worker(command, **_kwargs):
    output = Path(command[command.index("--output") + 1])
    input_path = Path(command[command.index("--input") + 1])
    pack = json.loads(input_path.read_text(encoding="utf-8"))
    output.write_text(
        json.dumps(
            {
                "runtime": {
                    "python": "3.11.15",
                    "packages": {"torch": "2.10.0+cu128"},
                    "device": "NVIDIA GeForce RTX 5090",
                },
                "cases": [
                    {"id": case["id"], "score": 0.5, "error_spans": []}
                    for case in pack["cases"]
                ],
            }
        ),
        encoding="utf-8",
    )
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_metric_example_matches_schema() -> None:
    pack = validate_document(SMOKE_PACK, "metric-pack.schema.json")
    assert pack["cases"][0]["reference"] == "Hallo Welt"


def test_run_xcomet_uses_isolated_runtime_and_writes_valid_result(
    monkeypatch, tmp_path
) -> None:
    python, model, _support = _paths(tmp_path)
    output = tmp_path / "result.json"
    monkeypatch.setattr(external_metrics, "_sha256_model", lambda _path: "a" * 64)
    monkeypatch.setattr(external_metrics.subprocess, "run", _successful_worker)

    result = run_external_metric(
        SMOKE_PACK,
        output,
        metric="xcomet",
        runtime_python=python,
        model_path=model,
        model_id="Unbabel/XCOMET-XL",
        model_sha256="a" * 64,
        hf_home=tmp_path,
    )

    assert result["summary"] == {
        "case_count": 1,
        "mean_score": 0.5,
        "minimum_score": 0.5,
        "maximum_score": 0.5,
    }
    assert result["metric"]["direction"] == "higher_is_better"
    validate_document(output, "metric-result.schema.json")


def test_run_metricx_passes_local_support_paths(monkeypatch, tmp_path) -> None:
    python, model, support = _paths(tmp_path)
    selected = {}

    def worker(command, **kwargs):
        selected["command"] = command
        return _successful_worker(command, **kwargs)

    monkeypatch.setattr(external_metrics.subprocess, "run", worker)
    monkeypatch.setattr(external_metrics, "_sha256_model", lambda _path: "b" * 64)
    result = run_external_metric(
        SMOKE_PACK,
        tmp_path / "result.json",
        metric="metricx-24",
        runtime_python=python,
        model_path=model,
        model_id="google/metricx-24-hybrid-xl-v2p6-bfloat16",
        model_sha256="b" * 64,
        mode="qe",
        tokenizer_path=support,
        metricx_source=support,
    )

    assert "--tokenizer" in selected["command"]
    assert "--metricx-source" in selected["command"]
    assert result["metric"]["direction"] == "lower_is_better"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"metric": "unknown"}, "Unsupported metric"),
        ({"mode": "bad"}, "Unsupported metric mode"),
        ({"batch_size": 0}, "batch_size"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"model_sha256": "bad"}, "model_sha256"),
        ({"model_id": ""}, "model_id"),
    ],
)
def test_run_external_metric_rejects_invalid_configuration(tmp_path, kwargs, message) -> None:
    python, model, _support = _paths(tmp_path)
    options = {
        "metric": "xcomet",
        "runtime_python": python,
        "model_path": model,
        "model_id": "model",
        "model_sha256": "a" * 64,
        "hf_home": tmp_path,
    }
    options.update(kwargs)
    with pytest.raises(ExternalMetricError, match=message):
        run_external_metric(SMOKE_PACK, tmp_path / "result.json", **options)


def test_xcomet_rejects_qe_and_metricx_requires_support_paths(tmp_path) -> None:
    python, model, _support = _paths(tmp_path)
    common = {
        "runtime_python": python,
        "model_path": model,
        "model_id": "model",
        "model_sha256": "a" * 64,
        "hf_home": tmp_path,
    }
    with pytest.raises(ExternalMetricError, match="requires reference"):
        run_external_metric(
            SMOKE_PACK, tmp_path / "x.json", metric="xcomet", mode="qe", **common
        )
    with pytest.raises(ExternalMetricError, match="requires both"):
        run_external_metric(
            SMOKE_PACK, tmp_path / "m.json", metric="metricx-24", **common
        )


def test_reference_mode_rejects_missing_reference_and_duplicate_ids(tmp_path) -> None:
    python, model, _support = _paths(tmp_path)
    pack = json.loads(SMOKE_PACK.read_text(encoding="utf-8"))
    pack["cases"][0].pop("reference")
    input_path = tmp_path / "missing-ref.json"
    input_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ExternalMetricError, match="missing: en-de-perfect"):
        run_external_metric(
            input_path,
            tmp_path / "result.json",
            metric="xcomet",
            runtime_python=python,
            model_path=model,
            model_id="model",
            model_sha256="a" * 64,
            hf_home=tmp_path,
        )

    pack["cases"].append(dict(pack["cases"][0]))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ExternalMetricError, match="unique"):
        run_external_metric(
            duplicate,
            tmp_path / "result.json",
            metric="metricx-24",
            runtime_python=python,
            model_path=model,
            model_id="model",
            model_sha256="a" * 64,
            mode="qe",
            tokenizer_path=tmp_path,
            metricx_source=tmp_path,
        )


def test_worker_failures_timeout_and_malformed_output_are_explicit(monkeypatch, tmp_path) -> None:
    python, model, _support = _paths(tmp_path)
    common = {
        "metric": "xcomet",
        "runtime_python": python,
        "model_path": model,
        "model_id": "model",
        "model_sha256": "a" * 64,
        "hf_home": tmp_path,
    }
    monkeypatch.setattr(external_metrics, "_sha256_model", lambda _path: "a" * 64)
    monkeypatch.setattr(
        external_metrics.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=3, stdout="", stderr="boom"),
    )
    with pytest.raises(ExternalMetricError, match="code 3: boom"):
        run_external_metric(SMOKE_PACK, tmp_path / "failed.json", **common)

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("worker", 1)

    monkeypatch.setattr(external_metrics.subprocess, "run", timeout)
    with pytest.raises(ExternalMetricError, match="runtime budget"):
        run_external_metric(
            SMOKE_PACK, tmp_path / "timeout.json", timeout_seconds=1, **common
        )

    def malformed(command, **_kwargs):
        Path(command[command.index("--output") + 1]).write_text("{}", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(external_metrics.subprocess, "run", malformed)
    with pytest.raises(ExternalMetricError, match="runtime metadata"):
        run_external_metric(SMOKE_PACK, tmp_path / "malformed.json", **common)


def test_metric_schema_rejects_empty_pack(tmp_path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(
        json.dumps({"schema_version": 1, "id": "x", "suite": "x", "cases": []}),
        encoding="utf-8",
    )
    with pytest.raises(DocumentValidationError):
        validate_document(path, "metric-pack.schema.json")


def test_model_sha_is_verified_before_worker_launch(monkeypatch, tmp_path) -> None:
    python, model, _support = _paths(tmp_path)
    monkeypatch.setattr(external_metrics, "_sha256_model", lambda _path: "b" * 64)
    with pytest.raises(ExternalMetricError, match="SHA-256 mismatch"):
        run_external_metric(
            SMOKE_PACK,
            tmp_path / "result.json",
            metric="xcomet",
            runtime_python=python,
            model_path=model,
            model_id="model",
            model_sha256="a" * 64,
            hf_home=tmp_path,
        )


def test_model_directory_hashes_the_single_known_weight_file(tmp_path) -> None:
    model = tmp_path / "model"
    model.mkdir()
    weight = model / "pytorch_model.bin"
    weight.write_bytes(b"weights")

    assert external_metrics._sha256_model(model) == hashlib.sha256(b"weights").hexdigest()

    (model / "model.safetensors").write_bytes(b"other")
    with pytest.raises(ExternalMetricError, match="exactly one"):
        external_metrics._sha256_model(model)


def test_path_guards_and_worker_result_failures(tmp_path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ExternalMetricError, match="not a file"):
        external_metrics._require_file(missing, "Python")
    with pytest.raises(ExternalMetricError, match="does not exist"):
        external_metrics._require_path(missing, "Model")
    with pytest.raises(ExternalMetricError, match="not a directory"):
        external_metrics._require_directory(missing, "Cache")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")
    with pytest.raises(ExternalMetricError, match="valid JSON"):
        external_metrics._read_worker_result(malformed, ["case"])

    wrong_cases = tmp_path / "wrong-cases.json"
    wrong_cases.write_text(
        json.dumps({"runtime": {}, "cases": [{"id": "other", "score": 1.0}]}),
        encoding="utf-8",
    )
    with pytest.raises(ExternalMetricError, match="unexpected cases"):
        external_metrics._read_worker_result(wrong_cases, ["case"])

    bad_score = tmp_path / "bad-score.json"
    bad_score.write_text(
        json.dumps({"runtime": {}, "cases": [{"id": "case", "score": "high"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ExternalMetricError, match="non-numeric"):
        external_metrics._read_worker_result(bad_score, ["case"])

    bad_score.write_text(
        json.dumps({"runtime": {}, "cases": [{"id": "case", "score": float("nan")}]}),
        encoding="utf-8",
    )
    with pytest.raises(ExternalMetricError, match="non-numeric"):
        external_metrics._read_worker_result(bad_score, ["case"])

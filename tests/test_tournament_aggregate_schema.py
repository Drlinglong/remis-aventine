from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.validation import DocumentValidationError, validate_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_AGGREGATE = (
    PROJECT_ROOT / "examples" / "aggregates" / "remis-tournament.aggregate.example.json"
)
SCHEMA_NAME = "tournament-aggregate.schema.json"


def _write_variant(tmp_path: Path, mutate) -> Path:
    document = json.loads(EXAMPLE_AGGREGATE.read_text(encoding="utf-8"))
    mutate(document)
    path = tmp_path / "aggregate.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_example_tournament_aggregate_matches_schema() -> None:
    document = validate_document(EXAMPLE_AGGREGATE, SCHEMA_NAME)

    assert document["score_version"] == "tournament-score-v0.1"
    assert document["benchmark_pack"]["sha256"]
    assert document["recipe"]["sha256"]
    assert document["recipe"]["inference"]["reasoning"] == {
        "mode": "disabled",
        "display_label": "none",
        "effort": None,
    }
    assert document["overall"]["sample_count"] == 7
    assert document["overall"]["coverage"] == 1
    assert document["regional_scores"]["european"]["language_scores"]["fr"]["score"] == 87


def test_future_namespaced_extension_is_explicitly_allowed(tmp_path: Path) -> None:
    path = _write_variant(
        tmp_path,
        lambda document: document.update({"extensions": {"x-lab": {"run": 1}}}),
    )

    validate_document(path, SCHEMA_NAME)


def test_missing_score_version_is_rejected(tmp_path: Path) -> None:
    path = _write_variant(tmp_path, lambda document: document.pop("score_version"))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("score_version" in issue for issue in exc_info.value.issues)


def test_recipe_must_publish_reasoning_configuration(tmp_path: Path) -> None:
    path = _write_variant(
        tmp_path,
        lambda document: document["recipe"].pop("inference"),
    )

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("inference" in issue for issue in exc_info.value.issues)


def test_ungraded_reasoning_uses_label_without_fake_effort(tmp_path: Path) -> None:
    def enable_ungraded_reasoning(document: dict) -> None:
        document["recipe"]["inference"]["reasoning"] = {
            "mode": "enabled",
            "display_label": "reasoning",
            "effort": None,
        }

    validate_document(_write_variant(tmp_path, enable_ungraded_reasoning), SCHEMA_NAME)


def test_invalid_benchmark_hash_is_rejected(tmp_path: Path) -> None:
    path = _write_variant(
        tmp_path,
        lambda document: document["benchmark_pack"].update({"sha256": "not-a-sha256"}),
    )

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("sha256" in issue for issue in exc_info.value.issues)


def test_coverage_above_one_is_rejected(tmp_path: Path) -> None:
    path = _write_variant(tmp_path, lambda document: document["overall"].update({"coverage": 1.01}))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("coverage" in issue for issue in exc_info.value.issues)


def test_unmeasured_scores_signals_and_telemetry_can_be_explicitly_null(
    tmp_path: Path,
) -> None:
    def make_unmeasured(document: dict) -> None:
        document["components"]["style_voice"] = {
            "score": None,
            "sample_count": 0,
            "decision_count": 0,
            "coverage": 0,
            "status": "insufficient_data",
        }
        document["regional_scores"]["european"] = {
            "score": None,
            "sample_count": 0,
            "decision_count": 0,
            "coverage": 0,
            "status": "insufficient_data",
            "language_scores": {},
        }
        document["remis_workflow_signals"]["cross_batch_drift"] = {
            "value": None,
            "sample_count": 0,
            "decision_count": 0,
            "coverage": 0,
            "status": "insufficient_data",
        }
        document["telemetry"].update(
            {
                "elapsed_seconds": None,
                "ttft_ms": {"status": "insufficient_data", "p50": None, "p95": None},
                "latency_ms": None,
                "throughput_tokens_per_second": None,
                "tokens": None,
                "cost": None,
                "peak_vram_mb": None,
                "peak_ram_mb": None,
            }
        )

    path = _write_variant(tmp_path, make_unmeasured)

    validate_document(path, SCHEMA_NAME)


def test_complete_score_cannot_be_null(tmp_path: Path) -> None:
    path = _write_variant(tmp_path, lambda document: document["overall"].update({"score": None}))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("score" in issue for issue in exc_info.value.issues)


def test_cost_requires_provenance(tmp_path: Path) -> None:
    path = _write_variant(tmp_path, lambda document: document["telemetry"]["cost"].pop("source"))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert exc_info.value.issues


@pytest.mark.parametrize("missing_field", ["sample_count", "coverage"])
def test_overall_score_requires_sample_and_coverage_metadata(
    tmp_path: Path, missing_field: str
) -> None:
    path = _write_variant(tmp_path, lambda document: document["overall"].pop(missing_field))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any(missing_field in issue for issue in exc_info.value.issues)


def test_unknown_top_level_field_is_rejected(tmp_path: Path) -> None:
    path = _write_variant(tmp_path, lambda document: document.update({"manual_score": 99}))

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, SCHEMA_NAME)

    assert any("manual_score" in issue for issue in exc_info.value.issues)

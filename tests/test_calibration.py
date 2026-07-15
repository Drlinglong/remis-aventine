from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.calibration import (
    CalibrationFixtureError,
    load_calibration_fixture,
    summarize_calibration_fixture,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAKE_MQM = PROJECT_ROOT / "examples" / "calibration" / "fake-mqm-v1.json"
FAKE_ACES = PROJECT_ROOT / "examples" / "calibration" / "fake-aces-v1.json"


def test_fake_mqm_exercises_recall_false_good_and_parse_failure() -> None:
    summary = summarize_calibration_fixture(FAKE_MQM)

    assert summary["case_count"] == 5
    assert summary["valid_judge_count"] == 4
    assert summary["json_parse_failure_count"] == 1
    assert summary["schema_failure_count"] == 0
    assert summary["verdict_accuracy"] == 0.6
    assert summary["major_error_recall"] == 0.5
    assert summary["major_false_negative_rate"] == 0.5
    assert summary["critical_error_recall"] == 1.0
    assert summary["false_good_rate"] == 0.25
    assert summary["bad_candidate_detection_accuracy"] is None
    assert summary["source_evidence_coverage"] == 0.5
    assert summary["category_confusion_counts"]["style"] == {"none": 1}


def test_fake_aces_exercises_pairwise_metrics_and_schema_failure() -> None:
    summary = summarize_calibration_fixture(FAKE_ACES)

    assert summary["case_count"] == 4
    assert summary["valid_judge_rate"] == 0.75
    assert summary["schema_failure_count"] == 1
    assert summary["pairwise_accuracy"] == 0.5
    assert summary["bad_candidate_detection_accuracy"] == 0.333333
    assert summary["major_false_negative_rate"] == 0.333333
    assert summary["single_verdict_accuracy"] is None
    assert summary["low_confidence_rate"] == 0.333333
    assert summary["phenomenon_accuracy_by_type"]["role_swap"]["accuracy"] == 0.0


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "must be a JSON object"),
        ({"schema_version": 2, "id": "x", "suite": "x", "cases": []}, "must be 1"),
        ({"schema_version": 1, "id": "", "suite": "x", "cases": []}, "non-empty id"),
        ({"schema_version": 1, "id": "x", "suite": "", "cases": []}, "non-empty suite"),
        ({"schema_version": 1, "id": "x", "suite": "x", "cases": {}}, "must be an array"),
    ],
)
def test_calibration_envelope_rejects_invalid_shapes(tmp_path, payload, message) -> None:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CalibrationFixtureError, match=message):
        load_calibration_fixture(path)


def test_calibration_loader_reports_invalid_json(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(CalibrationFixtureError, match="line 1, column 2"):
        load_calibration_fixture(path)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("not-an-object", "must be an object"),
        ({"id": "", "gold": {}}, "non-empty id"),
        ({"id": "case", "gold": None}, "requires a gold object"),
        ({"id": "case", "gold": {"mode": "other"}}, "invalid gold mode"),
        (
            {"id": "case", "gold": {"mode": "single", "max_severity": "fatal"}},
            "invalid gold severity",
        ),
    ],
)
def test_calibration_cases_reject_invalid_contracts(tmp_path, case, message) -> None:
    path = tmp_path / "fixture.json"
    path.write_text(
        json.dumps({"schema_version": 1, "id": "fixture", "suite": "fake", "cases": [case]}),
        encoding="utf-8",
    )

    with pytest.raises(CalibrationFixtureError, match=message):
        summarize_calibration_fixture(path)


def test_case_id_mismatch_is_counted_as_schema_failure(tmp_path) -> None:
    fixture = load_calibration_fixture(FAKE_MQM)
    fixture["cases"] = [fixture["cases"][0]]
    fixture["cases"][0]["judge_output"]["case_id"] = "wrong-id"
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    summary = summarize_calibration_fixture(path)

    assert summary["schema_failure_count"] == 1
    assert "expected 'mqm-clean'" in summary["failures"][0]["issues"][0]

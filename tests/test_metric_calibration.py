from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.metric_calibration import (
    MetricCalibrationError,
    _ranking_summary,
    build_metric_pack_from_calibration,
    summarize_metric_calibration,
    write_metric_calibration_report,
)
from remis_aventine.validation import validate_document


def _source_pack() -> dict:
    return {
        "schema_version": 1,
        "id": "source-v1",
        "suite": "calibration",
        "cases": [
            {
                "id": "single",
                "origin_suite": "mqm",
                "partition": "calibration",
                "input": {
                    "language_pair": "en-de",
                    "source": "Hello",
                    "candidate": "Hallo",
                    "reference": "Hallo",
                },
                "gold": {
                    "mode": "single",
                    "verdict": "pass",
                    "max_severity": "none",
                    "primary_category": "none",
                    "phenomenon": "no-error",
                },
            },
            {
                "id": "pair",
                "origin_suite": "aces",
                "input": {
                    "language_pair": "fr-ru",
                    "source": "source",
                    "candidate_a": "good",
                    "candidate_b": "bad",
                    "reference": "reference",
                },
                "gold": {
                    "mode": "pairwise",
                    "verdict": "candidate_a",
                    "max_severity": "major",
                    "primary_category": "accuracy",
                    "phenomenon": "omission",
                },
            },
            {
                "id": "no-reference",
                "input": {"source": "x", "candidate": "y"},
                "gold": {"mode": "single"},
            },
        ],
    }


def _write_source(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "source.json"
    path.write_text(json.dumps(payload or _source_pack()), encoding="utf-8")
    return path


def _result(pack: dict, *, direction: str = "higher_is_better") -> dict:
    scores = {"single::candidate": 0.5, "pair::candidate_a": 0.9, "pair::candidate_b": 0.2}
    return {
        "schema_version": 1,
        "pack_id": pack["id"],
        "metric": {
            "name": "xcomet",
            "model_id": "Unbabel/XCOMET-XL",
            "model_sha256": "a" * 64,
            "mode": "reference",
            "direction": direction,
        },
        "runtime": {"python": "3.11", "packages": {}, "device": "test"},
        "started_at": "2026-07-15T00:00:00Z",
        "finished_at": "2026-07-15T00:00:01Z",
        "cases": [{"id": case["id"], "score": scores[case["id"]]} for case in pack["cases"]],
        "summary": {
            "case_count": 3,
            "mean_score": sum(scores.values()) / 3,
            "minimum_score": 0.2,
            "maximum_score": 0.9,
        },
    }


def test_build_metric_pack_flattens_single_and_pairwise_cases(tmp_path) -> None:
    output = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), output)

    assert [case["id"] for case in pack["cases"]] == [
        "single::candidate",
        "pair::candidate_a",
        "pair::candidate_b",
    ]
    assert pack["adapter"]["selected_source_case_count"] == 2
    assert pack["adapter"]["skipped_case_counts"] == {"missing_reference": 1}
    assert pack["cases"][1]["metadata"]["gold_verdict"] == "candidate_a"
    validate_document(output, "metric-pack.schema.json")


def test_build_metric_pack_rejects_source_without_eligible_cases(tmp_path) -> None:
    source = _source_pack()
    source["cases"] = [source["cases"][2]]
    with pytest.raises(MetricCalibrationError, match="No complete"):
        build_metric_pack_from_calibration(
            _write_source(tmp_path, source), tmp_path / "metric-pack.json"
        )


def test_build_metric_pack_rejects_duplicate_eligible_ids(tmp_path) -> None:
    source = _source_pack()
    source["cases"].insert(1, dict(source["cases"][0]))
    with pytest.raises(MetricCalibrationError, match="Duplicate eligible"):
        build_metric_pack_from_calibration(
            _write_source(tmp_path, source), tmp_path / "metric-pack.json"
        )


def test_metric_report_summarizes_single_and_pairwise_gold(tmp_path) -> None:
    pack_path = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), pack_path)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(_result(pack)), encoding="utf-8")

    report = summarize_metric_calibration(pack_path, result_path)

    assert report["single"]["scores_by_gold_verdict"]["pass"]["mean"] == 0.5
    assert report["pairwise"]["accuracy"] == 1.0
    assert report["pairwise"]["by_language_pair"]["fr-ru"]["correct_count"] == 1
    assert report["pairwise"]["cases"][0]["margin"] == pytest.approx(0.7)


def test_lower_is_better_and_equal_scores_change_pairwise_decision(tmp_path) -> None:
    pack_path = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), pack_path)
    result = _result(pack, direction="lower_is_better")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    assert summarize_metric_calibration(pack_path, result_path)["pairwise"]["accuracy"] == 0.0

    for case in result["cases"]:
        if case["id"].startswith("pair::"):
            case["score"] = 0.4
    result_path.write_text(json.dumps(result), encoding="utf-8")
    pairwise = summarize_metric_calibration(pack_path, result_path)["pairwise"]
    assert pairwise["tie_count"] == 1


def test_metric_report_rejects_pack_or_case_mismatch(tmp_path) -> None:
    pack_path = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), pack_path)
    result = _result(pack)
    result_path = tmp_path / "result.json"
    result["pack_id"] = "wrong"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(MetricCalibrationError, match="does not match"):
        summarize_metric_calibration(pack_path, result_path)

    result = _result(pack)
    result["cases"].pop()
    result["summary"]["case_count"] = 2
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(MetricCalibrationError, match="do not match"):
        summarize_metric_calibration(pack_path, result_path)


def test_metric_report_requires_calibration_metadata(tmp_path) -> None:
    pack_path = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), pack_path)
    pack["cases"][0].pop("metadata")
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(_result(pack)), encoding="utf-8")

    with pytest.raises(MetricCalibrationError, match="missing calibration metadata"):
        summarize_metric_calibration(pack_path, result_path)


def test_write_metric_report_creates_json_and_markdown(tmp_path) -> None:
    pack_path = tmp_path / "metric-pack.json"
    pack = build_metric_pack_from_calibration(_write_source(tmp_path), pack_path)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(_result(pack)), encoding="utf-8")
    output_json = tmp_path / "report" / "report.json"
    output_markdown = tmp_path / "report" / "report.md"

    report = write_metric_calibration_report(
        pack_path, result_path, output_json, output_markdown
    )

    assert report["pairwise"]["accuracy"] == 1.0
    assert json.loads(output_json.read_text(encoding="utf-8"))["hypothesis_count"] == 3
    assert "Pairwise gold accuracy: 1.0000" in output_markdown.read_text(encoding="utf-8")


def test_single_ranking_summary_is_threshold_free() -> None:
    rows = [
        ({"gold_severity": "none"}, 0.9),
        ({"gold_severity": "minor"}, 0.7),
        ({"gold_severity": "major"}, 0.7),
        ({"gold_severity": "critical"}, 0.1),
    ]

    severity = _ranking_summary(rows, higher_is_better=True, pass_fail_only=False)
    pass_fail = _ranking_summary(rows, higher_is_better=True, pass_fail_only=True)

    assert severity == {
        "comparison_count": 6,
        "correct_count": 5,
        "tie_count": 1,
        "accuracy": 5 / 6,
    }
    assert pass_fail["comparison_count"] == 3
    assert pass_fail["accuracy"] == 1.0

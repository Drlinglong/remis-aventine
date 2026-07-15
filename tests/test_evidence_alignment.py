from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.evidence_alignment import (
    EvidenceAlignmentError,
    summarize_evidence_alignment,
    write_evidence_alignment_report,
)
from remis_aventine.metric_calibration import build_metric_pack_from_calibration


def _evaluation(case_id: str, mode: str, verdict: str, *, severity: str | None = None) -> dict:
    errors = []
    if severity:
        errors.append(
            {
                "candidate": "candidate" if mode == "single" else "candidate_b",
                "category": "accuracy",
                "severity": severity,
                "explanation": "test error",
            }
        )
    return {
        "schema_version": 1,
        "case_id": case_id,
        "judge": {
            "profile": "test-profile",
            "model": "test-judge",
            "prompt_revision": "test-prompt",
            "calibration_revision": "test-calibration",
        },
        "evaluation": {
            "mode": mode,
            "verdict": verdict,
            "confidence": "high",
            "errors": errors,
            "rationale": "test rationale",
            "limitations": [],
        },
    }


def _artifacts(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    cases = [
        {
            "id": "single-pass",
            "input": {
                "language_pair": "en-de",
                "source": "hello",
                "candidate": "hallo",
                "reference": "hallo",
            },
            "gold": {
                "mode": "single",
                "verdict": "pass",
                "max_severity": "none",
                "phenomenon": "no-error",
            },
        },
        {
            "id": "both-correct",
            "input": {
                "language_pair": "en-de",
                "source": "one",
                "candidate_a": "eins",
                "candidate_b": "zwei",
                "reference": "eins",
            },
            "gold": {
                "mode": "pairwise",
                "verdict": "candidate_a",
                "max_severity": "major",
                "phenomenon": "number",
            },
        },
        {
            "id": "metric-only",
            "input": {
                "language_pair": "en-fr",
                "source": "cat",
                "candidate_a": "chat",
                "candidate_b": "chien",
                "reference": "chat",
            },
            "gold": {
                "mode": "pairwise",
                "verdict": "candidate_a",
                "max_severity": "major",
                "phenomenon": "entity",
            },
        },
        {
            "id": "judge-only",
            "input": {
                "language_pair": "en-es",
                "source": "yes",
                "candidate_a": "si",
                "candidate_b": "no",
                "reference": "si",
            },
            "gold": {
                "mode": "pairwise",
                "verdict": "candidate_a",
                "max_severity": "major",
                "phenomenon": "negation",
            },
        },
        {
            "id": "both-wrong",
            "input": {
                "language_pair": "en-it",
                "source": "red",
                "candidate_a": "rosso",
                "candidate_b": "blu",
                "reference": "rosso",
            },
            "gold": {
                "mode": "pairwise",
                "verdict": "candidate_a",
                "max_severity": "major",
                "phenomenon": "commonsense",
            },
        },
    ]
    calibration = {
        "schema_version": 1,
        "id": "alignment-v1",
        "suite": "test",
        "cases": cases,
    }
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(json.dumps(calibration), encoding="utf-8")

    judged_cases = []
    verdicts = {
        "single-pass": "pass",
        "both-correct": "candidate_a",
        "metric-only": "candidate_b",
        "judge-only": "candidate_a",
        "both-wrong": "candidate_b",
    }
    for case in cases:
        mode = case["gold"]["mode"]
        verdict = verdicts[case["id"]]
        judged = dict(case)
        judged["judge_output"] = _evaluation(case["id"], mode, verdict)
        if mode == "pairwise":
            swapped = "candidate_b" if verdict == "candidate_a" else "candidate_a"
            judged["swap_judge_output"] = _evaluation(case["id"], mode, swapped)
        judged_cases.append(judged)
    judge_path = tmp_path / "judge.json"
    judge_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "alignment-v1.judge",
                "suite": "test",
                "run": {"model": "test-judge", "profile": "test-profile"},
                "cases": judged_cases,
            }
        ),
        encoding="utf-8",
    )

    metric_pack_path = tmp_path / "metric-pack.json"
    metric_pack = build_metric_pack_from_calibration(calibration_path, metric_pack_path)
    score_by_id = {
        "single-pass::candidate": 0.9,
        "both-correct::candidate_a": 0.9,
        "both-correct::candidate_b": 0.1,
        "metric-only::candidate_a": 0.9,
        "metric-only::candidate_b": 0.1,
        "judge-only::candidate_a": 0.1,
        "judge-only::candidate_b": 0.9,
        "both-wrong::candidate_a": 0.1,
        "both-wrong::candidate_b": 0.9,
    }
    metric_result = {
        "schema_version": 1,
        "pack_id": metric_pack["id"],
        "metric": {
            "name": "xcomet",
            "model_id": "test-xcomet",
            "model_sha256": "a" * 64,
            "mode": "reference",
            "direction": "higher_is_better",
        },
        "runtime": {"python": "3.11", "packages": {}, "device": "test"},
        "started_at": "2026-07-15T00:00:00Z",
        "finished_at": "2026-07-15T00:00:01Z",
        "cases": [
            {"id": case["id"], "score": score_by_id[case["id"]]}
            for case in metric_pack["cases"]
        ],
        "summary": {
            "case_count": len(score_by_id),
            "mean_score": sum(score_by_id.values()) / len(score_by_id),
            "minimum_score": 0.1,
            "maximum_score": 0.9,
        },
    }
    metric_result_path = tmp_path / "metric-result.json"
    metric_result_path.write_text(json.dumps(metric_result), encoding="utf-8")
    return calibration_path, judge_path, metric_pack_path, metric_result_path


def test_alignment_separates_complementary_and_shared_failures(tmp_path) -> None:
    calibration, judge, metric_pack, metric_result = _artifacts(tmp_path)

    report = summarize_evidence_alignment(
        calibration, judge, [(metric_pack, metric_result)]
    )

    assert report["judge"]["base_accuracy"] == 0.6
    assert report["judge"]["position_consistency"] == 1.0
    summary = report["metrics"]["xcomet"]
    assert summary["pairwise_accuracy"] == 0.5
    assert summary["both_correct"] == 1
    assert summary["judge_only_correct"] == 1
    assert summary["metric_only_correct"] == 1
    assert summary["both_wrong"] == 1
    assert summary["oracle_union_accuracy"] == 0.75
    assert summary["single_scores_by_judge_outcome"]["judge_correct"]["mean"] == 0.9
    assert len(report["review_queue"]) == 3
    metric_only = next(
        item for item in report["review_queue"] if item["case_id"] == "metric-only"
    )
    assert "judge_gold_mismatch" in metric_only["reasons"]


def test_alignment_marks_position_inconsistency_unresolved(tmp_path) -> None:
    calibration, judge, metric_pack, metric_result = _artifacts(tmp_path)
    payload = json.loads(judge.read_text(encoding="utf-8"))
    case = next(case for case in payload["cases"] if case["id"] == "both-correct")
    case["swap_judge_output"] = _evaluation("both-correct", "pairwise", "candidate_a")
    judge.write_text(json.dumps(payload), encoding="utf-8")

    report = summarize_evidence_alignment(
        calibration, judge, [(metric_pack, metric_result)]
    )

    assert report["judge"]["position_consistency"] == 0.75
    row = next(case for case in report["cases"] if case["case_id"] == "both-correct")
    assert row["judge"]["effective_verdict"] is None
    assert "judge_position_inconsistent" in next(
        item["reasons"] for item in report["review_queue"] if item["case_id"] == "both-correct"
    )


def test_alignment_rejects_mismatched_or_duplicate_evidence(tmp_path) -> None:
    calibration, judge, metric_pack, metric_result = _artifacts(tmp_path)
    payload = json.loads(judge.read_text(encoding="utf-8"))
    payload["cases"].pop()
    judge.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceAlignmentError, match="Judge cases do not match"):
        summarize_evidence_alignment(calibration, judge, [(metric_pack, metric_result)])

    _, judge, metric_pack, metric_result = _artifacts(tmp_path)
    with pytest.raises(EvidenceAlignmentError, match="Duplicate metric"):
        summarize_evidence_alignment(
            calibration,
            judge,
            [(metric_pack, metric_result), (metric_pack, metric_result)],
        )


def test_write_alignment_report(tmp_path) -> None:
    calibration, judge, metric_pack, metric_result = _artifacts(tmp_path)
    output_json = tmp_path / "out" / "alignment.json"
    output_markdown = tmp_path / "out" / "alignment.md"

    report = write_evidence_alignment_report(
        calibration,
        judge,
        [(metric_pack, metric_result)],
        output_json,
        output_markdown,
    )

    assert report["metrics"]["xcomet"]["both_wrong"] == 1
    assert json.loads(output_json.read_text(encoding="utf-8"))["judge"]["case_count"] == 5
    markdown = output_markdown.read_text(encoding="utf-8")
    assert "Oracle union accuracy: 0.75" in markdown
    assert "3 cases require review" in markdown


def test_alignment_requires_metric(tmp_path) -> None:
    calibration, judge, _, _ = _artifacts(tmp_path)
    with pytest.raises(EvidenceAlignmentError, match="At least one metric"):
        summarize_evidence_alignment(calibration, judge, [])

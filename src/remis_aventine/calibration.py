"""Calibration fixture loading and deterministic judge summary metrics."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from remis_aventine.validation import DocumentValidationError, validate_payload

SEVERITY_RANK = {"none": 0, "minor": 1, "major": 2, "critical": 3}


class CalibrationFixtureError(ValueError):
    """Raised when the calibration fixture envelope is malformed."""


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def load_calibration_fixture(path: Path) -> dict[str, Any]:
    """Load the small Aventine calibration envelope used by fake and real samples."""
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalibrationFixtureError(
            f"Invalid calibration JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(fixture, dict):
        raise CalibrationFixtureError("Calibration fixture must be a JSON object.")
    if fixture.get("schema_version") != 1:
        raise CalibrationFixtureError("Calibration fixture schema_version must be 1.")
    if not isinstance(fixture.get("id"), str) or not fixture["id"]:
        raise CalibrationFixtureError("Calibration fixture requires a non-empty id.")
    if not isinstance(fixture.get("suite"), str) or not fixture["suite"]:
        raise CalibrationFixtureError("Calibration fixture requires a non-empty suite.")
    if not isinstance(fixture.get("cases"), list):
        raise CalibrationFixtureError("Calibration fixture cases must be an array.")
    return fixture


def _parse_judge_output(
    case_id: str, value: Any
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            return None, {
                "case_id": case_id,
                "kind": "json_parse_failure",
                "detail": f"line {exc.lineno}, column {exc.colno}: {exc.msg}",
            }

    try:
        validated = validate_payload(value, "judge-result.schema.json")
    except DocumentValidationError as exc:
        return None, {
            "case_id": case_id,
            "kind": "schema_failure",
            "issues": list(exc.issues),
        }

    if validated["case_id"] != case_id:
        return None, {
            "case_id": case_id,
            "kind": "schema_failure",
            "issues": [f"$.case_id: expected {case_id!r}, received {validated['case_id']!r}"],
        }
    return validated, None


def _predicted_severity(evaluation: dict[str, Any]) -> str:
    errors = evaluation["errors"]
    if not errors:
        return "none"
    return max(
        (error["severity"] for error in errors),
        key=lambda severity: SEVERITY_RANK[severity],
    )


def _predicted_category(evaluation: dict[str, Any]) -> str:
    errors = evaluation["errors"]
    if not errors:
        return "none"
    most_severe = max(errors, key=lambda error: SEVERITY_RANK[error["severity"]])
    return str(most_severe["category"])


def summarize_calibration_fixture(path: Path) -> dict[str, Any]:
    """Summarize schema reliability and gold-label agreement for one fixture."""
    fixture = load_calibration_fixture(path)
    return _summarize_calibration(fixture, include_partitions=True)


def _summarize_calibration(fixture: dict[str, Any], *, include_partitions: bool) -> dict[str, Any]:
    cases = fixture["cases"]
    valid_count = 0
    verdict_correct = 0
    mode_totals: Counter[str] = Counter()
    mode_correct: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    predicted_error_severity_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    category_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    severity_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    phenomenon_totals: Counter[str] = Counter()
    phenomenon_correct: Counter[str] = Counter()
    major_total = 0
    major_detected = 0
    critical_total = 0
    critical_detected = 0
    bad_candidate_total = 0
    bad_candidate_correct = 0
    false_good_total = 0
    false_good_count = 0
    evidence_error_count = 0
    evidence_backed_error_count = 0
    swap_total = 0
    swap_valid = 0
    swap_correct = 0
    position_consistent = 0

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise CalibrationFixtureError(f"Case at index {index} must be an object.")
        case_id = case.get("id")
        gold = case.get("gold")
        if not isinstance(case_id, str) or not case_id:
            raise CalibrationFixtureError(f"Case at index {index} requires a non-empty id.")
        if not isinstance(gold, dict):
            raise CalibrationFixtureError(f"Case {case_id!r} requires a gold object.")
        expected_verdict = gold.get("verdict")
        mode = gold.get("mode")
        gold_severity = gold.get("max_severity", "none")
        gold_category = gold.get("primary_category", "none")
        phenomenon = gold.get("phenomenon", "unspecified")
        if mode not in {"single", "pairwise"}:
            raise CalibrationFixtureError(f"Case {case_id!r} has an invalid gold mode.")
        if gold_severity not in SEVERITY_RANK:
            raise CalibrationFixtureError(f"Case {case_id!r} has an invalid gold severity.")

        mode_totals[mode] += 1
        phenomenon_totals[str(phenomenon)] += 1
        if SEVERITY_RANK[gold_severity] >= SEVERITY_RANK["major"]:
            major_total += 1
        if gold_severity == "critical":
            critical_total += 1
        if mode == "single" and expected_verdict == "fail":
            false_good_total += 1
        if mode == "pairwise" and expected_verdict in {"candidate_a", "candidate_b"}:
            bad_candidate_total += 1

        output, failure = _parse_judge_output(case_id, case.get("judge_output"))
        if failure is not None:
            failure_counts[failure["kind"]] += 1
            failures.append(failure)
            category_confusion[str(gold_category)]["invalid_output"] += 1
            severity_confusion[str(gold_severity)]["invalid_output"] += 1
            continue

        valid_count += 1
        evaluation = output["evaluation"]
        predicted_verdict = evaluation["verdict"]
        predicted_severity = _predicted_severity(evaluation)
        predicted_category = _predicted_category(evaluation)
        confidence_counts[evaluation["confidence"]] += 1
        predicted_error_severity_counts[predicted_severity] += 1
        category_confusion[str(gold_category)][predicted_category] += 1
        severity_confusion[str(gold_severity)][predicted_severity] += 1
        for error in evaluation["errors"]:
            evidence_error_count += 1
            if error.get("source_excerpt"):
                evidence_backed_error_count += 1

        correct = evaluation["mode"] == mode and predicted_verdict == expected_verdict
        if correct:
            verdict_correct += 1
            mode_correct[mode] += 1
            phenomenon_correct[str(phenomenon)] += 1
            if mode == "pairwise" and expected_verdict in {"candidate_a", "candidate_b"}:
                bad_candidate_correct += 1

        if (
            SEVERITY_RANK[gold_severity] >= SEVERITY_RANK["major"]
            and SEVERITY_RANK[predicted_severity] >= SEVERITY_RANK["major"]
        ):
            major_detected += 1
        if gold_severity == "critical" and predicted_severity == "critical":
            critical_detected += 1
        if mode == "single" and expected_verdict == "fail" and predicted_verdict == "pass":
            false_good_count += 1

        if "swap_judge_output" in case:
            swap_total += 1
            swap_output, _swap_failure = _parse_judge_output(case_id, case.get("swap_judge_output"))
            if swap_output is not None:
                swap_valid += 1
                swap_verdict = swap_output["evaluation"]["verdict"]
                inverted_expected = {
                    "candidate_a": "candidate_b",
                    "candidate_b": "candidate_a",
                }.get(expected_verdict, expected_verdict)
                inverted_prediction = {
                    "candidate_a": "candidate_b",
                    "candidate_b": "candidate_a",
                }.get(predicted_verdict, predicted_verdict)
                if swap_verdict == inverted_expected:
                    swap_correct += 1
                if swap_verdict == inverted_prediction:
                    position_consistent += 1

    phenomenon_metrics = {
        phenomenon: {
            "case_count": count,
            "correct_count": phenomenon_correct[phenomenon],
            "accuracy": _rate(phenomenon_correct[phenomenon], count),
        }
        for phenomenon, count in sorted(phenomenon_totals.items())
    }

    summary = {
        "schema_version": 1,
        "fixture_id": fixture["id"],
        "suite": fixture["suite"],
        "case_count": len(cases),
        "valid_judge_count": valid_count,
        "valid_judge_rate": _rate(valid_count, len(cases)),
        "json_parse_failure_count": failure_counts["json_parse_failure"],
        "schema_failure_count": failure_counts["schema_failure"],
        "verdict_accuracy": _rate(verdict_correct, len(cases)),
        "single_verdict_accuracy": _rate(mode_correct["single"], mode_totals["single"]),
        "pairwise_accuracy": _rate(mode_correct["pairwise"], mode_totals["pairwise"]),
        "major_error_recall": _rate(major_detected, major_total),
        "major_false_negative_rate": _rate(major_total - major_detected, major_total),
        "critical_error_recall": _rate(critical_detected, critical_total),
        "bad_candidate_detection_accuracy": _rate(bad_candidate_correct, bad_candidate_total),
        "false_good_rate": _rate(false_good_count, false_good_total),
        "low_confidence_rate": _rate(confidence_counts["low"], valid_count),
        "source_evidence_coverage": _rate(evidence_backed_error_count, evidence_error_count),
        "swap_valid_rate": _rate(swap_valid, swap_total),
        "swap_accuracy": _rate(swap_correct, swap_total),
        "position_consistency_rate": _rate(position_consistent, swap_valid),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "predicted_error_severity_counts": dict(sorted(predicted_error_severity_counts.items())),
        "phenomenon_accuracy_by_type": phenomenon_metrics,
        "category_confusion_counts": {
            gold: dict(sorted(predicted.items()))
            for gold, predicted in sorted(category_confusion.items())
        },
        "severity_confusion_counts": {
            gold: dict(sorted(predicted.items()))
            for gold, predicted in sorted(severity_confusion.items())
        },
        "failures": failures,
    }
    if include_partitions:
        partitions = sorted(
            {case.get("partition") for case in cases if isinstance(case.get("partition"), str)}
        )
        if partitions:
            summary["partition_metrics"] = {
                partition: _summarize_calibration(
                    {
                        **fixture,
                        "cases": [case for case in cases if case.get("partition") == partition],
                    },
                    include_partitions=False,
                )
                for partition in partitions
            }
    return summary

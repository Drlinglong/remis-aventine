"""Align human gold, structured judges, and automatic metric evidence."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from remis_aventine.calibration import SEVERITY_RANK, load_calibration_fixture
from remis_aventine.validation import DocumentValidationError, validate_document, validate_payload


class EvidenceAlignmentError(ValueError):
    """Raised when evidence artifacts cannot be joined without guessing."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceAlignmentError(f"Invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceAlignmentError(f"Expected a JSON object in {path}.")
    return value


def _judge_output(case_id: str, value: Any) -> tuple[dict[str, Any] | None, str | None]:
    try:
        output = validate_payload(value, "judge-result.schema.json")
    except DocumentValidationError:
        return None, "invalid"
    if output["case_id"] != case_id:
        return None, "case_id_mismatch"
    return output, None


def _swap_verdict(verdict: str) -> str:
    return {
        "candidate_a": "candidate_b",
        "candidate_b": "candidate_a",
    }.get(verdict, verdict)


def _severity(evaluation: dict[str, Any]) -> str:
    if not evaluation["errors"]:
        return "none"
    return max(
        (error["severity"] for error in evaluation["errors"]),
        key=SEVERITY_RANK.__getitem__,
    )


def _metric_rows(pack_path: Path, result_path: Path) -> tuple[str, dict[str, Any], dict[str, Any]]:
    pack = validate_document(pack_path, "metric-pack.schema.json")
    result = validate_document(result_path, "metric-result.schema.json")
    if result["pack_id"] != pack["id"]:
        raise EvidenceAlignmentError(
            f"Metric result {result['pack_id']!r} does not match pack {pack['id']!r}."
        )
    pack_cases = {case["id"]: case for case in pack["cases"]}
    result_cases = {case["id"]: case for case in result["cases"]}
    if len(result_cases) != len(result["cases"]) or set(result_cases) != set(pack_cases):
        raise EvidenceAlignmentError("Metric result cases do not match its pack exactly.")
    name = result["metric"]["name"]
    rows: dict[str, dict[str, Any]] = defaultdict(dict)
    for hypothesis_id, metric_case in result_cases.items():
        metadata = pack_cases[hypothesis_id].get("metadata") or {}
        source_case_id = metadata.get("source_case_id")
        role = metadata.get("candidate_role")
        if not isinstance(source_case_id, str) or role not in {
            "candidate",
            "candidate_a",
            "candidate_b",
        }:
            raise EvidenceAlignmentError("Metric pack is missing calibration join metadata.")
        rows[source_case_id][role] = float(metric_case["score"])
    return name, result["metric"], dict(rows)


def summarize_evidence_alignment(
    calibration_path: Path,
    judge_path: Path,
    metrics: list[tuple[Path, Path]],
) -> dict[str, Any]:
    """Join independent evidence without turning metric scores into invented labels."""
    if not metrics:
        raise EvidenceAlignmentError("At least one metric pack/result pair is required.")
    calibration = load_calibration_fixture(calibration_path)
    judge = _load_json(judge_path)
    source_cases = {case["id"]: case for case in calibration["cases"]}
    judge_cases = {case.get("id"): case for case in judge.get("cases", [])}
    if len(source_cases) != len(calibration["cases"]):
        raise EvidenceAlignmentError("Calibration case ids must be unique.")
    if set(judge_cases) != set(source_cases):
        raise EvidenceAlignmentError("Judge cases do not match the calibration pack exactly.")

    metric_inputs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for pack_path, result_path in metrics:
        name, metadata, rows = _metric_rows(pack_path, result_path)
        if name in metric_inputs:
            raise EvidenceAlignmentError(f"Duplicate metric name: {name}")
        if set(rows) != set(source_cases):
            raise EvidenceAlignmentError(f"Metric {name} cases do not match calibration cases.")
        metric_inputs[name] = (metadata, rows)

    judge_counts: Counter[str] = Counter()
    metric_counts: dict[str, Counter[str]] = {name: Counter() for name in metric_inputs}
    single_scores: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list) for name in metric_inputs
    }
    cases: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []

    for case_id, source_case in source_cases.items():
        gold = source_case["gold"]
        mode = gold["mode"]
        gold_verdict = gold["verdict"]
        judged_case = judge_cases[case_id]
        base, base_failure = _judge_output(case_id, judged_case.get("judge_output"))
        swap = None
        swap_failure = None
        if "swap_judge_output" in judged_case:
            swap, swap_failure = _judge_output(case_id, judged_case["swap_judge_output"])

        base_verdict = base["evaluation"]["verdict"] if base else None
        normalized_swap = _swap_verdict(swap["evaluation"]["verdict"]) if swap else None
        position_consistent = normalized_swap == base_verdict if swap else None
        effective_verdict = base_verdict
        if swap is not None and not position_consistent:
            effective_verdict = None
        judge_correct = effective_verdict == gold_verdict if effective_verdict else False
        judge_counts["case_count"] += 1
        judge_counts["valid_base"] += base is not None
        judge_counts["base_correct"] += base_verdict == gold_verdict
        judge_counts["swap_present"] += swap is not None or swap_failure is not None
        judge_counts["position_consistent"] += position_consistent is True
        judge_counts["effective_correct"] += judge_correct

        row: dict[str, Any] = {
            "case_id": case_id,
            "mode": mode,
            "language_pair": source_case.get("input", {}).get("language_pair", "unknown"),
            "phenomenon": gold.get("phenomenon", "unknown"),
            "gold_verdict": gold_verdict,
            "gold_severity": gold.get("max_severity", "unknown"),
            "judge": {
                "base_verdict": base_verdict,
                "normalized_swap_verdict": normalized_swap,
                "effective_verdict": effective_verdict,
                "position_consistent": position_consistent,
                "correct": judge_correct,
                "failure": base_failure or swap_failure,
                "confidence": base["evaluation"]["confidence"] if base else None,
                "predicted_severity": _severity(base["evaluation"]) if base else None,
            },
            "metrics": {},
        }

        review_reasons: list[str] = []
        if base is None:
            review_reasons.append("judge_invalid")
        elif position_consistent is False:
            review_reasons.append("judge_position_inconsistent")
        if not judge_correct:
            review_reasons.append("judge_gold_mismatch")

        for name, (metric_metadata, metric_rows) in metric_inputs.items():
            scores = metric_rows[case_id]
            direction = metric_metadata["direction"]
            metric_verdict = None
            metric_correct = None
            if mode == "pairwise":
                score_a = scores["candidate_a"]
                score_b = scores["candidate_b"]
                if score_a == score_b:
                    metric_verdict = "tie"
                elif (score_a > score_b) == (direction == "higher_is_better"):
                    metric_verdict = "candidate_a"
                else:
                    metric_verdict = "candidate_b"
                metric_correct = metric_verdict == gold_verdict
                metric_counts[name]["pairwise_count"] += 1
                metric_counts[name]["correct"] += metric_correct
                if effective_verdict is not None:
                    category = (
                        "both_correct"
                        if judge_correct and metric_correct
                        else "judge_only_correct"
                        if judge_correct
                        else "metric_only_correct"
                        if metric_correct
                        else "both_wrong"
                    )
                    metric_counts[name][category] += 1
                    if effective_verdict != metric_verdict:
                        metric_counts[name]["prediction_disagreement"] += 1
                        review_reasons.append(f"judge_{name}_disagreement")
                    if category == "both_wrong":
                        review_reasons.append(f"judge_{name}_both_wrong")
            else:
                score = scores["candidate"]
                single_scores[name]["judge_correct" if judge_correct else "judge_wrong"].append(
                    score
                )

            row["metrics"][name] = {
                "direction": direction,
                "scores": scores,
                "verdict": metric_verdict,
                "correct": metric_correct,
            }
        cases.append(row)
        if review_reasons:
            review_queue.append({"case_id": case_id, "reasons": sorted(set(review_reasons))})

    metric_summaries = {}
    for name, (metadata, _) in metric_inputs.items():
        counts = metric_counts[name]
        pairwise_count = counts["pairwise_count"]
        aligned = sum(
            counts[key]
            for key in ("both_correct", "judge_only_correct", "metric_only_correct", "both_wrong")
        )
        score_groups = {
            group: {
                "count": len(values),
                "mean": sum(values) / len(values) if values else None,
            }
            for group, values in single_scores[name].items()
        }
        metric_summaries[name] = {
            "model_id": metadata["model_id"],
            "direction": metadata["direction"],
            "pairwise_count": pairwise_count,
            "pairwise_accuracy": counts["correct"] / pairwise_count if pairwise_count else None,
            "aligned_pairwise_count": aligned,
            "both_correct": counts["both_correct"],
            "judge_only_correct": counts["judge_only_correct"],
            "metric_only_correct": counts["metric_only_correct"],
            "both_wrong": counts["both_wrong"],
            "prediction_disagreement": counts["prediction_disagreement"],
            "oracle_union_accuracy": (
                (
                    counts["both_correct"]
                    + counts["judge_only_correct"]
                    + counts["metric_only_correct"]
                )
                / aligned
                if aligned
                else None
            ),
            "single_scores_by_judge_outcome": score_groups,
        }

    total = judge_counts["case_count"]
    swap_total = judge_counts["swap_present"]
    return {
        "schema_version": 1,
        "calibration_pack_id": calibration["id"],
        "judge": {
            "model": judge.get("run", {}).get("model", "unknown"),
            "profile": judge.get("run", {}).get("profile", "unknown"),
            "case_count": total,
            "valid_base_count": judge_counts["valid_base"],
            "base_accuracy": judge_counts["base_correct"] / total if total else None,
            "swap_case_count": swap_total,
            "position_consistency": (
                judge_counts["position_consistent"] / swap_total if swap_total else None
            ),
            "effective_accuracy": judge_counts["effective_correct"] / total if total else None,
        },
        "metrics": metric_summaries,
        "review_queue": review_queue,
        "cases": cases,
    }


def write_evidence_alignment_report(
    calibration_path: Path,
    judge_path: Path,
    metrics: list[tuple[Path, Path]],
    output_json: Path,
    output_markdown: Path,
) -> dict[str, Any]:
    """Write a detailed JSON join and a compact human-readable report."""
    report = summarize_evidence_alignment(calibration_path, judge_path, metrics)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    judge = report["judge"]
    lines = [
        "# Gold / judge / metric evidence alignment",
        "",
        f"- Calibration pack: `{report['calibration_pack_id']}`",
        f"- Judge: `{judge['model']}` / `{judge['profile']}`",
        f"- Cases: {judge['case_count']}",
        f"- Judge base accuracy: {judge['base_accuracy']:.4f}",
        f"- Judge effective accuracy: {judge['effective_accuracy']:.4f}",
    ]
    if judge["position_consistency"] is not None:
        lines.append(f"- Judge position consistency: {judge['position_consistency']:.4f}")
    lines.extend(["", "## Pairwise alignment", ""])
    for name, summary in report["metrics"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Metric accuracy: {summary['pairwise_accuracy']}",
                f"- Both correct: {summary['both_correct']}",
                f"- Judge only correct: {summary['judge_only_correct']}",
                f"- Metric only correct: {summary['metric_only_correct']}",
                f"- Both wrong: {summary['both_wrong']}",
                f"- Prediction disagreements: {summary['prediction_disagreement']}",
                f"- Oracle union accuracy: {summary['oracle_union_accuracy']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Review queue",
            "",
            f"{len(report['review_queue'])} cases require review because evidence was invalid, "
            "position-inconsistent, disagreeing, or jointly wrong.",
        ]
    )
    output_markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

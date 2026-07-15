"""Adapt calibration packs to automatic-metric inputs and summarize their results."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from remis_aventine.calibration import load_calibration_fixture
from remis_aventine.validation import validate_document, validate_payload

ADAPTER_REVISION = "calibration-metric-v1"
SEVERITY_RANK = {"none": 0, "minor": 1, "major": 2, "critical": 3}


class MetricCalibrationError(ValueError):
    """Raised when calibration evidence cannot be adapted or compared safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _case_metadata(case: dict[str, Any], role: str) -> dict[str, Any]:
    gold = case.get("gold", {})
    case_input = case.get("input", {})
    return {
        "source_case_id": case["id"],
        "candidate_role": role,
        "language_pair": case_input.get("language_pair", "unknown"),
        "origin_suite": case.get("origin_suite", "unknown"),
        "partition": case.get("partition", "unspecified"),
        "gold_mode": gold.get("mode", "unknown"),
        "gold_verdict": gold.get("verdict", "unknown"),
        "gold_severity": gold.get("max_severity", "unknown"),
        "gold_category": gold.get("primary_category", "unknown"),
        "phenomenon": gold.get("phenomenon", "unknown"),
    }


def build_metric_pack_from_calibration(
    input_path: Path, output_path: Path
) -> dict[str, Any]:
    """Flatten reference-bearing single and pairwise cases into metric hypotheses."""
    source = load_calibration_fixture(input_path)
    emitted: list[dict[str, Any]] = []
    skipped: dict[str, int] = defaultdict(int)
    selected_source_ids: set[str] = set()

    for case in source["cases"]:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("id"), str)
            or not case["id"]
            or not isinstance(case.get("input"), dict)
            or not isinstance(case.get("gold"), dict)
        ):
            skipped["malformed_case"] += 1
            continue
        if case["id"] in selected_source_ids:
            raise MetricCalibrationError(f"Duplicate eligible source case id: {case['id']}")
        case_input = case["input"]
        source_text = case_input.get("source")
        reference = case_input.get("reference")
        if not isinstance(source_text, str) or not source_text:
            skipped["missing_source"] += 1
            continue
        if not isinstance(reference, str) or not reference:
            skipped["missing_reference"] += 1
            continue

        mode = case.get("gold", {}).get("mode")
        roles = ("candidate",) if mode == "single" else ("candidate_a", "candidate_b")
        if mode not in {"single", "pairwise"}:
            skipped["unsupported_mode"] += 1
            continue
        hypotheses = []
        for role in roles:
            hypothesis = case_input.get(role)
            if not isinstance(hypothesis, str) or not hypothesis:
                hypotheses = []
                break
            hypotheses.append((role, hypothesis))
        if not hypotheses:
            skipped["missing_hypothesis"] += 1
            continue

        selected_source_ids.add(case["id"])
        emitted.extend(
            {
                "id": f"{case['id']}::{role}",
                "source": source_text,
                "hypothesis": hypothesis,
                "reference": reference,
                "metadata": _case_metadata(case, role),
            }
            for role, hypothesis in hypotheses
        )

    if not emitted:
        raise MetricCalibrationError("No complete reference-bearing cases were found.")
    pack = {
        "schema_version": 1,
        "id": f"metric.{source['id']}.{ADAPTER_REVISION}",
        "suite": source["suite"],
        "description": "Reference-bearing hypotheses adapted for automatic metric calibration.",
        "adapter": {
            "name": "calibration-to-metric",
            "revision": ADAPTER_REVISION,
            "source_pack_id": source["id"],
            "source_sha256": _sha256(input_path),
            "source_case_count": len(source["cases"]),
            "selected_source_case_count": len(selected_source_ids),
            "emitted_hypothesis_count": len(emitted),
            "skipped_case_counts": dict(sorted(skipped.items())),
        },
        "cases": emitted,
    }
    validated = validate_payload(pack, "metric-pack.schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return validated


def _score_summary(scores: list[float]) -> dict[str, Any]:
    return {
        "count": len(scores),
        "mean": sum(scores) / len(scores),
        "minimum": min(scores),
        "maximum": max(scores),
    }


def _group_summaries(
    rows: list[tuple[dict[str, Any], float]], key: str
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for metadata, score in rows:
        grouped[str(metadata[key])].append(score)
    return {name: _score_summary(scores) for name, scores in sorted(grouped.items())}


def _ranking_summary(
    rows: list[tuple[dict[str, Any], float]],
    *,
    higher_is_better: bool,
    pass_fail_only: bool,
) -> dict[str, Any]:
    comparisons = 0
    correct = 0
    ties = 0
    for left_index, (left, left_score) in enumerate(rows):
        left_rank = SEVERITY_RANK.get(left["gold_severity"])
        if left_rank is None:
            continue
        for right, right_score in rows[left_index + 1 :]:
            right_rank = SEVERITY_RANK.get(right["gold_severity"])
            if right_rank is None or left_rank == right_rank:
                continue
            if pass_fail_only and (left_rank == 0) == (right_rank == 0):
                continue
            comparisons += 1
            if left_score == right_score:
                ties += 1
                continue
            better_gold_score, worse_gold_score = (
                (left_score, right_score) if left_rank < right_rank else (right_score, left_score)
            )
            if (better_gold_score > worse_gold_score) == higher_is_better:
                correct += 1
    return {
        "comparison_count": comparisons,
        "correct_count": correct,
        "tie_count": ties,
        "accuracy": correct / comparisons if comparisons else None,
    }


def summarize_metric_calibration(
    pack_path: Path, result_path: Path
) -> dict[str, Any]:
    """Join a metric result to its pack and summarize gold-conditioned evidence."""
    pack = validate_document(pack_path, "metric-pack.schema.json")
    result = validate_document(result_path, "metric-result.schema.json")
    if result["pack_id"] != pack["id"]:
        raise MetricCalibrationError(
            f"Metric result pack_id {result['pack_id']!r} does not match {pack['id']!r}."
        )
    pack_cases = {case["id"]: case for case in pack["cases"]}
    required_metadata = {
        "source_case_id",
        "candidate_role",
        "language_pair",
        "gold_mode",
        "gold_verdict",
        "gold_severity",
        "phenomenon",
    }
    if any(
        not isinstance(case.get("metadata"), dict)
        or not required_metadata.issubset(case["metadata"])
        for case in pack["cases"]
    ):
        raise MetricCalibrationError("Metric pack cases are missing calibration metadata.")
    result_ids = [case["id"] for case in result["cases"]]
    if len(result_ids) != len(set(result_ids)) or set(result_ids) != set(pack_cases):
        raise MetricCalibrationError("Metric result cases do not match the metric pack exactly.")

    rows = [
        (pack_cases[case["id"]]["metadata"], float(case["score"]))
        for case in result["cases"]
    ]
    single_rows = [
        (metadata, score) for metadata, score in rows if metadata["gold_mode"] == "single"
    ]
    pairwise: dict[str, dict[str, tuple[dict[str, Any], float]]] = defaultdict(dict)
    for metadata, score in rows:
        if metadata["gold_mode"] == "pairwise":
            pairwise[metadata["source_case_id"]][metadata["candidate_role"]] = (
                metadata,
                score,
            )

    higher_is_better = result["metric"]["direction"] == "higher_is_better"
    pairwise_rows = []
    for source_case_id, candidates in sorted(pairwise.items()):
        if set(candidates) != {"candidate_a", "candidate_b"}:
            raise MetricCalibrationError(f"Incomplete pairwise scores for {source_case_id}.")
        metadata = candidates["candidate_a"][0]
        score_a = candidates["candidate_a"][1]
        score_b = candidates["candidate_b"][1]
        if score_a == score_b:
            predicted = "tie"
        elif (score_a > score_b) == higher_is_better:
            predicted = "candidate_a"
        else:
            predicted = "candidate_b"
        pairwise_rows.append(
            {
                "source_case_id": source_case_id,
                "language_pair": metadata["language_pair"],
                "phenomenon": metadata["phenomenon"],
                "gold": metadata["gold_verdict"],
                "predicted": predicted,
                "correct": predicted == metadata["gold_verdict"],
                "score_a": score_a,
                "score_b": score_b,
                "margin": abs(score_a - score_b),
            }
        )

    def pairwise_group(key: str) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in pairwise_rows:
            grouped[row[key]].append(row)
        return {
            name: {
                "case_count": len(values),
                "correct_count": sum(row["correct"] for row in values),
                "accuracy": sum(row["correct"] for row in values) / len(values),
                "tie_count": sum(row["predicted"] == "tie" for row in values),
                "mean_margin": sum(row["margin"] for row in values) / len(values),
            }
            for name, values in sorted(grouped.items())
        }

    report = {
        "schema_version": 1,
        "pack_id": pack["id"],
        "metric": result["metric"],
        "hypothesis_count": len(rows),
        "language_pair_scores": _group_summaries(rows, "language_pair"),
        "single": {
            "case_count": len(single_rows),
            "scores_by_gold_verdict": _group_summaries(single_rows, "gold_verdict"),
            "scores_by_gold_severity": _group_summaries(single_rows, "gold_severity"),
            "pass_fail_ranking": _ranking_summary(
                single_rows,
                higher_is_better=higher_is_better,
                pass_fail_only=True,
            ),
            "severity_ranking": _ranking_summary(
                single_rows,
                higher_is_better=higher_is_better,
                pass_fail_only=False,
            ),
        },
        "pairwise": {
            "case_count": len(pairwise_rows),
            "correct_count": sum(row["correct"] for row in pairwise_rows),
            "accuracy": (
                sum(row["correct"] for row in pairwise_rows) / len(pairwise_rows)
                if pairwise_rows
                else None
            ),
            "tie_count": sum(row["predicted"] == "tie" for row in pairwise_rows),
            "by_language_pair": pairwise_group("language_pair"),
            "by_phenomenon": pairwise_group("phenomenon"),
            "cases": pairwise_rows,
        },
    }
    return report


def write_metric_calibration_report(
    pack_path: Path,
    result_path: Path,
    output_json: Path,
    output_markdown: Path,
) -> dict[str, Any]:
    """Write machine-readable and compact Markdown metric calibration reports."""
    report = summarize_metric_calibration(pack_path, result_path)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pairwise = report["pairwise"]
    lines = [
        f"# {report['metric']['name']} calibration report",
        "",
        f"- Pack: `{report['pack_id']}`",
        f"- Hypotheses: {report['hypothesis_count']}",
        f"- Direction: `{report['metric']['direction']}`",
        f"- Single cases: {report['single']['case_count']}",
        f"- Pairwise cases: {pairwise['case_count']}",
    ]
    if pairwise["accuracy"] is not None:
        lines.extend(
            [
                f"- Pairwise gold accuracy: {pairwise['accuracy']:.4f}",
                f"- Pairwise ties: {pairwise['tie_count']}",
                "",
                "## Pairwise by language pair",
                "",
                "| Language pair | Cases | Correct | Accuracy | Ties | Mean margin |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for language_pair, summary in pairwise["by_language_pair"].items():
            lines.append(
                f"| {language_pair} | {summary['case_count']} | {summary['correct_count']} | "
                f"{summary['accuracy']:.4f} | {summary['tie_count']} | "
                f"{summary['mean_margin']:.4f} |"
            )
    output_markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

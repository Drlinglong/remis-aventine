"""Pairwise recipe comparison and repair restraint reporting for Remis artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from remis_aventine.calibration import load_calibration_fixture
from remis_aventine.validation import DocumentValidationError, validate_payload

PAIRWISE_REVISION = "remis-recipe-pairwise-v1"


class RemisPairwiseError(ValueError):
    """Raised when two adapted Remis runs cannot be compared safely."""


def _load_run(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RemisPairwiseError(
            f"Invalid run JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    try:
        result = validate_payload(document, "run-result.schema.json")
    except DocumentValidationError as exc:
        raise RemisPairwiseError("Invalid Aventine run result: " + "; ".join(exc.issues)) from exc
    if result["suite"] != "remis":
        raise RemisPairwiseError(f"Expected suite 'remis', received {result['suite']!r}.")
    return result


def _recipe(run: dict[str, Any]) -> dict[str, str]:
    return {
        "id": run["recipe"]["id"],
        "sha256": run["recipe"]["sha256"],
        "run_id": run["run_id"],
        "model_label": str(run.get("environment", {}).get("model_label") or run["recipe"]["id"]),
    }


def _eligible(case: dict[str, Any]) -> bool:
    return case.get("execution_status") == "completed" and (
        case.get("hard_validation", {}).get("passed") is True
    )


def _repair_summary(run: dict[str, Any]) -> dict[str, Any]:
    repair_cases = [case for case in run["cases"] if case.get("track") == "repair"]
    completed = [case for case in repair_cases if case.get("execution_status") == "completed"]
    unchanged = [
        case
        for case in completed
        if case.get("automatic_metrics", {}).get("valid_items_unchanged") is True
    ]
    over_edited = [
        case
        for case in completed
        if case.get("automatic_metrics", {}).get("valid_items_unchanged") is False
    ]
    exact = [
        case
        for case in completed
        if case.get("automatic_metrics", {}).get("reference_exact_match") is True
    ]
    return {
        "case_count": len(repair_cases),
        "completed_count": len(completed),
        "hard_pass_count": sum(_eligible(case) for case in repair_cases),
        "valid_items_unchanged_count": len(unchanged),
        "over_editing_count": len(over_edited),
        "over_editing_case_ids": [case["id"] for case in over_edited],
        "reference_exact_match_count": len(exact),
        "over_editing_rate": round(len(over_edited) / len(completed), 6) if completed else None,
    }


def build_remis_pairwise_pack(
    left_path: Path, right_path: Path, output_path: Path
) -> dict[str, Any]:
    """Build only the soft-quality comparisons not already decided by hard validators."""
    left = _load_run(left_path)
    right = _load_run(right_path)
    left_recipe = _recipe(left)
    right_recipe = _recipe(right)
    if left_recipe["sha256"] == right_recipe["sha256"]:
        raise RemisPairwiseError("Pairwise comparison requires two distinct recipe hashes.")

    left_cases = {case["id"]: case for case in left["cases"]}
    right_cases = {case["id"]: case for case in right["cases"]}
    if left_cases.keys() != right_cases.keys():
        left_only = sorted(left_cases.keys() - right_cases.keys())
        right_only = sorted(right_cases.keys() - left_cases.keys())
        raise RemisPairwiseError(
            f"Runs must contain identical case ids; left_only={left_only}, right_only={right_only}."
        )

    soft_cases: list[dict[str, Any]] = []
    policy_cases: list[dict[str, Any]] = []
    for case_id in left_cases:
        left_case = left_cases[case_id]
        right_case = right_cases[case_id]
        left_eligible = _eligible(left_case)
        right_eligible = _eligible(right_case)
        common = {
            "id": case_id,
            "track": left_case.get("track"),
            "left_eligible": left_eligible,
            "right_eligible": right_eligible,
        }
        if not (left_eligible and right_eligible):
            winner = "left" if left_eligible else "right" if right_eligible else "neither"
            policy_cases.append({**common, "winner": winner, "decision_source": "hard_validation"})
            continue

        left_outputs = left_case.get("candidate_outputs")
        right_outputs = right_case.get("candidate_outputs")
        if not isinstance(left_outputs, list) or not isinstance(right_outputs, list):
            policy_cases.append(
                {**common, "winner": "neither", "decision_source": "missing_candidate_output"}
            )
            continue
        input_payload: dict[str, Any] = {
            "task": left_case.get("track"),
            "source_language": left_case.get("source_metadata", {}).get("source_language"),
            "target_language": left_case.get("source_metadata", {}).get("target_language"),
            "source": left_case.get("source_inputs", []),
            "candidate_a": left_outputs,
            "candidate_b": right_outputs,
            "focus": left_case.get("source_metadata", {}).get("focus", []),
        }
        if left_case.get("track") == "repair":
            evidence = left_case.get("repair_evidence") or {}
            input_payload.update(
                broken_translation=evidence.get("broken_translation"),
                injected_errors=evidence.get("injected_errors", []),
                instruction=(
                    "Prefer a candidate that fixes the stated defects while preserving "
                    "already-valid items. "
                    "Penalize unnecessary rewrites as over_editing."
                ),
            )
        soft_cases.append(
            {
                **common,
                "origin_suite": "remis",
                "evaluation_mode": "pairwise",
                "ab_swap": True,
                "input": input_payload,
                "candidate_mapping": {
                    "candidate_a": left_recipe["id"],
                    "candidate_b": right_recipe["id"],
                },
            }
        )

    identity = hashlib.sha256(
        f"{left_recipe['sha256']}:{right_recipe['sha256']}".encode()
    ).hexdigest()[:16]
    pack = {
        "schema_version": 1,
        "id": f"remis-pairwise-{identity}",
        "suite": "remis-pairwise",
        "description": "Operational Remis recipe comparison; judge outputs are not human gold.",
        "adapter": {"revision": PAIRWISE_REVISION},
        "recipes": {"left": left_recipe, "right": right_recipe},
        "policy_cases": policy_cases,
        "repair_over_editing": {
            "left": _repair_summary(left),
            "right": _repair_summary(right),
        },
        "cases": soft_cases,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return pack


def _evaluation(case: dict[str, Any], field: str) -> dict[str, Any] | None:
    value = case.get(field)
    if not isinstance(value, dict) or "benchmark_failure" in value:
        return None
    try:
        return validate_payload(value, "judge-result.schema.json")["evaluation"]
    except DocumentValidationError:
        return None


def _normalized_verdict(verdict: str, *, swapped: bool = False) -> str:
    if swapped:
        return {"candidate_a": "candidate_b", "candidate_b": "candidate_a"}.get(verdict, verdict)
    return verdict


def _judge_decision(case: dict[str, Any]) -> dict[str, Any]:
    base = _evaluation(case, "judge_output")
    swap = _evaluation(case, "swap_judge_output")
    if base is None or swap is None:
        return {"winner": "unresolved", "decision_source": "judge_missing_or_invalid"}
    base_verdict = str(base["verdict"])
    swap_verdict = _normalized_verdict(str(swap["verdict"]), swapped=True)
    if base_verdict != swap_verdict:
        return {
            "winner": "unresolved",
            "decision_source": "judge_position_inconsistent",
            "base_verdict": base_verdict,
            "swap_verdict_normalized": swap_verdict,
        }
    winner = {"candidate_a": "left", "candidate_b": "right"}.get(base_verdict, base_verdict)
    return {
        "winner": winner,
        "decision_source": "judge_position_consistent",
        "verdict": base_verdict,
        "confidence": base.get("confidence"),
    }


def summarize_remis_pairwise(input_path: Path) -> dict[str, Any]:
    """Apply hard-veto and position-consistency policies to a pack or completed judge run."""
    fixture = load_calibration_fixture(input_path)
    recipes = fixture.get("recipes")
    policy_cases = fixture.get("policy_cases")
    repair = fixture.get("repair_over_editing")
    valid_envelope = (
        isinstance(recipes, dict)
        and isinstance(policy_cases, list)
        and isinstance(repair, dict)
    )
    if not valid_envelope:
        raise RemisPairwiseError("Input is not a Remis pairwise pack or judge result.")
    decisions = [dict(case) for case in policy_cases]
    for case in fixture["cases"]:
        decisions.append(
            {
                "id": case["id"],
                "track": case.get("track"),
                "left_eligible": True,
                "right_eligible": True,
                **_judge_decision(case),
            }
        )
    counts = Counter(decision["winner"] for decision in decisions)
    return {
        "schema_version": 1,
        "id": f"{fixture['id']}.report",
        "suite": "remis-pairwise-report",
        "recipes": recipes,
        "summary": {
            "case_count": len(decisions),
            "left_win_count": counts["left"],
            "right_win_count": counts["right"],
            "tie_count": counts["tie"],
            "neither_count": counts["neither"],
            "unresolved_count": counts["unresolved"],
            "hard_validation_decision_count": sum(
                case.get("decision_source") == "hard_validation" for case in decisions
            ),
            "judge_position_inconsistent_count": sum(
                case.get("decision_source") == "judge_position_inconsistent" for case in decisions
            ),
        },
        "repair_over_editing": repair,
        "cases": decisions,
        "judge_run": fixture.get("run"),
    }


def render_remis_pairwise_markdown(report: dict[str, Any]) -> str:
    """Render the compact human-facing form of a pairwise JSON report."""
    left = report["recipes"]["left"]
    right = report["recipes"]["right"]
    summary = report["summary"]
    lines = [
        "# Remis recipe pairwise report",
        "",
        f"- Left: `{left['id']}` (`{left['sha256'][:12]}`)",
        f"- Right: `{right['id']}` (`{right['sha256'][:12]}`)",
        f"- Cases: {summary['case_count']}",
        f"- Wins: left {summary['left_win_count']}, right {summary['right_win_count']}",
        "- Tie / neither / unresolved: "
        f"{summary['tie_count']} / {summary['neither_count']} / {summary['unresolved_count']}",
        f"- Hard-validator decisions: {summary['hard_validation_decision_count']}",
        f"- Position-inconsistent judge decisions: {summary['judge_position_inconsistent_count']}",
        "",
        "## Repair restraint",
        "",
        "| Recipe | Completed | Hard pass | Over-editing | Rate | Reference exact |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for side in ("left", "right"):
        item = report["repair_over_editing"][side]
        rate = "n/a" if item["over_editing_rate"] is None else f"{item['over_editing_rate']:.1%}"
        lines.append(
            f"| {side} | {item['completed_count']} | {item['hard_pass_count']} | "
            f"{item['over_editing_count']} | {rate} | {item['reference_exact_match_count']} |"
        )
    lines.extend(
        [
            "",
            "## Case decisions",
            "",
            "| Case | Track | Winner | Source |",
            "|---|---|---|---|",
        ]
    )
    for case in report["cases"]:
        lines.append(
            f"| `{case['id']}` | {case.get('track') or ''} | {case['winner']} | "
            f"{case['decision_source']} |"
        )
    return "\n".join(lines) + "\n"


def write_remis_pairwise_report(
    input_path: Path, json_path: Path, markdown_path: Path
) -> dict[str, Any]:
    report = summarize_remis_pairwise(input_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_remis_pairwise_markdown(report), encoding="utf-8")
    return report

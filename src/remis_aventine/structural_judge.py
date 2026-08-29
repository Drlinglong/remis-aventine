"""Executable two-family adjudication for syntax-legal protected-token changes."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StructuralJudgeError(ValueError):
    """Raised when structural evidence, independence, or checkpoints are invalid."""


class StructuralJudgeBudgetExceeded(StructuralJudgeError):
    """Raised before a structural call can exceed its USD cap."""


@dataclass(frozen=True)
class StructuralJudgeIdentity:
    id: str
    family: str


def _sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_structural_cases(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand only candidates routed to structural review from a v0.3 pairwise pack."""
    identities = pack.get("candidate_identities") or {}
    cases = []
    for queued in pack.get("structural_review_queue", []):
        for label, route_key, review_key in (
            ("candidate_a", "left_route", "left_review_queue"),
            ("candidate_b", "right_route", "right_review_queue"),
        ):
            if queued.get(route_key) != "structural_judges":
                continue
            identity = identities.get(label)
            if not isinstance(identity, dict) or not identity.get("model_family"):
                raise StructuralJudgeError(f"Missing identity for {label}.")
            cases.append(
                {
                    "id": f"{queued['id']}::{label}",
                    "occurrence_id": queued["id"],
                    "execution_identity_sha256": _sha256(identity),
                    "candidate_label": label,
                    "candidate_family": identity["model_family"],
                    "evaluation_mode": "single",
                    "evaluation_scope": "structural",
                    "input": {
                        "language_pair": queued["direction"],
                        "source": queued["source"],
                        "candidate": queued[label],
                        "structural_findings": deepcopy(queued.get(review_key, [])),
                    },
                }
            )
    if len({case["id"] for case in cases}) != len(cases):
        raise StructuralJudgeError("Structural cases require unique IDs.")
    return cases


def plan_structural_dual_judge(
    cases: list[dict[str, Any]],
    judge_a: StructuralJudgeIdentity,
    judge_b: StructuralJudgeIdentity,
) -> dict[str, Any]:
    if judge_a.id == judge_b.id or judge_a.family == judge_b.family:
        raise StructuralJudgeError("Structural judges must use independent model families.")
    calls = []
    for case in cases:
        if case.get("candidate_family") in {judge_a.family, judge_b.family}:
            raise StructuralJudgeError(f"Self-judging prohibited for {case.get('id')}.")
        for judge in (judge_a, judge_b):
            calls.append(
                {
                    "id": f"{case['id']}::{judge.id}",
                    "case_id": case["id"],
                    "judge_id": judge.id,
                    "judge_family": judge.family,
                }
            )
    plan = {
        "protocol": "aventine-structural-dual-judge-v0.3",
        "cases_sha256": _sha256(cases),
        "judge_identities": [
            {"id": judge_a.id, "family": judge_a.family},
            {"id": judge_b.id, "family": judge_b.family},
        ],
        "case_count": len(cases),
        "planned_call_count": len(calls),
        "calls": calls,
    }
    plan["sha256"] = _sha256(plan)
    return plan


def _cost(judge: Any, usage: dict[str, Any]) -> float:
    fields = judge.cost_fields(usage, {})
    value = fields.get("exact_cost_usd", fields.get("estimated_cost_usd"))
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise StructuralJudgeError("Structural judges require non-negative USD cost evidence.")
    return float(value)


def execute_structural_dual_judge(
    plan: dict[str, Any],
    cases: list[dict[str, Any]],
    judges: dict[str, Any],
    output_path: Path,
    *,
    max_cost_usd: float,
    reserve_per_call_usd: float,
) -> dict[str, Any]:
    """Execute exactly one HTTP attempt per judge/case and checkpoint every response."""
    if max_cost_usd < 0 or reserve_per_call_usd < 0:
        raise StructuralJudgeError("Budget values must be non-negative.")
    if _sha256(cases) != plan.get("cases_sha256"):
        raise StructuralJudgeError("Structural cases do not match the plan evidence hash.")
    case_by_id = {case["id"]: case for case in cases}
    if set(judges) != {item["id"] for item in plan["judge_identities"]}:
        raise StructuralJudgeError("Exactly one adapter is required for each structural judge.")
    if output_path.exists():
        report = json.loads(output_path.read_text(encoding="utf-8"))
        if report.get("plan_sha256") != plan.get("sha256"):
            raise StructuralJudgeError("Checkpoint belongs to a different structural plan.")
    else:
        report = {
            "schema_version": 1,
            "status": "running",
            "protocol": plan["protocol"],
            "plan_sha256": plan["sha256"],
            "cases_sha256": plan["cases_sha256"],
            "judge_identities": deepcopy(plan["judge_identities"]),
            "max_cost_usd": max_cost_usd,
            "reserve_per_call_usd": reserve_per_call_usd,
            "results": [],
        }
        _atomic(output_path, report)
    completed = {result["call_id"] for result in report["results"]}
    for call in plan["calls"]:
        if call["id"] in completed:
            continue
        observed = sum(float(result.get("cost_usd") or 0) for result in report["results"])
        unknown = sum(result.get("cost_usd") is None for result in report["results"])
        committed = observed + unknown * reserve_per_call_usd
        if committed + reserve_per_call_usd > max_cost_usd:
            report["status"] = "budget_stopped"
            _atomic(output_path, report)
            raise StructuralJudgeBudgetExceeded("Next structural call exceeds the budget cap.")
        try:
            judge = judges[call["judge_id"]]
            result, usage = judge.evaluate_once(deepcopy(case_by_id[call["case_id"]]))
            verdict = (result.get("evaluation") or {}).get("verdict")
            decision = {"pass": "acceptable", "fail": "lost_or_added"}.get(
                verdict, "uncertain"
            )
            call_result = {
                "call_id": call["id"],
                "case_id": call["case_id"],
                "judge_id": call["judge_id"],
                "decision": decision,
                "cost_usd": _cost(judge, usage),
                "usage": usage,
                "judge_result": result,
            }
        except Exception as exc:  # one paid attempt; intentionally no retry
            call_result = {
                "call_id": call["id"],
                "case_id": call["case_id"],
                "judge_id": call["judge_id"],
                "decision": "uncertain",
                "cost_usd": None,
                "execution_failure": f"{type(exc).__name__}: {exc}",
            }
        report["results"].append(call_result)
        _atomic(output_path, report)

    results_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in report["results"]:
        results_by_case[result["case_id"]].append(result)
    decisions = []
    resolutions = []
    for case in cases:
        values = [result["decision"] for result in results_by_case[case["id"]]]
        resolved = len(values) == 2 and values[0] == values[1] and values[0] != "uncertain"
        decisions.append(
            {"case_id": case["id"], "decisions": values, "resolved": resolved}
        )
        if len(values) == 2 and all(
            value in {"acceptable", "lost_or_added"} for value in values
        ):
            resolutions.append(
                {
                    "execution_identity_sha256": case["execution_identity_sha256"],
                    "occurrence_id": case["occurrence_id"],
                    "decisions": values,
                }
            )
    report["status"] = "completed"
    observed_cost = sum(
        float(result["cost_usd"])
        for result in report["results"]
        if result.get("cost_usd") is not None
    )
    cost_count = sum(result.get("cost_usd") is not None for result in report["results"])
    resolved_count = sum(item["resolved"] for item in decisions)
    report["summary"] = {
        "case_count": len(cases),
        "resolved_count": resolved_count,
        "unresolved_count": sum(not item["resolved"] for item in decisions),
        "observed_cost_usd": round(observed_cost, 10) if cost_count else None,
        "cost_observation_count": cost_count,
        "cost_per_resolved_usd": (
            round(observed_cost / resolved_count, 10)
            if cost_count and resolved_count
            else None
        ),
        "decisions": decisions,
    }
    report["resolutions"] = resolutions
    _atomic(output_path, report)
    return report


__all__ = [
    "StructuralJudgeBudgetExceeded",
    "StructuralJudgeError",
    "StructuralJudgeIdentity",
    "build_structural_cases",
    "execute_structural_dual_judge",
    "plan_structural_dual_judge",
]

"""Deterministic adaptive dual-judge protocol for Aventine v0.3."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERDICTS = frozenset({"candidate_a", "candidate_b", "tie", "neither", "uncertain"})


class DualJudgeError(ValueError):
    """Raised when judge independence or result contracts are violated."""


class DualJudgeBudgetExceeded(DualJudgeError):
    """Raised before the next judge call can exceed the budget cap."""


@dataclass(frozen=True)
class JudgeIdentity:
    id: str
    family: str

    def __post_init__(self) -> None:
        if not self.id or not self.family:
            raise DualJudgeError("Judge id and family must be non-empty.")


def _digest(seed: int, *parts: str) -> str:
    payload = "\0".join((str(seed), *parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _audit_case_ids(cases: list[dict[str, Any]], seed: int, audit_rate: float) -> set[str]:
    if not 0 <= audit_rate <= 1:
        raise DualJudgeError("audit_rate must be between 0 and 1.")
    groups: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        groups[case["stratum"]].append(case["id"])
    selected: set[str] = set()
    for stratum, case_ids in groups.items():
        count = math.ceil(len(case_ids) * audit_rate) if audit_rate else 0
        ranked = sorted(case_ids, key=lambda case_id: _digest(seed, "audit", stratum, case_id))
        selected.update(ranked[:count])
    return selected


def _validate_cases(
    cases: list[dict[str, Any]], judges: tuple[JudgeIdentity, JudgeIdentity]
) -> None:
    if judges[0].id == judges[1].id or judges[0].family == judges[1].family:
        raise DualJudgeError("The two judges must be independent model families.")
    seen = set()
    for case in cases:
        if not isinstance(case.get("id"), str) or not case["id"]:
            raise DualJudgeError("Every case requires a non-empty id.")
        if case["id"] in seen:
            raise DualJudgeError(f"Duplicate case id: {case['id']}")
        seen.add(case["id"])
        if not isinstance(case.get("stratum"), str) or not case["stratum"]:
            raise DualJudgeError(f"Case {case['id']} requires a stratum.")
        candidate_families = case.get("candidate_families")
        if not isinstance(candidate_families, list) or not candidate_families:
            raise DualJudgeError(f"Case {case['id']} requires candidate_families.")
        conflicts = set(candidate_families) & {judges[0].family, judges[1].family}
        if conflicts:
            raise DualJudgeError(
                f"Self-judging prohibited for case {case['id']}: {', '.join(sorted(conflicts))}"
            )


def _call(
    case: dict[str, Any], judge: JudgeIdentity, orientation: str, phase: str
) -> dict[str, Any]:
    return {
        "id": f"{case['id']}::{judge.id}::{orientation}",
        "case_id": case["id"],
        "judge_id": judge.id,
        "judge_family": judge.family,
        "orientation": orientation,
        "phase": phase,
        "stratum": case["stratum"],
    }


def plan_dual_judge(
    cases: list[dict[str, Any]],
    judge_a: JudgeIdentity,
    judge_b: JudgeIdentity,
    *,
    seed: int,
    audit_rate: float = 0.2,
) -> dict[str, Any]:
    """Plan two opposing initial orientations plus a stratified full-four audit."""
    judges = (judge_a, judge_b)
    _validate_cases(cases, judges)
    audit_ids = _audit_case_ids(cases, seed, audit_rate)
    calls = []
    for case in cases:
        first_is_ab = int(_digest(seed, "orientation", case["id"])[0], 16) % 2 == 0
        orientations = ("ab", "ba") if first_is_ab else ("ba", "ab")
        calls.extend(
            _call(case, judge, orientation, "initial")
            for judge, orientation in zip(judges, orientations, strict=True)
        )
        if case["id"] in audit_ids:
            calls.extend(
                _call(case, judge, "ba" if orientation == "ab" else "ab", "audit")
                for judge, orientation in zip(judges, orientations, strict=True)
            )
    plan = {
        "protocol": "adaptive-dual-judge-v0.3",
        "seed": seed,
        "audit_rate": audit_rate,
        "judge_identities": [{"id": judge.id, "family": judge.family} for judge in judges],
        "case_count": len(cases),
        "audit_case_ids": sorted(audit_ids),
        "planned_call_count": len(calls),
        "calls": calls,
    }
    plan["sha256"] = _canonical_sha256(plan)
    return plan


def normalize_verdict(verdict: str, orientation: str) -> str:
    if verdict not in VERDICTS:
        raise DualJudgeError(f"Unsupported verdict: {verdict!r}")
    if orientation not in {"ab", "ba"}:
        raise DualJudgeError(f"Unsupported orientation: {orientation!r}")
    if orientation == "ba":
        return {"candidate_a": "candidate_b", "candidate_b": "candidate_a"}.get(verdict, verdict)
    return verdict


def plan_disagreement_followups(
    plan: dict[str, Any], results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Add each judge's missing orientation only for non-audit initial disagreement."""
    result_by_call = {
        result.get("call_id"): result
        for result in results
        if not result.get("execution_failure") and result.get("verdict") in VERDICTS
    }
    calls_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in plan["calls"]:
        calls_by_case[call["case_id"]].append(call)
    followups = []
    for case_id, calls in calls_by_case.items():
        if any(call["phase"] == "audit" for call in calls):
            continue
        initial = [call for call in calls if call["phase"] == "initial"]
        if any(call["id"] not in result_by_call for call in initial):
            continue
        normalized = [
            normalize_verdict(result_by_call[call["id"]]["verdict"], call["orientation"])
            for call in initial
        ]
        if normalized[0] == normalized[1]:
            continue
        for call in initial:
            followups.append(
                {
                    **deepcopy(call),
                    "id": f"{case_id}::{call['judge_id']}::"
                    f"{'ba' if call['orientation'] == 'ab' else 'ab'}",
                    "orientation": "ba" if call["orientation"] == "ab" else "ab",
                    "phase": "disagreement_followup",
                }
            )
    return followups


def summarize_dual_judge(
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    followups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve only agreement that survives available orientation checks."""
    all_calls = [*plan["calls"], *(followups or [])]
    result_by_call = {
        result.get("call_id"): result
        for result in results
        if not result.get("execution_failure") and result.get("verdict") in VERDICTS
    }
    calls_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in all_calls:
        calls_by_case[call["case_id"]].append(call)
    decisions = []
    total_cost = 0.0
    cost_count = 0
    for result in results:
        if result.get("cost_usd") is not None:
            total_cost += float(result["cost_usd"])
            cost_count += 1
    for case_id, calls in calls_by_case.items():
        available = [call for call in calls if call["id"] in result_by_call]
        by_judge: dict[str, list[str]] = defaultdict(list)
        for call in available:
            verdict = result_by_call[call["id"]].get("verdict")
            by_judge[call["judge_id"]].append(normalize_verdict(verdict, call["orientation"]))
        judge_consistent = {
            judge_id: len(set(verdicts)) == 1 for judge_id, verdicts in by_judge.items()
        }
        representatives = [verdicts[0] for verdicts in by_judge.values() if verdicts]
        complete_initial = sum(call["phase"] == "initial" for call in available) == 2
        required_four = any(call["phase"] != "initial" for call in calls)
        complete_required = len(available) == (4 if required_four else 2)
        resolved = (
            complete_initial
            and complete_required
            and len(representatives) == 2
            and all(judge_consistent.values())
            and representatives[0] == representatives[1]
        )
        decisions.append(
            {
                "case_id": case_id,
                "resolved": resolved,
                "verdict": representatives[0] if resolved else "unresolved",
                "judge_position_consistency": judge_consistent,
                "call_count": len(available),
            }
        )
    resolved_count = sum(decision["resolved"] for decision in decisions)
    position_checks = sum(
        len(decision["judge_position_consistency"])
        for decision in decisions
        if decision["call_count"] == 4
    )
    position_consistent = sum(
        sum(decision["judge_position_consistency"].values())
        for decision in decisions
        if decision["call_count"] == 4
    )
    return {
        "protocol": plan["protocol"],
        "case_count": len(decisions),
        "resolved_count": resolved_count,
        "unresolved_count": len(decisions) - resolved_count,
        "resolved_coverage": resolved_count / len(decisions) if decisions else 0,
        "position_consistency": (
            position_consistent / position_checks if position_checks else None
        ),
        "observed_cost_usd": round(total_cost, 10) if cost_count else None,
        "cost_observation_count": cost_count,
        "cost_per_resolved_usd": (
            round(total_cost / resolved_count, 10) if cost_count and resolved_count else None
        ),
        "decisions": decisions,
    }


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _oriented_case(case: dict[str, Any], orientation: str) -> dict[str, Any]:
    oriented = deepcopy(case)
    if orientation == "ba":
        oriented["candidate_a"], oriented["candidate_b"] = (
            oriented["candidate_b"],
            oriented["candidate_a"],
        )
    return oriented


def execute_adaptive_dual_judge(
    plan: dict[str, Any],
    cases: list[dict[str, Any]],
    transports: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
    output_path: Path,
    *,
    max_cost_usd: float,
    reserve_per_call_usd: float,
) -> dict[str, Any]:
    """Execute initial/audit calls, then only the required disagreement followups.

    A transport receives the public call descriptor and correctly oriented case.
    It must return ``verdict`` and may return observed ``cost_usd``. Exceptions are
    checkpointed as failed calls and are never retried implicitly, preventing an
    uncertain provider response from silently becoming a duplicate paid call.
    """
    if max_cost_usd < 0 or reserve_per_call_usd < 0:
        raise DualJudgeError("Budget values must be non-negative.")
    case_by_id = {case.get("id"): case for case in cases}
    if None in case_by_id or len(case_by_id) != len(cases):
        raise DualJudgeError("Execution cases require unique non-empty IDs.")
    planned_case_ids = {call["case_id"] for call in plan["calls"]}
    if planned_case_ids != set(case_by_id):
        raise DualJudgeError("Execution cases do not match the judge plan.")
    judge_ids = {identity["id"] for identity in plan["judge_identities"]}
    if set(transports) != judge_ids:
        raise DualJudgeError("Exactly one transport is required for each planned judge.")

    if output_path.exists():
        report = json.loads(output_path.read_text(encoding="utf-8"))
        if report.get("plan_sha256") != plan.get("sha256"):
            raise DualJudgeError("Checkpoint belongs to a different dual-judge plan.")
    else:
        report = {
            "schema_version": 1,
            "status": "running",
            "protocol": plan["protocol"],
            "plan_sha256": plan["sha256"],
            "max_cost_usd": max_cost_usd,
            "reserve_per_call_usd": reserve_per_call_usd,
            "results": [],
            "followup_calls": [],
        }
        _atomic_json(output_path, report)

    def execute_calls(calls: list[dict[str, Any]]) -> None:
        completed = {result["call_id"] for result in report["results"]}
        for call in calls:
            if call["id"] in completed:
                continue
            observed = sum(
                float(result["cost_usd"])
                for result in report["results"]
                if result.get("cost_usd") is not None
            )
            unknown = sum(result.get("cost_usd") is None for result in report["results"])
            committed = observed + unknown * reserve_per_call_usd
            if committed + reserve_per_call_usd > max_cost_usd:
                report["status"] = "budget_stopped"
                report["committed_cost_usd"] = round(committed, 10)
                _atomic_json(output_path, report)
                raise DualJudgeBudgetExceeded(
                    f"Next judge call would exceed USD {max_cost_usd:.6f} budget cap."
                )
            try:
                response = transports[call["judge_id"]](
                    deepcopy(call),
                    _oriented_case(case_by_id[call["case_id"]], call["orientation"]),
                )
                if not isinstance(response, dict) or response.get("verdict") not in VERDICTS:
                    raise DualJudgeError("Judge transport returned an invalid verdict contract.")
                cost = response.get("cost_usd")
                if cost is not None and (
                    not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0
                ):
                    raise DualJudgeError("Judge cost_usd must be non-negative or null.")
                result = {"call_id": call["id"], **deepcopy(response)}
            except Exception as exc:  # one paid attempt; intentionally no retry
                result = {
                    "call_id": call["id"],
                    "verdict": None,
                    "cost_usd": None,
                    "execution_failure": f"{type(exc).__name__}: {exc}",
                }
            report["results"].append(result)
            _atomic_json(output_path, report)

    execute_calls(plan["calls"])
    followups = plan_disagreement_followups(plan, report["results"])
    report["followup_calls"] = followups
    _atomic_json(output_path, report)
    execute_calls(followups)
    report["summary"] = summarize_dual_judge(plan, report["results"], followups=followups)
    report["status"] = "completed"
    _atomic_json(output_path, report)
    return report


__all__ = [
    "DualJudgeError",
    "DualJudgeBudgetExceeded",
    "JudgeIdentity",
    "execute_adaptive_dual_judge",
    "normalize_verdict",
    "plan_disagreement_followups",
    "plan_dual_judge",
    "summarize_dual_judge",
]

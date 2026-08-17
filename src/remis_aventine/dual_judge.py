"""Deterministic adaptive dual-judge protocol for Aventine v0.3."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

VERDICTS = frozenset({"candidate_a", "candidate_b", "tie", "neither", "uncertain"})


class DualJudgeError(ValueError):
    """Raised when judge independence or result contracts are violated."""


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
    return {
        "protocol": "adaptive-dual-judge-v0.3",
        "seed": seed,
        "audit_rate": audit_rate,
        "judge_identities": [{"id": judge.id, "family": judge.family} for judge in judges],
        "case_count": len(cases),
        "audit_case_ids": sorted(audit_ids),
        "planned_call_count": len(calls),
        "calls": calls,
    }


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
    result_by_call = {result.get("call_id"): result for result in results}
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
    result_by_call = {result.get("call_id"): result for result in results}
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


__all__ = [
    "DualJudgeError",
    "JudgeIdentity",
    "normalize_verdict",
    "plan_disagreement_followups",
    "plan_dual_judge",
    "summarize_dual_judge",
]

"""Preflight call-volume and reserve-cost estimates for Aventine v0.3 campaigns."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any


class V03BudgetError(ValueError):
    """Raised when a campaign estimate has invalid topology or assumptions."""


def _rate(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise V03BudgetError(f"{name} must be between 0 and 1.")
    return float(value)


def _pair_count(contestants: int, topology: str) -> int:
    if contestants < 2:
        raise V03BudgetError("At least two contestants are required.")
    if topology == "full-round-robin":
        return contestants * (contestants - 1) // 2
    if topology == "single-anchor":
        return contestants - 1
    if topology == "double-anchor":
        return 2 * contestants - 3
    raise V03BudgetError(f"Unknown pairing topology: {topology}")


def estimate_v03_campaign(
    *,
    contestants: int,
    contestant_calls_each: int = 370,
    judgeable_items_per_pair: int = 598,
    topology: str = "full-round-robin",
    audit_rate: float = 0.2,
    disagreement_rate: float = 0.1,
    structural_rate: float = 0.02,
    contestant_call_usd: float = 0.0065,
    judge_call_usd: float = 0.0025,
) -> dict[str, Any]:
    """Estimate expected and worst-case calls without pretending they are quoted prices."""
    for name, value in (
        ("contestant_calls_each", contestant_calls_each),
        ("judgeable_items_per_pair", judgeable_items_per_pair),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise V03BudgetError(f"{name} must be a non-negative integer.")
    audit_rate = _rate(audit_rate, "audit_rate")
    disagreement_rate = _rate(disagreement_rate, "disagreement_rate")
    structural_rate = _rate(structural_rate, "structural_rate")
    if contestant_call_usd < 0 or judge_call_usd < 0:
        raise V03BudgetError("Per-call reserve costs must be non-negative.")

    pairs = _pair_count(contestants, topology)
    audit_items = min(judgeable_items_per_pair, math.ceil(judgeable_items_per_pair * audit_rate))
    non_audit_items = judgeable_items_per_pair - audit_items
    disagreement_items = math.ceil(non_audit_items * disagreement_rate)
    soft_calls_per_pair = (
        2 * judgeable_items_per_pair + 2 * audit_items + 2 * disagreement_items
    )
    soft_calls = pairs * soft_calls_per_pair
    soft_calls_worst = pairs * 4 * judgeable_items_per_pair
    structural_cases_each = math.ceil(judgeable_items_per_pair * structural_rate)
    structural_calls = contestants * structural_cases_each * 2
    structural_calls_worst = contestants * judgeable_items_per_pair * 2
    contestant_calls = contestants * contestant_calls_each

    contestant_cost = Decimal(contestant_calls) * Decimal(str(contestant_call_usd))
    judge_cost = Decimal(soft_calls + structural_calls) * Decimal(str(judge_call_usd))
    worst_judge_cost = Decimal(soft_calls_worst + structural_calls_worst) * Decimal(
        str(judge_call_usd)
    )
    return {
        "protocol": "aventine-v0.3-campaign-estimate",
        "pricing_kind": "caller-supplied-reserve-not-provider-quote",
        "assumptions": {
            "contestants": contestants,
            "topology": topology,
            "pair_count": pairs,
            "contestant_calls_each": contestant_calls_each,
            "judgeable_items_per_pair": judgeable_items_per_pair,
            "audit_rate": audit_rate,
            "disagreement_rate": disagreement_rate,
            "structural_rate": structural_rate,
            "contestant_call_usd": contestant_call_usd,
            "judge_call_usd": judge_call_usd,
        },
        "expected_calls": {
            "contestant": contestant_calls,
            "soft_judges": soft_calls,
            "structural_judges": structural_calls,
            "total": contestant_calls + soft_calls + structural_calls,
        },
        "worst_case_calls": {
            "soft_judges": soft_calls_worst,
            "structural_judges": structural_calls_worst,
            "total": contestant_calls + soft_calls_worst + structural_calls_worst,
        },
        "reserve_cost_usd": {
            "contestants": round(float(contestant_cost), 4),
            "judges_expected": round(float(judge_cost), 4),
            "total_expected": round(float(contestant_cost + judge_cost), 4),
            "judges_worst_case": round(float(worst_judge_cost), 4),
            "total_worst_case": round(float(contestant_cost + worst_judge_cost), 4),
        },
    }


__all__ = ["V03BudgetError", "estimate_v03_campaign"]

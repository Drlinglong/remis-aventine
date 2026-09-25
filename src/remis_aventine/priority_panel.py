"""Versioned OpenRouter judge pool with contestant-family recusal.

Historical provider identities retain their meaning. These profiles are a new
panel, not replacements behind an existing checkpoint identity.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from remis_aventine.judge import OpenRouterGeminiJudge

REVISION = "priority-mimo26-luna6-ds41-gemini38-20260925-v1"


@dataclass(frozen=True)
class Member:
    id: str
    model: str
    family: str
    canonical: str
    input_price: float
    output_price: float
    cache_price: float


MEMBERS = (
    Member(
        "mimo26",
        "xiaomi/mimo-v2.6-pro",
        "xiaomi-mimo",
        "xiaomi/mimo-v2.6-pro-20260921",
        0.435,
        0.87,
        0.0036,
    ),
    Member(
        "luna6", "openai/gpt-6-luna", "openai-gpt", "openai/gpt-6-luna-20260922", 0.1, 0.5, 0.01
    ),
    Member(
        "ds41",
        "deepseek/deepseek-v4.1-flash",
        "deepseek",
        "deepseek/deepseek-v4.1-flash-20260910",
        0.3,
        1.2,
        0.006,
    ),
)
FALLBACK = Member(
    "gemini38-fallback",
    "google/gemini-3.8-flash",
    "google-gemini",
    "google/gemini-3.8-flash-20260902",
    0.75,
    3.75,
    0.075,
)
ALL_MEMBERS = {m.id: m for m in (*MEMBERS, FALLBACK)}


def model_family(model: str) -> str:
    vendor = model.split("/", 1)[0].lower()
    return {
        "openai": "openai-gpt",
        "xiaomi": "xiaomi-mimo",
        "deepseek": "deepseek",
        "google": "google-gemini",
    }.get(vendor, vendor)


def select_panel(candidate_models: list[str]) -> tuple[list[Member], list[Member]]:
    """Select two eligible priority judges; Gemini fills an independence gap."""
    excluded = {model_family(model) for model in candidate_models}
    eligible = [m for m in MEMBERS if m.family not in excluded]
    fallback = [FALLBACK] if FALLBACK.family not in excluded else []
    primary = eligible[:2]
    if len(primary) < 2:
        primary += fallback[: 2 - len(primary)]
    if len(primary) != 2:
        raise ValueError("Two independent, non-contestant families are required")
    return primary, [m for m in fallback if m not in primary]


def resolve_votes(votes: list[str | None]) -> str | None:
    """Require two matching valid votes; one success never becomes consensus."""
    valid = {"pass", "fail", "candidate_a", "candidate_b", "tie", "neither"}
    counts = Counter(v for v in votes if v in valid)
    winners = [v for v, n in counts.items() if n >= 2]
    return winners[0] if len(winners) == 1 else None


def oriented(case: dict[str, Any], orientation: str) -> dict[str, Any]:
    result = deepcopy(case)
    if orientation == "ba":
        result["input"]["candidate_a"], result["input"]["candidate_b"] = (
            result["input"]["candidate_b"],
            result["input"]["candidate_a"],
        )
    return result


def normalize_vote(verdict: str | None, orientation: str) -> str | None:
    return (
        {"candidate_a": "candidate_b", "candidate_b": "candidate_a"}.get(verdict, verdict)
        if orientation == "ba"
        else verdict
    )


class PriorityJudge(OpenRouterGeminiJudge):
    """Uncapped structured judge with profile-specific price fallback."""

    def __init__(self, api_key: str, member_id: str, **kwargs: Any) -> None:
        member = ALL_MEMBERS[member_id]
        self.member = member
        self.provider = f"openrouter-{member.id}-{REVISION}"
        self.provider_label = member.model
        self.model_id = member.model
        self.canonical_model_id = member.canonical
        self.profile = self.provider
        self.max_tokens = None
        self.reasoning_effort = "medium" if member == FALLBACK else "high"
        super().__init__(api_key, **kwargs)

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        body = super().request_body(case)
        body.pop("max_tokens", None)
        body.pop("seed", None)
        if self.member.id == "mimo26":
            body["reasoning"] = {"enabled": True, "exclude": True}
        # OpenAI's strict schema requires an explicit type beside const.
        if self.member.id == "luna6":
            body["response_format"]["json_schema"]["schema"]["properties"]["evaluation"][
                "properties"
            ]["mode"]["type"] = "string"
        return body

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        m = self.member
        estimate = (
            usage.get("cache_hit_input_tokens", 0) * m.cache_price
            + usage.get("cache_miss_input_tokens", 0) * m.input_price
            + usage.get("output_tokens", 0) * m.output_price
        ) / 1_000_000
        ticks = usage.get("cost_in_usd_ticks", 0)
        return {
            "exact_cost_usd": ticks / 10_000_000_000 if ticks else None,
            "estimated_cost_usd": round(estimate, 10),
            "cost_source": "openrouter_usage" if ticks else "token_estimate",
            "price_snapshot": "2026-09-25; DeepSeek peak fallback",
        }

"""Generate website-ready Aventine v0.3 tournament aggregates from raw evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from typing import Any

from remis_aventine.exam_execution import V03_DIRECTIONS
from remis_aventine.multilingual_scoring import aggregate_multilingual_v03
from remis_aventine.validation import validate_payload

_DIRECTION_RE = re.compile(r"::(?P<direction>[^:]+->[^:]+)::repeat-\d+$")
_POINTS = {
    "candidate_a": (Decimal(1), Decimal(0)),
    "candidate_b": (Decimal(0), Decimal(1)),
    "tie": (Decimal("0.5"), Decimal("0.5")),
    "neither": (Decimal(0), Decimal(0)),
}


class V03AggregateError(ValueError):
    """Raised when run, structural, or pairwise evidence cannot be reconciled."""


def _sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _identity(run: dict[str, Any]) -> tuple[dict[str, Any], str]:
    identity = run.get("execution_identity")
    digest = run.get("execution_identity_sha256")
    if not isinstance(identity, dict) or not identity or digest != _sha256(identity):
        raise V03AggregateError("Run lacks a valid execution identity.")
    return identity, digest


def _direction(job_id: str) -> str:
    match = _DIRECTION_RE.search(job_id)
    if match is None or match.group("direction") not in V03_DIRECTIONS:
        raise V03AggregateError(f"Cannot derive a v0.3 direction from job_id: {job_id}")
    return match.group("direction")


def _structural_map(resolutions: list[dict[str, Any]]) -> dict[tuple[str, str], bool | None]:
    result: dict[tuple[str, str], bool | None] = {}
    for resolution in resolutions:
        key = (
            resolution.get("execution_identity_sha256"),
            resolution.get("occurrence_id"),
        )
        if not all(isinstance(value, str) and value for value in key) or key in result:
            raise V03AggregateError(
                "Structural resolutions require unique identity/occurrence keys."
            )
        decisions = resolution.get("decisions")
        if (
            not isinstance(decisions, list)
            or len(decisions) != 2
            or any(value not in {"acceptable", "lost_or_added"} for value in decisions)
        ):
            raise V03AggregateError("Structural resolution requires exactly two valid decisions.")
        result[key] = (
            decisions[0] == "acceptable" if decisions[0] == decisions[1] else None
        )
    return result


def _empty_bucket() -> dict[str, Any]:
    return {"total": 0, "resolved": 0, "points": Decimal(0)}


def _telemetry(run: dict[str, Any]) -> dict[str, Any]:
    elapsed = Decimal(0)
    observed_cost = Decimal(0)
    cost_observations = 0
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0
    total_tokens = 0
    raw_passes = 0
    normalized_calls = 0
    results = run.get("results", [])
    for result in results:
        elapsed += Decimal(str(result.get("elapsed_seconds") or 0))
        if result.get("cost_usd") is not None:
            observed_cost += Decimal(str(result["cost_usd"]))
            cost_observations += 1
        usage = result.get("usage") or {}
        prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion = int(
            usage.get("completion_tokens") or usage.get("output_tokens") or 0
        )
        details = usage.get("completion_tokens_details") or usage.get(
            "output_tokens_details"
        ) or {}
        reasoning = int(details.get("reasoning_tokens") or usage.get("reasoning_tokens") or 0)
        prompt_tokens += prompt
        completion_tokens += completion
        reasoning_tokens += reasoning
        total_tokens += int(usage.get("total_tokens") or prompt + completion)
        validation = result.get("validation") or {}
        raw_passes += validation.get("raw_contract_pass") is True
        normalized_calls += bool(validation.get("normalization_operations"))
    elapsed_float = float(elapsed)
    return {
        "call_count": len(results),
        "elapsed_seconds": elapsed_float,
        "throughput_output_tokens_per_second": (
            round(completion_tokens / elapsed_float, 4) if elapsed_float else None
        ),
        "tokens": {
            "input": prompt_tokens,
            "output_including_reasoning": completion_tokens,
            "reasoning": reasoning_tokens,
            "total": total_tokens,
        },
        "cost_usd": (
            float(observed_cost) if cost_observations == len(results) else None
        ),
        "cost_observation_count": cost_observations,
        "raw_contract_pass_rate": (
            round(raw_passes / len(results), 6) if results else None
        ),
        "normalization_applied_rate": (
            round(normalized_calls / len(results), 6) if results else None
        ),
    }


def _component(bucket: dict[str, Any]) -> dict[str, Any]:
    total = bucket["total"]
    resolved = bucket["resolved"]
    return {
        "score": round(float(bucket["points"] / resolved * 100), 4) if resolved else None,
        "coverage": round(resolved / total, 6) if total else 0,
        "sample_count": total,
        "decision_count": resolved,
    }


def _aggregate_component(
    direction_components: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    usable = {
        direction: value
        for direction, value in direction_components.items()
        if value["score"] is not None
    }
    return aggregate_multilingual_v03(usable)


def build_v03_leaderboard(
    runs: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    *,
    structural_resolutions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine hard reliability, adaptive pairwise decisions, and observed telemetry.

    Each match object contains ``pack`` and the completed adaptive ``judge_report``.
    Direction quality is ``60% soft preference + 40% hard reliability``. The final
    intelligence score is the equal-weight average of all 18 direction scores; missing
    directions remain incomplete and are never renormalized.
    """
    if len(runs) < 2:
        raise V03AggregateError("A leaderboard requires at least two contestant runs.")
    structural = _structural_map(structural_resolutions or [])
    contestants: dict[str, dict[str, Any]] = {}
    hard: dict[str, dict[str, dict[str, Any]]] = {}
    soft: dict[str, dict[str, dict[str, Any]]] = {}

    exam_hashes = {run.get("exam_sha256") for run in runs}
    if len(exam_hashes) != 1 or None in exam_hashes:
        raise V03AggregateError("Contestant runs do not share one exam hash.")
    for run in runs:
        if run.get("status") != "completed":
            raise V03AggregateError("All contestant runs must be completed.")
        identity, digest = _identity(run)
        if digest in contestants:
            raise V03AggregateError("Duplicate contestant execution identity.")
        contestants[digest] = {"identity": identity, "run": run}
        hard[digest] = defaultdict(_empty_bucket)
        soft[digest] = defaultdict(_empty_bucket)
        for result in run.get("results", []):
            job_id = result.get("job_id")
            if not isinstance(job_id, str):
                raise V03AggregateError("Every result requires a job_id.")
            direction = _direction(job_id)
            for item in (result.get("validation") or {}).get("items", []):
                occurrence_id = f"{job_id}::{item.get('item_id')}"
                route = (item.get("classification") or {}).get("route")
                bucket = hard[digest][direction]
                bucket["total"] += 1
                if route == "pass":
                    bucket["resolved"] += 1
                    bucket["points"] += 1
                elif route == "hard_fail":
                    bucket["resolved"] += 1
                elif route == "structural_judges":
                    decision = structural.get((digest, occurrence_id))
                    if decision is not None:
                        bucket["resolved"] += 1
                        bucket["points"] += int(decision)
                else:
                    raise V03AggregateError(f"Unsupported structural route: {route!r}")

    seen_matches = set()
    for match in matches:
        pack = match.get("pack") or {}
        report = match.get("judge_report") or {}
        unhashed_pack = {key: value for key, value in pack.items() if key != "sha256"}
        if pack.get("sha256") != _sha256(unhashed_pack):
            raise V03AggregateError("Pairwise pack hash is invalid.")
        cases = pack.get("soft_judge_cases") or []
        if report.get("status") != "completed" or report.get("cases_sha256") != _sha256(cases):
            raise V03AggregateError("Judge report is incomplete or bound to different cases.")
        identities = pack.get("candidate_identities") or {}
        digests = tuple(_sha256(identities.get(label)) for label in ("candidate_a", "candidate_b"))
        if any(digest not in contestants for digest in digests):
            raise V03AggregateError("Pairwise match references an unknown contestant.")
        match_key = tuple(sorted(digests))
        if match_key in seen_matches:
            raise V03AggregateError("Duplicate pairwise contestant match.")
        seen_matches.add(match_key)
        decisions = {
            decision["case_id"]: decision
            for decision in (report.get("summary") or {}).get("decisions", [])
        }
        if set(decisions) != {case["id"] for case in cases}:
            raise V03AggregateError("Judge decisions do not align with the pairwise pack.")
        for case in cases:
            direction = case["input"]["language_pair"]
            if direction not in V03_DIRECTIONS:
                raise V03AggregateError(f"Unknown match direction: {direction}")
            decision = decisions[case["id"]]
            for digest in digests:
                soft[digest][direction]["total"] += 1
            verdict = decision.get("verdict")
            if not decision.get("resolved") or verdict not in _POINTS:
                continue
            points = _POINTS[verdict]
            for digest, point in zip(digests, points, strict=True):
                soft[digest][direction]["resolved"] += 1
                soft[digest][direction]["points"] += point

    profiles = []
    for digest, contestant in contestants.items():
        hard_components = {
            direction: _component(hard[digest][direction]) for direction in V03_DIRECTIONS
        }
        soft_components = {
            direction: _component(soft[digest][direction]) for direction in V03_DIRECTIONS
        }
        direction_scores = {}
        normalized = {}
        for direction in V03_DIRECTIONS:
            hard_value = hard_components[direction]
            soft_value = soft_components[direction]
            score = None
            if hard_value["score"] is not None and soft_value["score"] is not None:
                soft_score = Decimal(str(soft_value["score"]))
                hard_score = Decimal(str(hard_value["score"]))
                score = round(
                    soft_score * Decimal("0.6") + hard_score * Decimal("0.4"), 4
                )
                normalized[direction] = {
                    "score": score,
                    "coverage": min(hard_value["coverage"], soft_value["coverage"]),
                    "sample_count": hard_value["sample_count"] + soft_value["sample_count"],
                    "decision_count": hard_value["decision_count"] + soft_value["decision_count"],
                }
            direction_scores[direction] = {
                "score": float(score) if score is not None else None,
                "hard_format": hard_value,
                "soft_preference": soft_value,
            }
        multilingual = aggregate_multilingual_v03(normalized)
        hard_aggregate = _aggregate_component(hard_components)
        soft_aggregate = _aggregate_component(soft_components)
        profiles.append(
            {
                "execution_identity_sha256": digest,
                "recipe": deepcopy(contestant["identity"]),
                "scores": {
                    **multilingual,
                    "hard_format": hard_aggregate["overall_intelligence"],
                    "soft_preference": soft_aggregate["overall_intelligence"],
                    "direction_components": direction_scores,
                },
                "telemetry": _telemetry(contestant["run"]),
            }
        )
    profiles.sort(key=lambda value: value["execution_identity_sha256"])
    complete = all(
        profile["scores"]["overall_intelligence"]["status"] == "complete"
        for profile in profiles
    )
    leaderboard = {
        "schema_version": 1,
        "protocol": "aventine-multilingual-tournament-v0.3",
        "score_version": "multilingual-pilot-v0.3-60soft-40hard",
        "status": "complete" if complete else "incomplete",
        "exam_sha256": next(iter(exam_hashes)),
        "direction_count": len(V03_DIRECTIONS),
        "contestant_count": len(profiles),
        "match_count": len(matches),
        "profiles": profiles,
    }
    validate_payload(leaderboard, "v03-leaderboard.schema.json")
    return leaderboard


__all__ = ["V03AggregateError", "build_v03_leaderboard"]

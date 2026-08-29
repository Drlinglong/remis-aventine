"""Equal-direction score aggregation for the frozen Aventine v0.3 topology."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from remis_aventine.exam_execution import V03_DIRECTIONS

EAST_ASIAN_TARGETS = ("ja", "ko")
CONTINENTAL_TARGETS = ("de", "ru", "fr", "es", "pt-BR", "tr")


class MultilingualScoringError(ValueError):
    """Raised when direction evidence is malformed."""


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise MultilingualScoringError(f"{name} must be numeric.")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise MultilingualScoringError(f"{name} must be numeric.") from exc
    if not result.is_finite():
        raise MultilingualScoringError(f"{name} must be finite.")
    return result


def _normalize(results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    unknown = sorted(set(results) - set(V03_DIRECTIONS))
    if unknown:
        raise MultilingualScoringError(f"Unknown directions: {', '.join(unknown)}")
    normalized = {}
    for direction, result in results.items():
        if not isinstance(result, dict):
            raise MultilingualScoringError(f"{direction} result must be an object.")
        score = _decimal(result.get("score"), f"{direction}.score")
        coverage = _decimal(result.get("coverage"), f"{direction}.coverage")
        if not 0 <= score <= 100 or not 0 <= coverage <= 1:
            raise MultilingualScoringError(f"{direction} score or coverage is out of range.")
        sample_count = result.get("sample_count")
        decision_count = result.get("decision_count")
        if (
            not isinstance(sample_count, int)
            or isinstance(sample_count, bool)
            or sample_count < 0
            or not isinstance(decision_count, int)
            or isinstance(decision_count, bool)
            or decision_count < 0
        ):
            raise MultilingualScoringError(f"{direction} counts must be non-negative integers.")
        normalized[direction] = {
            "score": score,
            "coverage": coverage,
            "sample_count": sample_count,
            "decision_count": decision_count,
        }
    return normalized


def _number(value: Decimal | None) -> float | int | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantized) if quantized == quantized.to_integral() else float(quantized)


def _measure(normalized: dict[str, dict[str, Any]], directions: tuple[str, ...]) -> dict[str, Any]:
    missing = [direction for direction in directions if direction not in normalized]
    available = [normalized[direction] for direction in directions if direction in normalized]
    if missing:
        return {
            "score": None,
            "sample_count": sum(value["sample_count"] for value in available),
            "decision_count": sum(value["decision_count"] for value in available),
            "coverage": _number(
                sum((value["coverage"] for value in available), Decimal(0))
                / Decimal(len(directions))
            ),
            "status": "incomplete",
            "missing_directions": missing,
        }
    score = sum((value["score"] for value in available), Decimal(0)) / Decimal(len(directions))
    coverage = sum((value["coverage"] for value in available), Decimal(0)) / Decimal(
        len(directions)
    )
    return {
        "score": _number(score),
        "sample_count": sum(value["sample_count"] for value in available),
        "decision_count": sum(value["decision_count"] for value in available),
        "coverage": _number(coverage),
        "status": "complete" if coverage == 1 else "partial",
        "missing_directions": [],
    }


def aggregate_multilingual_v03(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate all 18 directions without renormalizing missing evidence."""
    normalized = _normalize(results)
    east_by_source = {
        source: _measure(normalized, tuple(f"{source}->{target}" for target in EAST_ASIAN_TARGETS))
        for source in ("zh-CN", "en")
    }
    continental_by_source = {
        source: _measure(normalized, tuple(f"{source}->{target}" for target in CONTINENTAL_TARGETS))
        for source in ("zh-CN", "en")
    }
    east = _measure(
        normalized,
        tuple(f"{source}->{target}" for source in ("zh-CN", "en") for target in EAST_ASIAN_TARGETS),
    )
    east["source_groups"] = east_by_source
    continental = _measure(
        normalized,
        tuple(
            f"{source}->{target}" for source in ("zh-CN", "en") for target in CONTINENTAL_TARGETS
        ),
    )
    continental["source_groups"] = continental_by_source
    per_extended_language = {
        target: _measure(normalized, (f"zh-CN->{target}", f"en->{target}"))
        for target in (*EAST_ASIAN_TARGETS, *CONTINENTAL_TARGETS)
    }
    return {
        "score_version": "multilingual-score-v0.3",
        "direction_count": len(V03_DIRECTIONS),
        "overall_intelligence": _measure(normalized, V03_DIRECTIONS),
        "zh_en_core": _measure(normalized, ("zh-CN->en", "en->zh-CN")),
        "east_asian": east,
        "continental": continental,
        "per_extended_language": per_extended_language,
        "direction_scores": {
            direction: (
                {
                    "score": _number(normalized[direction]["score"]),
                    "coverage": _number(normalized[direction]["coverage"]),
                    "sample_count": normalized[direction]["sample_count"],
                    "decision_count": normalized[direction]["decision_count"],
                }
                if direction in normalized
                else None
            )
            for direction in V03_DIRECTIONS
        },
    }


__all__ = [
    "CONTINENTAL_TARGETS",
    "EAST_ASIAN_TARGETS",
    "MultilingualScoringError",
    "aggregate_multilingual_v03",
]

from __future__ import annotations

import pytest

from remis_aventine.exam_execution import V03_DIRECTIONS
from remis_aventine.multilingual_scoring import (
    MultilingualScoringError,
    aggregate_multilingual_v03,
)


def _results(score: float = 80, coverage: float = 1) -> dict[str, dict]:
    return {
        direction: {
            "score": score,
            "coverage": coverage,
            "sample_count": 2,
            "decision_count": 2,
        }
        for direction in V03_DIRECTIONS
    }


def test_all_eighteen_directions_are_equal_weighted() -> None:
    results = _results(0)
    results["zh-CN->en"]["score"] = 100

    aggregate = aggregate_multilingual_v03(results)

    assert aggregate["direction_count"] == 18
    assert aggregate["overall_intelligence"]["score"] == 5.56
    assert aggregate["zh_en_core"]["score"] == 50
    assert aggregate["overall_intelligence"]["status"] == "complete"


def test_source_groups_and_single_language_scores_are_explicit() -> None:
    results = _results(50)
    results["zh-CN->ja"]["score"] = 100
    results["zh-CN->ko"]["score"] = 80
    results["en->ja"]["score"] = 20
    results["en->ko"]["score"] = 0

    aggregate = aggregate_multilingual_v03(results)

    assert aggregate["east_asian"]["source_groups"]["zh-CN"]["score"] == 90
    assert aggregate["east_asian"]["source_groups"]["en"]["score"] == 10
    assert aggregate["east_asian"]["score"] == 50
    assert aggregate["per_extended_language"]["ja"]["score"] == 60
    assert aggregate["per_extended_language"]["ko"]["score"] == 40


def test_missing_direction_never_silently_renormalizes() -> None:
    results = _results()
    del results["en->tr"]

    aggregate = aggregate_multilingual_v03(results)

    assert aggregate["overall_intelligence"]["score"] is None
    assert aggregate["overall_intelligence"]["status"] == "incomplete"
    assert aggregate["overall_intelligence"]["missing_directions"] == ["en->tr"]
    assert aggregate["continental"]["score"] is None
    assert aggregate["per_extended_language"]["tr"]["score"] is None


def test_coverage_is_kept_separate_from_quality() -> None:
    aggregate = aggregate_multilingual_v03(_results(score=90, coverage=0.75))

    assert aggregate["overall_intelligence"]["score"] == 90
    assert aggregate["overall_intelligence"]["coverage"] == 0.75
    assert aggregate["overall_intelligence"]["status"] == "partial"


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda results: results.update({"ja->ko": results["en->ja"]}), "Unknown"),
        (lambda results: results["en->ja"].update(score=101), "out of range"),
        (lambda results: results["en->ja"].update(coverage=-1), "out of range"),
        (lambda results: results["en->ja"].update(sample_count=1.5), "counts"),
    ],
)
def test_malformed_direction_results_are_rejected(mutation, match: str) -> None:
    results = _results()
    mutation(results)
    with pytest.raises(MultilingualScoringError, match=match):
        aggregate_multilingual_v03(results)

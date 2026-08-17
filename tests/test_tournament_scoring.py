from __future__ import annotations

import json
from decimal import Decimal

import pytest

from remis_aventine.tournament_scoring import (
    COVERAGE_POLICY_VERSION,
    EAST_ASIAN_LANGUAGES,
    EUROPEAN_LANGUAGES,
    PILOT_SCORE_VERSION,
    REGIONAL_POLICY_VERSION,
    CoverageDenominator,
    LanguageResult,
    ScoringInputError,
    StageOutcome,
    aggregate_regional_scores,
    calculate_decision_coverage,
    canonical_json,
    compute_pilot_score,
    score_stage,
    stage_multiplier,
)


def _complete_language_results(
    *,
    european_score: int = 80,
    east_asian_score: int = 60,
    sample_count: int = 1,
    coverage: Decimal | float = Decimal("1"),
) -> dict[str, LanguageResult]:
    return {
        language: LanguageResult(european_score, sample_count, coverage)
        for language in EUROPEAN_LANGUAGES
    } | {
        language: LanguageResult(east_asian_score, sample_count, coverage)
        for language in EAST_ASIAN_LANGUAGES
    }


def test_pilot_score_uses_versioned_decimal_formula_and_half_up_rounding() -> None:
    result = compute_pilot_score(Decimal("0.80"), Decimal("1.00"))

    assert result.score_version == PILOT_SCORE_VERSION
    assert result.raw_score == Decimal("88.0000")
    assert result.score == Decimal("88.00")
    assert result.to_dict() == {
        "score_version": "pilot-score-v0.1",
        "score": 88,
        "raw_score": 88,
        "soft_preference": 0.8,
        "hard_reliability": 1,
        "weights": {"soft_preference": 0.6, "hard_reliability": 0.4},
        "rounding": "ROUND_HALF_UP@0.01",
    }

    rounded = compute_pilot_score(Decimal("0.001"), Decimal("0.001"))
    assert rounded.raw_score == Decimal("0.1000")
    assert rounded.score == Decimal("0.10")


@pytest.mark.parametrize(
    "soft, hard",
    [
        (0, 0),
        (1, 1),
        (Decimal("0.25"), Decimal("0.75")),
        (0.1, 0.2),
    ],
)
def test_pilot_score_accepts_inclusive_boundaries_and_is_repeatable(soft, hard) -> None:
    first = compute_pilot_score(soft, hard)
    second = compute_pilot_score(soft, hard)

    assert first.score == second.score
    assert first.canonical_json() == second.canonical_json()


@pytest.mark.parametrize(
    "soft, hard",
    [
        (-0.01, 0.5),
        (0.5, 1.01),
        (float("nan"), 0.5),
        (0.5, float("inf")),
        (True, 0.5),
        (0.5, "not-a-number"),
    ],
)
def test_pilot_score_rejects_invalid_inputs(soft, hard) -> None:
    with pytest.raises(ScoringInputError):
        compute_pilot_score(soft, hard)


@pytest.mark.parametrize(
    "stage, outcome, expected",
    [
        ("translation", "pass", Decimal("1.00")),
        ("translation", "recoverable_hard_failure", Decimal("0.67")),
        ("translation", "recoverable_contract_failure", Decimal("0.67")),
        ("translation", "unusable", Decimal("0.00")),
        ("translation", "misaligned", Decimal("0.00")),
        ("translation", "empty", Decimal("0.00")),
        ("translation", "execution_failure", Decimal("0.00")),
        ("proofreading", "pass", Decimal("1.00")),
        ("proofreading", "hard_failure", Decimal("0.00")),
        ("repair", "contract_failure", Decimal("0.00")),
        ("repair", "execution_failure", Decimal("0.00")),
    ],
)
def test_stage_multiplier_policy(stage, outcome, expected) -> None:
    assert stage_multiplier(stage, outcome) == expected


def test_recoverable_translation_multiplies_existing_score_without_granting_release() -> None:
    result = score_stage(
        "translation",
        Decimal("100"),
        StageOutcome.RECOVERABLE_HARD_FAILURE,
        release_eligible=True,
    )

    assert result.linguistic_score == Decimal("100.00")
    assert result.multiplier == Decimal("0.67")
    assert result.adjusted_score == Decimal("67.00")
    assert result.release_eligible is False


def test_proofreading_failure_is_zero_even_if_translation_was_recoverable() -> None:
    result = score_stage(
        "proofreading",
        Decimal("88.88"),
        "recoverable_hard_failure",
        release_eligible=True,
    )

    assert result.adjusted_score == Decimal("0.00")
    assert result.multiplier == Decimal("0.00")
    assert result.release_eligible is False


def test_stage_score_boundary_and_invalid_inputs() -> None:
    assert score_stage("translation", 0, "pass").adjusted_score == Decimal("0.00")
    assert score_stage("translation", 100, "pass").adjusted_score == Decimal("100.00")
    with pytest.raises(ScoringInputError):
        score_stage("translation", 100.01, "pass")
    with pytest.raises(ScoringInputError):
        score_stage("translation", 20, "not-a-stage-outcome")


def test_decision_coverage_counts_unresolved_without_calling_it_model_failure() -> None:
    result = calculate_decision_coverage(10, 8, unresolved_decisions=2)

    assert result.score_version == COVERAGE_POLICY_VERSION
    assert result.denominator == 10
    assert result.resolved_decisions == 8
    assert result.unresolved_decisions == 2
    assert result.coverage == Decimal("0.800000")
    assert result.coverage_defined is True
    assert "failure" not in result.to_dict()


def test_eligible_decision_coverage_uses_explicit_eligible_denominator() -> None:
    result = calculate_decision_coverage(
        10,
        6,
        eligible_decisions=8,
        denominator=CoverageDenominator.ELIGIBLE,
    )

    assert result.denominator_policy == "eligible"
    assert result.denominator == 8
    assert result.unresolved_decisions == 2
    assert result.coverage == Decimal("0.750000")


def test_zero_decision_coverage_is_explicitly_undefined() -> None:
    result = calculate_decision_coverage(0, 0)

    assert result.coverage == Decimal("0.000000")
    assert result.coverage_defined is False
    assert result.to_dict()["coverage_defined"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"planned_decisions": -1, "resolved_decisions": 0},
        {"planned_decisions": 2, "resolved_decisions": 3},
        {"planned_decisions": 2, "resolved_decisions": 1, "eligible_decisions": 3},
        {
            "planned_decisions": 2,
            "resolved_decisions": 1,
            "denominator": "eligible",
        },
        {
            "planned_decisions": 2,
            "resolved_decisions": 1,
            "unresolved_decisions": 0,
        },
    ],
)
def test_decision_coverage_rejects_invalid_inputs(kwargs) -> None:
    with pytest.raises(ScoringInputError):
        calculate_decision_coverage(**kwargs)


def test_regional_aggregation_is_equal_weighted_and_multilingual_is_50_50() -> None:
    result = aggregate_regional_scores(
        _complete_language_results(european_score=80, east_asian_score=60)
    )

    assert result.score_version == REGIONAL_POLICY_VERSION
    assert result.region("European").score == Decimal("80.00")
    assert result.region("East Asian").score == Decimal("60.00")
    assert result.region("Multilingual").score == Decimal("70.00")
    assert result.region("European").complete is True


def test_regional_aggregation_does_not_weight_by_unequal_sample_count() -> None:
    results = _complete_language_results()
    results["FR"] = LanguageResult(100, 100, 1)
    results["DE"] = LanguageResult(0, 1, 1)

    result = aggregate_regional_scores(results)

    assert result.region("European").score == Decimal("70.00")


def test_missing_language_makes_region_and_multilingual_incomplete() -> None:
    results = _complete_language_results()
    del results["FR"]

    result = aggregate_regional_scores(results)
    european = result.region("European")
    multilingual = result.region("Multilingual")

    assert european.complete is False
    assert european.score is None
    assert european.missing_languages == ("FR",)
    assert multilingual.complete is False
    assert multilingual.score is None
    assert multilingual.missing_languages == ("FR",)


def test_sample_and_coverage_thresholds_are_explicit_and_cause_incomplete() -> None:
    results = _complete_language_results(sample_count=2, coverage=0.75)

    result = aggregate_regional_scores(results, min_samples=3, min_coverage=0.8)
    european = result.region("European")
    east_asian = result.region("East Asian")

    assert result.min_samples == 3
    assert result.min_coverage == Decimal("0.800000")
    assert european.complete is False
    assert set(european.sample_insufficient_languages) == set(EUROPEAN_LANGUAGES)
    assert set(european.coverage_insufficient_languages) == set(EUROPEAN_LANGUAGES)
    assert east_asian.complete is False
    assert result.region("Multilingual").score is None


def test_undefined_language_coverage_is_incomplete_even_with_zero_threshold() -> None:
    results = _complete_language_results()
    results["FR"] = LanguageResult(80, 1, 0, coverage_defined=False)

    result = aggregate_regional_scores(results, min_coverage=0)

    assert result.region("European").complete is False
    assert result.region("European").coverage_insufficient_languages == ("FR",)


def test_empty_regional_input_is_explicitly_incomplete_not_silently_extrapolated() -> None:
    result = aggregate_regional_scores({})

    for region in ("European", "East Asian", "Multilingual"):
        assert result.region(region).complete is False
        assert result.region(region).score is None


def test_regional_input_can_be_json_like_and_rejects_unknown_language() -> None:
    payload = {
        language: {"score": 50, "sample_count": 1, "coverage": 1}
        for language in (*EUROPEAN_LANGUAGES, *EAST_ASIAN_LANGUAGES)
    }
    assert aggregate_regional_scores(payload).region("Multilingual").score == Decimal("50.00")

    with pytest.raises(ScoringInputError):
        aggregate_regional_scores({"EN": {"score": 50, "sample_count": 1, "coverage": 1}})


def test_results_have_stable_key_order_and_canonical_json() -> None:
    input_results = _complete_language_results()
    result = aggregate_regional_scores(dict(reversed(list(input_results.items()))))
    payload = result.to_dict()
    assert list(payload) == [
        "score_version",
        "policy_version",
        "min_samples",
        "min_coverage",
        "language_results",
        "regions",
    ]
    assert list(payload["language_results"]) == [
        "FR",
        "DE",
        "RU",
        "ES",
        "PT",
        "TR",
        "ZH-CN",
        "JA",
        "KO",
    ]
    assert payload["language_results"]["FR"] == {
        "score": 80,
        "sample_count": 1,
        "coverage": 1,
        "coverage_defined": True,
    }
    assert list(payload["regions"]) == ["European", "East Asian", "Multilingual"]
    assert result.canonical_json() == canonical_json(result)
    assert json.loads(result.canonical_json()) == payload


@pytest.mark.parametrize(
    "args",
    [
        (-1, 1, 1),
        (101, 1, 1),
        (50, -1, 1),
        (50, 1, 1.1),
    ],
)
def test_language_result_rejects_out_of_range_values(args) -> None:
    with pytest.raises(ScoringInputError):
        LanguageResult(*args)

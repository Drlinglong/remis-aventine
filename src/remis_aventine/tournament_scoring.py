"""Deterministic, policy-versioned scoring primitives for Aventine tournaments.

This module deliberately contains policy and arithmetic only.  It does not run
models, inspect judge output, or implement presentation logic.  Callers can
feed it already-normalized linguistic results and serialize the returned
immutable result objects with :func:`canonical_json`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType
from typing import Any, TypeAlias

PILOT_SCORE_VERSION = "pilot-score-v0.1"
STAGE_POLICY_VERSION = "stage-policy-v0.1"
COVERAGE_POLICY_VERSION = "coverage-v0.1"
REGIONAL_POLICY_VERSION = "regional-v0.1"

PILOT_ROUNDING_POLICY = "ROUND_HALF_UP@0.01"
SCORE_QUANTUM = Decimal("0.01")
DISPLAY_QUANTUM = Decimal("0.000001")
SOFT_PREFERENCE_WEIGHT = Decimal("0.60")
HARD_RELIABILITY_WEIGHT = Decimal("0.40")
RECOVERABLE_TRANSLATION_MULTIPLIER = Decimal("0.67")

EUROPEAN_LANGUAGES = ("FR", "DE", "RU", "ES", "PT", "TR")
EAST_ASIAN_LANGUAGES = ("ZH-CN", "JA", "KO")
REGIONAL_LANGUAGE_GROUPS = {
    "European": EUROPEAN_LANGUAGES,
    "East Asian": EAST_ASIAN_LANGUAGES,
}
REGION_ORDER = ("European", "East Asian", "Multilingual")
SUPPORTED_REGIONAL_LANGUAGES = frozenset((*EUROPEAN_LANGUAGES, *EAST_ASIAN_LANGUAGES))
SUPPORTED_LANGUAGE_ORDER = (*EUROPEAN_LANGUAGES, *EAST_ASIAN_LANGUAGES)

NumberLike: TypeAlias = Decimal | int | float | str


class ScoringInputError(ValueError):
    """Raised when a scoring input violates the published policy contract."""


class Stage(str, Enum):
    """Evaluation stage to which a failure multiplier is applied."""

    TRANSLATION = "translation"
    PROOFREADING = "proofreading"
    REPAIR = "repair"


class StageOutcome(str, Enum):
    """Normalized outcome labels consumed by the stage policy."""

    PASS = "pass"
    RECOVERABLE_HARD_FAILURE = "recoverable_hard_failure"
    RECOVERABLE_CONTRACT_FAILURE = "recoverable_contract_failure"
    HARD_FAILURE = "hard_failure"
    CONTRACT_FAILURE = "contract_failure"
    UNUSABLE = "unusable"
    MISALIGNED = "misaligned"
    EMPTY = "empty"
    EXECUTION_FAILURE = "execution_failure"


class CoverageDenominator(str, Enum):
    """The planned-decision population used as a coverage denominator."""

    PLANNED = "planned"
    ELIGIBLE = "eligible"


@dataclass(frozen=True, slots=True)
class PilotScore:
    """A versioned Pilot Score v0.1 calculation.

    ``soft_preference`` and ``hard_reliability`` are normalized proportions in
    ``[0, 1]``.  ``score`` and ``raw_score`` are on a 0--100 scale.  The
    published score is rounded to two decimal places with ROUND_HALF_UP;
    internal arithmetic remains Decimal-based.
    """

    score_version: str
    soft_preference: Decimal
    hard_reliability: Decimal
    raw_score: Decimal
    score: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, JSON-compatible representation."""

        return {
            "score_version": self.score_version,
            "score": _json_number(self.score),
            "raw_score": _json_number(_quantize(self.raw_score, DISPLAY_QUANTUM)),
            "soft_preference": _json_number(_quantize(self.soft_preference, DISPLAY_QUANTUM)),
            "hard_reliability": _json_number(_quantize(self.hard_reliability, DISPLAY_QUANTUM)),
            "weights": {
                "soft_preference": _json_number(SOFT_PREFERENCE_WEIGHT),
                "hard_reliability": _json_number(HARD_RELIABILITY_WEIGHT),
            },
            "rounding": PILOT_ROUNDING_POLICY,
        }

    def canonical_json(self) -> str:
        """Return a stable JSON encoding suitable for hashing or snapshots."""

        return canonical_json(self)


def compute_pilot_score(
    soft_preference: NumberLike,
    hard_reliability: NumberLike,
    *,
    score_version: str = PILOT_SCORE_VERSION,
) -> PilotScore:
    """Compute ``100 * (0.60 * soft + 0.40 * hard)`` deterministically.

    Both inputs must be finite numeric values in the inclusive range ``[0, 1]``.
    Floats are converted through their shortest decimal string before Decimal
    arithmetic, so the binary representation of a float is never scored
    directly.  The raw result is retained for diagnostics and the published
    result is rounded with :data:`PILOT_ROUNDING_POLICY`.
    """

    _validate_version(score_version, "score_version")
    soft = _bounded_decimal(soft_preference, "soft_preference", Decimal("0"), Decimal("1"))
    hard = _bounded_decimal(hard_reliability, "hard_reliability", Decimal("0"), Decimal("1"))
    raw_score = Decimal("100") * (SOFT_PREFERENCE_WEIGHT * soft + HARD_RELIABILITY_WEIGHT * hard)
    score = _quantize(raw_score, SCORE_QUANTUM)
    return PilotScore(
        score_version=score_version,
        soft_preference=soft,
        hard_reliability=hard,
        raw_score=raw_score,
        score=score,
    )


_OUTCOME_ALIASES = {
    "recoverable_hard": StageOutcome.RECOVERABLE_HARD_FAILURE.value,
    "recoverable_contract": StageOutcome.RECOVERABLE_CONTRACT_FAILURE.value,
    "hard": StageOutcome.HARD_FAILURE.value,
    "contract": StageOutcome.CONTRACT_FAILURE.value,
    "execution": StageOutcome.EXECUTION_FAILURE.value,
}
_RECOVERABLE_TRANSLATION_OUTCOMES = frozenset(
    {
        StageOutcome.RECOVERABLE_HARD_FAILURE,
        StageOutcome.RECOVERABLE_CONTRACT_FAILURE,
    }
)


@dataclass(frozen=True, slots=True)
class StageScore:
    """A linguistic score after applying the stage-specific failure policy.

    ``linguistic_score`` and ``adjusted_score`` use a 0--100 scale.  A
    recoverable translation failure can retain linguistic evidence at 0.67,
    but it can never turn ``release_eligible`` into ``True``.  Proofreading
    and repair failures are non-recoverable under this policy.
    """

    policy_version: str
    stage: str
    outcome: str
    linguistic_score: Decimal
    multiplier: Decimal
    adjusted_score: Decimal
    release_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, JSON-compatible representation."""

        return {
            "policy_version": self.policy_version,
            "stage": self.stage,
            "outcome": self.outcome,
            "linguistic_score": _json_number(self.linguistic_score),
            "multiplier": _json_number(self.multiplier),
            "adjusted_score": _json_number(self.adjusted_score),
            "release_eligible": self.release_eligible,
        }

    def canonical_json(self) -> str:
        """Return a stable JSON encoding suitable for hashing or snapshots."""

        return canonical_json(self)


def stage_multiplier(
    stage: Stage | str,
    outcome: StageOutcome | str,
) -> Decimal:
    """Return the deterministic multiplier for a stage outcome.

    Translation pass is 1.00, recoverable hard/contract failure is 0.67, and
    all unusable, misaligned, empty, unrecoverable, or execution failures are
    zero.  Proofreading and repair pass is 1.00 and every non-pass outcome is
    zero.
    """

    normalized_stage = _coerce_stage(stage)
    normalized_outcome = _coerce_outcome(outcome)
    if normalized_outcome is StageOutcome.PASS:
        return Decimal("1.00")
    if (
        normalized_stage is Stage.TRANSLATION
        and normalized_outcome in _RECOVERABLE_TRANSLATION_OUTCOMES
    ):
        return RECOVERABLE_TRANSLATION_MULTIPLIER
    return Decimal("0.00")


def score_stage(
    stage: Stage | str,
    linguistic_score: NumberLike,
    outcome: StageOutcome | str,
    *,
    release_eligible: bool = True,
    policy_version: str = STAGE_POLICY_VERSION,
) -> StageScore:
    """Apply stage policy to an existing 0--100 linguistic score.

    ``release_eligible`` is an upstream hard-validator decision.  Passing a
    failed or recoverable outcome always forces the returned value to ``False``;
    the multiplier never grants release eligibility.
    """

    _validate_version(policy_version, "policy_version")
    if not isinstance(release_eligible, bool):
        raise ScoringInputError("release_eligible must be a bool")
    normalized_stage = _coerce_stage(stage)
    normalized_outcome = _coerce_outcome(outcome)
    score = _bounded_decimal(linguistic_score, "linguistic_score", Decimal("0"), Decimal("100"))
    multiplier = stage_multiplier(normalized_stage, normalized_outcome)
    adjusted_score = _quantize(score * multiplier, SCORE_QUANTUM)
    return StageScore(
        policy_version=policy_version,
        stage=normalized_stage.value,
        outcome=normalized_outcome.value,
        linguistic_score=_quantize(score, SCORE_QUANTUM),
        multiplier=multiplier,
        adjusted_score=adjusted_score,
        release_eligible=release_eligible if normalized_outcome is StageOutcome.PASS else False,
    )


@dataclass(frozen=True, slots=True)
class DecisionCoverage:
    """Coverage of resolved decisions over a planned or eligible denominator.

    An unresolved decision is not a model failure.  It contributes to the
    unresolved count and lowers coverage only.  A zero denominator produces
    ``coverage=0`` with ``coverage_defined=False`` so callers cannot mistake
    an empty population for complete coverage.
    """

    score_version: str
    denominator_policy: str
    planned_decisions: int
    eligible_decisions: int
    denominator: int
    resolved_decisions: int
    unresolved_decisions: int
    coverage: Decimal
    coverage_defined: bool

    @property
    def coverage_percent(self) -> Decimal:
        """Return coverage on a 0--100 display scale."""

        return _quantize(self.coverage * Decimal("100"), SCORE_QUANTUM)

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, JSON-compatible representation."""

        return {
            "score_version": self.score_version,
            "denominator_policy": self.denominator_policy,
            "planned_decisions": self.planned_decisions,
            "eligible_decisions": self.eligible_decisions,
            "denominator": self.denominator,
            "resolved_decisions": self.resolved_decisions,
            "unresolved_decisions": self.unresolved_decisions,
            "coverage": _json_number(self.coverage),
            "coverage_percent": _json_number(self.coverage_percent),
            "coverage_defined": self.coverage_defined,
        }

    def canonical_json(self) -> str:
        """Return a stable JSON encoding suitable for hashing or snapshots."""

        return canonical_json(self)


def calculate_decision_coverage(
    planned_decisions: int,
    resolved_decisions: int,
    *,
    eligible_decisions: int | None = None,
    denominator: CoverageDenominator | str = CoverageDenominator.PLANNED,
    unresolved_decisions: int | None = None,
    score_version: str = COVERAGE_POLICY_VERSION,
) -> DecisionCoverage:
    """Calculate decision coverage without treating unresolved as failure.

    ``denominator`` must be ``"planned"`` or ``"eligible"``.  The planned
    population is always required; the eligible population is required when
    it is selected as the denominator and must not exceed the planned count.
    If ``unresolved_decisions`` is supplied it must equal
    ``denominator - resolved_decisions``.
    """

    _validate_version(score_version, "score_version")
    planned = _non_negative_int(planned_decisions, "planned_decisions")
    resolved = _non_negative_int(resolved_decisions, "resolved_decisions")
    normalized_denominator = _coerce_denominator(denominator)
    if eligible_decisions is None:
        if normalized_denominator is CoverageDenominator.ELIGIBLE:
            raise ScoringInputError("eligible_decisions is required when denominator='eligible'")
        eligible = planned
    else:
        eligible = _non_negative_int(eligible_decisions, "eligible_decisions")
        if eligible > planned:
            raise ScoringInputError("eligible_decisions cannot exceed planned_decisions")
    denominator_count = (
        planned if normalized_denominator is CoverageDenominator.PLANNED else eligible
    )
    if resolved > denominator_count:
        raise ScoringInputError("resolved_decisions cannot exceed the denominator")
    calculated_unresolved = denominator_count - resolved
    if unresolved_decisions is None:
        unresolved = calculated_unresolved
    else:
        unresolved = _non_negative_int(unresolved_decisions, "unresolved_decisions")
        if unresolved != calculated_unresolved:
            raise ScoringInputError(
                "unresolved_decisions must equal denominator - resolved_decisions"
            )
    coverage_defined = denominator_count != 0
    coverage = (
        _quantize(Decimal(resolved) / Decimal(denominator_count), DISPLAY_QUANTUM)
        if coverage_defined
        else Decimal("0.000000")
    )
    return DecisionCoverage(
        score_version=score_version,
        denominator_policy=normalized_denominator.value,
        planned_decisions=planned,
        eligible_decisions=eligible,
        denominator=denominator_count,
        resolved_decisions=resolved,
        unresolved_decisions=unresolved,
        coverage=coverage,
        coverage_defined=coverage_defined,
    )


@dataclass(frozen=True, slots=True)
class LanguageResult:
    """A per-language linguistic score and its evidence sufficiency metadata.

    ``score`` is on a 0--100 scale, ``coverage`` is a normalized proportion in
    ``[0, 1]``, and ``sample_count`` is the number of evaluated samples.  A
    ``coverage_defined=False`` result is explicitly incomplete even when a
    caller sets a permissive minimum coverage threshold.
    """

    score: Decimal
    sample_count: int
    coverage: Decimal
    coverage_defined: bool = True

    def __post_init__(self) -> None:
        score = _bounded_decimal(self.score, "score", Decimal("0"), Decimal("100"))
        sample_count = _non_negative_int(self.sample_count, "sample_count")
        coverage = _bounded_decimal(self.coverage, "coverage", Decimal("0"), Decimal("1"))
        if not isinstance(self.coverage_defined, bool):
            raise ScoringInputError("coverage_defined must be a bool")
        object.__setattr__(self, "score", _quantize(score, SCORE_QUANTUM))
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(self, "coverage", _quantize(coverage, DISPLAY_QUANTUM))

    def to_dict(self) -> dict[str, Any]:
        """Return normalized per-language evidence as JSON-compatible data."""

        return {
            "score": _json_number(self.score),
            "sample_count": self.sample_count,
            "coverage": _json_number(self.coverage),
            "coverage_defined": self.coverage_defined,
        }


@dataclass(frozen=True, slots=True)
class RegionScore:
    """The equal-weight result and completeness diagnostics for one region."""

    region: str
    required_languages: tuple[str, ...]
    score: Decimal | None
    complete: bool
    included_languages: tuple[str, ...]
    missing_languages: tuple[str, ...]
    sample_insufficient_languages: tuple[str, ...]
    coverage_insufficient_languages: tuple[str, ...]
    incomplete_reasons: tuple[str, ...]
    policy_version: str
    min_samples: int
    min_coverage: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, JSON-compatible representation."""

        return {
            "region": self.region,
            "score": _json_number(self.score),
            "complete": self.complete,
            "required_languages": list(self.required_languages),
            "included_languages": list(self.included_languages),
            "missing_languages": list(self.missing_languages),
            "sample_insufficient_languages": list(self.sample_insufficient_languages),
            "coverage_insufficient_languages": list(self.coverage_insufficient_languages),
            "incomplete_reasons": list(self.incomplete_reasons),
            "policy_version": self.policy_version,
            "min_samples": self.min_samples,
            "min_coverage": _json_number(self.min_coverage),
        }

    def canonical_json(self) -> str:
        """Return a stable JSON encoding suitable for hashing or snapshots."""

        return canonical_json(self)


@dataclass(frozen=True, slots=True)
class RegionalAggregation:
    """Versioned European, East Asian, and 50/50 multilingual aggregation."""

    score_version: str
    policy_version: str
    min_samples: int
    min_coverage: Decimal
    language_results: Mapping[str, LanguageResult]
    regions: Mapping[str, RegionScore]

    def __post_init__(self) -> None:
        _validate_version(self.score_version, "score_version")
        _validate_version(self.policy_version, "policy_version")
        min_samples = _positive_int(self.min_samples, "min_samples")
        min_coverage = _bounded_decimal(
            self.min_coverage, "min_coverage", Decimal("0"), Decimal("1")
        )
        language_results = _normalize_language_results(self.language_results)
        normalized_language_results = {
            language: language_results[language]
            for language in SUPPORTED_LANGUAGE_ORDER
            if language in language_results
        }
        normalized_regions = {
            region: self.regions[region] for region in REGION_ORDER if region in self.regions
        }
        object.__setattr__(self, "min_samples", min_samples)
        object.__setattr__(self, "min_coverage", _quantize(min_coverage, DISPLAY_QUANTUM))
        object.__setattr__(
            self,
            "language_results",
            MappingProxyType(normalized_language_results),
        )
        object.__setattr__(self, "regions", MappingProxyType(normalized_regions))

    def region(self, name: str) -> RegionScore:
        """Return a named regional result, raising ``KeyError`` if unavailable."""

        try:
            return self.regions[name]
        except KeyError as exc:
            raise KeyError(f"unknown region: {name}") from exc

    def to_dict(self) -> dict[str, Any]:
        """Return a stable, JSON-compatible representation."""

        return {
            "score_version": self.score_version,
            "policy_version": self.policy_version,
            "min_samples": self.min_samples,
            "min_coverage": _json_number(self.min_coverage),
            "language_results": {
                language: self.language_results[language].to_dict()
                for language in SUPPORTED_LANGUAGE_ORDER
                if language in self.language_results
            },
            "regions": {
                region: self.regions[region].to_dict()
                for region in REGION_ORDER
                if region in self.regions
            },
        }

    def canonical_json(self) -> str:
        """Return a stable JSON encoding suitable for hashing or snapshots."""

        return canonical_json(self)


def aggregate_regional_scores(
    language_results: Mapping[str, LanguageResult | Mapping[str, Any]],
    *,
    min_samples: int = 1,
    min_coverage: NumberLike = Decimal("1"),
    score_version: str = REGIONAL_POLICY_VERSION,
    policy_version: str = REGIONAL_POLICY_VERSION,
) -> RegionalAggregation:
    """Aggregate language scores with explicit completeness requirements.

    European is the equal-weight mean of FR/DE/RU/ES/PT/TR; East Asian is the
    equal-weight mean of ZH-CN/JA/KO; Multilingual is exactly 50/50 between
    those two regional scores.  Every required language must be present and
    meet ``min_samples`` and ``min_coverage``.  Missing or insufficient data
    yields ``score=None`` and ``complete=False``; available languages are never
    silently used as a substitute for the required set.
    """

    _validate_version(score_version, "score_version")
    _validate_version(policy_version, "policy_version")
    minimum_samples = _positive_int(min_samples, "min_samples")
    minimum_coverage = _bounded_decimal(min_coverage, "min_coverage", Decimal("0"), Decimal("1"))
    normalized_results = _normalize_language_results(language_results)
    regions = {
        "European": _aggregate_region(
            "European",
            EUROPEAN_LANGUAGES,
            normalized_results,
            minimum_samples,
            minimum_coverage,
            policy_version,
        ),
        "East Asian": _aggregate_region(
            "East Asian",
            EAST_ASIAN_LANGUAGES,
            normalized_results,
            minimum_samples,
            minimum_coverage,
            policy_version,
        ),
    }
    regions["Multilingual"] = _aggregate_multilingual_region(
        regions["European"],
        regions["East Asian"],
        minimum_samples,
        minimum_coverage,
        policy_version,
    )
    return RegionalAggregation(
        score_version=score_version,
        policy_version=policy_version,
        min_samples=minimum_samples,
        min_coverage=minimum_coverage,
        language_results=normalized_results,
        regions=regions,
    )


def canonical_json(value: Any) -> str:
    """Canonicalize a scoring result or JSON-like value for stable comparison.

    Result objects use their ``to_dict`` method.  Mapping keys are sorted and
    compact separators are used; non-finite JSON values are rejected.
    """

    payload = value.to_dict() if hasattr(value, "to_dict") else value
    return json.dumps(
        _json_safe(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _aggregate_region(
    region: str,
    required_languages: tuple[str, ...],
    results: Mapping[str, LanguageResult],
    min_samples: int,
    min_coverage: Decimal,
    policy_version: str,
) -> RegionScore:
    missing = tuple(language for language in required_languages if language not in results)
    sample_insufficient = tuple(
        language
        for language in required_languages
        if language in results and results[language].sample_count < min_samples
    )
    coverage_insufficient = tuple(
        language
        for language in required_languages
        if language in results
        and (not results[language].coverage_defined or results[language].coverage < min_coverage)
    )
    incomplete_reasons = []
    if missing:
        incomplete_reasons.append("missing_language")
    if sample_insufficient:
        incomplete_reasons.append("sample_threshold")
    if coverage_insufficient:
        incomplete_reasons.append("coverage_threshold")
    complete = not (missing or sample_insufficient or coverage_insufficient)
    included = tuple(
        language
        for language in required_languages
        if language in results
        and language not in sample_insufficient
        and language not in coverage_insufficient
    )
    score = (
        _quantize(
            sum((results[language].score for language in required_languages), Decimal("0"))
            / Decimal(len(required_languages)),
            SCORE_QUANTUM,
        )
        if complete
        else None
    )
    return RegionScore(
        region=region,
        required_languages=required_languages,
        score=score,
        complete=complete,
        included_languages=included,
        missing_languages=missing,
        sample_insufficient_languages=sample_insufficient,
        coverage_insufficient_languages=coverage_insufficient,
        incomplete_reasons=tuple(incomplete_reasons),
        policy_version=policy_version,
        min_samples=min_samples,
        min_coverage=_quantize(min_coverage, DISPLAY_QUANTUM),
    )


def _aggregate_multilingual_region(
    european: RegionScore,
    east_asian: RegionScore,
    min_samples: int,
    min_coverage: Decimal,
    policy_version: str,
) -> RegionScore:
    missing = _ordered_union(european.missing_languages, east_asian.missing_languages)
    sample_insufficient = _ordered_union(
        european.sample_insufficient_languages,
        east_asian.sample_insufficient_languages,
    )
    coverage_insufficient = _ordered_union(
        european.coverage_insufficient_languages,
        east_asian.coverage_insufficient_languages,
    )
    reasons = []
    if not european.complete:
        reasons.append("european_incomplete")
    if not east_asian.complete:
        reasons.append("east_asian_incomplete")
    score = (
        _quantize((european.score + east_asian.score) / Decimal("2"), SCORE_QUANTUM)
        if european.complete and east_asian.complete
        else None
    )
    return RegionScore(
        region="Multilingual",
        required_languages=(*EUROPEAN_LANGUAGES, *EAST_ASIAN_LANGUAGES),
        score=score,
        complete=european.complete and east_asian.complete,
        included_languages=((*european.included_languages, *east_asian.included_languages)),
        missing_languages=missing,
        sample_insufficient_languages=sample_insufficient,
        coverage_insufficient_languages=coverage_insufficient,
        incomplete_reasons=tuple(reasons),
        policy_version=policy_version,
        min_samples=min_samples,
        min_coverage=_quantize(min_coverage, DISPLAY_QUANTUM),
    )


def _normalize_language_results(
    language_results: Mapping[str, LanguageResult | Mapping[str, Any]],
) -> dict[str, LanguageResult]:
    if not isinstance(language_results, Mapping):
        raise ScoringInputError("language_results must be a mapping")
    normalized: dict[str, LanguageResult] = {}
    for language, value in language_results.items():
        canonical_language = _coerce_language(language)
        if canonical_language in normalized:
            raise ScoringInputError(f"duplicate language result: {canonical_language}")
        if isinstance(value, LanguageResult):
            result = value
        elif isinstance(value, Mapping):
            missing = {"score", "sample_count", "coverage"} - set(value)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ScoringInputError(
                    f"language result for {canonical_language} is missing: {missing_text}"
                )
            result = LanguageResult(
                score=value["score"],
                sample_count=value["sample_count"],
                coverage=value["coverage"],
                coverage_defined=value.get("coverage_defined", True),
            )
        else:
            raise ScoringInputError(
                f"language result for {canonical_language} must be LanguageResult or mapping"
            )
        normalized[canonical_language] = result
    return normalized


def _coerce_language(value: Any) -> str:
    if not isinstance(value, str):
        raise ScoringInputError("language keys must be strings")
    normalized = value.strip().upper().replace("_", "-")
    if normalized not in SUPPORTED_REGIONAL_LANGUAGES:
        raise ScoringInputError(f"unsupported regional language: {value!r}")
    return normalized


def _coerce_stage(value: Stage | str) -> Stage:
    if isinstance(value, Stage):
        return value
    if not isinstance(value, str):
        raise ScoringInputError("stage must be 'translation', 'proofreading', or 'repair'")
    try:
        return Stage(value.strip().lower())
    except ValueError as exc:
        raise ScoringInputError(f"unsupported stage: {value!r}") from exc


def _coerce_outcome(value: StageOutcome | str) -> StageOutcome:
    if isinstance(value, StageOutcome):
        return value
    if not isinstance(value, str):
        raise ScoringInputError("outcome must be a supported stage outcome string")
    normalized = value.strip().lower()
    normalized = _OUTCOME_ALIASES.get(normalized, normalized)
    try:
        return StageOutcome(normalized)
    except ValueError as exc:
        raise ScoringInputError(f"unsupported stage outcome: {value!r}") from exc


def _coerce_denominator(value: CoverageDenominator | str) -> CoverageDenominator:
    if isinstance(value, CoverageDenominator):
        return value
    if not isinstance(value, str):
        raise ScoringInputError("denominator must be 'planned' or 'eligible'")
    try:
        return CoverageDenominator(value.strip().lower())
    except ValueError as exc:
        raise ScoringInputError(f"unsupported denominator: {value!r}") from exc


def _validate_version(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ScoringInputError(f"{name} must be a non-empty string")


def _to_decimal(value: NumberLike, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ScoringInputError(f"{name} must be numeric, not bool")
    try:
        if isinstance(value, float):
            decimal = Decimal(str(value))
        elif isinstance(value, (Decimal, int, str)):
            decimal = Decimal(value)
        else:
            raise ScoringInputError(f"{name} must be Decimal, int, float, or str")
    except (InvalidOperation, ValueError) as exc:
        raise ScoringInputError(f"{name} must be a finite decimal value") from exc
    if not decimal.is_finite():
        raise ScoringInputError(f"{name} must be finite")
    return decimal


def _bounded_decimal(value: NumberLike, name: str, lower: Decimal, upper: Decimal) -> Decimal:
    decimal = _to_decimal(value, name)
    if decimal < lower or decimal > upper:
        raise ScoringInputError(f"{name} must be between {lower} and {upper}")
    return decimal


def _quantize(value: Decimal, quantum: Decimal) -> Decimal:
    try:
        return value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ScoringInputError(
            "decimal value cannot be represented at the requested precision"
        ) from exc


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ScoringInputError(f"{name} must be a non-negative integer")
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ScoringInputError(f"{name} must be a positive integer")
    return value


def _json_number(value: Decimal | None) -> int | float | None:
    if value is None:
        return None
    text = format(value, "f").rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return 0
    if "." not in text:
        return int(text)
    return float(text)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _json_number(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def _ordered_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    values = []
    for group in groups:
        for value in group:
            if value not in values:
                values.append(value)
    return tuple(values)


__all__ = [
    "COVERAGE_POLICY_VERSION",
    "CoverageDenominator",
    "DecisionCoverage",
    "EAST_ASIAN_LANGUAGES",
    "EUROPEAN_LANGUAGES",
    "HARD_RELIABILITY_WEIGHT",
    "LanguageResult",
    "PILOT_ROUNDING_POLICY",
    "PILOT_SCORE_VERSION",
    "PilotScore",
    "RECOVERABLE_TRANSLATION_MULTIPLIER",
    "REGIONAL_LANGUAGE_GROUPS",
    "REGIONAL_POLICY_VERSION",
    "RegionalAggregation",
    "RegionScore",
    "ScoringInputError",
    "SOFT_PREFERENCE_WEIGHT",
    "STAGE_POLICY_VERSION",
    "Stage",
    "StageOutcome",
    "StageScore",
    "SUPPORTED_LANGUAGE_ORDER",
    "SUPPORTED_REGIONAL_LANGUAGES",
    "aggregate_regional_scores",
    "calculate_decision_coverage",
    "canonical_json",
    "compute_pilot_score",
    "score_stage",
    "stage_multiplier",
]

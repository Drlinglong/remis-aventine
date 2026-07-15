from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from remis_aventine.adapters.mt_metrics_eval import (
    MTMetricsEvalAdapterError,
    build_mtme_mqm_pack,
)


@dataclass
class _Error:
    start: int
    end: int
    category: str
    severity: str
    score: float | None = None
    is_source_error: bool = False


@dataclass
class _Rating:
    errors: list[_Error]


class _EvalSet:
    rating_names = {"mqm.merged"}
    std_ref = "refA"
    src = ["source clean", "source minor", "source major", "source critical", "unrated"]
    all_refs = {"refA": ["ref clean", "ref minor", "ref major", "ref critical", "ref"]}
    sys_outputs = {"system-b": ["clean", "minor", "major", "critical", "unrated output"]}

    def Ratings(self, name):
        assert name == "mqm.merged"
        return {
            "system-b": [
                _Rating([]),
                _Rating([_Error(0, 5, "Fluency/Grammar", "Minor")]),
                _Rating([_Error(0, 5, "Accuracy/Omission", "Major")]),
                _Rating([_Error(0, 8, "Accuracy/Non-translation", "Critical")]),
                None,
            ]
        }

    def DocsPerSeg(self):
        return ["doc-1", "doc-1", "doc-2", "doc-2", "doc-3"]

    def RaterIdsPerSeg(self, name):
        assert name == "mqm.merged"
        return {"system-b": ["rater-1", "rater-1", "rater-2", "rater-2", None]}

    def DomainsPerSeg(self):
        return ["news"] * 5


def _factory(_test_set, _language_pair, _data_root):
    return _EvalSet()


def test_build_mtme_pack_is_bounded_balanced_and_reproducible(tmp_path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = build_mtme_mqm_pack(
        "wmt23",
        "en-de",
        "mqm.merged",
        "mt-metrics-eval-v2-test",
        first_path,
        limit=3,
        evalset_factory=_factory,
        library_version="test-version",
    )
    second = build_mtme_mqm_pack(
        "wmt23",
        "en-de",
        "mqm.merged",
        "mt-metrics-eval-v2-test",
        second_path,
        limit=3,
        evalset_factory=_factory,
        library_version="test-version",
    )

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert first["adapter"]["available_rated_case_count"] == 4
    assert first["adapter"]["selection_algorithm"] == "severity-round-robin-sha256-v1"
    assert [case["gold"]["max_severity"] for case in first["cases"]] == [
        "critical",
        "major",
        "minor",
    ]
    critical = first["cases"][0]
    assert critical["gold"]["primary_category"] == "accuracy"
    assert critical["input"]["reference"] == "ref critical"
    assert critical["provenance"]["document"] == "doc-2"
    assert critical["provenance"]["rater"] == "rater-2"
    assert critical["provenance"]["mqm_errors"][0]["start"] == 0
    assert json.loads(first_path.read_text(encoding="utf-8")) == first


def test_mtme_pack_can_filter_systems(tmp_path) -> None:
    with pytest.raises(MTMetricsEvalAdapterError, match="has no systems: missing"):
        build_mtme_mqm_pack(
            "wmt23",
            "en-de",
            "mqm.merged",
            "revision",
            tmp_path / "pack.json",
            systems=["missing"],
            evalset_factory=_factory,
        )


def test_mtme_pack_lists_available_rating_sets(tmp_path) -> None:
    with pytest.raises(MTMetricsEvalAdapterError, match="available: mqm.merged"):
        build_mtme_mqm_pack(
            "wmt23",
            "en-de",
            "unknown",
            "revision",
            tmp_path / "pack.json",
            evalset_factory=_factory,
        )


def test_mtme_pack_rejects_unknown_severity(tmp_path) -> None:
    class BadEvalSet(_EvalSet):
        def Ratings(self, _name):
            return {"system-b": [_Rating([_Error(0, 1, "Other", "catastrophic")])] * 5}

    with pytest.raises(MTMetricsEvalAdapterError, match="Unsupported MQM severity"):
        build_mtme_mqm_pack(
            "wmt23",
            "en-de",
            "mqm.merged",
            "revision",
            tmp_path / "pack.json",
            evalset_factory=lambda *_args: BadEvalSet(),
        )


@pytest.mark.parametrize("limit", [0, -1])
def test_mtme_pack_requires_positive_limit(tmp_path, limit) -> None:
    with pytest.raises(MTMetricsEvalAdapterError, match="greater than zero"):
        build_mtme_mqm_pack(
            "wmt23",
            "en-de",
            "mqm.merged",
            "revision",
            tmp_path / "pack.json",
            limit=limit,
            evalset_factory=_factory,
        )

from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.pilot_aggregate import PilotAggregateError, write_pilot_aggregate


def _run(path: Path, recipe: str, hard: list[tuple[str, bool]]) -> None:
    cases = []
    for index, (track, passed) in enumerate(hard):
        cases.append(
            {
                "id": f"case-{index}",
                "track": track,
                "execution_status": "completed",
                "hard_validation": {"passed": passed},
                "automatic_metrics": {"parsed": True, "item_count_match": True},
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        )
    path.write_text(
        json.dumps(
            {
                "suite": "remis",
                "recipe": {
                    "id": recipe,
                    "snapshot": {"fixture_sha256": "frozen"},
                },
                "summary": {"elapsed_seconds": 2},
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )


def _report(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "suite": "remis-pairwise-report",
                "recipes": {"left": {"id": "recipe.a"}, "right": {"id": "recipe.b"}},
                "judge_run": {
                    "config_fingerprint": "judge",
                    "configuration": {"provider": "deepseek-flash", "model": "deepseek-v4-flash"},
                },
                "cases": [
                    {"decision_source": "judge_position_consistent", "winner": "left"},
                    {"decision_source": "judge_position_consistent", "winner": "tie"},
                    {"decision_source": "judge_position_inconsistent", "winner": "unresolved"},
                    {"decision_source": "hard_validation", "winner": "right"},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_builds_score_with_stage_policy_and_soft_coverage(tmp_path: Path) -> None:
    for profile in ("a", "b"):
        for repeat in range(3):
            _run(
                tmp_path / f"{profile}-{repeat}.json",
                f"recipe.{profile}",
                [("translation", profile == "a"), ("repair", True)],
            )
    _report(tmp_path / "pair.json")
    manifest = {
        "schema_version": 1,
        "aggregate_id": "pilot-test",
        "profiles": [
            {
                "id": profile,
                "label": profile.upper(),
                "runs": [f"{profile}-{repeat}.json" for repeat in range(3)],
            }
            for profile in ("a", "b")
        ],
        "pairwise_reports": ["pair.json"],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    aggregate = write_pilot_aggregate(
        tmp_path / "manifest.json", tmp_path / "out.json", tmp_path / "out.md"
    )

    a, b = aggregate["entries"]
    assert a["profile_id"] == "a"
    assert a["score"]["score"] == 85.0
    assert a["hard_reliability"]["sample_count"] == 6
    assert a["soft_preference"]["coverage"]["coverage"] == 0.5
    assert b["hard_reliability"]["value"] == pytest.approx(0.835)
    assert "PREVIEW aggregate" in (tmp_path / "out.md").read_text(encoding="utf-8")


def test_rejects_missing_round_robin_pair(tmp_path: Path) -> None:
    for profile in ("a", "b", "c"):
        for repeat in range(3):
            _run(
                tmp_path / f"{profile}-{repeat}.json",
                f"recipe.{profile}",
                [("translation", True)],
            )
    _report(tmp_path / "pair.json")
    manifest = {
        "schema_version": 1,
        "profiles": [
            {"id": profile, "runs": [f"{profile}-{repeat}.json" for repeat in range(3)]}
            for profile in ("a", "b", "c")
        ],
        "pairwise_reports": ["pair.json"],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PilotAggregateError, match="pairwise opponents"):
        write_pilot_aggregate(
            tmp_path / "manifest.json", tmp_path / "out.json", tmp_path / "out.md"
        )


def test_misaligned_translation_is_not_recoverable(tmp_path: Path) -> None:
    from remis_aventine.pilot_aggregate import _hard_case_value

    case = {
        "track": "translation",
        "execution_status": "completed",
        "hard_validation": {"passed": False},
        "automatic_metrics": {"parsed": True, "item_count_match": False},
    }

    assert _hard_case_value(case) == 0

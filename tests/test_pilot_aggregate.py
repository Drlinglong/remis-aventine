from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine import pilot_aggregate
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
                "run_id": path.stem,
                "recipe": {
                    "id": recipe,
                    "sha256": recipe.rsplit(".", 1)[-1] * 64,
                    "snapshot": {"fixture_sha256": "frozen"},
                },
                "summary": {"elapsed_seconds": 2},
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )


def _report(
    path: Path,
    left_run_id: str = "a-0",
    right_run_id: str = "b-0",
    *,
    left_recipe: str = "recipe.a",
    right_recipe: str = "recipe.b",
) -> None:
    path.write_text(
        json.dumps(
            {
                "suite": "remis-pairwise-report",
                "recipes": {
                    "left": {
                        "id": left_recipe,
                        "sha256": left_recipe.rsplit(".", 1)[-1] * 64,
                        "run_id": left_run_id,
                    },
                    "right": {
                        "id": right_recipe,
                        "sha256": right_recipe.rsplit(".", 1)[-1] * 64,
                        "run_id": right_run_id,
                    },
                },
                "judge_run": {
                    "config_fingerprint": "judge",
                    "configuration": {"provider": "deepseek-flash", "model": "deepseek-v4-flash"},
                    "estimated_cost_rmb": 0.1,
                    "cumulative_estimated_cost_rmb": 0.25,
                    "http_attempt_count": 1,
                    "cumulative_http_attempt_count": 4,
                },
                "cases": [
                    {"decision_source": "judge_position_consistent", "winner": "left"},
                    {"decision_source": "judge_position_consistent", "winner": "right"},
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
    assert a["score"]["score"] == 70.0
    assert a["hard_reliability"]["sample_count"] == 6
    assert a["soft_preference"]["coverage"]["coverage"] == 0.75
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


def test_anchor_panel_scores_challenger_without_round_robin(tmp_path: Path) -> None:
    profiles = ("high", "mid", "low", "challenger")
    for profile in profiles:
        for repeat in range(3):
            _run(
                tmp_path / f"{profile}-{repeat}.json",
                f"recipe.{profile}",
                [("translation", True), ("repair", True)],
            )
    for anchor in ("high", "mid", "low"):
        _report(
            tmp_path / f"challenger-vs-{anchor}.json",
            "challenger-0",
            f"{anchor}-0",
            left_recipe="recipe.challenger",
            right_recipe=f"recipe.{anchor}",
        )
    manifest = {
        "schema_version": 1,
        "aggregate_id": "anchored-test",
        "selection_policy": {
            "mode": "anchor-panel",
            "revision": "three-tier-v1",
            "anchors": ["high", "mid", "low"],
        },
        "profiles": [
            {
                "id": profile,
                "label": profile.title(),
                "runs": (
                    [f"{profile}-0.json"]
                    if profile in {"high", "mid", "low"}
                    else [f"{profile}-{repeat}.json" for repeat in range(3)]
                ),
            }
            for profile in profiles
        ],
        "pairwise_reports": [f"challenger-vs-{anchor}.json" for anchor in ("high", "mid", "low")],
    }
    aggregate = write_pilot_aggregate(
        _write_manifest(tmp_path, manifest), tmp_path / "anchored.json", tmp_path / "anchored.md"
    )

    assert aggregate["score_version"] == "pilot-score-v0.2-anchored"
    assert aggregate["selection_policy"]["anchors"][0]["profile_id"] == "high"
    assert aggregate["sample_design"]["anchor_count"] == 3
    assert [entry["profile_id"] for entry in aggregate["entries"]] == ["challenger"]
    entry = aggregate["entries"][0]
    assert entry["score"]["score_version"] == "pilot-score-v0.2-anchored"
    assert entry["soft_preference"]["opponents"] == ["high", "low", "mid"]
    assert entry["soft_preference"]["confidence_interval"]["sample_count"] == 9
    assert aggregate["judge_telemetry"]["estimated_cost_rmb"] == 0.75
    assert aggregate["judge_telemetry"]["http_attempt_count"] == 12


def test_anchor_panel_requires_every_anchor_opponent(tmp_path: Path) -> None:
    profiles = ("high", "mid", "low", "challenger")
    for profile in profiles:
        _run(tmp_path / f"{profile}.json", f"recipe.{profile}", [("translation", True)])
    for anchor in ("high", "mid"):
        _report(
            tmp_path / f"challenger-vs-{anchor}.json",
            "challenger",
            anchor,
            left_recipe="recipe.challenger",
            right_recipe=f"recipe.{anchor}",
        )
    manifest = {
        "schema_version": 1,
        "expected_run_count": 1,
        "selection_policy": {
            "mode": "anchor-panel",
            "revision": "three-tier-v1",
            "anchors": ["high", "mid", "low"],
        },
        "profiles": [{"id": profile, "runs": [f"{profile}.json"]} for profile in profiles],
        "pairwise_reports": [
            "challenger-vs-high.json",
            "challenger-vs-mid.json",
        ],
    }

    with pytest.raises(PilotAggregateError, match="expected.*high.*low.*mid"):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))


def test_misaligned_translation_is_not_recoverable(tmp_path: Path) -> None:
    from remis_aventine.pilot_aggregate import _hard_case_value

    case = {
        "track": "translation",
        "execution_status": "completed",
        "hard_validation": {"passed": False},
        "automatic_metrics": {"parsed": True, "item_count_match": False},
    }

    assert _hard_case_value(case) == 0


def _valid_manifest(tmp_path: Path) -> dict:
    _run(tmp_path / "a.json", "recipe.a", [("translation", True)])
    _run(tmp_path / "b.json", "recipe.b", [("translation", True)])
    _report(tmp_path / "pair.json", "a", "b")
    return {
        "schema_version": 1,
        "expected_run_count": 1,
        "profiles": [
            {"id": "a", "runs": ["a.json"]},
            {"id": "b", "runs": ["b.json"]},
        ],
        "pairwise_reports": ["pair.json"],
    }


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_json_helpers_and_hard_case_branches(tmp_path: Path) -> None:
    with pytest.raises(PilotAggregateError, match="Unable to read"):
        pilot_aggregate._read_json(tmp_path / "missing.json")
    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    with pytest.raises(PilotAggregateError, match="JSON object"):
        pilot_aggregate._read_json(array)

    absolute = tmp_path.resolve() / "artifact.json"
    assert pilot_aggregate._resolve(tmp_path / "other", str(absolute)) == absolute
    assert pilot_aggregate._hard_case_value({"execution_status": "failed"}) == 0
    assert (
        pilot_aggregate._hard_case_value(
            {
                "execution_status": "completed",
                "track": "translation",
                "hard_validation": {"passed": False},
                "automatic_metrics": {"parsed": False, "item_count_match": True},
            }
        )
        == pilot_aggregate.RECOVERABLE_TRANSLATION_MULTIPLIER
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda manifest: manifest.update(schema_version=2), "schema_version"),
        (lambda manifest: manifest.update(profiles=[]), "At least two"),
        (lambda manifest: manifest.update(pairwise_reports=[]), "pairwise_reports"),
        (lambda manifest: manifest["profiles"].__setitem__(0, "bad"), "profile entry"),
        (lambda manifest: manifest["profiles"][0].update(id=""), "profile id"),
        (lambda manifest: manifest["profiles"][0].update(runs=[]), "exactly 1 runs"),
    ],
)
def test_manifest_shape_failures(tmp_path: Path, mutate, message: str) -> None:
    manifest = _valid_manifest(tmp_path)
    mutate(manifest)
    with pytest.raises(PilotAggregateError, match=message):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))


@pytest.mark.parametrize(
    ("run_change", "message"),
    [
        ({"suite": "other"}, "non-Remis"),
        ({"recipe": {"id": ""}}, "one recipe id"),
        ({"run_id": ""}, "unique run ids"),
        ({"cases": []}, "has no cases"),
        (
            {
                "recipe": {
                    "id": "recipe.a",
                    "sha256": "a" * 64,
                    "snapshot": {"fixture_sha256": "other"},
                }
            },
            "fixture hash",
        ),
    ],
)
def test_run_artifact_failures(tmp_path: Path, run_change: dict, message: str) -> None:
    manifest = _valid_manifest(tmp_path)
    run = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
    run.update(run_change)
    (tmp_path / "a.json").write_text(json.dumps(run), encoding="utf-8")
    with pytest.raises(PilotAggregateError, match=message):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))


def test_duplicate_recipe_and_pairwise_report_failures(tmp_path: Path) -> None:
    manifest = _valid_manifest(tmp_path)
    run = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    run["recipe"]["id"] = "recipe.a"
    (tmp_path / "b.json").write_text(json.dumps(run), encoding="utf-8")
    with pytest.raises(PilotAggregateError, match="more than one profile"):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))

    manifest = _valid_manifest(tmp_path)
    manifest["pairwise_reports"].append("pair.json")
    with pytest.raises(PilotAggregateError, match="Duplicate pairwise"):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"suite": "other"}, "Not a Remis"),
        (
            {"recipes": {"left": {"id": "unknown"}, "right": {"id": "recipe.b"}}},
            "unknown tournament recipe",
        ),
        (
            {
                "recipes": {
                    "left": {"id": "recipe.a", "sha256": "c" * 64, "run_id": "a"},
                    "right": {"id": "recipe.b", "sha256": "b" * 64, "run_id": "b"},
                }
            },
            "provenance does not match",
        ),
        (
            {"cases": [{"decision_source": "judge_position_consistent", "winner": "unknown"}]},
            "has winner",
        ),
        (
            {"cases": [{"decision_source": "judge_position_inconsistent", "winner": "unresolved"}]},
            "no resolved soft decisions",
        ),
    ],
)
def test_pairwise_artifact_failures(tmp_path: Path, change: dict, message: str) -> None:
    manifest = _valid_manifest(tmp_path)
    report = json.loads((tmp_path / "pair.json").read_text(encoding="utf-8"))
    report.update(change)
    (tmp_path / "pair.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(PilotAggregateError, match=message):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))


def test_profiles_require_equal_hard_case_counts(tmp_path: Path) -> None:
    manifest = _valid_manifest(tmp_path)
    run = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    run["cases"].append(dict(run["cases"][0], id="extra"))
    (tmp_path / "b.json").write_text(json.dumps(run), encoding="utf-8")
    with pytest.raises(PilotAggregateError, match="same number of hard cases"):
        pilot_aggregate.build_pilot_aggregate(_write_manifest(tmp_path, manifest))

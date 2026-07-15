from __future__ import annotations

import json

import pytest

from remis_aventine.remis_pairwise import (
    RemisPairwiseError,
    build_remis_pairwise_pack,
    render_remis_pairwise_markdown,
    summarize_remis_pairwise,
    write_remis_pairwise_report,
)


def _case(case_id: str, *, track: str, passed: bool, unchanged: bool | None = None) -> dict:
    metrics = {"hard_pass": passed}
    if unchanged is not None:
        metrics.update(valid_items_unchanged=unchanged, reference_exact_match=unchanged)
    case = {
        "id": case_id,
        "track": track,
        "execution_status": "completed",
        "hard_validation": {"enabled": True, "passed": passed, "findings": []},
        "automatic_metrics": metrics,
        "candidate_outputs": [f"{case_id}-output"],
        "source_inputs": [f"{case_id}-source"],
        "source_metadata": {"source_language": "en", "target_language": "zh-CN"},
    }
    if track == "repair":
        case["repair_evidence"] = {
            "broken_translation": ["broken"],
            "reference_translation": ["fixed"],
            "injected_errors": [{"code": "test"}],
        }
    return case


def _run(recipe: str, sha: str, cases: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "run_id": f"run-{recipe}",
        "suite": "remis",
        "recipe": {"id": recipe, "sha256": sha},
        "started_at": "2026-07-15T00:00:00Z",
        "finished_at": "2026-07-15T00:00:01Z",
        "environment": {"model_label": recipe},
        "cases": cases,
        "summary": {},
    }


def _judge(case_id: str, verdict: str) -> dict:
    return {
        "schema_version": 1,
        "case_id": case_id,
        "judge": {
            "profile": "test",
            "model": "fake",
            "prompt_revision": "test-v1",
            "calibration_revision": "test-pack",
        },
        "evaluation": {
            "mode": "pairwise",
            "verdict": verdict,
            "confidence": "high",
            "errors": [],
            "rationale": "Synthetic decision.",
            "limitations": [],
        },
    }


def _write(path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_build_pack_applies_hard_veto_and_summarizes_repair(tmp_path) -> None:
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    output = tmp_path / "pack.json"
    _write(
        left_path,
        _run(
            "left",
            "a" * 64,
            [
                _case("hard", track="translation", passed=True),
                _case("soft", track="repair", passed=True, unchanged=False),
            ],
        ),
    )
    _write(
        right_path,
        _run(
            "right",
            "b" * 64,
            [
                _case("hard", track="translation", passed=False),
                _case("soft", track="repair", passed=True, unchanged=True),
            ],
        ),
    )

    pack = build_remis_pairwise_pack(left_path, right_path, output)

    assert pack["policy_cases"][0]["winner"] == "left"
    assert [case["id"] for case in pack["cases"]] == ["soft"]
    assert pack["cases"][0]["evaluation_mode"] == "pairwise"
    assert "gold" not in pack["cases"][0]
    assert pack["repair_over_editing"]["left"]["over_editing_count"] == 1
    assert pack["repair_over_editing"]["right"]["over_editing_count"] == 0


def test_report_requires_position_consistency(tmp_path) -> None:
    left = _run("left", "a" * 64, [_case("soft", track="repair", passed=True, unchanged=True)])
    right = _run("right", "b" * 64, [_case("soft", track="repair", passed=True, unchanged=True)])
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    pack_path = tmp_path / "pack.json"
    _write(left_path, left)
    _write(right_path, right)
    pack = build_remis_pairwise_pack(left_path, right_path, pack_path)
    pack["cases"][0]["judge_output"] = _judge("soft", "candidate_a")
    pack["cases"][0]["swap_judge_output"] = _judge("soft", "candidate_b")
    _write(pack_path, pack)

    report = summarize_remis_pairwise(pack_path)

    assert report["summary"]["left_win_count"] == 1
    assert report["summary"]["unresolved_count"] == 0
    assert "Repair restraint" in render_remis_pairwise_markdown(report)

    pack["cases"][0]["swap_judge_output"] = _judge("soft", "candidate_a")
    _write(pack_path, pack)
    inconsistent = summarize_remis_pairwise(pack_path)
    assert inconsistent["summary"]["judge_position_inconsistent_count"] == 1
    assert inconsistent["summary"]["unresolved_count"] == 1

    json_path = tmp_path / "nested" / "report.json"
    markdown_path = tmp_path / "nested" / "report.md"
    written = write_remis_pairwise_report(pack_path, json_path, markdown_path)
    assert json.loads(json_path.read_text(encoding="utf-8")) == written
    assert markdown_path.read_text(encoding="utf-8").startswith("# Remis recipe pairwise report")


def test_pairwise_rejects_mismatched_case_sets(tmp_path) -> None:
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    _write(
        left_path,
        _run("left", "a" * 64, [_case("left-only", track="translation", passed=True)]),
    )
    _write(
        right_path,
        _run("right", "b" * 64, [_case("right-only", track="translation", passed=True)]),
    )

    with pytest.raises(RemisPairwiseError, match="identical case ids"):
        build_remis_pairwise_pack(left_path, right_path, tmp_path / "pack.json")

from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.exam_execution import (
    V03_DIRECTIONS,
    BudgetExceeded,
    ExamExecutionError,
    build_execution_plan,
    estimate_plan_cost,
    load_exam,
    run_execution_plan,
)


def _exam() -> dict:
    translation_tasks = []
    packs = []
    for index, direction in enumerate(V03_DIRECTIONS):
        source, target = direction.split("->")
        task_id = f"case-{index}::{direction}"
        translation_tasks.append(
            {
                "id": task_id,
                "source_lang": source,
                "target_lang": target,
                "source_items": [{"key": "event.f", "text": "Source"}],
            }
        )
        packs.append(
            {
                "id": f"pack-{index}::{direction}",
                "mode": "translation",
                "source_lang": source,
                "target_lang": target,
                "task_ids": [task_id],
                "context": "context",
            }
        )
    return {
        "schema_version": 1,
        "exam_id": "v0.3-test",
        "status": "ready-for-authorized-pilot",
        "directions": list(V03_DIRECTIONS),
        "policy": {"contestant_repetitions": 2},
        "translation_tasks": translation_tasks,
        "repair_tasks": [
            {
                "id": "repair-case",
                "mode": "repair",
                "source_lang": "en",
                "target_lang": "zh-CN",
                "source_items": [{"key": "event.f", "text": "Source"}],
                "broken": ["broken"],
            }
        ],
        "execution_packs": [
            *packs,
            {
                "id": "repair-pack",
                "mode": "repair",
                "source_lang": "en",
                "target_lang": "zh-CN",
                "task_ids": ["repair-case"],
            },
        ],
    }


def test_load_and_build_full_eighteen_direction_plan(tmp_path: Path) -> None:
    path = tmp_path / "exam.json"
    path.write_text(json.dumps(_exam()), encoding="utf-8")

    exam = load_exam(path)
    plan = build_execution_plan(exam)

    assert plan.directions == V03_DIRECTIONS
    assert plan.repetitions == 2
    assert len(plan.jobs) == 36
    assert len({job["id"] for job in plan.jobs}) == 36
    assert estimate_plan_cost(plan, 0.05) == 1.8
    assert plan.sha256 == build_execution_plan(exam).sha256


def test_selection_preserves_canonical_direction_order() -> None:
    plan = build_execution_plan(_exam(), directions=["en->tr", "zh-CN->en"], repetitions=1)

    assert plan.directions == ("zh-CN->en", "en->tr")
    assert [job["direction"] for job in plan.jobs] == ["zh-CN->en", "en->tr"]


def test_repairs_are_explicit_and_not_direction_weighted() -> None:
    plan = build_execution_plan(
        _exam(), directions=["zh-CN->en"], repetitions=2, include_repairs=True
    )

    assert len(plan.jobs) == 4
    assert [job["mode"] for job in plan.jobs] == [
        "translation",
        "repair",
        "translation",
        "repair",
    ]
    assert plan.include_repairs is True


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda exam: exam.update(status="draft"), "not frozen"),
        (lambda exam: exam["directions"].pop(), "18-direction"),
    ],
)
def test_load_rejects_unfrozen_or_incomplete_exam(tmp_path: Path, mutator, match: str) -> None:
    exam = _exam()
    mutator(exam)
    path = tmp_path / "exam.json"
    path.write_text(json.dumps(exam), encoding="utf-8")

    with pytest.raises(ExamExecutionError, match=match):
        load_exam(path)


def test_plan_rejects_unknown_direction_and_missing_task() -> None:
    with pytest.raises(ExamExecutionError, match="Unknown directions"):
        build_execution_plan(_exam(), directions=["ja->ko"])

    exam = _exam()
    exam["execution_packs"][0]["task_ids"] = ["missing"]
    with pytest.raises(ExamExecutionError, match="unknown task"):
        build_execution_plan(exam, directions=["zh-CN->en"])


def test_checkpoint_resume_does_not_repeat_paid_calls(tmp_path: Path) -> None:
    plan = build_execution_plan(_exam(), directions=["zh-CN->en"], repetitions=2)
    output = tmp_path / "run.json"
    calls = []

    def transport(job: dict) -> dict:
        calls.append(job["id"])
        return {"cost_usd": 0.01, "outputs": [job["id"]]}

    first = run_execution_plan(plan, output, transport, max_cost_usd=1, reserve_per_call_usd=0.05)
    second = run_execution_plan(plan, output, transport, max_cost_usd=1, reserve_per_call_usd=0.05)

    assert first == second
    assert len(calls) == 2
    assert second["status"] == "completed"
    assert second["observed_cost_usd"] == 0.02


def test_budget_stops_before_transport_and_checkpoint_is_resumable(tmp_path: Path) -> None:
    plan = build_execution_plan(_exam(), directions=["zh-CN->en"], repetitions=2)
    output = tmp_path / "run.json"
    calls = []

    def transport(job: dict) -> dict:
        calls.append(job["id"])
        return {"cost_usd": None, "outputs": []}

    with pytest.raises(BudgetExceeded, match="exceed"):
        run_execution_plan(plan, output, transport, max_cost_usd=0.05, reserve_per_call_usd=0.05)

    report = json.loads(output.read_text(encoding="utf-8"))
    assert calls == [plan.jobs[0]["id"]]
    assert report["status"] == "budget_stopped"
    assert len(report["results"]) == 1


def test_resume_rejects_different_plan(tmp_path: Path) -> None:
    first = build_execution_plan(_exam(), directions=["zh-CN->en"], repetitions=1)
    second = build_execution_plan(_exam(), directions=["en->zh-CN"], repetitions=1)
    output = tmp_path / "run.json"
    run_execution_plan(
        first,
        output,
        lambda job: {"cost_usd": 0, "outputs": [job["id"]]},
        max_cost_usd=1,
        reserve_per_call_usd=0,
    )

    with pytest.raises(ExamExecutionError, match="different execution plan"):
        run_execution_plan(
            second,
            output,
            lambda job: {},
            max_cost_usd=1,
            reserve_per_call_usd=0,
        )


def test_resume_rejects_recipe_identity_drift(tmp_path: Path) -> None:
    plan = build_execution_plan(_exam(), directions=["zh-CN->en"], repetitions=1)
    output = tmp_path / "run.json"
    run_execution_plan(
        plan,
        output,
        lambda job: {"cost_usd": 0, "outputs": [job["id"]]},
        max_cost_usd=1,
        reserve_per_call_usd=0,
        execution_identity={"model": "vendor/model-a", "reasoning": "high"},
    )

    with pytest.raises(ExamExecutionError, match="different execution identity"):
        run_execution_plan(
            plan,
            output,
            lambda job: {},
            max_cost_usd=1,
            reserve_per_call_usd=0,
            execution_identity={"model": "vendor/model-b", "reasoning": "high"},
        )

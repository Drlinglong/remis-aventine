from __future__ import annotations

from copy import deepcopy

import pytest

from remis_aventine.dual_judge import (
    DualJudgeBudgetExceeded,
    DualJudgeError,
    JudgeIdentity,
    execute_adaptive_dual_judge,
    make_judge_transport,
    normalize_verdict,
    plan_disagreement_followups,
    plan_dual_judge,
    summarize_dual_judge,
)

JUDGE_A = JudgeIdentity("gemini-3.7-flash", "gemini")
JUDGE_B = JudgeIdentity("deepseek-v4", "deepseek")


def _cases(count: int = 10) -> list[dict]:
    return [
        {
            "id": f"case-{index}",
            "stratum": "en->zh-CN:flavor" if index < count // 2 else "en->de:flavor",
            "candidate_families": ["luna", "claude"],
        }
        for index in range(count)
    ]


def _result(call: dict, canonical_verdict: str, cost: float = 0.01) -> dict:
    submitted = normalize_verdict(canonical_verdict, call["orientation"])
    return {"call_id": call["id"], "verdict": submitted, "cost_usd": cost}


def test_plan_is_seeded_opposed_and_stratified_twenty_percent() -> None:
    plan = plan_dual_judge(_cases(), JUDGE_A, JUDGE_B, seed=20260818)
    repeated = plan_dual_judge(_cases(), JUDGE_A, JUDGE_B, seed=20260818)

    assert plan == repeated
    assert len(plan["sha256"]) == 64
    assert len(plan["cases_sha256"]) == 64
    assert len(plan["audit_case_ids"]) == 2
    assert plan["planned_call_count"] == 24
    for case_id in {call["case_id"] for call in plan["calls"]}:
        initial = [
            call
            for call in plan["calls"]
            if call["case_id"] == case_id and call["phase"] == "initial"
        ]
        assert {call["orientation"] for call in initial} == {"ab", "ba"}


def test_self_judging_and_same_family_judges_are_rejected() -> None:
    cases = _cases(2)
    cases[0]["candidate_families"] = ["gemini", "claude"]
    with pytest.raises(DualJudgeError, match="Self-judging"):
        plan_dual_judge(cases, JUDGE_A, JUDGE_B, seed=1)
    with pytest.raises(DualJudgeError, match="independent"):
        plan_dual_judge(_cases(2), JUDGE_A, JudgeIdentity("other-gemini", "gemini"), seed=1)


def test_normalize_verdict_maps_swapped_candidate_labels() -> None:
    assert normalize_verdict("candidate_a", "ab") == "candidate_a"
    assert normalize_verdict("candidate_a", "ba") == "candidate_b"
    assert normalize_verdict("tie", "ba") == "tie"


def test_agreement_resolves_without_extra_calls() -> None:
    plan = plan_dual_judge(_cases(2), JUDGE_A, JUDGE_B, seed=1, audit_rate=0)
    results = [_result(call, "candidate_a") for call in plan["calls"]]

    assert plan_disagreement_followups(plan, results) == []
    report = summarize_dual_judge(plan, results)
    assert report["resolved_count"] == 2
    assert report["resolved_coverage"] == 1
    assert report["cost_per_resolved_usd"] == 0.02


def test_disagreement_adds_missing_orientation_and_strictly_resolves() -> None:
    plan = plan_dual_judge(_cases(2), JUDGE_A, JUDGE_B, seed=1, audit_rate=0)
    initial = []
    for call in plan["calls"]:
        canonical = "candidate_a" if call["judge_id"] == JUDGE_A.id else "candidate_b"
        initial.append(_result(call, canonical))
    followups = plan_disagreement_followups(plan, initial)

    assert len(followups) == 4
    completed = [*initial]
    for call in followups:
        canonical = "candidate_a" if call["judge_id"] == JUDGE_A.id else "candidate_b"
        completed.append(_result(call, canonical))
    report = summarize_dual_judge(plan, completed, followups=followups)
    assert report["resolved_count"] == 0
    assert report["unresolved_count"] == 2
    assert report["position_consistency"] == 1


def test_audit_detects_position_inconsistency() -> None:
    plan = plan_dual_judge(_cases(2), JUDGE_A, JUDGE_B, seed=1, audit_rate=1)
    results = []
    for call in plan["calls"]:
        canonical = "candidate_a"
        if call["judge_id"] == JUDGE_A.id and call["phase"] == "audit":
            canonical = "candidate_b"
        results.append(_result(call, canonical))

    report = summarize_dual_judge(plan, results)
    assert report["resolved_count"] == 0
    assert report["position_consistency"] == 0.5
    assert all(decision["call_count"] == 4 for decision in report["decisions"])


def test_incomplete_calls_remain_unresolved_without_becoming_failure() -> None:
    plan = plan_dual_judge(_cases(2), JUDGE_A, JUDGE_B, seed=1, audit_rate=0)
    report = summarize_dual_judge(plan, [_result(plan["calls"][0], "candidate_a")])

    assert report["resolved_count"] == 0
    assert report["unresolved_count"] == 2
    assert report["resolved_coverage"] == 0


def test_adaptive_executor_checkpoints_resumes_and_runs_only_needed_followups(
    tmp_path,
) -> None:
    cases = _cases(2)
    for case in cases:
        case["candidate_a"] = "A"
        case["candidate_b"] = "B"
    plan = plan_dual_judge(cases, JUDGE_A, JUDGE_B, seed=1, audit_rate=0)
    calls = []

    def transport(call: dict, oriented: dict) -> dict:
        calls.append((call["id"], oriented["candidate_a"]))
        canonical = "candidate_a" if call["judge_id"] == JUDGE_A.id else "candidate_b"
        return {"verdict": normalize_verdict(canonical, call["orientation"]), "cost_usd": 0.01}

    output = tmp_path / "judge.json"
    first = execute_adaptive_dual_judge(
        plan,
        cases,
        {JUDGE_A.id: transport, JUDGE_B.id: transport},
        output,
        max_cost_usd=1,
        reserve_per_call_usd=0.02,
    )
    second = execute_adaptive_dual_judge(
        plan,
        cases,
        {JUDGE_A.id: transport, JUDGE_B.id: transport},
        output,
        max_cost_usd=1,
        reserve_per_call_usd=0.02,
    )

    assert first == second
    assert len(calls) == 8
    assert first["summary"]["unresolved_count"] == 2
    assert {value for _call_id, value in calls} == {"A", "B"}


def test_adaptive_executor_stops_before_budget_and_does_not_retry_failure(tmp_path) -> None:
    cases = _cases(2)
    for case in cases:
        case["candidate_a"] = "A"
        case["candidate_b"] = "B"
    plan = plan_dual_judge(cases, JUDGE_A, JUDGE_B, seed=1, audit_rate=0)
    attempts = []

    def failing(call: dict, oriented: dict) -> dict:
        attempts.append(call["id"])
        raise RuntimeError("provider failed after one attempt")

    output = tmp_path / "judge.json"
    with pytest.raises(DualJudgeBudgetExceeded):
        execute_adaptive_dual_judge(
            plan,
            cases,
            {JUDGE_A.id: failing, JUDGE_B.id: failing},
            output,
            max_cost_usd=0.02,
            reserve_per_call_usd=0.02,
        )

    assert len(attempts) == 1


def test_nested_candidate_input_is_swapped_and_schema_judge_is_adapted(tmp_path) -> None:
    case = {
        **_cases(1)[0],
        "evaluation_mode": "pairwise",
        "input": {"candidate_a": "A", "candidate_b": "B"},
    }
    plan = plan_dual_judge([case], JUDGE_A, JUDGE_B, seed=1, audit_rate=0)

    class FakeJudge:
        provider = "fake"
        model_id = "fake/model"
        profile = "fake-profile"
        prompt_revision = "p1"
        reasoning_effort = "high"

        def evaluate_once(self, oriented):
            verdict = (
                "candidate_a"
                if oriented["input"]["candidate_a"] == "A"
                else "candidate_b"
            )
            return {"evaluation": {"verdict": verdict}}, {"output_tokens": 1}

        def cost_fields(self, usage, prior):
            return {"estimated_cost_usd": 0.001}

    transport = make_judge_transport(FakeJudge())
    result = execute_adaptive_dual_judge(
        plan,
        [case],
        {JUDGE_A.id: transport, JUDGE_B.id: transport},
        tmp_path / "nested.json",
        max_cost_usd=1,
        reserve_per_call_usd=0.01,
    )

    assert result["summary"]["resolved_count"] == 1
    assert result["summary"]["decisions"][0]["verdict"] == "candidate_a"


def test_resume_rejects_changed_candidate_text(tmp_path) -> None:
    cases = [{**_cases(1)[0], "input": {"candidate_a": "A", "candidate_b": "B"}}]
    plan = plan_dual_judge(cases, JUDGE_A, JUDGE_B, seed=1, audit_rate=0)

    def transport(call, oriented):
        return {"verdict": "tie", "cost_usd": 0}

    output = tmp_path / "bound.json"
    execute_adaptive_dual_judge(
        plan,
        cases,
        {JUDGE_A.id: transport, JUDGE_B.id: transport},
        output,
        max_cost_usd=1,
        reserve_per_call_usd=0,
    )
    changed = deepcopy(cases)
    changed[0]["input"]["candidate_a"] = "changed"

    with pytest.raises(DualJudgeError, match="Execution cases do not match"):
        execute_adaptive_dual_judge(
            plan,
            changed,
            {JUDGE_A.id: transport, JUDGE_B.id: transport},
            output,
            max_cost_usd=1,
            reserve_per_call_usd=0,
        )

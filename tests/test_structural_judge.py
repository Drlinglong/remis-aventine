from pathlib import Path

import pytest

from remis_aventine.judge import DeepSeekJudge
from remis_aventine.structural_judge import (
    StructuralJudgeError,
    StructuralJudgeIdentity,
    build_structural_cases,
    execute_structural_dual_judge,
    plan_structural_dual_judge,
)


def _pack() -> dict:
    return {
        "candidate_identities": {
            "candidate_a": {"requested_model": "a", "model_family": "family-a"},
            "candidate_b": {"requested_model": "b", "model_family": "family-b"},
        },
        "structural_review_queue": [
            {
                "id": "official::en->zh-CN::repeat-1::case::en->zh-CN::0",
                "direction": "en->zh-CN",
                "source": "[Name] saw [Name].",
                "candidate_a": "[Name]到场了。",
                "candidate_b": "[Name]看见了[Name]。",
                "left_route": "structural_judges",
                "right_route": "pass",
                "left_review_queue": [{"code": "variable_count"}],
                "right_review_queue": [],
            }
        ],
    }


class FakeJudge:
    def __init__(self, verdict: str) -> None:
        self.verdict = verdict

    def evaluate_once(self, case):
        assert case["evaluation_scope"] == "structural"
        return {"evaluation": {"verdict": self.verdict}}, {"output_tokens": 1}

    def cost_fields(self, usage, prior):
        return {"estimated_cost_usd": 0.001}


def test_build_plan_and_execute_agreed_structural_pass(tmp_path: Path) -> None:
    cases = build_structural_cases(_pack())
    judge_a = StructuralJudgeIdentity("judge-a", "judge-family-a")
    judge_b = StructuralJudgeIdentity("judge-b", "judge-family-b")
    plan = plan_structural_dual_judge(cases, judge_a, judge_b)

    report = execute_structural_dual_judge(
        plan,
        cases,
        {"judge-a": FakeJudge("pass"), "judge-b": FakeJudge("pass")},
        tmp_path / "structural.json",
        max_cost_usd=1,
        reserve_per_call_usd=0.01,
    )

    assert len(cases) == 1
    assert plan["planned_call_count"] == 2
    assert report["summary"]["resolved_count"] == 1
    assert report["summary"]["observed_cost_usd"] == 0.002
    assert report["summary"]["cost_per_resolved_usd"] == 0.002
    assert report["resolutions"][0]["decisions"] == ["acceptable", "acceptable"]


def test_disagreement_is_exported_but_remains_unresolved(tmp_path: Path) -> None:
    cases = build_structural_cases(_pack())
    judge_a = StructuralJudgeIdentity("judge-a", "judge-family-a")
    judge_b = StructuralJudgeIdentity("judge-b", "judge-family-b")
    plan = plan_structural_dual_judge(cases, judge_a, judge_b)
    report = execute_structural_dual_judge(
        plan,
        cases,
        {"judge-a": FakeJudge("pass"), "judge-b": FakeJudge("fail")},
        tmp_path / "structural.json",
        max_cost_usd=1,
        reserve_per_call_usd=0.01,
    )

    assert report["summary"]["unresolved_count"] == 1
    assert report["resolutions"][0]["decisions"] == ["acceptable", "lost_or_added"]


def test_family_exclusion_rejects_candidate_self_judging() -> None:
    cases = build_structural_cases(_pack())
    with pytest.raises(StructuralJudgeError, match="Self-judging"):
        plan_structural_dual_judge(
            cases,
            StructuralJudgeIdentity("candidate-family", "family-a"),
            StructuralJudgeIdentity("other", "judge-family"),
        )


def test_changed_case_evidence_cannot_resume_plan(tmp_path: Path) -> None:
    cases = build_structural_cases(_pack())
    plan = plan_structural_dual_judge(
        cases,
        StructuralJudgeIdentity("judge-a", "judge-family-a"),
        StructuralJudgeIdentity("judge-b", "judge-family-b"),
    )
    changed = [dict(cases[0])]
    changed[0]["input"] = {**changed[0]["input"], "candidate": "changed"}

    with pytest.raises(StructuralJudgeError, match="evidence hash"):
        execute_structural_dual_judge(
            plan,
            changed,
            {"judge-a": FakeJudge("pass"), "judge-b": FakeJudge("pass")},
            tmp_path / "structural.json",
            max_cost_usd=1,
            reserve_per_call_usd=0.01,
        )


def test_structural_prompt_forbids_unrelated_style_judgment() -> None:
    case = build_structural_cases(_pack())[0]
    body = DeepSeekJudge("test-key").request_body(case)
    prompt = body["messages"][1]["content"]

    assert "Evaluate ONLY" in prompt
    assert "Do not fail for unrelated style" in prompt
    assert "variable_count" in prompt

import hashlib
import json
from pathlib import Path

from remis_aventine.dual_judge import (
    JudgeIdentity,
    execute_adaptive_dual_judge,
    normalize_verdict,
    plan_dual_judge,
)
from remis_aventine.exam_execution import V03_DIRECTIONS
from remis_aventine.structural_judge import (
    StructuralJudgeIdentity,
    build_structural_cases,
    execute_structural_dual_judge,
    plan_structural_dual_judge,
)
from remis_aventine.v03_aggregate import build_v03_leaderboard
from remis_aventine.v03_tournament import build_v03_pairwise_pack


def _sha(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _exam() -> dict:
    tasks = []
    for direction in V03_DIRECTIONS:
        source, target = direction.split("->")
        tasks.append(
            {
                "id": f"case-{source}-{target}::{direction}",
                "case_id": f"case-{source}-{target}",
                "origin": "integration",
                "source_lang": source,
                "target_lang": target,
                "source_items": [{"key": "text", "text": "[Name] saw [Name]."}],
                "reference": ["reference"],
                "context": "full-topology integration test",
                "focus": ["meaning", "protected variables"],
            }
        )
    return {
        "translation_tasks": tasks,
        "repair_tasks": [
            {
                "id": "repair-case::repair",
                "case_id": "repair-case",
                "origin": "integration",
                "mode": "repair",
                "source_lang": "en",
                "target_lang": "zh-CN",
                "source_items": [{"key": "repair", "text": "§YWarning§!"}],
                "clean_reference": ["§Y警告§!"],
                "injected_errors": ["missing color terminator"],
                "context": "repair integration test",
            }
        ],
    }


def _run(model: str, family: str, *, structural_first: bool = False) -> dict:
    identity = {"requested_model": model, "model_family": family, "reasoning_effort": "high"}
    results = []
    for direction in V03_DIRECTIONS:
        source, target = direction.split("->")
        task_id = f"case-{source}-{target}::{direction}"
        for repeat in (1, 2):
            structural = structural_first and direction == "en->zh-CN" and repeat == 1
            results.append(
                {
                    "job_id": f"integration::{direction}::repeat-{repeat}",
                    "elapsed_seconds": 1,
                    "cost_usd": 0.001,
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                        "completion_tokens_details": {"reasoning_tokens": 2},
                    },
                    "validation": {
                        "raw_contract_pass": True,
                        "normalization_operations": [],
                        "items": [
                            {
                                "item_id": f"{task_id}::0",
                                "output": (
                                    f"{model}: [Name] arrived."
                                    if structural
                                    else f"{model}: [Name] saw [Name]."
                                ),
                                "classification": {
                                    "route": (
                                        "structural_judges" if structural else "pass"
                                    ),
                                    "structural_review_queue": (
                                        [{"code": "variable_count_changed"}]
                                        if structural
                                        else []
                                    ),
                                },
                            }
                        ],
                    },
                }
            )
    for repeat in (1, 2):
        results.append(
            {
                "job_id": f"integration-repair::en->zh-CN::repeat-{repeat}",
                "elapsed_seconds": 1,
                "cost_usd": 0.001,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "completion_tokens_details": {"reasoning_tokens": 2},
                },
                "validation": {
                    "raw_contract_pass": True,
                    "normalization_operations": [],
                    "items": [
                        {
                            "item_id": "repair-case::repair::0",
                            "output": f"{model}: §Y警告§!",
                            "classification": {
                                "route": "pass",
                                "structural_review_queue": [],
                            },
                        }
                    ],
                },
            }
        )
    return {
        "status": "completed",
        "exam_sha256": "full-18-direction-integration",
        "plan_sha256": "shared-plan",
        "planned_call_count": len(results),
        "execution_identity": identity,
        "execution_identity_sha256": _sha(identity),
        "results": results,
    }


class StructuralPassJudge:
    def evaluate_once(self, case):
        return {"evaluation": {"verdict": "pass"}}, {"output_tokens": 1}

    def cost_fields(self, usage, prior):
        return {"estimated_cost_usd": 0.001}


def test_full_18_direction_two_repeat_pipeline(tmp_path: Path) -> None:
    left = _run("left/model", "left-family", structural_first=True)
    right = _run("right/model", "right-family")
    pack = build_v03_pairwise_pack(_exam(), left, right)

    assert pack["counts"] == {
        "soft_judge": 37,
        "deterministic_hard": 0,
        "structural_review": 1,
        "total": 38,
    }

    structural_cases = build_structural_cases(pack)
    structural_plan = plan_structural_dual_judge(
        structural_cases,
        StructuralJudgeIdentity("structural-a", "structural-family-a"),
        StructuralJudgeIdentity("structural-b", "structural-family-b"),
    )
    structural_report = execute_structural_dual_judge(
        structural_plan,
        structural_cases,
        {
            "structural-a": StructuralPassJudge(),
            "structural-b": StructuralPassJudge(),
        },
        tmp_path / "structural.json",
        max_cost_usd=1,
        reserve_per_call_usd=0.01,
    )

    soft_cases = pack["soft_judge_cases"]
    soft_plan = plan_dual_judge(
        soft_cases,
        JudgeIdentity("soft-a", "soft-family-a"),
        JudgeIdentity("soft-b", "soft-family-b"),
        seed=20260818,
        audit_rate=0.2,
    )

    def prefer_left(call, oriented):
        canonical = "candidate_a"
        return {
            "verdict": normalize_verdict(canonical, call["orientation"]),
            "cost_usd": 0.001,
        }

    soft_report = execute_adaptive_dual_judge(
        soft_plan,
        soft_cases,
        {"soft-a": prefer_left, "soft-b": prefer_left},
        tmp_path / "soft.json",
        max_cost_usd=10,
        reserve_per_call_usd=0.01,
    )
    aggregate = build_v03_leaderboard(
        [left, right],
        [{"pack": pack, "judge_report": soft_report}],
        structural_resolutions=structural_report["resolutions"],
    )
    profiles = {
        profile["recipe"]["requested_model"]: profile for profile in aggregate["profiles"]
    }

    assert structural_report["summary"]["resolved_count"] == 1
    assert soft_report["summary"]["resolved_count"] == 37
    assert aggregate["status"] == "complete"
    assert profiles["left/model"]["scores"]["overall_intelligence"]["score"] == 100
    assert profiles["right/model"]["scores"]["overall_intelligence"]["score"] == 40
    assert profiles["left/model"]["scores"]["east_asian"]["status"] == "complete"
    assert profiles["left/model"]["scores"]["continental"]["status"] == "complete"
    assert profiles["left/model"]["telemetry"]["call_count"] == 38

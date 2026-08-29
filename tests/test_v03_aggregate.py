import hashlib
import json

import pytest

from remis_aventine.v03_aggregate import V03AggregateError, build_v03_leaderboard


def _sha(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _run(model: str, family: str, *, route: str = "pass") -> dict:
    identity = {"requested_model": model, "model_family": family}
    return {
        "status": "completed",
        "exam_sha256": "exam",
        "execution_identity": identity,
        "execution_identity_sha256": _sha(identity),
        "results": [
            {
                "job_id": "official::en->zh-CN::repeat-1",
                "elapsed_seconds": 2,
                "cost_usd": 0.01,
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
                            "item_id": "case::en->zh-CN::0",
                            "classification": {"route": route},
                        }
                    ],
                },
            }
        ],
    }


def _match(left: dict, right: dict, *, verdict: str = "candidate_a") -> dict:
    case = {
        "id": "official::en->zh-CN::repeat-1::case::en->zh-CN::0",
        "input": {"language_pair": "en->zh-CN", "candidate_a": "A", "candidate_b": "B"},
    }
    pack = {
        "candidate_identities": {
            "candidate_a": left["execution_identity"],
            "candidate_b": right["execution_identity"],
        },
        "soft_judge_cases": [case],
    }
    pack["sha256"] = _sha(pack)
    report = {
        "status": "completed",
        "cases_sha256": _sha([case]),
        "summary": {"decisions": [{"case_id": case["id"], "resolved": True, "verdict": verdict}]},
    }
    return {"pack": pack, "judge_report": report}


def test_builds_incomplete_18_direction_profile_without_renormalizing() -> None:
    left = _run("left", "family-left")
    right = _run("right", "family-right")
    result = build_v03_leaderboard([left, right], [_match(left, right)])
    profiles = {profile["recipe"]["requested_model"]: profile for profile in result["profiles"]}

    assert result["status"] == "incomplete"
    assert result["direction_count"] == 18
    assert profiles["left"]["scores"]["direction_components"]["en->zh-CN"]["score"] == 100
    assert profiles["right"]["scores"]["direction_components"]["en->zh-CN"]["score"] == 40
    assert profiles["left"]["scores"]["overall_intelligence"]["score"] is None
    assert profiles["left"]["telemetry"]["tokens"]["total"] == 15
    assert profiles["left"]["telemetry"]["cost_usd"] == 0.01


def test_structural_disagreement_remains_unresolved_hard_coverage() -> None:
    left = _run("left", "family-left", route="structural_judges")
    right = _run("right", "family-right")
    occurrence = "official::en->zh-CN::repeat-1::case::en->zh-CN::0"
    result = build_v03_leaderboard(
        [left, right],
        [_match(left, right)],
        structural_resolutions=[
            {
                "execution_identity_sha256": left["execution_identity_sha256"],
                "occurrence_id": occurrence,
                "decisions": ["acceptable", "lost_or_added"],
            }
        ],
    )
    profile = next(
        value for value in result["profiles"] if value["recipe"]["requested_model"] == "left"
    )

    hard = profile["scores"]["direction_components"]["en->zh-CN"]["hard_format"]
    assert hard["score"] is None
    assert hard["coverage"] == 0


def test_rejects_judge_report_bound_to_different_candidates() -> None:
    left = _run("left", "family-left")
    right = _run("right", "family-right")
    match = _match(left, right)
    match["judge_report"]["cases_sha256"] = "wrong"

    with pytest.raises(V03AggregateError, match="different cases"):
        build_v03_leaderboard([left, right], [match])

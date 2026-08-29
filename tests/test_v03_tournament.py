from copy import deepcopy

import pytest

from remis_aventine.v03_tournament import V03TournamentError, build_v03_pairwise_pack


def _identity(model: str, family: str) -> tuple[dict, str]:
    import hashlib
    import json

    value = {"requested_model": model, "model_family": family}
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value, hashlib.sha256(payload.encode()).hexdigest()


def _run(model: str, family: str, routes: tuple[str, ...], *, repeats: int = 1) -> dict:
    identity, digest = _identity(model, family)
    items = []
    for index, route in enumerate(routes):
        items.append(
            {
                "item_id": f"case::en->zh-CN::{index}",
                "output": f"{model}-{index}",
                "classification": {
                    "route": route,
                    "structural_review_queue": [{"code": "token"}]
                    if route == "structural_judges"
                    else [],
                },
            }
        )
    results = []
    for repeat in range(1, repeats + 1):
        repeated = deepcopy(items)
        for item in repeated:
            item["output"] = f"{item['output']}-repeat-{repeat}"
        results.append(
            {
                "job_id": f"official::en->zh-CN::repeat-{repeat}",
                "validation": {"items": repeated},
            }
        )
    return {
        "status": "completed",
        "exam_sha256": "exam",
        "plan_sha256": "plan",
        "planned_call_count": 1,
        "execution_identity": identity,
        "execution_identity_sha256": digest,
        "results": results,
    }


def _exam() -> dict:
    return {
        "translation_tasks": [
            {
                "id": "case::en->zh-CN",
                "case_id": "case",
                "origin": "official",
                "source_lang": "en",
                "target_lang": "zh-CN",
                "source_items": [
                    {"key": "one", "text": "one"},
                    {"key": "two", "text": "two"},
                    {"key": "three", "text": "three"},
                ],
                "reference": ["一", "二", "三"],
                "context": "ctx",
                "focus": ["style"],
            }
        ]
    }


def test_build_routes_items_without_double_penalizing_hard_failures() -> None:
    pack = build_v03_pairwise_pack(
        _exam(),
        _run("a", "family-a", ("pass", "hard_fail", "structural_judges")),
        _run("b", "family-b", ("pass", "pass", "pass")),
    )

    assert pack["counts"] == {
        "soft_judge": 1,
        "deterministic_hard": 1,
        "structural_review": 1,
        "total": 3,
    }
    assert pack["deterministic_hard_decisions"][0]["winner"] == "candidate_b"
    case = pack["soft_judge_cases"][0]
    assert case["candidate_families"] == ["family-a", "family-b"]
    assert case["input"]["reference"] == "一"


def test_two_repeats_remain_distinct_occurrences() -> None:
    pack = build_v03_pairwise_pack(
        _exam(),
        _run("a", "family-a", ("pass", "pass", "pass"), repeats=2),
        _run("b", "family-b", ("pass", "pass", "pass"), repeats=2),
    )

    assert pack["counts"]["total"] == 6
    assert len({case["id"] for case in pack["soft_judge_cases"]}) == 6


def test_rejects_missing_or_tampered_execution_identity() -> None:
    left = _run("a", "family-a", ("pass", "pass", "pass"))
    left["execution_identity"]["requested_model"] = "tampered"

    with pytest.raises(V03TournamentError, match="valid execution identity"):
        build_v03_pairwise_pack(_exam(), left, _run("b", "family-b", ("pass", "pass", "pass")))


def test_rejects_mismatched_item_sets() -> None:
    right = _run("b", "family-b", ("pass", "pass", "pass"))
    right = deepcopy(right)
    right["results"][0]["validation"]["items"].pop()

    with pytest.raises(V03TournamentError, match="different item sets"):
        build_v03_pairwise_pack(_exam(), _run("a", "family-a", ("pass", "pass", "pass")), right)

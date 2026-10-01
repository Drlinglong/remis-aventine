import copy
import json
from pathlib import Path

import pytest

from remis_aventine.validation import (
    DocumentValidationError,
    validate_document,
    validate_payload,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "web" / "public" / "data" / "v03-zh-en-results.json"
SCHEMA_NAME = "v03-zh-en-public-result.schema.json"


def test_local_results_publish_two_identified_recipes_without_ranking_unmeasured_cost() -> None:
    result = RESULT.with_name("v03-zh-en-anchors-local-20261001.json")
    payload = validate_document(result, SCHEMA_NAME)
    assert payload["contestant_count"] == len(payload["profiles"]) == 2
    assert payload["score_version"] == "v0.3-zh-en-anchors-local-20261001-v1"
    assert {profile["model_id"] for profile in payload["profiles"]} == {
        "bilibili/index-translate-9b-q8_0",
        "xiaomi/mimo-v2.6-distill-qwen-9b-q4_k_s",
    }
    for profile in payload["profiles"]:
        assert profile["telemetry"]["cost_usd"] is None
        assert profile["telemetry"]["cost_rank_eligible"] is False
    assert payload["soft_resolved_count"] + payload["soft_unresolved_count"] == 114


def test_published_zh_en_result_satisfies_its_public_contract() -> None:
    payload = validate_document(RESULT, SCHEMA_NAME)

    assert payload["artifact_id"] == "v0.3-zh-en-results"
    assert payload["protocol"] == "aventine-v0.3-zh-en-balanced-degree4-sample20-60soft-40hard"
    assert payload["score_version"] == "v0.3-zh-en-60soft-40hard"
    assert payload["direction_count"] == 2
    assert payload["contestant_count"] == len(payload["profiles"]) == 17
    assert (
        payload["soft_resolved_count"] + payload["soft_unresolved_count"]
        == payload["soft_case_count"]
    )
    assert len({profile["model_id"] for profile in payload["profiles"]}) == 17
    assert len({profile["execution_identity_sha256"] for profile in payload["profiles"]}) == 17


def test_published_zh_en_contract_is_strict_and_distinct_from_multilingual_contract() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    modified = copy.deepcopy(payload)
    modified["unexpected_contract_field"] = True

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_payload(modified, SCHEMA_NAME)

    assert any("Additional properties are not allowed" in issue for issue in exc_info.value.issues)
    with pytest.raises(DocumentValidationError):
        validate_payload(payload, "v03-public-result.schema.json")


def test_anchor_protocol_requires_its_own_version_and_three_distinct_anchors() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["protocol"] = "aventine-v0.3-zh-en-fixed-anchors-priority-dual"
    payload["score_version"] = "v0.3-zh-en-anchors-20260925-v1"
    payload["judge_cost_missing_calls"] = 0
    with pytest.raises(DocumentValidationError):
        validate_payload(payload, SCHEMA_NAME)
    payload["anchor_panel"] = {
        "revision": payload["score_version"],
        "models": ["qwen/qwen3.8-max", "meta/muse-spark-1.2", "upstage/solar-pro4"],
        "manifest_sha256": "a" * 64,
        "judge_revision": "priority-mimo26-luna6-ds41-gemini38-20260925-v1",
    }
    validate_payload(payload, SCHEMA_NAME)
    local = copy.deepcopy(payload)
    local["score_version"] = "v0.3-zh-en-anchors-local-20261001-v1"
    local["anchor_panel"]["revision"] = local["score_version"]
    validate_payload(local, SCHEMA_NAME)
    duplicate = copy.deepcopy(payload)
    duplicate["anchor_panel"]["models"][1] = duplicate["anchor_panel"]["models"][0]
    with pytest.raises(DocumentValidationError):
        validate_payload(duplicate, SCHEMA_NAME)
    payload["score_version"] = "v0.3-zh-en-60soft-40hard"
    with pytest.raises(DocumentValidationError):
        validate_payload(payload, SCHEMA_NAME)

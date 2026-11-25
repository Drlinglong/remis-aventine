import json
from pathlib import Path

import pytest

from remis_aventine.validation import validate_document


def test_fixed_anchor_publication_has_the_completed_requested_cohort():
    path = Path(__file__).resolve().parents[1] / "web/public/data/v03-zh-en-anchors-20260925.json"
    artifact = validate_document(path, "v03-zh-en-public-result.schema.json")
    required = {
        "openai/gpt-6-luna",
        "openai/gpt-6-sol",
        "xiaomi/mimo-v2.6-pro",
        "deepseek/deepseek-v4.1-flash",
        "openai/gpt-5.6-luna",
        "deepseek/deepseek-v4-flash-0731",
    }
    assert required <= {p["model_id"] for p in artifact["profiles"]}
    assert artifact["contestant_count"] == len(artifact["profiles"])
    assert artifact["score_version"] == "v0.3-zh-en-anchors-20260925-v1"
    assert len(artifact["anchor_panel"]["models"]) == 3
    assert (
        artifact["soft_resolved_count"] + artifact["soft_unresolved_count"]
        == artifact["soft_case_count"]
    )
    for profile in artifact["profiles"]:
        directions = list(profile["directions"].values())
        assert sum(d["hard"]["total"] for d in directions) == 76
        assert 0 < sum(d["soft"]["total"] for d in directions) <= 60
        for direction in directions:
            assert direction["score"] == pytest.approx(
                0.6 * direction["soft"]["score"] + 0.4 * direction["hard"]["score"], abs=0.0001
            )
        assert profile["zh_en_score"] == pytest.approx(
            sum(d["score"] for d in directions) / 2, abs=0.0001
        )
    text = path.read_text(encoding="utf-8")
    for private_key in ("source_text", "candidate_a", "candidate_b", "raw_response", "rationale"):
        assert f'"{private_key}"' not in text


def test_october_publication_retains_complete_exam_and_coverage():
    path = Path(__file__).resolve().parents[1] / "web/public/data/v03-zh-en-anchors-20261009.json"
    artifact = validate_document(path, "v03-zh-en-public-result.schema.json")
    assert artifact["score_version"] == "v0.3-zh-en-anchors-20261009-v1"
    assert {p["model_id"] for p in artifact["profiles"]} == {
        "anthropic/claude-haiku-5.5",
        "openai/gpt-6.1-sol",
    }
    soft_total = soft_resolved = 0
    for profile in artifact["profiles"]:
        directions = list(profile["directions"].values())
        assert sum(d["hard"]["total"] for d in directions) == 76
        assert 0 < sum(d["soft"]["total"] for d in directions) <= 60
        for direction in directions:
            soft_total += direction["soft"]["total"]
            soft_resolved += direction["soft"]["resolved"]
            assert direction["score"] == pytest.approx(
                0.6 * direction["soft"]["score"] + 0.4 * direction["hard"]["score"], abs=0.0001
            )
        assert profile["zh_en_score"] == pytest.approx(
            sum(d["score"] for d in directions) / 2, abs=0.0001
        )
    assert artifact["soft_case_count"] == soft_total
    assert artifact["soft_resolved_count"] == soft_resolved
    assert artifact["soft_unresolved_count"] == soft_total - soft_resolved

def test_november_publication_has_three_complete_medium_profiles():
    root = Path(__file__).resolve().parents[1] / "web/public/data"
    path = root / "v03-zh-en-anchors-20261125.json"
    artifact = validate_document(path, "v03-zh-en-public-result.schema.json")
    assert artifact["contestant_count"] == 3
    assert {profile["model_id"] for profile in artifact["profiles"]} == {
        "openai/gpt-6.1-terra", "openai/gpt-6.2-sol", "openai/gpt-6.2-astra",
    }
    settings = json.loads((root / "v03-execution-settings.json").read_text(encoding="utf-8"))
    for profile in artifact["profiles"]:
        execution = settings["identities"][profile["execution_identity_sha256"]]
        assert execution["reasoning"] == "medium"
        assert execution["generation"]["calls"] == 44
        directions = profile["directions"].values()
        assert sum(d["hard"]["total"] for d in directions) == 76
        assert sum(d["soft"]["total"] for d in directions) == 60
        assert profile["zh_en_score"] == pytest.approx(
            sum(d["score"] for d in directions) / 2, abs=0.0001
        )

import json
from pathlib import Path

from remis_aventine.validation import validate_document


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "examples" / "v03" / "v03-public-result.template.json"


def test_public_result_template_is_small_valid_and_frontend_safe() -> None:
    payload = validate_document(TEMPLATE, "v03-public-result.schema.json")

    assert len(payload["profiles"]) == 1
    assert len(payload["directions"]) == 1
    assert payload["profiles"][0]["model_id"] == "upstage/solar-pro4"
    assert payload["profiles"][0]["focused_capabilities"] == ["ko"]
    assert payload["profiles"][0]["service_tier"] == "default"
    assert all(judge["service_tier"] == "batch" for judge in payload["judge_panel"])
    assert {anchor["level"] for anchor in payload["anchors"]} == {"high", "medium", "low"}
    assert payload["watchlist"][0]["model_id"] == "skt/A.X-K2"
    assert TEMPLATE.read_text(encoding="utf-8").count("\n") < 400


def test_public_result_template_contains_no_fake_scores() -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    scores = payload["profiles"][0]["scores"]

    assert all(
        scores[name]["score"] is None
        for name in (
            "overall_intelligence",
            "zh_en_core",
            "east_asian",
            "continental",
            "hard_format",
            "soft_preference",
        )
    )
    assert scores["per_extended_language"]["ko"]["score"] is None
    assert scores["direction_scores"][0]["direction_id"] == "en->ko"

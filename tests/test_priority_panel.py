import pytest

from remis_aventine.priority_panel import (
    PriorityJudge,
    normalize_vote,
    oriented,
    resolve_votes,
    select_panel,
)


def test_swapped_judgment_maps_back_without_mutating_the_frozen_case():
    case = {"input": {"candidate_a": "first", "candidate_b": "second"}}
    swapped = oriented(case, "ba")
    assert swapped["input"] == {"candidate_a": "second", "candidate_b": "first"}
    assert case["input"] == {"candidate_a": "first", "candidate_b": "second"}
    assert oriented(case, "ab") == case
    assert (
        resolve_votes([normalize_vote("candidate_b", "ba"), normalize_vote("candidate_a", "ab")])
        == "candidate_a"
    )
    with pytest.raises(ValueError, match="Two independent"):
        select_panel(["openai/gpt-6-sol", "xiaomi/mimo-v2.6-pro", "deepseek/deepseek-v4.1-flash"])


def test_contestants_recuse_entire_family_and_fallback_only_when_needed():
    for model, expected in [
        ("openai/gpt-6-luna", ["mimo26", "ds41"]),
        ("openai/gpt-6-sol", ["mimo26", "ds41"]),
        ("xiaomi/mimo-v2.6-pro", ["luna6", "ds41"]),
        ("deepseek/deepseek-v4.1-flash", ["mimo26", "luna6"]),
    ]:
        primary, fallback = select_panel([model])
        assert [m.id for m in primary] == expected
        assert [m.id for m in fallback] == ["gemini38-fallback"]
    primary, fallback = select_panel(["openai/gpt-6-sol", "xiaomi/mimo-v2.5"])
    assert [m.id for m in primary] == ["ds41", "gemini38-fallback"]
    assert fallback == []


def test_incomplete_or_split_votes_do_not_become_consensus():
    assert resolve_votes(["pass", None]) is None
    assert resolve_votes(["pass", "fail"]) is None
    assert resolve_votes(["pass", "fail", "pass"]) == "pass"
    assert resolve_votes(["pass", "fail", "uncertain"]) is None
    assert normalize_vote("candidate_a", "ba") == "candidate_b"
    assert normalize_vote("tie", "ba") == "tie"


def test_new_profiles_have_no_output_cap_and_do_not_inherit_gemini_prices():
    case = {
        "id": "test",
        "evaluation_mode": "single",
        "input": {"language_pair": "en-zh", "source": "Hi", "candidate": "你好"},
    }
    for member in ("mimo26", "luna6", "ds41", "gemini38-fallback"):
        judge = PriorityJudge("test", member)
        assert "max_tokens" not in judge.request_body(case)
        cost = judge.cost_fields({"output_tokens": 1_000_000}, {})
        assert cost["exact_cost_usd"] is None
        assert cost["estimated_cost_usd"] == judge.member.output_price

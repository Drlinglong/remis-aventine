from __future__ import annotations

import json
import urllib.error
from io import BytesIO

import pytest

from remis_aventine.calibration import summarize_calibration_fixture
from remis_aventine.judge import (
    DeepSeekFlashJudge,
    DeepSeekJudge,
    GoogleGemmaJudge,
    JudgeRunError,
    OpenRouterDeepSeekFlashJudge,
    OpenRouterGeminiHighJudge,
    OpenRouterGeminiJudge,
    OpenRouterJudge,
    OpenRouterLunaJudge,
    XAIJudge,
    judge_from_environment,
    run_judge_pack,
)


def _evaluation(mode: str = "single", verdict: str = "pass") -> dict:
    return {
        "evaluation": {
            "mode": mode,
            "verdict": verdict,
            "confidence": "high",
            "errors": [],
            "rationale": "The candidate preserves the available evidence.",
            "limitations": [],
        }
    }


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _api_response(evaluation: dict, *, cached: int = 10) -> _Response:
    payload = {
        "choices": [
            {"message": {"content": json.dumps(evaluation), "reasoning_content": "secret"}}
        ],
        "usage": {
            "prompt_tokens": 40,
            "completion_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": cached},
        },
    }
    return _Response(json.dumps(payload).encode())


def _case(case_id: str = "case-1") -> dict:
    return {
        "id": case_id,
        "input": {"language_pair": "en-zh", "source": "Hello", "candidate": "你好"},
        "gold": {"mode": "single", "verdict": "pass"},
    }


def test_deepseek_judge_wraps_server_owned_metadata_and_usage() -> None:
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        return _api_response(_evaluation())

    result, usage = DeepSeekJudge("test-key", opener=opener).evaluate(_case())

    assert result["case_id"] == "case-1"
    assert result["judge"]["model"] == "deepseek-v4-pro"
    assert "reasoning_content" not in json.dumps(result)
    assert usage == {
        "cache_hit_input_tokens": 10,
        "cache_miss_input_tokens": 30,
        "output_tokens": 20,
    }
    request_body = json.loads(requests[0].data)
    assert request_body["thinking"] == {"type": "enabled"}
    assert request_body["response_format"] == {"type": "json_object"}
    assert request_body["max_tokens"] == 8000


def test_resume_cost_fields_use_prior_cumulative_totals() -> None:
    deepseek = DeepSeekJudge("test-key")
    deepseek_cost = deepseek.cost_fields(
        {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 1000,
        },
        {
            "estimated_cost_rmb": 0.1,
            "cumulative_estimated_cost_rmb": 0.9,
        },
    )
    assert deepseek_cost["prior_estimated_cost_rmb"] == 0.9
    assert deepseek_cost["cumulative_estimated_cost_rmb"] > 0.9

    xai = XAIJudge("test-key")
    xai_cost = xai.cost_fields(
        {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 1000,
            "reasoning_tokens": 0,
            "cost_in_usd_ticks": 0,
        },
        {"exact_cost_usd": 0.1, "cumulative_exact_cost_usd": 0.8},
    )
    assert xai_cost["prior_exact_cost_usd"] == 0.8
    assert xai_cost["cumulative_exact_cost_usd"] > 0.8


def test_deepseek_judge_removes_optional_null_fields() -> None:
    evaluation = _evaluation()
    evaluation["evaluation"]["errors"] = [
        {
            "candidate": "candidate",
            "category": "style",
            "severity": "minor",
            "explanation": "Slightly awkward.",
            "source_excerpt": None,
        }
    ]

    def opener(_request, **_kwargs):
        return _api_response(evaluation)

    result, _usage = DeepSeekJudge("test-key", opener=opener).evaluate(_case())

    assert "source_excerpt" not in result["evaluation"]["errors"][0]


def test_deepseek_judge_retries_transient_failure() -> None:
    calls = 0
    sleeps = []

    def opener(_request, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.URLError("temporary")
        return _api_response(_evaluation(), cached=0)

    judge = DeepSeekJudge("test-key", opener=opener, sleeper=sleeps.append)
    judge.evaluate(_case())

    assert calls == 2
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": []},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": '{"evaluation": {}}'}}]},
    ],
)
def test_deepseek_judge_rejects_malformed_output(payload) -> None:
    def opener(_request, **_kwargs):
        return _Response(json.dumps(payload).encode())

    with pytest.raises(JudgeRunError):
        DeepSeekJudge("test-key", opener=opener, sleeper=lambda _seconds: None).evaluate(_case())


def test_judge_from_environment_reads_ignored_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("# local\nDEEPSEEK_API_KEY='from-file'\n", encoding="utf-8")

    judge = judge_from_environment(env_path)

    assert judge.api_key == "from-file"


def test_judge_from_environment_selects_deepseek_flash(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("DEEPSEEK_API_KEY=flash-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, "deepseek-flash")

    assert isinstance(judge, DeepSeekFlashJudge)
    assert judge.model_id == "deepseek-v4-flash"
    assert judge.max_tokens == 8000
    assert judge.reasoning_effort == "low"
    assert judge.api_key == "flash-test"
    request_body = judge.request_body(
        {
            "id": "pair-1",
            "evaluation_mode": "pairwise",
            "input": {
                "language_pair": "en-zh",
                "source": "Hello",
                "candidate_a": "你好",
                "candidate_b": "您好",
            },
            "gold": {"mode": "pairwise", "verdict": "tie"},
        }
    )
    assert request_body["model"] == "deepseek-v4-flash"
    assert request_body["thinking"] == {"type": "enabled"}
    assert request_body["reasoning_effort"] == "low"
    assert request_body["max_tokens"] == 8000
    costs = judge.cost_fields(
        {
            "cache_hit_input_tokens": 1_000_000,
            "cache_miss_input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
        },
        {},
    )
    assert costs["estimated_cost_rmb"] == 3.02


class _FakeJudge:
    provider = "fake"
    provider_label = "Fake"
    model_id = "fake"
    profile = "fake"
    prompt_revision = "fake"
    max_tokens = 100
    thinking = "disabled"
    reasoning_effort = "none"

    def empty_usage(self):
        return {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 0,
        }

    def cost_fields(self, usage, prior_run):
        current = round(usage["output_tokens"] / 1_000_000, 6)
        prior = float(prior_run.get("estimated_cost_rmb", 0.0))
        return {
            "estimated_cost_rmb": current,
            "prior_estimated_cost_rmb": prior,
            "cumulative_estimated_cost_rmb": round(prior + current, 6),
        }

    def evaluate(self, case):
        mode = case.get("evaluation_mode") or case["gold"]["mode"]
        verdict = case.get("synthetic_verdict") or case["gold"]["verdict"]
        return {
            "schema_version": 1,
            "case_id": case["id"],
            "judge": {
                "profile": "fake",
                "model": "fake",
                "prompt_revision": "fake",
                "calibration_revision": "fake",
            },
            **_evaluation(mode, verdict),
        }, {"cache_hit_input_tokens": 1, "cache_miss_input_tokens": 2, "output_tokens": 3}


class _CountingAttemptJudge(_FakeJudge):
    def __init__(self, *, fail_once: set[str] | None = None, interrupt_on: int | None = None):
        self.calls: list[str] = []
        self.sleeps: list[float] = []
        self.sleeper = self.sleeps.append
        self.fail_once = set(fail_once or set())
        self.interrupt_on = interrupt_on

    def evaluate_once(self, case):
        self.calls.append(case["id"])
        if self.interrupt_on == len(self.calls):
            raise KeyboardInterrupt("synthetic interruption")
        if case["id"] in self.fail_once:
            self.fail_once.remove(case["id"])
            raise JudgeRunError("synthetic provider failure", failure_type="provider")
        return self.evaluate(case)


def test_run_judge_pack_adds_aces_swap_and_cost(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [
            {**_case("mqm"), "partition": "calibration"},
            {
                "id": "aces",
                "origin_suite": "aces",
                "partition": "holdout",
                "input": {"source": "x", "candidate_a": "good", "candidate_b": "bad"},
                "gold": {"mode": "pairwise", "verdict": "candidate_a"},
            },
        ],
    }
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_judge_pack(input_path, output_path, _FakeJudge(), max_calls=3)

    assert result["run"]["planned_call_count"] == 3
    assert result["run"]["usage"]["output_tokens"] == 9
    assert result["run"]["estimated_cost_rmb"] > 0
    assert result["cases"][1]["swap_judge_output"]["case_id"] == "aces"
    assert output_path.is_file()
    summary = summarize_calibration_fixture(output_path)
    assert summary["swap_accuracy"] == 1.0
    assert summary["position_consistency_rate"] == 1.0
    assert set(summary["partition_metrics"]) == {"calibration", "holdout"}


def test_run_judge_pack_supports_goldless_operational_pairwise(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "remis-pairwise-v1",
        "suite": "remis-pairwise",
        "recipes": {"left": {"id": "a"}, "right": {"id": "b"}},
        "policy_cases": [],
        "repair_over_editing": {"left": {}, "right": {}},
        "cases": [
            {
                "id": "repair",
                "evaluation_mode": "pairwise",
                "synthetic_verdict": "tie",
                "ab_swap": True,
                "input": {"source": ["x"], "candidate_a": ["a"], "candidate_b": ["b"]},
            }
        ],
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_judge_pack(input_path, tmp_path / "output.json", _FakeJudge(), max_calls=2)

    assert result["run"]["planned_call_count"] == 2
    assert result["recipes"] == fixture["recipes"]
    assert result["cases"][0]["judge_output"]["evaluation"]["mode"] == "pairwise"


def test_run_judge_pack_enforces_call_cap(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(JudgeRunError, match="exceeds max_calls"):
        run_judge_pack(path, tmp_path / "output.json", _FakeJudge(), max_calls=1)


def test_run_judge_pack_selects_exact_case_ids(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_judge_pack(
        path,
        tmp_path / "output.json",
        _FakeJudge(),
        case_ids=["two"],
    )

    assert [case["id"] for case in result["cases"]] == ["two"]

    with pytest.raises(JudgeRunError, match="Unknown case ids"):
        run_judge_pack(
            path,
            tmp_path / "missing.json",
            _FakeJudge(),
            case_ids=["missing"],
        )


def test_run_judge_pack_resumes_only_failed_outputs(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    input_path = tmp_path / "input.json"
    prior_path = tmp_path / "prior.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    prior = run_judge_pack(input_path, prior_path, _FakeJudge())
    prior["cases"][1]["judge_output"] = {"benchmark_failure": {"detail": "failed"}}
    prior_path.write_text(json.dumps(prior), encoding="utf-8")

    result = run_judge_pack(
        input_path,
        tmp_path / "resumed.json",
        _FakeJudge(),
        resume_from=prior_path,
    )

    assert result["run"]["planned_call_count"] == 1
    assert result["run"]["reused_result_count"] == 1
    assert result["run"]["logical_result_count"] == 2
    assert result["run"]["resume_from"] == str(prior_path)


def test_run_judge_pack_rejects_incompatible_resume(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case()],
    }
    input_path = tmp_path / "input.json"
    prior_path = tmp_path / "prior.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    prior_path.write_text(
        json.dumps({**fixture, "run": {"model": "other"}}),
        encoding="utf-8",
    )

    with pytest.raises(JudgeRunError, match="incompatible judge configuration"):
        run_judge_pack(
            input_path,
            tmp_path / "output.json",
            _FakeJudge(),
            resume_from=prior_path,
        )


def test_deepseek_judge_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(JudgeRunError, match="DEEPSEEK_API_KEY"):
        judge_from_environment(tmp_path / "missing.env")


def test_xai_judge_uses_low_reasoning_strict_schema_and_exact_cost() -> None:
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        payload = {
            "choices": [{"message": {"content": json.dumps(_evaluation())}}],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 30,
                "prompt_tokens_details": {"cached_tokens": 20},
                "completion_tokens_details": {"reasoning_tokens": 12},
                "cost_in_usd_ticks": 12_300_000,
            },
        }
        return _Response(json.dumps(payload).encode())

    judge = XAIJudge("test-key", opener=opener)
    result, usage = judge.evaluate(_case())

    assert result["judge"]["model"] == "grok-4.5"
    assert usage["reasoning_tokens"] == 12
    assert usage["cost_in_usd_ticks"] == 12_300_000
    body = json.loads(requests[0].data)
    assert body["reasoning_effort"] == "low"
    assert body["response_format"]["type"] == "json_schema"
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["evaluation"]["properties"]["mode"] == {"const": "single"}
    error_schema = schema["properties"]["evaluation"]["properties"]["errors"]["items"]
    assert error_schema["properties"]["source_excerpt"] == {"type": ["string", "null"]}
    assert requests[0].headers["X-grok-conv-id"] == "aventine-translation-judge-v2"
    costs = judge.cost_fields(usage, {})
    assert costs["exact_cost_usd"] == 0.00123
    assert costs["estimated_cost_usd"] == 0.000322
    assert costs["cost_source"] == "api_ticks"


def test_judge_from_environment_selects_xai(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("XAI_API_KEY=xai-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, "xai")

    assert isinstance(judge, XAIJudge)
    assert judge.api_key == "xai-test"


def test_openrouter_judge_uses_v4_pro_structured_output_and_usd_pricing() -> None:
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        return _api_response(_evaluation(mode="pairwise", verdict="candidate_a"), cached=0)

    judge = OpenRouterJudge("test-key", opener=opener)
    result, usage = judge.evaluate(
        {
            "id": "pair-1",
            "evaluation_mode": "pairwise",
            "input": {
                "language_pair": "en-zh",
                "source": "Hello",
                "candidate_a": "你好",
                "candidate_b": "您好",
            },
            "gold": {"mode": "pairwise", "verdict": "tie"},
        }
    )

    assert result["judge"]["model"] == "deepseek/deepseek-v4-pro"
    body = json.loads(requests[0].data)
    assert body["reasoning_effort"] == "high"
    assert body["max_tokens"] == 8000
    assert "thinking" not in body
    assert body["response_format"]["type"] == "json_schema"
    assert requests[0].headers["Http-referer"] == ("https://drlinglong.github.io/Remis/aventine/")
    costs = judge.cost_fields(usage, {})
    assert costs["estimated_cost_usd"] > 0
    assert costs["cost_source"] == "token_estimate"


def test_judge_from_environment_selects_openrouter(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=openrouter-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, "openrouter")

    assert isinstance(judge, OpenRouterJudge)
    assert judge.api_key == "openrouter-test"


def test_openrouter_gemini_uses_medium_reasoning_schema_and_exact_cost() -> None:
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        payload = {
            "model": "google/gemini-3.7-flash-20260813",
            "provider": "Google Vertex",
            "choices": [{"message": {"content": json.dumps(_evaluation())}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 60,
                "prompt_tokens_details": {"cached_tokens": 40},
                "completion_tokens_details": {"reasoning_tokens": 45},
                "cost": 0.000135,
            },
        }
        return _Response(json.dumps(payload).encode())

    judge = OpenRouterGeminiJudge("test-key", opener=opener)
    result, usage = judge.evaluate(_case())

    assert result["judge"] == {
        "profile": "openrouter-gemini-3.7-flash-reasoning-medium-structured-seeded-v2",
        "model": "google/gemini-3.7-flash",
        "canonical_model": "google/gemini-3.7-flash-20260813",
        "response_model": "google/gemini-3.7-flash-20260813",
        "routed_provider": "Google Vertex",
        "prompt_revision": "translation-judge-v2",
        "calibration_revision": "multilingual-48-v1",
    }
    assert usage == {
        "cache_hit_input_tokens": 40,
        "cache_miss_input_tokens": 60,
        "output_tokens": 60,
        "reasoning_tokens": 45,
        "cost_in_usd_ticks": 1_350_000,
    }
    body = json.loads(requests[0].data)
    assert body["reasoning"] == {"effort": "medium", "exclude": True}
    assert body["provider"] == {"require_parameters": True, "allow_fallbacks": False}
    assert body["seed"] == 20260818
    assert "reasoning_effort" not in body
    assert body["response_format"]["json_schema"]["strict"] is True
    costs = judge.cost_fields(usage, {})
    assert costs["exact_cost_usd"] == 0.000135
    assert costs["estimated_cost_usd"] == 0.0001365
    assert costs["cost_source"] == "openrouter_usage"


def test_openrouter_gemini_estimate_does_not_double_charge_reasoning() -> None:
    judge = OpenRouterGeminiJudge("test-key")
    usage = {
        "cache_hit_input_tokens": 0,
        "cache_miss_input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "reasoning_tokens": 900_000,
        "cost_in_usd_ticks": 0,
    }

    costs = judge.cost_fields(usage, {})

    assert costs["estimated_cost_usd"] == 2.25
    assert costs["exact_cost_usd"] == 2.25
    assert costs["cost_source"] == "token_estimate"


@pytest.mark.parametrize(
    ("provider", "judge_type", "effort"),
    [
        ("openrouter-gemini", OpenRouterGeminiJudge, "medium"),
        ("openrouter-gemini-high", OpenRouterGeminiHighJudge, "high"),
    ],
)
def test_judge_from_environment_selects_openrouter_gemini_profiles(
    tmp_path, monkeypatch, provider, judge_type, effort
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=openrouter-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, provider)

    assert isinstance(judge, judge_type)
    assert judge.reasoning_effort == effort
    assert judge.api_key == "openrouter-test"


@pytest.mark.parametrize(
    ("provider", "judge_type", "model"),
    [
        ("openrouter-luna", OpenRouterLunaJudge, "openai/gpt-5.6-luna"),
        (
            "openrouter-deepseek-flash",
            OpenRouterDeepSeekFlashJudge,
            "deepseek/deepseek-v4-flash-0731",
        ),
    ],
)
def test_judge_from_environment_selects_v03_normal_route_panel(
    tmp_path, monkeypatch, provider, judge_type, model
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=openrouter-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, provider)

    assert isinstance(judge, judge_type)
    assert judge.model_id == model
    assert judge.reasoning_effort == "high"
    body = judge.request_body(_case())
    assert body["model"] == model
    assert body["reasoning"] == {"effort": "high", "exclude": True}
    assert ":batch" not in body["model"]
    if provider == "openrouter-luna":
        assert "seed" not in body
        assert "response_format" not in body


def test_openrouter_luna_drops_non_contract_pairwise_dimensions() -> None:
    evaluation = _evaluation(mode="pairwise", verdict="candidate_a")["evaluation"]
    evaluation["dimensions"] = {
        "candidate_a": {"semantic_accuracy": 90},
        "candidate_b": {"semantic_accuracy": 80},
    }

    def opener(_request, **_kwargs):
        payload = {
            "choices": [{"message": {"content": json.dumps({"evaluation": evaluation})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.0001},
        }
        return _Response(json.dumps(payload).encode())

    case = _case()
    case["evaluation_mode"] = "pairwise"
    case["input"] = {
        "language_pair": "en-zh",
        "source": "Hello",
        "candidate_a": "你好",
        "candidate_b": "您好",
    }
    result, _usage = OpenRouterLunaJudge("test-key", opener=opener).evaluate(case)

    assert result["evaluation"]["verdict"] == "candidate_a"
    assert "dimensions" not in result["evaluation"]


def test_google_gemma_judge_uses_generate_content_schema_and_free_cost() -> None:
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        payload = {
            "candidates": [{"content": {"parts": [{"text": json.dumps(_evaluation())}]}}],
            "usageMetadata": {
                "promptTokenCount": 100,
                "candidatesTokenCount": 25,
                "cachedContentTokenCount": 40,
            },
        }
        return _Response(json.dumps(payload).encode())

    judge = GoogleGemmaJudge("test-key", opener=opener)
    result, usage = judge.evaluate(_case())

    assert result["judge"]["model"] == "gemma-4-31b-it"
    assert usage == {
        "cache_hit_input_tokens": 40,
        "cache_miss_input_tokens": 60,
        "output_tokens": 25,
        "reasoning_tokens": 0,
    }
    body = json.loads(requests[0].data)
    config = body["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    mode_schema = config["responseJsonSchema"]["properties"]["evaluation"]["properties"]["mode"]
    assert mode_schema == {"type": "string", "enum": ["single"]}
    assert "minLength" not in json.dumps(config["responseJsonSchema"])
    assert requests[0].headers["X-goog-api-key"] == "test-key"
    assert "Authorization" not in requests[0].headers
    assert judge.cost_fields(usage, {})["exact_cost_usd"] == 0.0


def test_judge_from_environment_selects_google(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=google-test\n", encoding="utf-8")

    judge = judge_from_environment(env_path, "google")

    assert isinstance(judge, GoogleGemmaJudge)
    assert judge.api_key == "google-test"


def test_run_judge_pack_records_call_failure(tmp_path) -> None:
    class BrokenJudge(_FakeJudge):
        def evaluate(self, _case):
            raise JudgeRunError("synthetic failure")

    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case()],
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_judge_pack(path, tmp_path / "output.json", BrokenJudge())

    assert result["run"]["failure_count"] == 1
    assert result["cases"][0]["judge_output"]["benchmark_failure"]["kind"] == "judge_call_failure"


def test_separate_budgets_fairly_share_attempts_before_retries(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    judge = _CountingAttemptJudge(fail_once={"one"})

    result = run_judge_pack(
        input_path,
        tmp_path / "output.json",
        judge,
        workers=1,
        logical_result_budget=2,
        http_attempt_budget=3,
        result_retry_budget=1,
    )

    assert judge.calls == ["one", "two", "one"]
    assert judge.sleeps == [1.0]
    assert result["run"]["planned_call_count"] == 2
    assert result["run"]["http_attempt_count"] == 3
    assert result["run"]["failure_count"] == 0


def test_partial_separate_budgets_keep_default_cost_caps(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case(f"case-{index}") for index in range(101)],
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    judge = _CountingAttemptJudge()

    result = run_judge_pack(
        input_path,
        tmp_path / "output.json",
        judge,
        result_retry_budget=0,
    )

    assert result["run"]["budget_mode"] == "separate"
    assert result["run"]["logical_result_budget"] == 100
    assert result["run"]["http_attempt_budget"] == 100
    assert result["run"]["scheduled_call_count"] == 100
    assert result["run"]["budget_skipped_count"] == 1
    assert result["run"]["status"] == "budget_exhausted"
    assert len(judge.calls) == 100


def test_interruption_checkpoint_resumes_without_repeating_valid_result(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    input_path = tmp_path / "input.json"
    checkpoint = tmp_path / "checkpoint.json"
    resumed_path = tmp_path / "resumed.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    interrupted_judge = _CountingAttemptJudge(interrupt_on=2)

    with pytest.raises(KeyboardInterrupt):
        run_judge_pack(
            input_path,
            tmp_path / "interrupted.json",
            interrupted_judge,
            checkpoint_path=checkpoint,
            logical_result_budget=2,
            http_attempt_budget=2,
            result_retry_budget=0,
        )

    partial = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert partial["run"]["status"] == "interrupted"
    assert partial["cases"][0]["judge_output"]["case_id"] == "one"
    assert "judge_output" not in partial["cases"][1]

    resumed_judge = _CountingAttemptJudge()
    result = run_judge_pack(
        input_path,
        resumed_path,
        resumed_judge,
        resume_from=checkpoint,
        checkpoint_path=tmp_path / "resumed-checkpoint.json",
        logical_result_budget=1,
        http_attempt_budget=1,
        result_retry_budget=0,
    )

    assert resumed_judge.calls == ["two"]
    assert result["run"]["reused_result_count"] == 1
    assert result["run"]["unfinished_result_count"] == 0
    assert result["run"]["prior_http_attempt_count"] == 2
    assert result["run"]["http_attempt_count"] == 1
    assert result["run"]["cumulative_http_attempt_count"] == 3


def test_resume_skips_all_valid_results_without_duplicate_calls(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one")],
    }
    input_path = tmp_path / "input.json"
    prior_path = tmp_path / "prior.json"
    resumed_path = tmp_path / "resumed.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    first_judge = _CountingAttemptJudge()
    run_judge_pack(input_path, prior_path, first_judge)

    second_judge = _CountingAttemptJudge()
    result = run_judge_pack(input_path, resumed_path, second_judge, resume_from=prior_path)

    assert first_judge.calls == ["one"]
    assert second_judge.calls == []
    assert result["run"]["planned_call_count"] == 0
    assert result["run"]["reused_result_count"] == 1


def test_resume_rejects_configuration_fingerprint_mismatch(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one")],
    }
    input_path = tmp_path / "input.json"
    prior_path = tmp_path / "prior.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    run_judge_pack(input_path, prior_path, _CountingAttemptJudge(), workers=1)

    with pytest.raises(JudgeRunError, match="configuration fingerprint"):
        run_judge_pack(
            input_path,
            tmp_path / "resumed.json",
            _CountingAttemptJudge(),
            workers=2,
            resume_from=prior_path,
        )


def test_budget_exhaustion_is_explicit_and_does_not_call_skipped_result(tmp_path) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [_case("one"), _case("two")],
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")
    judge = _CountingAttemptJudge()

    result = run_judge_pack(
        input_path,
        tmp_path / "output.json",
        judge,
        logical_result_budget=1,
        http_attempt_budget=1,
        result_retry_budget=0,
    )

    assert judge.calls == ["one"]
    assert result["run"]["status"] == "budget_exhausted"
    assert result["run"]["failure_counts"]["budget"] == 1
    assert result["cases"][1]["judge_output"]["benchmark_failure"]["failure_type"] == "budget"


@pytest.mark.parametrize(
    ("failure_type", "opener"),
    [
        ("timeout", lambda _request, **_kwargs: (_ for _ in ()).throw(TimeoutError("timeout"))),
        (
            "rate_limit",
            lambda _request, **_kwargs: (_ for _ in ()).throw(
                urllib.error.HTTPError("https://example.test", 429, "rate", {}, None)
            ),
        ),
        (
            "provider",
            lambda _request, **_kwargs: (_ for _ in ()).throw(
                urllib.error.HTTPError("https://example.test", 400, "bad", {}, None)
            ),
        ),
    ],
)
def test_judge_failure_classification_for_transport_errors(failure_type, opener) -> None:
    with pytest.raises(JudgeRunError) as exc_info:
        DeepSeekJudge("test-key", opener=opener, retries=0).evaluate(_case())

    assert exc_info.value.failure_type == failure_type


@pytest.mark.parametrize(
    ("content", "failure_type"),
    [('{"evaluation":', "truncation"), ("not-json", "json"), ('{"evaluation": {}}', "schema")],
)
def test_judge_failure_classification_for_structured_output(content, failure_type) -> None:
    def opener(_request, **_kwargs):
        payload = {"choices": [{"message": {"content": content}}]}
        return _Response(json.dumps(payload).encode())

    with pytest.raises(JudgeRunError) as exc_info:
        DeepSeekJudge("test-key", opener=opener, retries=0).evaluate(_case())

    assert exc_info.value.failure_type == failure_type

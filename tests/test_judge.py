from __future__ import annotations

import json
import urllib.error
from io import BytesIO

import pytest

from remis_aventine.calibration import summarize_calibration_fixture
from remis_aventine.judge import (
    DeepSeekJudge,
    JudgeRunError,
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
    assert request_body["max_tokens"] == 4000


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


class _FakeJudge:
    def evaluate(self, case):
        mode = case["gold"]["mode"]
        verdict = case["gold"]["verdict"]
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


def test_run_judge_pack_records_call_failure(tmp_path) -> None:
    class BrokenJudge:
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

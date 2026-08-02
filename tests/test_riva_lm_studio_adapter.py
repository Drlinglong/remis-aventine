from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from remis_aventine import riva_lm_studio_worker
from remis_aventine.adapters import riva_lm_studio as riva
from remis_aventine.adapters.riva_lm_studio import (
    LoadedLMStudioModel,
    RivaLMStudioAdapterError,
    RivaLMStudioContestant,
    RivaLMStudioProfile,
    discover_loaded_lm_studio_model,
    run_remis_riva_lm_studio_isolated,
)


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def _loaded_payload():
    return {
        "models": [
            {
                "key": "nvidia/riva-translate-4b-instruct-v2",
                "display_name": "Riva Translate v2",
                "path": "J:/private/model.gguf",
                "architecture": "mistral",
                "loaded_instances": [
                    {
                        "id": "riva-v2-q8",
                        "quantization": "Q8_0",
                        "context_length": 8192,
                        "path": "J:/private/model.gguf",
                    }
                ],
            }
        ]
    }


def test_discovery_resolves_auto_and_drops_private_paths() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeHTTPResponse(_loaded_payload())

    loaded = discover_loaded_lm_studio_model("http://127.0.0.1:1234/v1/", opener=opener)

    assert loaded.model_id == "riva-v2-q8"
    assert loaded.metadata["quantization"] == "Q8_0"
    assert "path" not in loaded.metadata
    assert captured == {"url": "http://127.0.0.1:1234/api/v1/models", "timeout": 10}
    explicit = discover_loaded_lm_studio_model(
        "http://127.0.0.1:1234", requested_model="riva-v2-q8", opener=opener
    )
    assert explicit.model_id == "riva-v2-q8"
    by_model_key = discover_loaded_lm_studio_model(
        "http://127.0.0.1:1234",
        requested_model="nvidia/riva-translate-4b-instruct-v2",
        opener=opener,
    )
    assert by_model_key.model_id == "riva-v2-q8"


def test_discovery_rejects_ambiguous_missing_and_malformed_models() -> None:
    def empty(*_args, **_kwargs):
        return FakeHTTPResponse({"models": []})

    with pytest.raises(RivaLMStudioAdapterError, match="exactly one"):
        discover_loaded_lm_studio_model(riva.DEFAULT_BASE_URL, opener=empty)
    with pytest.raises(RivaLMStudioAdapterError, match="not loaded"):
        discover_loaded_lm_studio_model(
            riva.DEFAULT_BASE_URL, requested_model="missing", opener=empty
        )
    with pytest.raises(RivaLMStudioAdapterError, match="models array"):
        discover_loaded_lm_studio_model(
            riva.DEFAULT_BASE_URL,
            opener=lambda *_args, **_kwargs: FakeHTTPResponse({}),
        )
    with pytest.raises(RivaLMStudioAdapterError, match="malformed"):
        discover_loaded_lm_studio_model(
            riva.DEFAULT_BASE_URL,
            opener=lambda *_args, **_kwargs: FakeHTTPResponse(b"not-json"),
        )


def test_profile_records_native_prompt_and_no_endpoint() -> None:
    profile = RivaLMStudioProfile("riva-v2", max_output_tokens=1024, quantization="Q8_0")
    loaded = LoadedLMStudioModel("riva-v2", {"quantization": "Q8_0"})
    request_profile = profile.request_profile(
        loaded_model=loaded, language_pairs=["en-zh-cn", "zh-cn-en", "en-zh-cn"]
    )

    assert request_profile["revision"] == "riva-translate-v2-lm-studio-v1"
    assert request_profile["language_pairs"] == ["en-zh-cn", "zh-cn-en"]
    assert request_profile["native_prompt"] == {
        "system": "language_pair_tag",
        "user": "source_text_only",
        "batch_strategy": "one_request_per_string",
        "glossary_strategy": "few_shot_priority",
    }
    assert request_profile["repair_strategy"] == "source_retranslation"
    assert request_profile["reasoning_label"] == "none"
    assert "base_url" not in request_profile


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": " "}, "non-empty"),
        ({"model": "riva", "base_url": "file:///model"}, "absolute HTTP"),
        ({"model": "riva", "base_url": "http://user:pass@localhost/v1"}, "credentials"),
        ({"model": "riva", "base_url": "http://localhost/custom"}, "empty or /v1"),
        ({"model": "riva", "max_output_tokens": 0}, "must be positive"),
        ({"model": "riva", "max_output_tokens": True}, "must be positive"),
        ({"model": "riva", "temperature": -0.1}, "between 0 and 2"),
        ({"model": "riva", "timeout_seconds": 0}, "must be positive"),
        ({"model": "riva", "quantization": " "}, "must not be empty"),
    ],
)
def test_profile_rejects_invalid_configuration(kwargs, message) -> None:
    with pytest.raises(RivaLMStudioAdapterError, match=message):
        RivaLMStudioProfile(**kwargs)


def test_language_pair_supports_pilot_and_rejects_non_english_pair() -> None:
    assert riva.riva_language_pair("en", "zh-CN") == "en-zh-cn"
    assert riva.riva_language_pair("zh-CN", "en") == "zh-cn-en"
    with pytest.raises(RivaLMStudioAdapterError, match="between English"):
        riva.riva_language_pair("de", "fr")
    with pytest.raises(RivaLMStudioAdapterError, match="Unsupported"):
        riva.riva_language_pair("en", "xx")


def test_translate_many_uses_native_language_tag_few_shots_and_aggregates_usage() -> None:
    captured = []
    responses = iter(
        [
            {
                "model": "riva-v2-q8",
                "choices": [{"finish_reason": "stop", "message": {"content": "法兰西"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                    "prompt_tokens_details": {"cached_tokens": 1},
                },
            },
            {
                "model": "riva-v2-q8",
                "choices": [{"finish_reason": "stop", "message": {"content": "得克萨斯"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14},
            },
        ]
    )

    def opener(request, timeout):
        captured.append((json.loads(request.data.decode("utf-8")), timeout, request.full_url))
        return FakeHTTPResponse(next(responses))

    contestant = RivaLMStudioContestant(
        RivaLMStudioProfile("riva-v2-q8", max_output_tokens=128), opener=opener
    )
    batch = contestant.translate_many(
        ["France", "Texas"],
        source_language="en",
        target_language="zh-CN",
        glossary_entries=[
            {"translations": {"en": "France", "zh-CN": "法兰西"}},
            {"translations": {"en": "ignored"}},
        ],
    )

    assert batch.translations == ["法兰西", "得克萨斯"]
    assert batch.usage == {
        "input_tokens": 21,
        "output_tokens": 5,
        "reasoning_tokens": 0,
        "cached_input_tokens": 1,
        "total_tokens": 26,
    }
    assert batch.response_models == ["riva-v2-q8", "riva-v2-q8"]
    assert len(batch.prompt_sha256) == 64
    first_body = captured[0][0]
    assert first_body["temperature"] == 0.0
    assert first_body["max_tokens"] == 128
    assert first_body["messages"] == [
        {"role": "system", "content": "en-zh-cn"},
        {"role": "user", "content": "France"},
        {"role": "assistant", "content": "法兰西"},
        {"role": "user", "content": "France"},
    ]
    assert captured[0][2].endswith("/v1/chat/completions")


def test_translate_rejects_empty_and_provider_failure_shapes() -> None:
    profile = RivaLMStudioProfile("riva")
    with pytest.raises(RivaLMStudioAdapterError, match="must not be empty"):
        RivaLMStudioContestant(profile).translate_many(
            [], source_language="en", target_language="zh-CN"
        )
    with pytest.raises(RivaLMStudioAdapterError, match="source text"):
        riva.build_riva_messages("", "en", "zh-CN", [])

    payloads = [
        ({}, "no Riva translation choice"),
        (
            {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]},
            "max_output_tokens",
        ),
        ({"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}, "empty"),
    ]
    for payload, message in payloads:
        contestant = RivaLMStudioContestant(
            profile, opener=lambda *_args, _payload=payload, **_kwargs: FakeHTTPResponse(_payload)
        )
        with pytest.raises(RivaLMStudioAdapterError, match=message):
            contestant.translate_many(["text"], source_language="en", target_language="zh-CN")


def test_full_runner_writes_raw_and_adapted_artifacts(monkeypatch, tmp_path: Path) -> None:
    cases = [
        {
            "id": "translation",
            "track": "translation",
            "source_lang": "en",
            "target_lang": "zh-CN",
            "source_entries": [{"key": "one", "text": "France"}],
            "glossary_entries": [{"translations": {"en": "France", "zh-CN": "法兰西"}}],
        },
        {
            "id": "repair",
            "track": "repair",
            "source_lang": "zh-CN",
            "target_lang": "en",
            "source_entries": [{"key": "two", "text": "你好"}],
        },
    ]

    class BaseHandler:
        def __init__(self, provider, model_id):
            self.provider_name = provider
            self.model_id = model_id
            self.client = self.initialize_client()

        def _parse_response(self, response, _texts, _target):
            return json.loads(response)["translations"]

    class Glossary:
        in_memory_glossary = {"entries": [{"term": "old"}]}

    def run_case(case, handler, _validator):
        task = SimpleNamespace(texts=[entry["text"] for entry in case["source_entries"]])
        prompt = handler._build_prompt(task)
        outputs = handler._parse_response(
            handler._call_api(handler.client, prompt), task.texts, case["target_lang"]
        )
        return {
            "id": case["id"],
            "track": case["track"],
            "prompt_sha256": "old",
            "execution_failure": None,
            "elapsed_seconds": 0.1,
            "outputs": outputs,
            "score": {
                "parsed": True,
                "item_count_match": True,
                "hard_pass": True,
                "quality_constraint_pass": True,
                "items": [],
            },
        }

    benchmark = SimpleNamespace(
        read_fixture=lambda _path: (
            {"name": "fixture", "manual_review_rubric": {"method": "pairwise"}},
            "fixture-hash",
        ),
        validate_fixture=lambda _fixture: cases,
        selected_cases=lambda _fixture, track, ids: [
            case
            for case in cases
            if (track == "all" or case["track"] == track) and (not ids or case["id"] in ids)
        ],
        run_translation_case=run_case,
        run_repair_case=run_case,
        summarize_results=lambda results: {
            "case_count": len(results),
            "execution_failure_count": 0,
            "structured_output_failure_count": 0,
            "hard_pass_count": len(results),
            "quality_constraint_pass_count": len(results),
            "elapsed_seconds": 0.2,
        },
    )
    glossary = Glossary()
    modules = {
        "benchmark": benchmark,
        "base_handler": BaseHandler,
        "validator": object,
        "glossary_manager": glossary,
    }

    @contextmanager
    def fake_imports(_root):
        yield modules

    monkeypatch.setattr(riva, "_remis_imports", fake_imports)
    monkeypatch.setattr(
        riva,
        "_remis_checkout_provenance",
        lambda _root: {"revision": "a" * 40, "source_sha256": "b" * 64},
    )
    monkeypatch.setattr(
        riva,
        "discover_loaded_lm_studio_model",
        lambda *_args, **_kwargs: LoadedLMStudioModel("riva-v2-q8", {"quantization": "Q8_0"}),
    )
    monkeypatch.setattr(
        riva,
        "convert_remis_result",
        lambda report, recipe_id=None: {
            "run_id": recipe_id or "generated",
            "provider": report["provider"],
        },
    )
    responses = iter(
        [
            {"model": "riva-v2-q8", "choices": [{"message": {"content": "法兰西"}}]},
            {"model": "riva-v2-q8", "choices": [{"message": {"content": "Hello"}}]},
        ]
    )

    def opener(*_args, **_kwargs):
        return FakeHTTPResponse(next(responses))

    raw = tmp_path / "raw/result.json"
    run = tmp_path / "run/result.json"

    result = riva.run_remis_riva_lm_studio(
        tmp_path,
        tmp_path / "fixture.json",
        raw,
        run,
        label="Riva v2",
        quantization="Q8_0",
        recipe_id="remis.riva-v2-q8.all",
        opener=opener,
    )

    assert result["run_id"] == "remis.riva-v2-q8.all"
    report = json.loads(raw.read_text(encoding="utf-8"))
    assert report["provider"] == "lm-studio-riva-native"
    assert report["request_profile"]["repair_strategy"] == "source_retranslation"
    assert report["request_profile"]["language_pairs"] == ["en-zh-cn", "zh-cn-en"]
    assert report["results"][0]["usage"]["reasoning_tokens"] == 0
    assert report["results"][0]["prompt_sha256"] != "old"
    assert json.loads(run.read_text(encoding="utf-8"))["provider"] == "lm-studio-riva-native"
    assert glossary.in_memory_glossary == {"entries": [{"term": "old"}]}


def test_runner_rejects_track_and_wraps_remis_import_error(monkeypatch, tmp_path) -> None:
    with pytest.raises(RivaLMStudioAdapterError, match="Unsupported"):
        riva.run_remis_riva_lm_studio(
            tmp_path, Path("fixture"), Path("raw"), Path("run"), track="bad"
        )
    monkeypatch.setattr(
        riva,
        "discover_loaded_lm_studio_model",
        lambda *_args, **_kwargs: LoadedLMStudioModel("riva", {}),
    )
    monkeypatch.setattr(
        riva,
        "_remis_checkout_provenance",
        lambda _root: (_ for _ in ()).throw(riva.GoogleAIStudioAdapterError("bad checkout")),
    )
    with pytest.raises(RivaLMStudioAdapterError, match="bad checkout"):
        riva.run_remis_riva_lm_studio(tmp_path, Path("fixture"), Path("raw"), Path("run"))


def test_isolated_runner_uses_stdin_and_classifies_failures(monkeypatch, tmp_path) -> None:
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args, 0, stdout='notice\n{"completed": true, "run_id": "run"}\n', stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_remis_riva_lm_studio_isolated(
        runtime,
        tmp_path,
        Path("fixture"),
        Path("raw"),
        Path("run"),
        quantization="Q8_0",
    )
    assert result["run_id"] == "run"
    assert captured["args"] == [
        str(runtime.resolve()),
        "-m",
        "remis_aventine.riva_lm_studio_worker",
    ]
    request = json.loads(captured["kwargs"]["input"])
    assert request["quantization"] == "Q8_0"
    assert "api_key" not in request

    failures = [
        (subprocess.CompletedProcess([], 1, "", "worker exploded"), "exploded"),
        (subprocess.CompletedProcess([], 0, "", ""), "no status"),
        (subprocess.CompletedProcess([], 0, "not-json", ""), "malformed"),
        (subprocess.CompletedProcess([], 0, "[]", ""), "must be an object"),
    ]
    for completed, message in failures:
        monkeypatch.setattr(subprocess, "run", lambda *_args, _c=completed, **_kwargs: _c)
        with pytest.raises(RivaLMStudioAdapterError, match=message):
            run_remis_riva_lm_studio_isolated(
                runtime, tmp_path, Path("fixture"), Path("raw"), Path("run")
            )


def test_isolated_runner_validates_runtime_timeout_and_subprocess_failure(
    monkeypatch, tmp_path
) -> None:
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"")
    with pytest.raises(RivaLMStudioAdapterError, match="does not exist"):
        run_remis_riva_lm_studio_isolated(
            tmp_path / "missing", tmp_path, Path("f"), Path("r"), Path("o")
        )
    with pytest.raises(RivaLMStudioAdapterError, match="timeout_seconds"):
        run_remis_riva_lm_studio_isolated(
            runtime, tmp_path, Path("f"), Path("r"), Path("o"), timeout_seconds=0
        )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("worker", 1)),
    )
    with pytest.raises(RivaLMStudioAdapterError, match="worker failed"):
        run_remis_riva_lm_studio_isolated(runtime, tmp_path, Path("f"), Path("r"), Path("o"))


def test_worker_validates_request_and_emits_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("[]"))
    assert riva_lm_studio_worker.main() == 2
    assert "JSON object" in capsys.readouterr().err

    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert riva_lm_studio_worker.main() == 2
    assert "remis_root" in capsys.readouterr().err

    request = {
        "remis_root": "repo",
        "fixture_path": "fixture.json",
        "raw_output_path": "raw.json",
        "run_output_path": "run.json",
        "model": "auto",
        "base_url": riva.DEFAULT_BASE_URL,
        "max_output_tokens": 128,
        "temperature": 0.0,
        "request_timeout_seconds": 300,
        "quantization": "Q8_0",
        "track": "all",
        "case_ids": [],
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))
    monkeypatch.setattr(
        riva_lm_studio_worker,
        "run_remis_riva_lm_studio",
        lambda *_args, **_kwargs: {"completed": True, "run_id": "run"},
    )
    assert riva_lm_studio_worker.main() == 0
    assert json.loads(capsys.readouterr().out)["run_id"] == "run"

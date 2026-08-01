import io
import json
import subprocess
import sys
import urllib.error
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from remis_aventine import google_ai_studio_worker
from remis_aventine.adapters import google_ai_studio as google_adapter
from remis_aventine.adapters.google_ai_studio import (
    GoogleAIStudioAdapterError,
    GoogleAIStudioContestant,
    GoogleAIStudioProfile,
    run_remis_google_ai_studio_isolated,
)


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeRawHTTPResponse(FakeHTTPResponse):
    def read(self):
        return self.payload


def test_profile_records_explicit_reasoning_without_credentials() -> None:
    profile = GoogleAIStudioProfile("gemini-3.6-flash", "high", 16_000)

    assert profile.request_profile() == {
        "revision": "google-ai-studio-contestant-v1",
        "api_mode": "generateContent",
        "model": "gemini-3.6-flash",
        "max_output_tokens": 16_000,
        "response_mime_type": "application/json",
        "reasoning": {
            "enabled": True,
            "effort": "high",
            "include_thoughts": False,
        },
        "reasoning_label": "high",
        "reasoning_effort_requested": "high",
        "client_max_retries": 0,
    }


@pytest.mark.parametrize("effort", ["none", "enabled", "xhigh", "max", ""])
def test_profile_rejects_unpublished_gemini_efforts(effort) -> None:
    with pytest.raises(GoogleAIStudioAdapterError, match="reasoning effort"):
        GoogleAIStudioProfile("gemini-3.6-flash", effort, 16_000)


def test_generate_uses_requested_model_profile_and_records_usage() -> None:
    captured = {}
    payload = {
        "modelVersion": "gemini-3.6-flash-20260731",
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "parts": [
                        {"text": "hidden summary", "thought": True},
                        {"text": '{"translations":["译文"]}'},
                    ]
                },
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 30,
            "thoughtsTokenCount": 45,
            "cachedContentTokenCount": 10,
            "totalTokenCount": 195,
        },
    }

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(payload)

    contestant = GoogleAIStudioContestant(
        "secret-test-key",
        GoogleAIStudioProfile("gemini-3.6-flash", "high", 16_000),
        opener=opener,
    )
    response = contestant.generate("Translate this fixture")

    assert response.text == '{"translations":["译文"]}'
    assert response.response_model == "gemini-3.6-flash-20260731"
    assert response.usage == {
        "input_tokens": 120,
        "output_tokens": 30,
        "reasoning_tokens": 45,
        "cached_input_tokens": 10,
        "total_tokens": 195,
    }
    assert captured["timeout"] == 300
    assert captured["request"].full_url.endswith("/gemini-3.6-flash:generateContent")
    body = json.loads(captured["request"].data.decode("utf-8"))
    assert body["generationConfig"] == {
        "maxOutputTokens": 16_000,
        "responseMimeType": "application/json",
        "thinkingConfig": {"thinkingLevel": "high", "includeThoughts": False},
    }


def test_generate_classifies_http_and_truncation_failures() -> None:
    def failing_opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "rate limit", {}, io.BytesIO())

    profile = GoogleAIStudioProfile("gemini-3.5-flash-lite", "minimal", 4_000)
    contestant = GoogleAIStudioContestant("test-key", profile, opener=failing_opener)
    with pytest.raises(GoogleAIStudioAdapterError, match="status 429"):
        contestant.generate("prompt")

    truncated = GoogleAIStudioContestant(
        "test-key",
        profile,
        opener=lambda _request, timeout: FakeHTTPResponse(
            {
                "candidates": [
                    {
                        "finishReason": "MAX_TOKENS",
                        "content": {"parts": [{"text": "partial"}]},
                    }
                ]
            }
        ),
    )
    with pytest.raises(GoogleAIStudioAdapterError, match="MAX_TOKENS"):
        truncated.generate("prompt")


def test_isolated_runner_uses_stdin_without_putting_credentials_in_argv(
    monkeypatch, tmp_path
) -> None:
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="Remis initialization notice\n"
            + json.dumps({"completed": True, "run_id": "run"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_remis_google_ai_studio_isolated(
        runtime,
        tmp_path,
        tmp_path / "fixture.json",
        tmp_path / "raw.json",
        tmp_path / "run.json",
        model="gemini-3.6-flash",
    )

    assert result == {"completed": True, "run_id": "run"}
    assert captured["args"] == [
        str(runtime.resolve()),
        "-m",
        "remis_aventine.google_ai_studio_worker",
    ]
    worker_request = json.loads(captured["kwargs"]["input"])
    assert worker_request["model"] == "gemini-3.6-flash"
    assert "api_key" not in worker_request
    assert "secret" not in " ".join(captured["args"]).lower()
    assert Path(captured["kwargs"]["cwd"]) == tmp_path.resolve()


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: GoogleAIStudioProfile(" ", "high", 1), "non-empty"),
        (lambda: GoogleAIStudioProfile("gemini", "high", True), "must be positive"),
        (lambda: GoogleAIStudioProfile("gemini", "high", 0), "must be positive"),
        (
            lambda: GoogleAIStudioContestant("", GoogleAIStudioProfile("gemini", "high", 1)),
            "not configured",
        ),
        (
            lambda: GoogleAIStudioContestant(
                "key", GoogleAIStudioProfile("gemini", "high", 1), timeout_seconds=0
            ),
            "must be positive",
        ),
    ],
)
def test_google_profile_and_transport_reject_invalid_configuration(factory, message) -> None:
    with pytest.raises(GoogleAIStudioAdapterError, match=message):
        factory()


def test_generate_classifies_transport_and_payload_failures() -> None:
    profile = GoogleAIStudioProfile("gemini", "high", 10)

    with pytest.raises(GoogleAIStudioAdapterError, match="must not be empty"):
        GoogleAIStudioContestant("key", profile)._request_body("")

    failures = [
        (
            lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
            "offline",
        ),
        (lambda *_args, **_kwargs: FakeRawHTTPResponse(b"not-json"), "malformed"),
        (lambda *_args, **_kwargs: FakeHTTPResponse({}), "no candidate"),
        (
            lambda *_args, **_kwargs: FakeHTTPResponse(
                {"candidates": [{"finishReason": "MALFORMED_FUNCTION_CALL"}]}
            ),
            "MALFORMED_FUNCTION_CALL",
        ),
        (
            lambda *_args, **_kwargs: FakeHTTPResponse(
                {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]}
            ),
            "no final text",
        ),
    ]
    for opener, message in failures:
        with pytest.raises(GoogleAIStudioAdapterError, match=message):
            GoogleAIStudioContestant("key", profile, opener=opener).generate("prompt")


def test_env_key_reader_handles_comments_quotes_and_missing_files(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# comment\nIGNORED\nGEMINI_API_KEY='secret'\n", encoding="utf-8")

    assert google_adapter._read_env_key(env, "GEMINI_API_KEY") == "secret"
    assert google_adapter._read_env_key(env, "MISSING") is None
    assert google_adapter._read_env_key(tmp_path / "absent", "GEMINI_API_KEY") is None


def test_remis_checkout_provenance_pins_revision_and_source_hash(
    monkeypatch, tmp_path: Path
) -> None:
    for relative in google_adapter.REMIS_IDENTITY_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, stdout="a" * 40 + "\n", stderr=""
        ),
    )

    first = google_adapter._remis_checkout_provenance(tmp_path)
    assert first["revision"] == "a" * 40
    assert len(first["source_sha256"]) == 64

    changed = tmp_path / google_adapter.REMIS_IDENTITY_PATHS[0]
    changed.write_text("changed", encoding="utf-8")
    assert (
        google_adapter._remis_checkout_provenance(tmp_path)["source_sha256"]
        != first["source_sha256"]
    )

    changed.unlink()
    with pytest.raises(GoogleAIStudioAdapterError, match="identity source is missing"):
        google_adapter._remis_checkout_provenance(tmp_path)


def test_remis_import_guard_and_import_failure(monkeypatch, tmp_path: Path) -> None:
    with (
        pytest.raises(GoogleAIStudioAdapterError, match="entrypoint is missing"),
        google_adapter._remis_imports(tmp_path),
    ):
        pass

    benchmark = tmp_path / "scripts/developer_tools/evaluate_translation_quality.py"
    benchmark.parent.mkdir(parents=True)
    benchmark.write_text("", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "scripts", SimpleNamespace(__path__=[str(tmp_path / "other")]))
    with (
        pytest.raises(GoogleAIStudioAdapterError, match="different Remis checkout"),
        google_adapter._remis_imports(tmp_path),
    ):
        pass

    monkeypatch.delitem(sys.modules, "scripts", raising=False)
    monkeypatch.setattr(
        google_adapter.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ImportError("broken checkout")),
    )
    with (
        pytest.raises(GoogleAIStudioAdapterError, match="broken checkout"),
        google_adapter._remis_imports(tmp_path),
    ):
        pass
    assert str(tmp_path.resolve()) not in sys.path


def test_run_remis_google_adapter_writes_both_artifact_layers(monkeypatch, tmp_path: Path) -> None:
    calls = []

    class BaseHandler:
        def __init__(self, provider, model_id):
            self.provider = provider
            self.model_id = model_id

    class Glossary:
        in_memory_glossary = {"entries": [{"term": "old"}]}

    benchmark = SimpleNamespace(
        read_fixture=lambda _path: (
            {"name": "fixture", "manual_review_rubric": {"scale": "pilot"}},
            "fixture-hash",
        ),
        validate_fixture=lambda fixture: calls.append(("validate", fixture["name"])),
        selected_cases=lambda _fixture, track, case_ids: [
            {"id": "translation", "track": "translation", "selection": (track, case_ids)},
            {"id": "repair", "track": "repair", "selection": (track, case_ids)},
        ],
        run_translation_case=lambda case, handler, validator: {
            "id": case["id"],
            "track": case["track"],
            "execution_status": "completed",
        },
        run_repair_case=lambda case, handler, validator: {
            "id": case["id"],
            "track": case["track"],
            "execution_status": "completed",
        },
        summarize_results=lambda results: {"case_count": len(results), "hard_pass_count": 2},
    )
    modules = {
        "benchmark": benchmark,
        "base_handler": BaseHandler,
        "validator": object,
        "glossary_manager": Glossary(),
        "get_api_key": lambda *_args: "settings-key",
    }

    @contextmanager
    def fake_imports(_root):
        yield modules

    monkeypatch.setattr(google_adapter, "_remis_imports", fake_imports)
    monkeypatch.setattr(
        google_adapter,
        "_remis_checkout_provenance",
        lambda _root: {"revision": "a" * 40, "source_sha256": "b" * 64},
    )
    monkeypatch.setattr(
        google_adapter,
        "convert_remis_result",
        lambda report, recipe_id=None: {
            "run_id": recipe_id or "generated",
            "provider": report["provider"],
        },
    )

    raw = tmp_path / "nested/raw.json"
    run = tmp_path / "nested/run.json"
    result = google_adapter.run_remis_google_ai_studio(
        tmp_path,
        tmp_path / "fixture.json",
        raw,
        run,
        model="gemini-test",
        label="Gemini Test",
        track="all",
        case_ids=("translation",),
        recipe_id="recipe.google",
    )

    assert result["completed"] is True
    assert result["run_id"] == "recipe.google"
    assert json.loads(raw.read_text(encoding="utf-8"))["model_label"] == "Gemini Test"
    assert json.loads(raw.read_text(encoding="utf-8"))["remis_checkout"]["revision"] == "a" * 40
    assert json.loads(run.read_text(encoding="utf-8"))["provider"] == "google-ai-studio"
    assert modules["glossary_manager"].in_memory_glossary == {"entries": [{"term": "old"}]}
    with pytest.raises(GoogleAIStudioAdapterError, match="Unsupported"):
        google_adapter.run_remis_google_ai_studio(
            tmp_path, Path("fixture"), Path("raw"), Path("run"), model="gemini", track="bad"
        )


def test_isolated_runner_classifies_worker_failures(monkeypatch, tmp_path: Path) -> None:
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"")
    cases = [
        (subprocess.CompletedProcess([], 1, stdout="", stderr="worker exploded"), "exploded"),
        (subprocess.CompletedProcess([], 0, stdout="", stderr=""), "no status"),
        (subprocess.CompletedProcess([], 0, stdout="notice\nnot-json", stderr=""), "malformed"),
        (subprocess.CompletedProcess([], 0, stdout="[]", stderr=""), "must be an object"),
    ]
    for completed, message in cases:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, _completed=completed, **_kwargs: _completed,
        )
        with pytest.raises(GoogleAIStudioAdapterError, match=message):
            run_remis_google_ai_studio_isolated(
                runtime, tmp_path, Path("fixture"), Path("raw"), Path("run"), model="gemini"
            )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("worker", 1)),
    )
    with pytest.raises(GoogleAIStudioAdapterError, match="failed"):
        run_remis_google_ai_studio_isolated(
            runtime, tmp_path, Path("fixture"), Path("raw"), Path("run"), model="gemini"
        )
    with pytest.raises(GoogleAIStudioAdapterError, match="does not exist"):
        run_remis_google_ai_studio_isolated(
            tmp_path / "missing",
            tmp_path,
            Path("fixture"),
            Path("raw"),
            Path("run"),
            model="gemini",
        )
    with pytest.raises(GoogleAIStudioAdapterError, match="timeout_seconds"):
        run_remis_google_ai_studio_isolated(
            runtime,
            tmp_path,
            Path("fixture"),
            Path("raw"),
            Path("run"),
            model="gemini",
            timeout_seconds=0,
        )


def test_google_worker_validates_request_and_emits_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("[]"))
    assert google_ai_studio_worker.main() == 2
    assert "JSON object" in capsys.readouterr().err

    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert google_ai_studio_worker.main() == 2
    assert "remis_root" in capsys.readouterr().err

    request = {
        "remis_root": "repo",
        "fixture_path": "fixture.json",
        "raw_output_path": "raw.json",
        "run_output_path": "run.json",
        "model": "gemini",
        "reasoning_effort": "high",
        "max_output_tokens": 100,
        "track": "all",
        "env_file": ".env",
        "case_ids": ["one"],
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))
    monkeypatch.setattr(
        google_ai_studio_worker,
        "run_remis_google_ai_studio",
        lambda *_args, **_kwargs: {"completed": True, "run_id": "run"},
    )
    assert google_ai_studio_worker.main() == 0
    assert json.loads(capsys.readouterr().out)["run_id"] == "run"

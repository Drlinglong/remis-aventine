import io
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

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

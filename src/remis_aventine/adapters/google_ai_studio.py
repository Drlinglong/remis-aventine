"""Google AI Studio contestant execution for the frozen Remis benchmark."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from remis_aventine.adapters.remis import convert_remis_result

ADAPTER_REVISION = "google-ai-studio-contestant-v1"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
SUPPORTED_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high"})


class GoogleAIStudioAdapterError(RuntimeError):
    """Raised when the bounded Google contestant adapter cannot complete safely."""


@dataclass(frozen=True, slots=True)
class GoogleAIStudioProfile:
    """One explicit Google AI Studio contestant recipe."""

    model: str
    reasoning_effort: str
    max_output_tokens: int

    def __post_init__(self) -> None:
        if not self.model or not self.model.strip():
            raise GoogleAIStudioAdapterError("Google model must be a non-empty string.")
        if self.reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
            supported = ", ".join(sorted(SUPPORTED_REASONING_EFFORTS))
            raise GoogleAIStudioAdapterError(
                f"Unsupported Google reasoning effort {self.reasoning_effort!r}; use {supported}."
            )
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens <= 0
        ):
            raise GoogleAIStudioAdapterError("Google max_output_tokens must be positive.")

    def request_profile(self) -> dict[str, Any]:
        """Return the public, credential-free recipe evidence."""
        return {
            "revision": ADAPTER_REVISION,
            "api_mode": "generateContent",
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "response_mime_type": "application/json",
            "reasoning": {
                "enabled": True,
                "effort": self.reasoning_effort,
                "include_thoughts": False,
            },
            "reasoning_label": self.reasoning_effort,
            "reasoning_effort_requested": self.reasoning_effort,
            "client_max_retries": 0,
        }


@dataclass(frozen=True, slots=True)
class GoogleAIStudioResponse:
    """Sanitized output and usage returned by one generateContent request."""

    text: str
    response_model: str
    usage: dict[str, int]


class GoogleAIStudioContestant:
    """Minimal synchronous generateContent transport with explicit reasoning."""

    def __init__(
        self,
        api_key: str,
        profile: GoogleAIStudioProfile,
        *,
        timeout_seconds: int = 300,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        if not api_key:
            raise GoogleAIStudioAdapterError("GEMINI_API_KEY is not configured.")
        if timeout_seconds <= 0:
            raise GoogleAIStudioAdapterError("Google timeout_seconds must be positive.")
        self._api_key = api_key
        self.profile = profile
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def _request_body(self, prompt: str) -> dict[str, Any]:
        if not prompt:
            raise GoogleAIStudioAdapterError("Google contestant prompt must not be empty.")
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self.profile.max_output_tokens,
                "responseMimeType": "application/json",
                "thinkingConfig": {
                    "thinkingLevel": self.profile.reasoning_effort,
                    "includeThoughts": False,
                },
            },
        }

    def generate(self, prompt: str) -> GoogleAIStudioResponse:
        """Execute one call without retries and discard thought summaries."""
        model_path = urllib.parse.quote(self.profile.model, safe="-._")
        request = urllib.request.Request(
            f"{API_ROOT}/{model_path}:generateContent",
            data=json.dumps(self._request_body(prompt), ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GoogleAIStudioAdapterError(
                f"Google AI Studio HTTP failure: status {exc.code}."
            ) from exc
        except urllib.error.URLError as exc:
            raise GoogleAIStudioAdapterError(
                f"Google AI Studio request failed: {exc.reason}."
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleAIStudioAdapterError(
                "Google AI Studio returned malformed response JSON."
            ) from exc

        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise GoogleAIStudioAdapterError("Google AI Studio returned no candidate.")
        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        if finish_reason in {"MAX_TOKENS", "MALFORMED_FUNCTION_CALL"}:
            raise GoogleAIStudioAdapterError(
                f"Google AI Studio response was incomplete: {finish_reason}."
            )
        parts = candidate.get("content", {}).get("parts", [])
        text_parts = [
            part["text"]
            for part in parts
            if isinstance(part, dict)
            and part.get("thought") is not True
            and isinstance(part.get("text"), str)
        ]
        text = "".join(text_parts).strip()
        if not text:
            raise GoogleAIStudioAdapterError("Google AI Studio returned no final text.")

        usage = payload.get("usageMetadata", {})
        return GoogleAIStudioResponse(
            text=text,
            response_model=str(payload.get("modelVersion") or self.profile.model),
            usage={
                "input_tokens": int(usage.get("promptTokenCount") or 0),
                "output_tokens": int(usage.get("candidatesTokenCount") or 0),
                "reasoning_tokens": int(usage.get("thoughtsTokenCount") or 0),
                "cached_input_tokens": int(usage.get("cachedContentTokenCount") or 0),
                "total_tokens": int(usage.get("totalTokenCount") or 0),
            },
        )


def _read_env_key(path: Path, name: str) -> str | None:
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


@contextmanager
def _remis_imports(remis_root: Path) -> Iterator[dict[str, Any]]:
    resolved = remis_root.resolve()
    benchmark_path = resolved / "scripts/developer_tools/evaluate_translation_quality.py"
    if not benchmark_path.is_file():
        raise GoogleAIStudioAdapterError(f"Remis benchmark entrypoint is missing: {benchmark_path}")
    loaded_scripts = sys.modules.get("scripts")
    loaded_path = getattr(loaded_scripts, "__path__", ()) if loaded_scripts else ()
    matching_checkout_loaded = any(
        Path(path).resolve() == (resolved / "scripts") for path in loaded_path
    )
    if loaded_path and not matching_checkout_loaded:
        raise GoogleAIStudioAdapterError(
            "A different Remis checkout is already imported; start a fresh process."
        )
    sys.path.insert(0, str(resolved))
    try:
        yield {
            "benchmark": importlib.import_module(
                "scripts.developer_tools.evaluate_translation_quality"
            ),
            "base_handler": importlib.import_module("scripts.core.base_handler").BaseApiHandler,
            "validator": importlib.import_module(
                "scripts.utils.post_process_validator"
            ).PostProcessValidator,
            "glossary_manager": importlib.import_module(
                "scripts.core.glossary_manager"
            ).glossary_manager,
            "get_api_key": importlib.import_module("scripts.app_settings").get_api_key,
        }
    except (ImportError, OSError) as exc:
        raise GoogleAIStudioAdapterError(f"Unable to import Remis benchmark: {exc}") from exc
    finally:
        if sys.path and sys.path[0] == str(resolved):
            sys.path.pop(0)


def run_remis_google_ai_studio(
    remis_root: Path,
    fixture_path: Path,
    raw_output_path: Path,
    run_output_path: Path,
    *,
    model: str,
    label: str | None = None,
    reasoning_effort: str = "high",
    max_output_tokens: int = 16_000,
    track: str = "all",
    case_ids: tuple[str, ...] = (),
    env_file: Path = Path(".env"),
    recipe_id: str | None = None,
    api_key: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    """Run the frozen Remis workflow through Google and emit both artifact layers."""
    if track not in {"all", "translation", "repair"}:
        raise GoogleAIStudioAdapterError(f"Unsupported Remis benchmark track: {track!r}.")
    profile = GoogleAIStudioProfile(model, reasoning_effort, max_output_tokens)
    with _remis_imports(remis_root) as modules:
        benchmark = modules["benchmark"]
        resolved_key = (
            api_key
            or modules["get_api_key"]("gemini", "GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or _read_env_key(env_file, "GEMINI_API_KEY")
        )
        contestant = GoogleAIStudioContestant(
            resolved_key or "",
            profile,
            opener=opener,
        )

        base_handler = modules["base_handler"]

        class RemisGoogleAIStudioHandler(base_handler):
            def initialize_client(self) -> GoogleAIStudioContestant:
                return contestant

            def _call_api(self, client: GoogleAIStudioContestant, prompt: str) -> str:
                response = client.generate(prompt)
                self.last_usage = response.usage
                self.last_response_model = response.response_model
                return response.text

        handler = RemisGoogleAIStudioHandler("gemini", model_id=model)
        handler.request_profile = profile.request_profile()
        fixture, fixture_hash = benchmark.read_fixture(fixture_path)
        benchmark.validate_fixture(fixture)
        cases = benchmark.selected_cases(fixture, track, set(case_ids))
        validator = modules["validator"]()
        glossary_manager = modules["glossary_manager"]
        previous_glossary = glossary_manager.in_memory_glossary
        glossary_manager.in_memory_glossary = {"entries": []}
        try:
            results = [
                (
                    benchmark.run_translation_case(case, handler, validator)
                    if case["track"] == "translation"
                    else benchmark.run_repair_case(case, handler, validator)
                )
                for case in cases
            ]
        finally:
            glossary_manager.in_memory_glossary = previous_glossary

        now = datetime.now(UTC)
        report = {
            "schema_version": 1,
            "benchmark": fixture["name"],
            "fixture_sha256": fixture_hash,
            "created_at_utc": now.isoformat(),
            "provider": "google-ai-studio",
            "model_id": model,
            "model_label": label or model,
            "track": track,
            "request_profile": profile.request_profile(),
            "policy": {
                "first_pass_format_failure": "measurement_not_execution_failure",
                "execution_failure": "provider_exception_only",
                "structured_output_failure": "parse_or_item_count_failure",
                "ranking_priority": "hard_constraints_then_blinded_language_quality",
            },
            "manual_review_rubric": fixture["manual_review_rubric"],
            "summary": benchmark.summarize_results(results),
            "results": results,
        }
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        converted = convert_remis_result(report, recipe_id=recipe_id)
        run_output_path.parent.mkdir(parents=True, exist_ok=True)
        run_output_path.write_text(
            json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "completed": True,
            "raw_output": str(raw_output_path),
            "run_output": str(run_output_path),
            "run_id": converted["run_id"],
            **report["summary"],
        }


def run_remis_google_ai_studio_isolated(
    runtime_python: Path,
    remis_root: Path,
    fixture_path: Path,
    raw_output_path: Path,
    run_output_path: Path,
    *,
    model: str,
    label: str | None = None,
    reasoning_effort: str = "high",
    max_output_tokens: int = 16_000,
    track: str = "all",
    case_ids: tuple[str, ...] = (),
    env_file: Path = Path(".env"),
    recipe_id: str | None = None,
    timeout_seconds: int = 3_600,
) -> dict[str, Any]:
    """Execute the bridge in a caller-selected Remis-capable Python runtime."""
    runtime = runtime_python.resolve()
    if not runtime.is_file():
        raise GoogleAIStudioAdapterError(f"Runtime Python does not exist: {runtime}")
    if timeout_seconds <= 0:
        raise GoogleAIStudioAdapterError("Worker timeout_seconds must be positive.")
    request = {
        "remis_root": str(remis_root.resolve()),
        "fixture_path": str(fixture_path.resolve()),
        "raw_output_path": str(raw_output_path.resolve()),
        "run_output_path": str(run_output_path.resolve()),
        "model": model,
        "label": label,
        "reasoning_effort": reasoning_effort,
        "max_output_tokens": max_output_tokens,
        "track": track,
        "case_ids": list(case_ids),
        "env_file": str(env_file.resolve()),
        "recipe_id": recipe_id,
    }
    package_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    prior_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        path for path in (str(package_root), str(remis_root.resolve()), prior_pythonpath) if path
    )
    try:
        completed = subprocess.run(
            [str(runtime), "-m", "remis_aventine.google_ai_studio_worker"],
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=remis_root.resolve(),
            env=environment,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GoogleAIStudioAdapterError(f"Google contestant worker failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown worker failure"
        raise GoogleAIStudioAdapterError(f"Google contestant worker failed: {detail}")
    status_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not status_lines:
        raise GoogleAIStudioAdapterError("Google contestant worker returned no status JSON.")
    try:
        result = json.loads(status_lines[-1])
    except json.JSONDecodeError as exc:
        raise GoogleAIStudioAdapterError(
            "Google contestant worker returned malformed status JSON."
        ) from exc
    if not isinstance(result, dict):
        raise GoogleAIStudioAdapterError("Google contestant worker status must be an object.")
    return result


__all__ = [
    "ADAPTER_REVISION",
    "GoogleAIStudioAdapterError",
    "GoogleAIStudioContestant",
    "GoogleAIStudioProfile",
    "GoogleAIStudioResponse",
    "run_remis_google_ai_studio",
    "run_remis_google_ai_studio_isolated",
]

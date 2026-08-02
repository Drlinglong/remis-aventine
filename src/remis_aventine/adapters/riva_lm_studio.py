"""Native Riva Translate v2 execution through an LM Studio-compatible endpoint."""

from __future__ import annotations

import hashlib
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADAPTER_REVISION = "riva-translate-v2-lm-studio-v1"
UTC = timezone.utc  # noqa: UP017 - worker must run under Remis's Python 3.10.
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "auto"
SUPPORTED_REPAIR_STRATEGY = "source_retranslation"
REMIS_IDENTITY_PATHS = (
    "scripts/developer_tools/evaluate_translation_quality.py",
    "scripts/core/base_handler.py",
    "scripts/core/glossary_manager.py",
    "scripts/utils/post_process_validator.py",
)

_LANGUAGE_TAGS = {
    "ar": "ar",
    "bg": "bg",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "el": "el",
    "en": "en",
    "es": "es",
    "es-es": "es-es",
    "es-us": "es-us",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "hi": "hi",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "lt": "lt",
    "lv": "lv",
    "nl": "nl",
    "no": "no",
    "pl": "pl",
    "pt": "pt",
    "pt-br": "pt-br",
    "pt-pt": "pt-pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "sl",
    "sv": "sv",
    "th": "th",
    "tr": "tr",
    "uk": "uk",
    "vi": "vi",
    "zh": "zh",
    "zh-cn": "zh-cn",
    "zh-hans": "zh-cn",
    "zh-tw": "zh-tw",
    "zh-hant": "zh-tw",
}


class RivaLMStudioAdapterError(RuntimeError):
    """Raised when the bounded local Riva adapter cannot execute safely."""


def _remis_checkout_provenance(remis_root: Path) -> dict[str, str]:
    resolved = remis_root.resolve()
    try:
        completed = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RivaLMStudioAdapterError(
            f"Unable to identify Remis checkout revision: {exc}"
        ) from exc
    revision = completed.stdout.strip()
    if completed.returncode != 0 or len(revision) != 40:
        detail = completed.stderr.strip() or "git rev-parse did not return a commit"
        raise RivaLMStudioAdapterError(f"Unable to identify Remis checkout revision: {detail}")

    digest = hashlib.sha256()
    for relative in REMIS_IDENTITY_PATHS:
        path = resolved / relative
        if not path.is_file():
            raise RivaLMStudioAdapterError(f"Remis identity source is missing: {path}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"revision": revision, "source_sha256": digest.hexdigest()}


@contextmanager
def _remis_imports(remis_root: Path) -> Iterator[dict[str, Any]]:
    resolved = remis_root.resolve()
    benchmark_path = resolved / "scripts/developer_tools/evaluate_translation_quality.py"
    if not benchmark_path.is_file():
        raise RivaLMStudioAdapterError(f"Remis benchmark entrypoint is missing: {benchmark_path}")
    loaded_scripts = sys.modules.get("scripts")
    loaded_path = getattr(loaded_scripts, "__path__", ()) if loaded_scripts else ()
    matching_checkout_loaded = any(
        Path(path).resolve() == (resolved / "scripts") for path in loaded_path
    )
    if loaded_path and not matching_checkout_loaded:
        raise RivaLMStudioAdapterError(
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
        }
    except (ImportError, OSError) as exc:
        raise RivaLMStudioAdapterError(f"Unable to import Remis benchmark: {exc}") from exc
    finally:
        if sys.path and sys.path[0] == str(resolved):
            sys.path.pop(0)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _convert_remis_result(report: dict[str, Any], recipe_id: str | None) -> dict[str, Any]:
    """Load Aventine schema conversion only in the parent-capable runtime."""
    from remis_aventine.adapters.remis import convert_remis_result

    return convert_remis_result(report, recipe_id=recipe_id)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalize_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RivaLMStudioAdapterError("LM Studio base_url must be an absolute HTTP(S) URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RivaLMStudioAdapterError(
            "LM Studio base_url must not contain credentials, query parameters, or fragments."
        )
    path = parsed.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise RivaLMStudioAdapterError("LM Studio base_url path must be empty or /v1.")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path or "/v1", "", ""))


def riva_language_pair(source_language: str, target_language: str) -> str:
    """Map a Remis language direction to an official Riva v2 system tag."""
    source = _LANGUAGE_TAGS.get(source_language.strip().lower())
    target = _LANGUAGE_TAGS.get(target_language.strip().lower())
    if not source or not target or source == target:
        raise RivaLMStudioAdapterError(
            f"Unsupported Riva language direction: {source_language!r} -> {target_language!r}."
        )
    if source != "en" and target != "en":
        raise RivaLMStudioAdapterError(
            "Riva Translate v2 supports benchmark directions between English "
            "and one other language."
        )
    return f"{source}-{target}"


def _public_model_metadata(model: dict[str, Any], instance: dict[str, Any]) -> dict[str, Any]:
    """Keep reproducibility fields while dropping local paths and runtime-only secrets."""
    allowed = (
        "id",
        "key",
        "display_name",
        "architecture",
        "quantization",
        "format",
        "size_bytes",
        "max_context_length",
        "context_length",
    )
    public = {
        key: value
        for source in (model, instance)
        for key in allowed
        if (value := source.get(key)) is not None
    }
    return public


@dataclass(frozen=True, slots=True)
class LoadedLMStudioModel:
    """Credential-free identity of one loaded LM Studio model instance."""

    model_id: str
    metadata: dict[str, Any]


def discover_loaded_lm_studio_model(
    base_url: str,
    *,
    requested_model: str = DEFAULT_MODEL,
    timeout_seconds: int = 10,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> LoadedLMStudioModel:
    """Resolve ``auto`` against LM Studio's loaded-instance endpoint."""
    normalized = _normalize_base_url(base_url)
    parsed = urllib.parse.urlsplit(normalized)
    status_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/api/v1/models", "", ""))
    request = urllib.request.Request(status_url, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RivaLMStudioAdapterError(
            f"LM Studio model discovery failed with HTTP {exc.code}."
        ) from exc
    except urllib.error.URLError as exc:
        raise RivaLMStudioAdapterError(
            f"LM Studio model discovery failed: {exc.reason}. Is the local server enabled?"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RivaLMStudioAdapterError("LM Studio returned malformed model metadata.") from exc

    models = payload.get("models")
    if not isinstance(models, list):
        raise RivaLMStudioAdapterError("LM Studio model discovery response has no models array.")
    loaded: list[LoadedLMStudioModel] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        instances = model.get("loaded_instances")
        if not isinstance(instances, list):
            continue
        for instance in instances:
            if not isinstance(instance, dict):
                continue
            model_id = instance.get("id") or model.get("key")
            if isinstance(model_id, str) and model_id:
                loaded.append(
                    LoadedLMStudioModel(model_id, _public_model_metadata(model, instance))
                )

    requested = requested_model.strip()
    if requested == DEFAULT_MODEL:
        if len(loaded) != 1:
            ids = [item.model_id for item in loaded]
            raise RivaLMStudioAdapterError(
                "--model auto requires exactly one loaded LM Studio instance; "
                f"found {len(loaded)}: {ids}."
            )
        return loaded[0]
    for item in loaded:
        if item.model_id == requested or item.metadata.get("key") == requested:
            return item
    ids = [item.model_id for item in loaded]
    raise RivaLMStudioAdapterError(
        f"Requested model {requested!r} is not loaded in LM Studio; loaded instances: {ids}."
    )


@dataclass(frozen=True, slots=True)
class RivaLMStudioProfile:
    """Explicit local recipe settings for NVIDIA Riva Translate v2."""

    model: str
    base_url: str = DEFAULT_BASE_URL
    max_output_tokens: int = 2_048
    temperature: float = 0.0
    timeout_seconds: int = 300
    quantization: str = "unknown"

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise RivaLMStudioAdapterError("Riva model must be a non-empty string.")
        object.__setattr__(self, "base_url", _normalize_base_url(self.base_url))
        if isinstance(self.max_output_tokens, bool) or self.max_output_tokens <= 0:
            raise RivaLMStudioAdapterError("Riva max_output_tokens must be positive.")
        if not 0.0 <= self.temperature <= 2.0:
            raise RivaLMStudioAdapterError("Riva temperature must be between 0 and 2.")
        if self.timeout_seconds <= 0:
            raise RivaLMStudioAdapterError("Riva timeout_seconds must be positive.")
        if not self.quantization.strip():
            raise RivaLMStudioAdapterError("Riva quantization label must not be empty.")

    def request_profile(
        self,
        *,
        loaded_model: LoadedLMStudioModel,
        language_pairs: list[str],
    ) -> dict[str, Any]:
        """Return public recipe evidence without exposing the local endpoint."""
        metadata = loaded_model.metadata
        return {
            "revision": ADAPTER_REVISION,
            "runtime": "lm_studio",
            "api_mode": "openai_chat_completions",
            "model": loaded_model.model_id,
            "model_family": "nvidia/Riva-Translate-4B-Instruct-v2",
            "loaded_model_metadata": metadata,
            "loaded_model_metadata_sha256": _sha256(metadata),
            "quantization": self.quantization,
            "max_output_tokens_per_string": self.max_output_tokens,
            "temperature": self.temperature,
            "language_pairs": sorted(set(language_pairs)),
            "native_prompt": {
                "system": "language_pair_tag",
                "user": "source_text_only",
                "batch_strategy": "one_request_per_string",
                "glossary_strategy": "few_shot_priority",
            },
            "repair_strategy": SUPPORTED_REPAIR_STRATEGY,
            "output_contract": "deterministic_adapter_json_wrapper",
            "reasoning": {"enabled": False, "effort": "none"},
            "reasoning_label": "none",
            "client_max_retries": 0,
        }


@dataclass(frozen=True, slots=True)
class RivaTranslationBatch:
    """One deterministic adapter-wrapped batch result."""

    translations: list[str]
    usage: dict[str, int]
    response_models: list[str]
    prompt_sha256: str


def riva_glossary_pairs(
    entries: list[dict[str, Any]], source_language: str, target_language: str
) -> list[tuple[str, str]]:
    """Convert Remis glossary entries into Riva-compatible few-shot pairs."""
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        translations = entry.get("translations")
        if not isinstance(translations, dict):
            continue
        source = translations.get(source_language)
        target = translations.get(target_language)
        if isinstance(source, str) and source and isinstance(target, str) and target:
            pairs.append((source, target))
    return pairs


def build_riva_messages(
    text: str,
    source_language: str,
    target_language: str,
    glossary_entries: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Build one model-native Riva v2 conversation without transport concerns."""
    if not text:
        raise RivaLMStudioAdapterError("Riva source text must not be empty.")
    messages = [
        {
            "role": "system",
            "content": riva_language_pair(source_language, target_language),
        }
    ]
    for source, target in riva_glossary_pairs(
        glossary_entries or [], source_language, target_language
    ):
        messages.extend(
            [
                {"role": "user", "content": source},
                {"role": "assistant", "content": target},
            ]
        )
    messages.append({"role": "user", "content": text})
    return messages


class RivaLMStudioContestant:
    """Minimal OpenAI-compatible transport using Riva's native chat template."""

    def __init__(
        self,
        profile: RivaLMStudioProfile,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.profile = profile
        self._opener = opener

    def _translate(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, int], str]:
        request_body = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": self.profile.temperature,
            "max_tokens": self.profile.max_output_tokens,
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.profile.base_url}/chat/completions",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.profile.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RivaLMStudioAdapterError(
                f"LM Studio Riva request failed with HTTP {exc.code}."
            ) from exc
        except urllib.error.URLError as exc:
            raise RivaLMStudioAdapterError(
                f"LM Studio Riva request failed: {exc.reason}. Is the local server enabled?"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RivaLMStudioAdapterError("LM Studio returned malformed response JSON.") from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RivaLMStudioAdapterError("LM Studio returned no Riva translation choice.")
        choice = choices[0]
        if choice.get("finish_reason") == "length":
            raise RivaLMStudioAdapterError(
                "Riva translation hit max_output_tokens before completion."
            )
        content = choice.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RivaLMStudioAdapterError("LM Studio returned an empty Riva translation.")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        prompt_details = usage.get("prompt_tokens_details")
        cached_tokens = (
            int(prompt_details.get("cached_tokens") or 0) if isinstance(prompt_details, dict) else 0
        )
        normalized_usage = {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "reasoning_tokens": 0,
            "cached_input_tokens": cached_tokens,
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        return content.strip(), normalized_usage, str(payload.get("model") or self.profile.model)

    def translate_many(
        self,
        texts: list[str],
        *,
        source_language: str,
        target_language: str,
        glossary_entries: list[dict[str, Any]] | None = None,
    ) -> RivaTranslationBatch:
        """Translate strings independently and aggregate transport telemetry."""
        if not texts:
            raise RivaLMStudioAdapterError("Riva translation batch must not be empty.")
        glossary = glossary_entries or []
        message_sets = [
            build_riva_messages(text, source_language, target_language, glossary) for text in texts
        ]
        translations: list[str] = []
        response_models: list[str] = []
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cached_input_tokens": 0,
            "total_tokens": 0,
        }
        for messages in message_sets:
            translation, item_usage, response_model = self._translate(messages)
            translations.append(translation)
            response_models.append(response_model)
            for key in usage:
                usage[key] += item_usage[key]
        return RivaTranslationBatch(
            translations=translations,
            usage=usage,
            response_models=response_models,
            prompt_sha256=_sha256(message_sets),
        )


def run_remis_riva_lm_studio(
    remis_root: Path,
    fixture_path: Path,
    raw_output_path: Path,
    run_output_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    label: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    max_output_tokens: int = 2_048,
    temperature: float = 0.0,
    request_timeout_seconds: int = 300,
    quantization: str = "unknown",
    track: str = "all",
    case_ids: tuple[str, ...] = (),
    recipe_id: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    convert_artifact: bool = True,
) -> dict[str, Any]:
    """Run frozen Remis cases through native Riva prompts and emit both artifact layers."""
    if track not in {"all", "translation", "repair"}:
        raise RivaLMStudioAdapterError(f"Unsupported Remis benchmark track: {track!r}.")
    loaded_model = discover_loaded_lm_studio_model(
        base_url,
        requested_model=model,
        opener=opener,
    )
    profile = RivaLMStudioProfile(
        loaded_model.model_id,
        base_url,
        max_output_tokens,
        temperature,
        request_timeout_seconds,
        quantization,
    )
    contestant = RivaLMStudioContestant(profile, opener=opener)
    try:
        checkout = _remis_checkout_provenance(remis_root)
        imports = _remis_imports(remis_root)
        with imports as modules:
            benchmark = modules["benchmark"]
            base_handler = modules["base_handler"]

            class RemisRivaHandler(base_handler):
                def initialize_client(self) -> RivaLMStudioContestant:
                    return contestant

                def _build_prompt(self, task: Any) -> str:
                    case = self.current_case
                    messages = [
                        build_riva_messages(
                            text,
                            case["source_lang"],
                            case["target_lang"],
                            case.get("glossary_entries", []),
                        )
                        for text in task.texts
                    ]
                    return _canonical_json(messages)

                def _call_api(self, client: RivaLMStudioContestant, _prompt: str) -> str:
                    case = self.current_case
                    texts = [entry["text"] for entry in case["source_entries"]]
                    batch = client.translate_many(
                        texts,
                        source_language=case["source_lang"],
                        target_language=case["target_lang"],
                        glossary_entries=case.get("glossary_entries", []),
                    )
                    self.last_usage = batch.usage
                    self.last_response_models = batch.response_models
                    self.last_prompt_sha256 = batch.prompt_sha256
                    self.last_request_count = len(texts)
                    return json.dumps(
                        {"translations": batch.translations},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )

            handler = RemisRivaHandler("lm_studio", model_id=loaded_model.model_id)
            fixture, fixture_hash = benchmark.read_fixture(fixture_path)
            benchmark.validate_fixture(fixture)
            cases = benchmark.selected_cases(fixture, track, set(case_ids))
            validator = modules["validator"]()
            glossary_manager = modules["glossary_manager"]
            previous_glossary = glossary_manager.in_memory_glossary
            glossary_manager.in_memory_glossary = {"entries": []}
            results: list[dict[str, Any]] = []
            try:
                for case in cases:
                    handler.current_case = case
                    handler.last_usage = None
                    handler.last_response_models = None
                    handler.last_prompt_sha256 = None
                    handler.last_request_count = None
                    result = (
                        benchmark.run_translation_case(case, handler, validator)
                        if case["track"] == "translation"
                        else benchmark.run_repair_case(case, handler, validator)
                    )
                    if handler.last_prompt_sha256:
                        result["prompt_sha256"] = handler.last_prompt_sha256
                        result["usage"] = handler.last_usage
                        models = sorted(set(handler.last_response_models or []))
                        result["response_model"] = models[0] if len(models) == 1 else models
                        result["request_count"] = handler.last_request_count
                    results.append(result)
            finally:
                glossary_manager.in_memory_glossary = previous_glossary

            language_pairs = [
                riva_language_pair(case["source_lang"], case["target_lang"]) for case in cases
            ]
            request_profile = profile.request_profile(
                loaded_model=loaded_model,
                language_pairs=language_pairs,
            )
            now = datetime.now(UTC)
            report = {
                "schema_version": 1,
                "benchmark": fixture["name"],
                "fixture_sha256": fixture_hash,
                "created_at_utc": now.isoformat(),
                "provider": "lm-studio-riva-native",
                "model_id": loaded_model.model_id,
                "model_label": label or "Riva Translate 4B Instruct v2",
                "track": track,
                "remis_checkout": checkout,
                "request_profile": request_profile,
                "policy": {
                    "translation_prompt": "riva_native_language_pair",
                    "glossary": "few_shot_priority",
                    "structured_output": "deterministic_adapter_wrapper",
                    "repair": SUPPORTED_REPAIR_STRATEGY,
                    "execution_failure": "transport_or_invalid_response_only",
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
            status = {
                "completed": True,
                "raw_output": str(raw_output_path),
                "model_id": loaded_model.model_id,
                **report["summary"],
            }
            if convert_artifact:
                converted = _convert_remis_result(report, recipe_id)
                run_output_path.parent.mkdir(parents=True, exist_ok=True)
                run_output_path.write_text(
                    json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                status.update(
                    run_output=str(run_output_path),
                    run_id=converted["run_id"],
                )
            return status
    except RivaLMStudioAdapterError:
        raise


def run_remis_riva_lm_studio_isolated(
    runtime_python: Path,
    remis_root: Path,
    fixture_path: Path,
    raw_output_path: Path,
    run_output_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    label: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    max_output_tokens: int = 2_048,
    temperature: float = 0.0,
    request_timeout_seconds: int = 300,
    quantization: str = "unknown",
    track: str = "all",
    case_ids: tuple[str, ...] = (),
    recipe_id: str | None = None,
    timeout_seconds: int = 3_600,
) -> dict[str, Any]:
    """Execute the Riva bridge in a caller-selected Remis-capable Python runtime."""
    runtime = runtime_python.resolve()
    if not runtime.is_file():
        raise RivaLMStudioAdapterError(f"Runtime Python does not exist: {runtime}")
    if timeout_seconds <= 0:
        raise RivaLMStudioAdapterError("Worker timeout_seconds must be positive.")
    request = {
        "remis_root": str(remis_root.resolve()),
        "fixture_path": str(fixture_path.resolve()),
        "raw_output_path": str(raw_output_path.resolve()),
        "run_output_path": str(run_output_path.resolve()),
        "model": model,
        "label": label,
        "base_url": base_url,
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
        "request_timeout_seconds": request_timeout_seconds,
        "quantization": quantization,
        "track": track,
        "case_ids": list(case_ids),
        "recipe_id": recipe_id,
    }
    package_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    prior_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        path for path in (str(package_root), str(remis_root.resolve()), prior_pythonpath) if path
    )
    # The isolated Windows account may not own the user's checkout. Trust only this
    # explicitly selected Remis root for provenance lookup without mutating Git config.
    environment["GIT_CONFIG_COUNT"] = "1"
    environment["GIT_CONFIG_KEY_0"] = "safe.directory"
    environment["GIT_CONFIG_VALUE_0"] = str(remis_root.resolve())
    try:
        completed = subprocess.run(
            [str(runtime), "-m", "remis_aventine.riva_lm_studio_worker"],
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=remis_root.resolve(),
            env=environment,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RivaLMStudioAdapterError(f"Riva contestant worker failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown worker failure"
        raise RivaLMStudioAdapterError(f"Riva contestant worker failed: {detail}")
    status_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not status_lines:
        raise RivaLMStudioAdapterError("Riva contestant worker returned no status JSON.")
    try:
        result = json.loads(status_lines[-1])
    except json.JSONDecodeError as exc:
        raise RivaLMStudioAdapterError(
            "Riva contestant worker returned malformed status JSON."
        ) from exc
    if not isinstance(result, dict):
        raise RivaLMStudioAdapterError("Riva contestant worker status must be an object.")
    try:
        raw_report = json.loads(raw_output_path.read_text(encoding="utf-8"))
        converted = _convert_remis_result(raw_report, recipe_id)
        run_output_path.parent.mkdir(parents=True, exist_ok=True)
        run_output_path.write_text(
            json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, TypeError) as exc:
        raise RivaLMStudioAdapterError(f"Unable to convert isolated Riva artifact: {exc}") from exc
    result.update(run_output=str(run_output_path), run_id=converted["run_id"])
    return result


__all__ = [
    "ADAPTER_REVISION",
    "DEFAULT_BASE_URL",
    "LoadedLMStudioModel",
    "RivaLMStudioAdapterError",
    "RivaLMStudioContestant",
    "RivaLMStudioProfile",
    "RivaTranslationBatch",
    "build_riva_messages",
    "discover_loaded_lm_studio_model",
    "riva_glossary_pairs",
    "riva_language_pair",
    "run_remis_riva_lm_studio",
    "run_remis_riva_lm_studio_isolated",
]

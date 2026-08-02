"""Schema-bound DeepSeek judge runner with bounded retries and usage accounting."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from remis_aventine.calibration import load_calibration_fixture
from remis_aventine.validation import DocumentValidationError, validate_payload

MODEL_ID = "deepseek-v4-pro"
PROMPT_REVISION = "translation-judge-v2"
PROFILE = "deepseek-v4-pro-thinking-high-8k"
MAX_TOKENS = 8000
PRICING_RMB_PER_MILLION = {"cache_hit_input": 0.025, "cache_miss_input": 3.0, "output": 6.0}
FLASH_MODEL_ID = "deepseek-v4-flash"
FLASH_PROFILE = "deepseek-v4-flash-thinking-low-8k"
FLASH_MAX_TOKENS = 8000
FLASH_PRICING_RMB_PER_MILLION = {
    "cache_hit_input": 0.02,
    "cache_miss_input": 1.0,
    "output": 2.0,
}
XAI_MODEL_ID = "grok-4.5"
XAI_PROFILE = "grok-4.5-reasoning-low-structured-v2"
XAI_MAX_TOKENS = 4000
XAI_PRICING_USD_PER_MILLION = {"cache_hit_input": 0.5, "cache_miss_input": 2.0, "output": 6.0}
GOOGLE_MODEL_ID = "gemma-4-31b-it"
GOOGLE_PROFILE = "gemma-4-31b-it-free-structured-v1"
GOOGLE_MAX_TOKENS = 4000
OPENROUTER_MODEL_ID = "deepseek/deepseek-v4-pro"
OPENROUTER_PROFILE = "openrouter-deepseek-v4-pro-reasoning-high-structured-8k-v1"
OPENROUTER_MAX_TOKENS = 8000
OPENROUTER_PRICING_USD_PER_MILLION = {
    "cache_hit_input": 0.003625,
    "cache_miss_input": 0.435,
    "output": 0.87,
}
OPENROUTER_GEMINI_MODEL_ID = "google/gemini-3.7-flash"
OPENROUTER_GEMINI_CANONICAL_MODEL_ID = "google/gemini-3.7-flash-20260813"
OPENROUTER_GEMINI_PROFILE = "openrouter-gemini-3.7-flash-reasoning-medium-structured-seeded-v2"
OPENROUTER_GEMINI_HIGH_PROFILE = "openrouter-gemini-3.7-flash-reasoning-high-structured-seeded-v2"
OPENROUTER_GEMINI_MAX_TOKENS = 8000
OPENROUTER_GEMINI_SEED = 20260818
OPENROUTER_GEMINI_PRICING_USD_PER_MILLION = {
    "cache_hit_input": 0.0375,
    "cache_miss_input": 0.375,
    "output_including_reasoning": 1.875,
}
OPENROUTER_LUNA_MODEL_ID = "openai/gpt-5.6-luna"
OPENROUTER_LUNA_PROFILE = "openrouter-gpt-5.6-luna-reasoning-high-structured-v2"
OPENROUTER_LUNA_MAX_TOKENS = 8000
OPENROUTER_DS_FLASH_MODEL_ID = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_DS_FLASH_PROFILE = "openrouter-deepseek-v4-flash-0731-reasoning-high-structured-v2"
OPENROUTER_DS_FLASH_MAX_TOKENS = 8000


FAILURE_TYPES = (
    "timeout",
    "rate_limit",
    "provider",
    "truncation",
    "json",
    "schema",
    "budget",
    "unknown",
)


class JudgeRunError(RuntimeError):
    """Raised when a bounded judge run cannot proceed safely."""

    def __init__(
        self,
        message: str,
        *,
        failure_type: str = "unknown",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.failure_type = failure_type if failure_type in FAILURE_TYPES else "unknown"
        self.retryable = retryable


def _is_timeout(value: Any) -> bool:
    text = str(value).lower()
    return (
        isinstance(value, (TimeoutError, socket.timeout))
        or "timed out" in text
        or "timeout" in text
    )


def _looks_truncated(text: str, error: json.JSONDecodeError) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if "unterminated" in error.msg.lower():
        return True
    return error.pos >= max(len(stripped) - 2, 0) and stripped[-1] in '{[,:"'


def _json_failure(context: str, text: str, error: json.JSONDecodeError) -> JudgeRunError:
    failure_type = "truncation" if _looks_truncated(text, error) else "json"
    return JudgeRunError(
        f"{context} returned invalid JSON: {error.msg}",
        failure_type=failure_type,
    )


def _failure_type(exc: BaseException) -> str:
    if isinstance(exc, JudgeRunError):
        return exc.failure_type
    if isinstance(exc, (TimeoutError, socket.timeout)) or _is_timeout(exc):
        return "timeout"
    if isinstance(exc, json.JSONDecodeError):
        return "json"
    return "unknown"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, JudgeRunError):
        return exc.retryable and exc.failure_type != "budget"
    return _failure_type(exc) != "budget"


SYSTEM_PROMPT = """You are a multilingual translation-quality evaluator. Judge meaning,
terminology, fluency, style, locale, context, and restraint. Do not invent requirements. A
reference is evidence, not automatically perfect. For pairwise cases select the meaningfully
better translation; use tie only when differences are immaterial. Treat omissions, additions,
negation, numbers, named entities, role swaps, broken protected tokens, and damaging over-editing
as serious. Return only one JSON object with an evaluation field. Do not include markdown.

Severity discipline: major means a substantive change to meaning, user action, terminology, or
communicative function. Critical means the output is unusable or could cause severe task harm.
Do not penalize natural idiomatic translation, harmless explicitation, or small intensity changes.
Those are minor only when they create a real quality defect; otherwise they are acceptable.

JSON example:
{
  "evaluation": {
    "mode": "single", "verdict": "fail", "confidence": "high",
    "errors": [{
      "candidate": "candidate", "category": "accuracy", "severity": "major",
      "explanation": "The negation is missing.", "source_excerpt": "not open",
      "candidate_excerpt": "open"
    }],
    "dimensions": {
      "semantic_accuracy": 20, "terminology": 90, "fluency": 90, "style": 90,
      "context_consistency": 70, "restraint": 100
    },
    "rationale": "The central proposition is reversed.", "limitations": []
  }
}

Valid single verdicts: pass, fail, uncertain. Valid pairwise verdicts: candidate_a, candidate_b,
tie, neither, uncertain. Error candidates must be candidate for single mode, or candidate_a /
candidate_b for pairwise mode. Categories: accuracy, terminology, fluency, style, locale,
context, over_editing, other. Severities: minor, major, critical. A fail needs at least one error.
"""


def _case_mode(case: dict[str, Any]) -> str:
    mode = case.get("evaluation_mode")
    if mode in {"single", "pairwise"}:
        return str(mode)
    return str(case["gold"]["mode"])


def _prompt(case: dict[str, Any]) -> str:
    mode = _case_mode(case)
    if case.get("evaluation_scope") == "structural":
        return (
            "Evaluate ONLY whether the protected-variable count change is a grammatically "
            "legitimate target-language rewrite. Pass only when every runtime value remains "
            "semantically represented and no new runtime value was invented. Fail when a "
            "variable/value was lost, duplicated, reassigned, or added. Do not fail for unrelated "
            "style or translation preferences. Use uncertain when the supplied context cannot "
            "resolve this narrow question. Return strict JSON matching the single-case example.\n"
            "INPUT:\n"
            + json.dumps(case["input"], ensure_ascii=False, sort_keys=True)
        )
    return (
        f"Evaluate this {mode} translation case. The language pair and all available evidence are "
        "inside INPUT. Return strict JSON matching the example.\nINPUT:\n"
        + json.dumps(case["input"], ensure_ascii=False, sort_keys=True)
    )


def _usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or 0)
    output = int(usage.get("completion_tokens") or 0)
    details = usage.get("prompt_tokens_details") or {}
    hit = int(usage.get("prompt_cache_hit_tokens") or details.get("cached_tokens") or 0)
    miss = int(usage.get("prompt_cache_miss_tokens") or max(prompt - hit, 0))
    return {"cache_hit_input_tokens": hit, "cache_miss_input_tokens": miss, "output_tokens": output}


def _xai_usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    input_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    output_details = (
        usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    )
    hit = int(input_details.get("cached_tokens") or 0)
    return {
        "cache_hit_input_tokens": hit,
        "cache_miss_input_tokens": max(prompt - hit, 0),
        "output_tokens": output,
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "cost_in_usd_ticks": int(usage.get("cost_in_usd_ticks") or 0),
    }


def _openrouter_usage(response: dict[str, Any]) -> dict[str, int]:
    """Normalize OpenRouter usage without charging reasoning twice.

    OpenRouter reports reasoning as a subset of completion tokens and bills it at the output
    rate. ``cost_in_usd_ticks`` preserves the response's exact account charge as an integer so
    concurrent aggregation remains lossless and deterministic.
    """
    usage = response.get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    input_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    output_details = (
        usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    )
    hit = int(input_details.get("cached_tokens") or 0)
    exact_cost = float(usage.get("cost") or 0.0)
    return {
        "cache_hit_input_tokens": hit,
        "cache_miss_input_tokens": max(prompt - hit, 0),
        "output_tokens": output,
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "cost_in_usd_ticks": round(exact_cost * 10_000_000_000),
    }


def _cost(usage: dict[str, int]) -> float:
    value = (
        usage["cache_hit_input_tokens"] * PRICING_RMB_PER_MILLION["cache_hit_input"]
        + usage["cache_miss_input_tokens"] * PRICING_RMB_PER_MILLION["cache_miss_input"]
        + usage["output_tokens"] * PRICING_RMB_PER_MILLION["output"]
    ) / 1_000_000
    return round(value, 6)


def _without_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_without_nulls(item) for item in value]
    return value


def _xai_response_schema(mode: str) -> dict[str, Any]:
    pairwise = mode == "pairwise"
    verdicts = (
        ["candidate_a", "candidate_b", "tie", "neither", "uncertain"]
        if pairwise
        else ["pass", "fail", "uncertain"]
    )
    candidates = ["candidate_a", "candidate_b"] if pairwise else ["candidate"]
    evaluation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "verdict", "confidence", "errors", "rationale", "limitations"],
        "properties": {
            "mode": {"const": mode},
            "verdict": {"type": "string", "enum": verdicts},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "candidate",
                        "category",
                        "severity",
                        "explanation",
                        "source_excerpt",
                        "candidate_excerpt",
                    ],
                    "properties": {
                        "candidate": {"type": "string", "enum": candidates},
                        "category": {
                            "type": "string",
                            "enum": [
                                "accuracy",
                                "terminology",
                                "fluency",
                                "style",
                                "locale",
                                "context",
                                "over_editing",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["minor", "major", "critical"]},
                        "explanation": {"type": "string", "minLength": 1},
                        "source_excerpt": {"type": ["string", "null"]},
                        "candidate_excerpt": {"type": ["string", "null"]},
                    },
                },
            },
            "rationale": {"type": "string", "minLength": 1},
            "limitations": {"type": "array", "items": {"type": "string", "minLength": 1}},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evaluation"],
        "properties": {"evaluation": evaluation},
    }


def _google_response_schema(mode: str) -> dict[str, Any]:
    schema = deepcopy(_xai_response_schema(mode))

    def simplify(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("minLength", None)
            if "const" in value:
                value["type"] = "string"
                value["enum"] = [value.pop("const")]
            for child in value.values():
                simplify(child)
        elif isinstance(value, list):
            for child in value:
                simplify(child)

    simplify(schema)
    return schema


class DeepSeekJudge:
    """OpenAI-compatible judge with bounded requests and no reasoning persistence."""

    provider = "deepseek"
    provider_label = "DeepSeek"
    credential_name = "DEEPSEEK_API_KEY"
    model_id = MODEL_ID
    profile = PROFILE
    prompt_revision = PROMPT_REVISION
    max_tokens = MAX_TOKENS
    thinking = "enabled"
    reasoning_effort = "high"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "https://api.deepseek.com/chat/completions",
        timeout_seconds: float = 120,
        retries: int = 2,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        if not api_key:
            raise JudgeRunError(f"{self.credential_name} is required.")
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.opener = opener
        self.sleeper = sleeper
        self.extra_headers = extra_headers or {}
        self.request_count = 0
        self.request_limit: int | None = None
        self._state_lock = Lock()
        self.total_usage = self.empty_usage()

    def empty_usage(self) -> dict[str, int]:
        return {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 0,
        }

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _prompt(case)},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "enabled"},
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
        }

    def parse_usage(self, response: dict[str, Any]) -> dict[str, int]:
        return _usage(response)

    def request_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

    def extract_content(self, response: dict[str, Any]) -> str:
        return str(response["choices"][0]["message"]["content"])

    def response_judge_metadata(self, response: dict[str, Any]) -> dict[str, str]:
        return {}

    def normalize_evaluation(
        self, evaluation: dict[str, Any], case: dict[str, Any]
    ) -> dict[str, Any]:
        return evaluation

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        current = _cost(usage)
        prior = float(
            prior_run.get(
                "cumulative_estimated_cost_rmb",
                prior_run.get("estimated_cost_rmb", 0.0),
            )
        )
        return {
            "pricing_rmb_per_million_tokens": PRICING_RMB_PER_MILLION,
            "estimated_cost_rmb": current,
            "prior_estimated_cost_rmb": prior,
            "cumulative_estimated_cost_rmb": round(prior + current, 6),
        }

    def set_request_limit(self, limit: int | None) -> None:
        """Reset and enforce a total HTTP-request budget for one run."""
        with self._state_lock:
            self.request_count = 0
            self.request_limit = limit

    def set_retry_budget(self, retries: int) -> None:
        """Set the retry count used by the compatibility ``evaluate`` method."""
        if retries < 0:
            raise JudgeRunError("result retry budget must be non-negative.", failure_type="budget")
        self.retries = retries

    def _reserve_request(self) -> None:
        with self._state_lock:
            if self.request_limit is not None and self.request_count >= self.request_limit:
                raise JudgeRunError(
                    f"HTTP request budget exhausted at {self.request_limit} requests.",
                    failure_type="budget",
                    retryable=False,
                )
            self.request_count += 1

    def evaluate_once(self, case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
        """Perform exactly one HTTP attempt for one logical result."""
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self.request_body(case), ensure_ascii=False).encode("utf-8"),
            headers=self.request_headers(),
            method="POST",
        )
        call_usage = self.empty_usage()
        response_text = ""
        content = ""
        try:
            self._reserve_request()
            with self.opener(request, timeout=self.timeout_seconds) as stream:
                raw_response = stream.read()
            response_text = raw_response.decode("utf-8")
            response = json.loads(response_text)
            response_usage = self.parse_usage(response)
            with self._state_lock:
                for key, value in response_usage.items():
                    call_usage[key] += value
                    self.total_usage[key] += value
            self._raise_if_truncated(response)
            content = self.extract_content(response)
            model_payload = json.loads(content)
            evaluation = self.normalize_evaluation(
                _without_nulls(model_payload["evaluation"]), case
            )
            result = {
                "schema_version": 1,
                "case_id": case["id"],
                "judge": {
                    "profile": self.profile,
                    "model": self.model_id,
                    "prompt_revision": self.prompt_revision,
                    "calibration_revision": case.get("pack_revision", "multilingual-48-v1"),
                    **self.response_judge_metadata(response),
                },
                "evaluation": evaluation,
            }
            validate_payload(result, "judge-result.schema.json")
            return result, call_usage
        except JudgeRunError:
            raise
        except urllib.error.HTTPError as exc:
            failure_type = "rate_limit" if exc.code == 429 else "provider"
            retryable = exc.code == 429 or 500 <= exc.code < 600
            raise JudgeRunError(
                f"{self.provider_label} HTTP failure: status {exc.code}",
                failure_type=failure_type,
                retryable=retryable,
            ) from exc
        except TimeoutError as exc:
            raise JudgeRunError(
                f"{self.provider_label} request timed out.",
                failure_type="timeout",
            ) from exc
        except (http.client.IncompleteRead, urllib.error.ContentTooShortError) as exc:
            raise JudgeRunError(
                f"{self.provider_label} response was truncated.",
                failure_type="truncation",
            ) from exc
        except urllib.error.URLError as exc:
            failure_type = "timeout" if _is_timeout(exc.reason) else "provider"
            raise JudgeRunError(
                f"{self.provider_label} request failed: {exc.reason}",
                failure_type=failure_type,
            ) from exc
        except json.JSONDecodeError as exc:
            source = content or response_text
            raise _json_failure(self.provider_label, source, exc) from exc
        except UnicodeDecodeError as exc:
            raise JudgeRunError(
                f"{self.provider_label} returned non-UTF-8 JSON.",
                failure_type="json",
            ) from exc
        except (AttributeError, KeyError, IndexError, TypeError) as exc:
            raise JudgeRunError(
                f"{self.provider_label} returned empty or malformed JSON content.",
                failure_type="provider",
            ) from exc
        except DocumentValidationError as exc:
            raise JudgeRunError(
                f"{self.provider_label} JSON failed judge schema: {'; '.join(exc.issues)}",
                failure_type="schema",
            ) from exc

    def _raise_if_truncated(self, response: dict[str, Any]) -> None:
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            finish_reason = choices[0].get("finish_reason")
            if finish_reason in {"length", "max_tokens", "MAX_TOKENS"}:
                raise JudgeRunError(
                    f"{self.provider_label} response reached the output token limit.",
                    failure_type="truncation",
                )
        candidates = response.get("candidates")
        if isinstance(candidates, list) and candidates:
            finish_reason = candidates[0].get("finishReason")
            if finish_reason in {"MAX_TOKENS", "length", "max_tokens"}:
                raise JudgeRunError(
                    f"{self.provider_label} response reached the output token limit.",
                    failure_type="truncation",
                )

    def evaluate(self, case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
        """Perform one logical result with the configured bounded retry policy."""
        last_error: JudgeRunError | None = None
        for attempt in range(self.retries + 1):
            try:
                return self.evaluate_once(case)
            except JudgeRunError as exc:
                if not exc.retryable or exc.failure_type == "budget":
                    raise
                last_error = exc
            if attempt < self.retries:
                self.sleeper(float(2**attempt))
        assert last_error is not None
        raise last_error


class DeepSeekFlashJudge(DeepSeekJudge):
    """Current DeepSeek V4 Flash judge for direct comparison with the Pro baseline."""

    provider = "deepseek-flash"
    provider_label = "DeepSeek Flash"
    model_id = FLASH_MODEL_ID
    profile = FLASH_PROFILE
    max_tokens = FLASH_MAX_TOKENS
    reasoning_effort = "low"

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        current = round(
            (
                usage["cache_hit_input_tokens"] * FLASH_PRICING_RMB_PER_MILLION["cache_hit_input"]
                + usage["cache_miss_input_tokens"]
                * FLASH_PRICING_RMB_PER_MILLION["cache_miss_input"]
                + usage["output_tokens"] * FLASH_PRICING_RMB_PER_MILLION["output"]
            )
            / 1_000_000,
            6,
        )
        prior = float(
            prior_run.get(
                "cumulative_estimated_cost_rmb",
                prior_run.get("estimated_cost_rmb", 0.0),
            )
        )
        return {
            "pricing_rmb_per_million_tokens": FLASH_PRICING_RMB_PER_MILLION,
            "estimated_cost_rmb": current,
            "prior_estimated_cost_rmb": prior,
            "cumulative_estimated_cost_rmb": round(prior + current, 6),
        }


class XAIJudge(DeepSeekJudge):
    """xAI Grok judge using low reasoning and strict structured output."""

    provider = "xai"
    provider_label = "xAI"
    credential_name = "XAI_API_KEY"
    model_id = XAI_MODEL_ID
    profile = XAI_PROFILE
    max_tokens = XAI_MAX_TOKENS
    thinking = "required"
    reasoning_effort = "low"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "https://api.x.ai/v1/chat/completions",
        timeout_seconds: float = 120,
        retries: int = 2,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(
            api_key,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            retries=retries,
            opener=opener,
            sleeper=sleeper,
            extra_headers={"x-grok-conv-id": "aventine-translation-judge-v2"},
        )

    def empty_usage(self) -> dict[str, int]:
        return {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cost_in_usd_ticks": 0,
        }

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _prompt(case)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "translation_judge_evaluation",
                    "strict": True,
                    "schema": _xai_response_schema(_case_mode(case)),
                },
            },
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
        }

    def parse_usage(self, response: dict[str, Any]) -> dict[str, int]:
        return _xai_usage(response)

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        estimated = round(
            (
                usage["cache_hit_input_tokens"] * XAI_PRICING_USD_PER_MILLION["cache_hit_input"]
                + usage["cache_miss_input_tokens"] * XAI_PRICING_USD_PER_MILLION["cache_miss_input"]
                + (usage["output_tokens"] + usage["reasoning_tokens"])
                * XAI_PRICING_USD_PER_MILLION["output"]
            )
            / 1_000_000,
            6,
        )
        exact = round(usage["cost_in_usd_ticks"] / 10_000_000_000, 10)
        current = exact or estimated
        prior = float(
            prior_run.get(
                "cumulative_exact_cost_usd",
                prior_run.get("exact_cost_usd", 0.0),
            )
        )
        return {
            "pricing_usd_per_million_tokens": XAI_PRICING_USD_PER_MILLION,
            "estimated_cost_usd": estimated,
            "exact_cost_usd": current,
            "prior_exact_cost_usd": prior,
            "cumulative_exact_cost_usd": round(prior + current, 10),
            "cost_source": "api_ticks" if exact else "token_estimate",
        }


class OpenRouterJudge(DeepSeekJudge):
    """OpenRouter-hosted DeepSeek V4 Pro judge with bounded structured output."""

    provider = "openrouter"
    provider_label = "OpenRouter"
    credential_name = "OPENROUTER_API_KEY"
    model_id = OPENROUTER_MODEL_ID
    profile = OPENROUTER_PROFILE
    max_tokens = OPENROUTER_MAX_TOKENS
    thinking = "enabled"
    reasoning_effort = "high"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
        timeout_seconds: float = 120,
        retries: int = 2,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(
            api_key,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            retries=retries,
            opener=opener,
            sleeper=sleeper,
            extra_headers={
                "HTTP-Referer": "https://drlinglong.github.io/Remis/aventine/",
                "X-Title": "Remis Aventine translation judge",
            },
        )

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _prompt(case)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "translation_judge_evaluation",
                    "strict": True,
                    "schema": _xai_response_schema(_case_mode(case)),
                },
            },
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
        }

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        current = round(
            (
                usage["cache_hit_input_tokens"]
                * OPENROUTER_PRICING_USD_PER_MILLION["cache_hit_input"]
                + usage["cache_miss_input_tokens"]
                * OPENROUTER_PRICING_USD_PER_MILLION["cache_miss_input"]
                + usage["output_tokens"] * OPENROUTER_PRICING_USD_PER_MILLION["output"]
            )
            / 1_000_000,
            6,
        )
        prior = float(
            prior_run.get(
                "cumulative_estimated_cost_usd",
                prior_run.get("estimated_cost_usd", 0.0),
            )
        )
        return {
            "pricing_usd_per_million_tokens": OPENROUTER_PRICING_USD_PER_MILLION,
            "estimated_cost_usd": current,
            "prior_estimated_cost_usd": prior,
            "cumulative_estimated_cost_usd": round(prior + current, 6),
            "cost_source": "token_estimate",
        }


class OpenRouterGeminiJudge(OpenRouterJudge):
    """Gemini 3.7 Flash judge routed through OpenRouter with explicit reasoning."""

    provider = "openrouter-gemini"
    provider_label = "OpenRouter Gemini 3.7 Flash"
    model_id = OPENROUTER_GEMINI_MODEL_ID
    canonical_model_id = OPENROUTER_GEMINI_CANONICAL_MODEL_ID
    profile = OPENROUTER_GEMINI_PROFILE
    max_tokens = OPENROUTER_GEMINI_MAX_TOKENS
    seed = OPENROUTER_GEMINI_SEED
    reasoning_effort = "medium"

    def empty_usage(self) -> dict[str, int]:
        return {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cost_in_usd_ticks": 0,
        }

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _prompt(case)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "translation_judge_evaluation",
                    "strict": True,
                    "schema": _xai_response_schema(_case_mode(case)),
                },
            },
            "reasoning": {"effort": self.reasoning_effort, "exclude": True},
            "provider": {"require_parameters": True, "allow_fallbacks": False},
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

    def parse_usage(self, response: dict[str, Any]) -> dict[str, int]:
        return _openrouter_usage(response)

    def response_judge_metadata(self, response: dict[str, Any]) -> dict[str, str]:
        metadata: dict[str, str] = {"canonical_model": self.canonical_model_id}
        routed_provider = response.get("provider")
        response_model = response.get("model")
        if isinstance(routed_provider, str) and routed_provider:
            metadata["routed_provider"] = routed_provider
        if isinstance(response_model, str) and response_model:
            metadata["response_model"] = response_model
        return metadata

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        estimated = round(
            (
                usage["cache_hit_input_tokens"]
                * OPENROUTER_GEMINI_PRICING_USD_PER_MILLION["cache_hit_input"]
                + usage["cache_miss_input_tokens"]
                * OPENROUTER_GEMINI_PRICING_USD_PER_MILLION["cache_miss_input"]
                + usage["output_tokens"]
                * OPENROUTER_GEMINI_PRICING_USD_PER_MILLION["output_including_reasoning"]
            )
            / 1_000_000,
            10,
        )
        exact = round(usage["cost_in_usd_ticks"] / 10_000_000_000, 10)
        current = exact or estimated
        prior = float(
            prior_run.get(
                "cumulative_exact_cost_usd",
                prior_run.get("exact_cost_usd", 0.0),
            )
        )
        return {
            "pricing_usd_per_million_tokens": OPENROUTER_GEMINI_PRICING_USD_PER_MILLION,
            "estimated_cost_usd": estimated,
            "exact_cost_usd": current,
            "prior_exact_cost_usd": prior,
            "cumulative_exact_cost_usd": round(prior + current, 10),
            "cost_source": "openrouter_usage" if exact else "token_estimate",
        }


class OpenRouterGeminiHighJudge(OpenRouterGeminiJudge):
    """High-reasoning qualification profile; not the default production judge."""

    provider = "openrouter-gemini-high"
    profile = OPENROUTER_GEMINI_HIGH_PROFILE
    reasoning_effort = "high"


class OpenRouterLunaJudge(OpenRouterGeminiJudge):
    """Primary v0.3 judge: Luna high over the normal OpenRouter endpoint."""

    provider = "openrouter-luna"
    provider_label = "OpenRouter GPT-5.6 Luna"
    model_id = OPENROUTER_LUNA_MODEL_ID
    canonical_model_id = OPENROUTER_LUNA_MODEL_ID
    profile = OPENROUTER_LUNA_PROFILE
    max_tokens = OPENROUTER_LUNA_MAX_TOKENS
    reasoning_effort = "high"

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        body = super().request_body(case)
        body.pop("seed", None)
        # Luna's current OpenRouter route rejects response_format despite returning
        # reliable JSON under the schema-explicit system prompt. The local validator
        # remains the contract boundary.
        body.pop("response_format", None)
        return body

    def normalize_evaluation(
        self, evaluation: dict[str, Any], case: dict[str, Any]
    ) -> dict[str, Any]:
        # Without provider-side response_format Luna sometimes returns useful
        # per-candidate dimension objects that the public scalar schema does not
        # represent. Verdict/errors/rationale remain schema-bound evidence.
        if _case_mode(case) == "pairwise":
            evaluation.pop("dimensions", None)
        return evaluation


class OpenRouterDeepSeekFlashJudge(OpenRouterGeminiJudge):
    """Low-cost third-family fallback over the normal OpenRouter endpoint."""

    provider = "openrouter-deepseek-flash"
    provider_label = "OpenRouter DeepSeek V4 Flash"
    model_id = OPENROUTER_DS_FLASH_MODEL_ID
    canonical_model_id = OPENROUTER_DS_FLASH_MODEL_ID
    profile = OPENROUTER_DS_FLASH_PROFILE
    max_tokens = OPENROUTER_DS_FLASH_MAX_TOKENS
    reasoning_effort = "high"


class GoogleGemmaJudge(DeepSeekJudge):
    """Google-hosted full-precision Gemma 4 judge on the Gemini API free tier."""

    provider = "google"
    provider_label = "Google Gemini API"
    credential_name = "GEMINI_API_KEY"
    model_id = GOOGLE_MODEL_ID
    profile = GOOGLE_PROFILE
    max_tokens = GOOGLE_MAX_TOKENS
    thinking = "not_configurable"
    reasoning_effort = "none"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = (
            "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent"
        ),
        timeout_seconds: float = 120,
        retries: int = 2,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(
            api_key,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            retries=retries,
            opener=opener,
            sleeper=sleeper,
        )

    def request_headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    def request_body(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{_prompt(case)}"}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": _google_response_schema(_case_mode(case)),
                "maxOutputTokens": self.max_tokens,
            },
        }

    def extract_content(self, response: dict[str, Any]) -> str:
        return str(response["candidates"][0]["content"]["parts"][0]["text"])

    def parse_usage(self, response: dict[str, Any]) -> dict[str, int]:
        usage = response.get("usageMetadata") or {}
        prompt = int(usage.get("promptTokenCount") or 0)
        cached = int(usage.get("cachedContentTokenCount") or 0)
        return {
            "cache_hit_input_tokens": cached,
            "cache_miss_input_tokens": max(prompt - cached, 0),
            "output_tokens": int(usage.get("candidatesTokenCount") or 0),
            "reasoning_tokens": int(usage.get("thoughtsTokenCount") or 0),
        }

    def empty_usage(self) -> dict[str, int]:
        return {
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
        }

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        return {
            "pricing": "Gemma 4 Gemini API free tier",
            "exact_cost_usd": 0.0,
            "prior_exact_cost_usd": 0.0,
            "cumulative_exact_cost_usd": 0.0,
            "cost_source": "official_free_tier",
        }


def _swapped_case(case: dict[str, Any]) -> dict[str, Any]:
    swapped = deepcopy(case)
    swapped["id"] = f"{case['id']}-ab-swap"
    swapped["input"]["candidate_a"], swapped["input"]["candidate_b"] = (
        swapped["input"]["candidate_b"],
        swapped["input"]["candidate_a"],
    )
    if isinstance(swapped.get("gold"), dict):
        verdict = swapped["gold"]["verdict"]
        swapped["gold"]["verdict"] = {
            "candidate_a": "candidate_b",
            "candidate_b": "candidate_a",
        }.get(verdict, verdict)
    return swapped


def _valid_prior_output(value: Any, case_id: str) -> bool:
    try:
        output = validate_payload(value, "judge-result.schema.json")
    except DocumentValidationError:
        return False
    return output["case_id"] == case_id


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON snapshot with replace-on-success semantics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _task_key(case_id: str, field: str) -> str:
    return json.dumps([case_id, field], ensure_ascii=False, separators=(",", ":"))


def _judge_configuration(
    input_path: Path,
    fixture: dict[str, Any],
    cases: list[dict[str, Any]],
    tasks: list[tuple[int, str, dict[str, Any]]],
    judge: DeepSeekJudge,
    *,
    workers: int,
    result_retry_budget: int,
) -> dict[str, Any]:
    configuration: dict[str, Any] = {
        "version": 1,
        "fixture_id": fixture["id"],
        "fixture_sha256": _sha256_file(input_path),
        "case_ids": [case["id"] for case in cases],
        "logical_tasks": [[cases[index]["id"], field] for index, field, _ in tasks],
        "provider": getattr(judge, "provider", "unknown"),
        "model": getattr(judge, "model_id", "unknown"),
        "profile": getattr(judge, "profile", "unknown"),
        "prompt_revision": getattr(judge, "prompt_revision", "unknown"),
        "max_tokens": getattr(judge, "max_tokens", None),
        "thinking": getattr(judge, "thinking", None),
        "reasoning_effort": getattr(judge, "reasoning_effort", None),
        "workers": workers,
        "result_retry_budget": result_retry_budget,
    }
    seed = getattr(judge, "seed", None)
    if seed is not None:
        configuration["seed"] = seed
    endpoint = getattr(judge, "endpoint", None)
    if endpoint is not None:
        configuration["endpoint"] = str(endpoint)
    return configuration


def _exception_failure_type(exc: BaseException) -> str:
    if isinstance(exc, JudgeRunError):
        return exc.failure_type
    if isinstance(exc, (TimeoutError, socket.timeout)) or _is_timeout(exc):
        return "timeout"
    if isinstance(exc, json.JSONDecodeError):
        return "json"
    text = str(exc).lower()
    if "429" in text or "rate limit" in text:
        return "rate_limit"
    if "schema" in text:
        return "schema"
    if "truncat" in text or "max token" in text:
        return "truncation"
    if "budget" in text:
        return "budget"
    return "unknown"


def _failure_payload(
    exc: BaseException,
    *,
    attempts: int,
    retries: int,
    budget_scope: str | None = None,
) -> dict[str, Any]:
    failure: dict[str, Any] = {
        "kind": "judge_call_failure",
        "failure_type": _exception_failure_type(exc),
        "detail": str(exc),
        "attempt_count": attempts,
        "retry_count": retries,
    }
    if budget_scope is not None:
        failure["budget_scope"] = budget_scope
    return {"benchmark_failure": failure}


def _failure_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts = {failure_type: 0 for failure_type in FAILURE_TYPES}
    for case in cases:
        for field in ("judge_output", "swap_judge_output"):
            value = case.get(field)
            if not isinstance(value, dict) or "benchmark_failure" not in value:
                continue
            failure = value["benchmark_failure"]
            failure_type = failure.get("failure_type") if isinstance(failure, dict) else None
            if failure_type not in counts:
                failure_type = "unknown"
            counts[failure_type] += 1
    return counts


def run_judge_pack(
    input_path: Path,
    output_path: Path,
    judge: DeepSeekJudge,
    *,
    limit: int | None = None,
    case_ids: list[str] | None = None,
    max_calls: int | None = None,
    workers: int = 1,
    resume_from: Path | None = None,
    logical_result_budget: int | None = None,
    http_attempt_budget: int | None = None,
    result_retry_budget: int | None = None,
    checkpoint_path: Path | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run judge results with separate budgets, fair retries, and atomic snapshots."""
    fixture = load_calibration_fixture(input_path)
    selected = fixture["cases"]
    if case_ids:
        requested = set(case_ids)
        selected = [case for case in selected if case.get("id") in requested]
        missing = requested - {case["id"] for case in selected}
        if missing:
            raise JudgeRunError(f"Unknown case ids: {', '.join(sorted(missing))}")
    cases = deepcopy(selected[:limit])
    if workers < 1:
        raise JudgeRunError("workers must be at least 1.")

    separate_budgets = any(
        value is not None
        for value in (logical_result_budget, http_attempt_budget, result_retry_budget)
    )
    if not separate_budgets and max_calls is None:
        max_calls = 100
    for name, value in (
        ("max_calls", max_calls),
        ("logical_result_budget", logical_result_budget),
        ("http_attempt_budget", http_attempt_budget),
        ("result_retry_budget", result_retry_budget),
    ):
        if value is not None and value < 0:
            raise JudgeRunError(f"{name} must be non-negative.", failure_type="budget")

    effective_retry_budget = (
        result_retry_budget
        if result_retry_budget is not None
        else max(int(getattr(judge, "retries", 0)), 0)
    )
    retry_setter = getattr(judge, "set_retry_budget", None)
    if callable(retry_setter) and result_retry_budget is not None:
        retry_setter(effective_retry_budget)

    for case in cases:
        case["pack_revision"] = fixture["id"]
    all_tasks: list[tuple[int, str, dict[str, Any]]] = []
    for case_index, case in enumerate(cases):
        all_tasks.append((case_index, "judge_output", case))
        if case.get("origin_suite") == "aces" or case.get("ab_swap") is True:
            all_tasks.append((case_index, "swap_judge_output", _swapped_case(case)))

    prior_run: dict[str, Any] = {}
    reused_result_count = 0
    current_configuration = _judge_configuration(
        input_path,
        fixture,
        cases,
        all_tasks,
        judge,
        workers=workers,
        result_retry_budget=effective_retry_budget,
    )
    config_fingerprint = _sha256_json(current_configuration)
    if resume_from is not None:
        prior = load_calibration_fixture(resume_from)
        prior_run = prior.get("run") or {}
        prior_fingerprint = prior_run.get("config_fingerprint")
        if prior_fingerprint is not None:
            if prior_fingerprint != config_fingerprint:
                raise JudgeRunError(
                    "Resume artifact has incompatible judge configuration fingerprint: "
                    f"expected {config_fingerprint}, received {prior_fingerprint}"
                )
        else:
            expected = {
                "model": getattr(judge, "model_id", None),
                "profile": getattr(judge, "profile", None),
                "prompt_revision": getattr(judge, "prompt_revision", None),
                "max_tokens": getattr(judge, "max_tokens", None),
                "reasoning_effort": getattr(judge, "reasoning_effort", None),
            }
            mismatches = [key for key, value in expected.items() if prior_run.get(key) != value]
            if mismatches:
                raise JudgeRunError(
                    "Resume artifact has incompatible judge configuration: " + ", ".join(mismatches)
                )
        prior_cases = {case["id"]: case for case in prior.get("cases", [])}
        for case_index, field, _evaluation_case in all_tasks:
            case = cases[case_index]
            prior_case = prior_cases.get(case["id"], {})
            if field in prior_case and _valid_prior_output(prior_case[field], case["id"]):
                case[field] = deepcopy(prior_case[field])
                reused_result_count += 1

    tasks = [
        (case_index, field, evaluation_case)
        for case_index, field, evaluation_case in all_tasks
        if field not in cases[case_index]
    ]
    if not separate_budgets:
        logical_budget = max_calls
        http_budget = max_calls
        budget_mode = "max_calls_compat"
        if logical_budget is not None and len(tasks) > logical_budget:
            raise JudgeRunError(f"Planned {len(tasks)} calls exceeds max_calls={logical_budget}.")
    else:
        default_budget = max_calls if max_calls is not None else 100
        logical_budget = (
            logical_result_budget if logical_result_budget is not None else default_budget
        )
        http_budget = http_attempt_budget if http_attempt_budget is not None else default_budget
        budget_mode = "separate"

    scheduled_tasks = tasks if logical_budget is None else tasks[:logical_budget]
    skipped_tasks = tasks[len(scheduled_tasks) :]
    budget_exhausted = bool(skipped_tasks)
    states: dict[str, dict[str, Any]] = {}
    for case_index, field, _evaluation_case in all_tasks:
        key = _task_key(cases[case_index]["id"], field)
        states[key] = {
            "case_id": cases[case_index]["id"],
            "field": field,
            "attempts": 0,
            "retries": 0,
            "status": "reused" if field in cases[case_index] else "pending",
        }

    def notify(event: dict[str, Any]) -> None:
        if progress is not None:
            with suppress(Exception):
                progress(event)

    def mark_budget(task: tuple[int, str, dict[str, Any]], scope: str, detail: str) -> None:
        case_index, field, _evaluation_case = task
        state = states[_task_key(cases[case_index]["id"], field)]
        cases[case_index][field] = _failure_payload(
            JudgeRunError(detail, failure_type="budget", retryable=False),
            attempts=state["attempts"],
            retries=state["retries"],
            budget_scope=scope,
        )
        state["status"] = "budget"
        state["failure_type"] = "budget"

    for task in skipped_tasks:
        mark_budget(
            task,
            "logical_result",
            "Logical result budget exhausted before this result was scheduled.",
        )

    request_limiter = getattr(judge, "set_request_limit", None)
    if callable(request_limiter):
        request_limiter(http_budget)
    starting_usage = deepcopy(getattr(judge, "total_usage", None))
    totals = judge.empty_usage()
    attempts_used = 0
    prior_http_attempt_count = int(
        prior_run.get("cumulative_http_attempt_count") or prior_run.get("http_attempt_count") or 0
    )
    checkpoint_target = checkpoint_path or output_path

    def usage_snapshot() -> dict[str, int]:
        judge_usage = getattr(judge, "total_usage", None)
        if isinstance(judge_usage, dict) and isinstance(starting_usage, dict):
            return {
                key: judge_usage.get(key, 0) - starting_usage.get(key, 0) for key in judge_usage
            }
        return dict(totals)

    def request_count() -> int:
        value = getattr(judge, "request_count", None)
        return int(value) if isinstance(value, int) else attempts_used

    def build_result(status: str) -> dict[str, Any]:
        failure_counts = _failure_counts(cases)
        completed_result_count = sum(
            field in cases[case_index] for case_index, field, _evaluation_case in all_tasks
        )
        run: dict[str, Any] = {
            "provider": getattr(judge, "provider", "unknown"),
            "model": getattr(judge, "model_id", "unknown"),
            "profile": getattr(judge, "profile", "unknown"),
            "prompt_revision": getattr(judge, "prompt_revision", "unknown"),
            "thinking": getattr(judge, "thinking", "unknown"),
            "reasoning_effort": getattr(judge, "reasoning_effort", "unknown"),
            "max_tokens": getattr(judge, "max_tokens", 0),
            "workers": workers,
            "budget_mode": budget_mode,
            "max_calls": max_calls,
            "logical_result_budget": logical_budget,
            "http_attempt_budget": http_budget,
            "result_retry_budget": effective_retry_budget,
            "planned_call_count": len(tasks),
            "scheduled_call_count": len(scheduled_tasks),
            "logical_result_count": len(all_tasks),
            "reused_result_count": reused_result_count,
            "completed_result_count": completed_result_count,
            "unfinished_result_count": len(all_tasks) - completed_result_count,
            "budget_skipped_count": len(skipped_tasks),
            "http_request_count": request_count(),
            "http_attempt_count": attempts_used,
            "prior_http_attempt_count": prior_http_attempt_count,
            "cumulative_http_attempt_count": prior_http_attempt_count + attempts_used,
            "failure_count": sum(failure_counts.values()),
            "failure_counts": failure_counts,
            "failure_taxonomy": list(FAILURE_TYPES),
            "usage": usage_snapshot(),
            "resume_from": str(resume_from) if resume_from is not None else None,
            "checkpoint_path": str(checkpoint_target),
            "config_fingerprint": config_fingerprint,
            "configuration": current_configuration,
            "status": status,
            "completed": status == "completed",
            "reasoning_persisted": False,
            "credentials_persisted": False,
            "task_state": {key: states[key] for key in sorted(states)},
        }
        run.update(judge.cost_fields(run["usage"], prior_run))
        result: dict[str, Any] = {
            "schema_version": 1,
            "id": f"{fixture['id']}.{getattr(judge, 'model_id', 'unknown')}",
            "suite": fixture["suite"],
            "description": (
                f"Schema-bound {getattr(judge, 'provider_label', 'judge')} calibration results; "
                "not human gold."
            ),
            "run": run,
            "cases": deepcopy(cases),
        }
        for field in ("adapter", "recipes", "policy_cases", "repair_over_editing"):
            if field in fixture:
                result[field] = deepcopy(fixture[field])
        return result

    def write_checkpoint(status: str) -> dict[str, Any]:
        snapshot = build_result(status)
        _atomic_write_json(checkpoint_target, snapshot)
        return snapshot

    notify(
        {
            "event": "started",
            "logical_result_count": len(all_tasks),
            "pending_result_count": len(tasks),
            "reused_result_count": reused_result_count,
            "logical_result_budget": logical_budget,
            "http_attempt_budget": http_budget,
        }
    )
    write_checkpoint("running")

    def invoke_once(task: tuple[int, str, dict[str, Any]]) -> tuple[Any, Any]:
        _case_index, _field, evaluation_case = task
        evaluator = getattr(judge, "evaluate_once", None)
        if callable(evaluator):
            return evaluator(evaluation_case)
        return judge.evaluate(evaluation_case)

    active: deque[tuple[int, str, dict[str, Any]]] = deque(scheduled_tasks)

    def handle_failure(task: tuple[int, str, dict[str, Any]], exc: BaseException) -> None:
        nonlocal budget_exhausted
        case_index, field, _evaluation_case = task
        state = states[_task_key(cases[case_index]["id"], field)]
        failure_type = _exception_failure_type(exc)
        if failure_type == "budget":
            budget_exhausted = True
        if (
            failure_type != "budget"
            and _is_retryable(exc)
            and state["retries"] < effective_retry_budget
        ):
            state["retries"] += 1
            state["status"] = "retrying"
            state["failure_type"] = failure_type
            state["retry_delay_seconds"] = float(2 ** (state["retries"] - 1))
            active.append(task)
            notify(
                {
                    "event": "retry",
                    "case_id": state["case_id"],
                    "field": field,
                    "failure_type": failure_type,
                    "retry_count": state["retries"],
                    "http_attempt_count": attempts_used,
                }
            )
            return
        cases[case_index][field] = _failure_payload(
            exc,
            attempts=state["attempts"],
            retries=state["retries"],
        )
        state["status"] = "budget" if failure_type == "budget" else "failed"
        state["failure_type"] = failure_type
        notify(
            {
                "event": "result",
                "case_id": state["case_id"],
                "field": field,
                "status": state["status"],
                "failure_type": failure_type,
                "http_attempt_count": attempts_used,
            }
        )

    try:
        while active:
            if http_budget is not None and attempts_used >= http_budget:
                budget_exhausted = True
                while active:
                    mark_budget(
                        active.popleft(),
                        "http_attempt",
                        "HTTP attempt budget exhausted before this result was scheduled.",
                    )
                break
            batch: list[tuple[int, str, dict[str, Any]]] = []
            retry_delay_seconds = 0.0
            while active and len(batch) < workers:
                if http_budget is not None and attempts_used + len(batch) >= http_budget:
                    break
                task = active.popleft()
                case_index, field, _evaluation_case = task
                state = states[_task_key(cases[case_index]["id"], field)]
                state["attempts"] += 1
                retry_delay_seconds = max(
                    retry_delay_seconds,
                    float(state.pop("retry_delay_seconds", 0.0)),
                )
                batch.append(task)
            if not batch:
                continue
            if retry_delay_seconds:
                getattr(judge, "sleeper", time.sleep)(retry_delay_seconds)
            attempts_used += len(batch)
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {executor.submit(invoke_once, task): task for task in batch}
                for future in as_completed(futures):
                    task = futures[future]
                    case_index, field, _evaluation_case = task
                    key = _task_key(cases[case_index]["id"], field)
                    try:
                        output, usage = future.result()
                    except Exception as exc:
                        handle_failure(task, exc)
                    else:
                        if usage is not None:
                            for usage_key, value in usage.items():
                                totals[usage_key] = totals.get(usage_key, 0) + value
                        if field == "swap_judge_output" and isinstance(output, dict):
                            output["case_id"] = cases[case_index]["id"]
                        cases[case_index][field] = output
                        states[key]["status"] = "completed"
                        notify(
                            {
                                "event": "result",
                                "case_id": cases[case_index]["id"],
                                "field": field,
                                "status": "completed",
                                "http_attempt_count": attempts_used,
                            }
                        )
                    write_checkpoint("running")
    except BaseException:
        write_checkpoint("interrupted")
        raise

    status = "budget_exhausted" if budget_exhausted else "completed"
    final_result = write_checkpoint(status)
    if checkpoint_target != output_path:
        _atomic_write_json(output_path, final_result)
    notify(
        {
            "event": "finished",
            "status": status,
            "completed_result_count": final_result["run"]["completed_result_count"],
            "failure_count": final_result["run"]["failure_count"],
            "http_attempt_count": final_result["run"]["http_attempt_count"],
        }
    )
    return final_result


def _project_env_value(path: Path, name: str) -> str:
    if not path.is_file():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return ""


def judge_from_environment(
    env_path: Path = Path(".env"), provider: str = "deepseek"
) -> DeepSeekJudge:
    """Create a provider judge from process env or a Git-ignored project .env."""
    clients: dict[str, tuple[str, type[DeepSeekJudge]]] = {
        "deepseek": ("DEEPSEEK_API_KEY", DeepSeekJudge),
        "deepseek-flash": ("DEEPSEEK_API_KEY", DeepSeekFlashJudge),
        "xai": ("XAI_API_KEY", XAIJudge),
        "google": ("GEMINI_API_KEY", GoogleGemmaJudge),
        "openrouter": ("OPENROUTER_API_KEY", OpenRouterJudge),
        "openrouter-gemini": ("OPENROUTER_API_KEY", OpenRouterGeminiJudge),
        "openrouter-gemini-high": ("OPENROUTER_API_KEY", OpenRouterGeminiHighJudge),
        "openrouter-luna": ("OPENROUTER_API_KEY", OpenRouterLunaJudge),
        "openrouter-deepseek-flash": (
            "OPENROUTER_API_KEY",
            OpenRouterDeepSeekFlashJudge,
        ),
    }
    try:
        credential_name, client_type = clients[provider]
    except KeyError as exc:
        raise JudgeRunError(f"Unsupported judge provider: {provider}") from exc
    api_key = os.environ.get(credential_name, "") or _project_env_value(env_path, credential_name)
    return client_type(api_key)

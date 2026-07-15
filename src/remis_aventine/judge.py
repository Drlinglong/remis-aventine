"""Schema-bound DeepSeek judge runner with bounded retries and usage accounting."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from remis_aventine.calibration import load_calibration_fixture
from remis_aventine.validation import DocumentValidationError, validate_payload

MODEL_ID = "deepseek-v4-pro"
PROMPT_REVISION = "translation-judge-v2"
PROFILE = "deepseek-v4-pro-thinking-high"
MAX_TOKENS = 4000
PRICING_RMB_PER_MILLION = {"cache_hit_input": 0.025, "cache_miss_input": 3.0, "output": 6.0}
XAI_MODEL_ID = "grok-4.5"
XAI_PROFILE = "grok-4.5-reasoning-low-structured-v2"
XAI_MAX_TOKENS = 4000
XAI_PRICING_USD_PER_MILLION = {"cache_hit_input": 0.5, "cache_miss_input": 2.0, "output": 6.0}
GOOGLE_MODEL_ID = "gemma-4-31b-it"
GOOGLE_PROFILE = "gemma-4-31b-it-free-structured-v1"
GOOGLE_MAX_TOKENS = 4000


class JudgeRunError(RuntimeError):
    """Raised when a bounded judge run cannot proceed safely."""


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

    def cost_fields(self, usage: dict[str, int], prior_run: dict[str, Any]) -> dict[str, Any]:
        current = _cost(usage)
        prior = float(prior_run.get("estimated_cost_rmb", 0.0))
        return {
            "pricing_rmb_per_million_tokens": PRICING_RMB_PER_MILLION,
            "estimated_cost_rmb": current,
            "prior_estimated_cost_rmb": prior,
            "cumulative_estimated_cost_rmb": round(prior + current, 6),
        }

    def set_request_limit(self, limit: int) -> None:
        """Reset and enforce a total HTTP-request budget for one run."""
        with self._state_lock:
            self.request_count = 0
            self.request_limit = limit

    def _reserve_request(self) -> None:
        with self._state_lock:
            if self.request_limit is not None and self.request_count >= self.request_limit:
                raise JudgeRunError(
                    f"HTTP request budget exhausted at {self.request_limit} requests."
                )
            self.request_count += 1

    def evaluate(self, case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self.request_body(case), ensure_ascii=False).encode("utf-8"),
            headers=self.request_headers(),
            method="POST",
        )
        last_error: JudgeRunError | None = None
        call_usage = self.empty_usage()
        for attempt in range(self.retries + 1):
            try:
                self._reserve_request()
                with self.opener(request, timeout=self.timeout_seconds) as stream:
                    response = json.loads(stream.read().decode("utf-8"))
                response_usage = self.parse_usage(response)
                with self._state_lock:
                    for key, value in response_usage.items():
                        call_usage[key] += value
                        self.total_usage[key] += value
                content = self.extract_content(response)
                model_payload = json.loads(content)
                evaluation = _without_nulls(model_payload["evaluation"])
                result = {
                    "schema_version": 1,
                    "case_id": case["id"],
                    "judge": {
                        "profile": self.profile,
                        "model": self.model_id,
                        "prompt_revision": self.prompt_revision,
                        "calibration_revision": case.get("pack_revision", "multilingual-48-v1"),
                    },
                    "evaluation": evaluation,
                }
                validate_payload(result, "judge-result.schema.json")
                return result, call_usage
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable:
                    raise JudgeRunError(
                        f"{self.provider_label} HTTP failure: status {exc.code}"
                    ) from exc
                last_error = JudgeRunError(f"{self.provider_label} HTTP failure: status {exc.code}")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = JudgeRunError(
                    f"{self.provider_label} returned malformed data: {type(exc).__name__}"
                )
            except (KeyError, IndexError, TypeError):
                last_error = JudgeRunError(
                    f"{self.provider_label} returned empty or malformed JSON content."
                )
            except DocumentValidationError as exc:
                last_error = JudgeRunError(
                    f"{self.provider_label} JSON failed judge schema: {'; '.join(exc.issues)}"
                )
            except JudgeRunError:
                raise
            if attempt == self.retries:
                assert last_error is not None
                raise last_error
            self.sleeper(float(2**attempt))

        raise AssertionError("unreachable")  # pragma: no cover


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
        prior = float(prior_run.get("exact_cost_usd", 0.0))
        return {
            "pricing_usd_per_million_tokens": XAI_PRICING_USD_PER_MILLION,
            "estimated_cost_usd": estimated,
            "exact_cost_usd": current,
            "prior_exact_cost_usd": prior,
            "cumulative_exact_cost_usd": round(prior + current, 10),
            "cost_source": "api_ticks" if exact else "token_estimate",
        }


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


def run_judge_pack(
    input_path: Path,
    output_path: Path,
    judge: DeepSeekJudge,
    *,
    limit: int | None = None,
    case_ids: list[str] | None = None,
    max_calls: int = 100,
    workers: int = 1,
    resume_from: Path | None = None,
) -> dict[str, Any]:
    """Run base cases plus ACES A/B swaps, recording failures without hiding them."""
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

    prior_run: dict[str, Any] = {}
    reused_result_count = 0
    if resume_from is not None:
        prior = load_calibration_fixture(resume_from)
        prior_run = prior.get("run") or {}
        expected = {
            "model": judge.model_id,
            "profile": judge.profile,
            "prompt_revision": judge.prompt_revision,
            "max_tokens": judge.max_tokens,
            "reasoning_effort": judge.reasoning_effort,
        }
        mismatches = [key for key, value in expected.items() if prior_run.get(key) != value]
        if mismatches:
            raise JudgeRunError(
                "Resume artifact has incompatible judge configuration: " + ", ".join(mismatches)
            )
        prior_cases = {case["id"]: case for case in prior["cases"]}
        for case in cases:
            prior_case = prior_cases.get(case["id"], {})
            for field in ("judge_output", "swap_judge_output"):
                if field in prior_case and _valid_prior_output(prior_case[field], case["id"]):
                    case[field] = deepcopy(prior_case[field])
                    reused_result_count += 1

    budget_setter = getattr(judge, "set_request_limit", None)
    if callable(budget_setter):
        budget_setter(max_calls)
    starting_usage = deepcopy(getattr(judge, "total_usage", None))

    totals = judge.empty_usage()
    tasks: list[tuple[int, str, dict[str, Any]]] = []
    for case_index, case in enumerate(cases):
        case["pack_revision"] = fixture["id"]
        if "judge_output" not in case:
            tasks.append((case_index, "judge_output", case))
        wants_swap = case.get("origin_suite") == "aces" or case.get("ab_swap") is True
        if wants_swap and "swap_judge_output" not in case:
            tasks.append((case_index, "swap_judge_output", _swapped_case(case)))

    planned_calls = len(tasks)
    if planned_calls > max_calls:
        raise JudgeRunError(f"Planned {planned_calls} calls exceeds max_calls={max_calls}.")

    failures = 0

    def execute(task: tuple[int, str, dict[str, Any]]) -> tuple[int, str, Any, Any]:
        case_index, field, evaluation_case = task
        try:
            output, usage = judge.evaluate(evaluation_case)
            return case_index, field, output, usage
        except JudgeRunError as exc:
            failure = {"benchmark_failure": {"kind": "judge_call_failure", "detail": str(exc)}}
            return case_index, field, failure, None

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(execute, task) for task in tasks]
        for future in as_completed(futures):
            case_index, field, output, usage = future.result()
            if usage is None:
                failures += 1
            else:
                for key, value in usage.items():
                    totals[key] += value
            if field == "swap_judge_output" and "case_id" in output:
                output["case_id"] = cases[case_index]["id"]
            cases[case_index][field] = output

    judge_usage = getattr(judge, "total_usage", None)
    if isinstance(judge_usage, dict) and isinstance(starting_usage, dict):
        totals = {key: judge_usage[key] - starting_usage[key] for key in totals}

    result = {
        "schema_version": 1,
        "id": f"{fixture['id']}.{judge.model_id}",
        "suite": fixture["suite"],
        "description": f"Schema-bound {judge.provider_label} calibration results; not human gold.",
        "run": {
            "provider": judge.provider,
            "model": judge.model_id,
            "profile": judge.profile,
            "prompt_revision": judge.prompt_revision,
            "thinking": judge.thinking,
            "reasoning_effort": judge.reasoning_effort,
            "max_tokens": judge.max_tokens,
            "workers": workers,
            "planned_call_count": planned_calls,
            "logical_result_count": planned_calls + reused_result_count,
            "reused_result_count": reused_result_count,
            "http_request_count": getattr(judge, "request_count", planned_calls),
            "failure_count": failures,
            "usage": totals,
            **judge.cost_fields(totals, prior_run),
            "resume_from": str(resume_from) if resume_from is not None else None,
            "reasoning_persisted": False,
            "credentials_persisted": False,
        },
        "cases": cases,
    }
    for field in ("adapter", "recipes", "policy_cases", "repair_over_editing"):
        if field in fixture:
            result[field] = deepcopy(fixture[field])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


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
        "xai": ("XAI_API_KEY", XAIJudge),
        "google": ("GEMINI_API_KEY", GoogleGemmaJudge),
    }
    try:
        credential_name, client_type = clients[provider]
    except KeyError as exc:
        raise JudgeRunError(f"Unsupported judge provider: {provider}") from exc
    api_key = os.environ.get(credential_name, "") or _project_env_value(env_path, credential_name)
    return client_type(api_key)

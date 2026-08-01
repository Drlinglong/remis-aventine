"""Read-only conversion of Remis translation benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from remis_aventine.validation import validate_payload

ADAPTER_REVISION = "remis-translation-quality-v3"

_PRIVATE_FIELD_NAMES = frozenset(
    {
        "api_base",
        "api_base_url",
        "api_endpoint",
        "api_key",
        "api_key_env",
        "api_token",
        "auth",
        "auth_header",
        "authorization",
        "base_url",
        "client_secret",
        "credential",
        "credential_name",
        "credentials",
        "endpoint",
        "headers",
        "password",
        "raw_response",
        "request_headers",
        "response_headers",
        "response_raw",
        "secret",
        "token",
    }
)
_PRIVATE_FIELD_SUFFIXES = (
    "_access_token",
    "_api_key",
    "_api_token",
    "_auth_token",
    "_base_url",
    "_bearer_token",
    "_client_secret",
    "_endpoint",
    "_id_token",
    "_password",
    "_raw_response",
    "_refresh_token",
    "_secret",
    "_secret_token",
    "_session_token",
)
_DROPPED = object()


class RemisCompatibilityError(ValueError):
    """Raised when a Remis artifact cannot be converted safely."""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def _is_private_field(key: object) -> bool:
    if not isinstance(key, str):
        return False
    camel_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    normalized = re.sub(r"[^a-z0-9]+", "_", camel_case.lower()).strip("_")
    return normalized in _PRIVATE_FIELD_NAMES or normalized.endswith(_PRIVATE_FIELD_SUFFIXES)


def _public_value(value: Any) -> Any:
    """Copy JSON-compatible evidence without provider secrets or transport details."""
    public_value = _public_value_or_dropped(value)
    return {} if public_value is _DROPPED else public_value


def _public_value_or_dropped(value: Any) -> Any:
    if isinstance(value, dict):
        public: dict[Any, Any] = {}
        for key, nested in value.items():
            if _is_private_field(key):
                continue
            public_nested = _public_value_or_dropped(nested)
            if public_nested is not _DROPPED:
                public[key] = public_nested
        return _DROPPED if value and not public else public
    if isinstance(value, list):
        public_list = [
            public_item
            for item in value
            if (public_item := _public_value_or_dropped(item)) is not _DROPPED
        ]
        return public_list
    return value


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_string(document: dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RemisCompatibilityError(f"Remis artifact requires a non-empty {key!r}.")
    return value


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RemisCompatibilityError(f"Invalid Remis created_at_utc: {value!r}.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _status(result: dict[str, Any]) -> str:
    if result.get("execution_failure"):
        return "execution_failure"
    score = result.get("score")
    if not isinstance(score, dict):
        return "structured_output_failure"
    if score.get("parsed") is not True or score.get("item_count_match") is not True:
        return "structured_output_failure"
    return "completed"


def _findings(score: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    items = score.get("items", [])
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            validations = item.get("validation", [])
            if isinstance(validations, list):
                for validation in validations:
                    finding = {"source": "remis_validation", "key": key}
                    if isinstance(validation, dict):
                        finding.update(_public_value(validation))
                    else:
                        finding["detail"] = str(validation)
                    findings.append(finding)
            parity = item.get("token_parity")
            if isinstance(parity, dict) and parity.get("passed") is False:
                findings.append(
                    {
                        "source": "remis_token_parity",
                        "key": key,
                        "missing": _public_value(parity.get("missing", [])),
                        "extra": _public_value(parity.get("extra", [])),
                    }
                )
    if score.get("hard_pass") is False and not findings:
        findings.append(
            {
                "source": "remis_hard_validation",
                "code": "hard_validation_failed_without_structured_finding",
            }
        )
    return findings


def _automatic_metrics(result: dict[str, Any]) -> dict[str, Any]:
    score = result.get("score")
    metrics = {
        "elapsed_seconds": result.get("elapsed_seconds"),
    }
    if not isinstance(score, dict):
        return metrics
    for key, value in score.items():
        if key != "items" and not _is_private_field(key):
            metrics[key] = _public_value(value)
    return metrics


def _source_inputs(score: dict[str, Any]) -> list[Any]:
    items = score.get("items")
    if not isinstance(items, list):
        return []
    return [_public_value(item.get("source")) for item in items if isinstance(item, dict)]


def _repair_evidence(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("track") != "repair":
        return None
    return {
        "injected_errors": _public_value(result.get("injected_errors", [])),
        "broken_translation": _public_value(result.get("broken_translation")),
        "reference_translation": _public_value(result.get("reference_translation")),
        "broken_validation": _public_value(result.get("broken_validation")),
    }


def _convert_case(result: dict[str, Any]) -> dict[str, Any]:
    case_id = _required_string(result, "id")
    status = _status(result)
    score = result.get("score") if isinstance(result.get("score"), dict) else {}
    passed = score.get("hard_pass") if status == "completed" else None
    converted = {
        "id": case_id,
        "execution_status": status,
        "hard_validation": {
            "enabled": True,
            "passed": passed if isinstance(passed, bool) else None,
            "findings": _findings(score),
        },
        "automatic_metrics": _automatic_metrics(result),
        "judge": None,
        "track": _public_value(result.get("track")),
        "source_metadata": _public_value(
            {
                "source_file": result.get("source_file"),
                "source_sha256": result.get("source_sha256"),
                "prompt_sha256": result.get("prompt_sha256"),
                "source_language": result.get("source_lang"),
                "target_language": result.get("target_lang"),
                "focus": result.get("focus", []),
            }
        ),
        "candidate_outputs": _public_value(result.get("outputs")),
        "source_inputs": _source_inputs(score),
        "usage": _public_value(result.get("usage")),
        "response_model": _public_value(result.get("response_model")),
    }
    repair_evidence = _repair_evidence(result)
    if repair_evidence is not None:
        converted["repair_evidence"] = repair_evidence
    return converted


def convert_remis_result(
    document: dict[str, Any], *, recipe_id: str | None = None
) -> dict[str, Any]:
    """Convert one Remis benchmark JSON object into an Aventine run result."""
    if not isinstance(document, dict):
        raise RemisCompatibilityError("Remis artifact must be a JSON object.")
    if document.get("schema_version") != 1:
        raise RemisCompatibilityError("Only Remis benchmark schema_version 1 is supported.")
    results = document.get("results")
    if not isinstance(results, list):
        raise RemisCompatibilityError("Remis artifact results must be an array.")

    provider = _required_string(document, "provider")
    model_id = _required_string(document, "model_id")
    model_label = _required_string(document, "model_label")
    track = _required_string(document, "track")
    benchmark = _required_string(document, "benchmark")
    fixture_sha256 = _required_string(document, "fixture_sha256")
    finished = _timestamp(_required_string(document, "created_at_utc"))
    source_summary = document.get("summary")
    if not isinstance(source_summary, dict):
        raise RemisCompatibilityError("Remis artifact summary must be an object.")
    request_profile = document.get("request_profile", {})
    if not isinstance(request_profile, dict):
        raise RemisCompatibilityError("Remis artifact request_profile must be an object.")
    elapsed_seconds = source_summary.get("elapsed_seconds", 0)
    if not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
        raise RemisCompatibilityError("Remis summary elapsed_seconds must be non-negative.")
    started = finished - timedelta(seconds=float(elapsed_seconds))

    prompt_hashes = sorted(
        {
            value
            for result in results
            if isinstance(result, dict)
            and isinstance((value := result.get("prompt_sha256")), str)
            and value
        }
    )
    recipe_snapshot = {
        "adapter_revision": ADAPTER_REVISION,
        "provider": provider,
        "model_id": model_id,
        "model_label": model_label,
        "track": track,
        "prompt_sha256": prompt_hashes,
        "fixture_sha256": fixture_sha256,
        "policy": _public_value(document.get("policy", {})),
        "request_profile": _public_value(request_profile),
    }
    resolved_recipe_id = recipe_id or f"remis.{_slug(provider)}.{_slug(model_id)}.{_slug(track)}"
    converted_cases = [_convert_case(result) for result in results if isinstance(result, dict)]
    if len(converted_cases) != len(results):
        raise RemisCompatibilityError("Every Remis result entry must be an object.")
    status_counts = {
        status: sum(case["execution_status"] == status for case in converted_cases)
        for status in ("completed", "execution_failure", "structured_output_failure")
    }

    converted = {
        "schema_version": 1,
        "run_id": f"remis-{finished.strftime('%Y%m%dT%H%M%SZ')}-{_slug(model_label)}",
        "suite": "remis",
        "recipe": {
            "id": resolved_recipe_id,
            "sha256": _canonical_sha256(recipe_snapshot),
            "provenance": "compatibility_snapshot",
            "snapshot": recipe_snapshot,
        },
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": finished.isoformat().replace("+00:00", "Z"),
        "environment": {
            "source_format": "remis_translation_quality_benchmark_v1",
            "adapter_revision": ADAPTER_REVISION,
            "benchmark": benchmark,
            "fixture_sha256": fixture_sha256,
            "provider": provider,
            "model_id": model_id,
            "model_label": model_label,
            "track": track,
        },
        "cases": converted_cases,
        "summary": {
            "case_count": len(converted_cases),
            "completed_count": status_counts["completed"],
            "execution_failure_count": status_counts["execution_failure"],
            "structured_output_failure_count": status_counts["structured_output_failure"],
            "hard_pass_count": sum(
                case["hard_validation"]["passed"] is True for case in converted_cases
            ),
            "elapsed_seconds": float(elapsed_seconds),
            "source_summary": _public_value(source_summary),
        },
    }
    return validate_payload(converted, "run-result.schema.json")


def adapt_remis_result(
    input_path: Path, output_path: Path, *, recipe_id: str | None = None
) -> dict[str, Any]:
    """Read, convert, validate, and write one Remis benchmark artifact."""
    try:
        source = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RemisCompatibilityError(
            f"Invalid Remis JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    converted = convert_remis_result(source, recipe_id=recipe_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return converted

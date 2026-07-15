"""Adapter from mt-metrics-eval MQM ratings to bounded Aventine judge packs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any

ADAPTER_REVISION = "mtme-mqm-v1"
SEVERITY_ORDER = ("critical", "major", "minor", "none")
SEVERITY_RANK = {severity: rank for rank, severity in enumerate(reversed(SEVERITY_ORDER))}


class MTMetricsEvalAdapterError(ValueError):
    """Raised when an EvalSet cannot be converted without guessing."""


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    aliases = {"": "none", "no-error": "none", "neutral": "none"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SEVERITY_RANK:
        raise MTMetricsEvalAdapterError(f"Unsupported MQM severity: {value!r}")
    return normalized


def _normalize_category(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    for category in ("accuracy", "terminology", "fluency", "style", "locale"):
        if normalized.startswith(category):
            return category
    if normalized in {"", "no-error"}:
        return "none"
    return "other"


def _error_payload(error: Any) -> dict[str, Any]:
    return {
        "start": _field(error, "start"),
        "end": _field(error, "end"),
        "category": _field(error, "category"),
        "severity": _field(error, "severity"),
        "score": _field(error, "score"),
        "is_source_error": bool(_field(error, "is_source_error", False)),
    }


def _gold(errors: list[Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    serialized = [_error_payload(error) for error in errors]
    if not serialized:
        return {
            "mode": "single",
            "verdict": "pass",
            "max_severity": "none",
            "primary_category": "none",
            "phenomenon": "no-error",
        }, serialized

    severities = [_normalize_severity(error["severity"]) for error in serialized]
    max_severity = max(severities, key=SEVERITY_RANK.__getitem__)
    primary_index = severities.index(max_severity)
    raw_category = serialized[primary_index]["category"]
    category = _normalize_category(raw_category)
    phenomenon = str(raw_category or "other").strip().lower().replace("/", ".")
    return {
        "mode": "single",
        "verdict": "fail",
        "max_severity": max_severity,
        "primary_category": category,
        "phenomenon": phenomenon,
    }, serialized


def _load_evalset(
    test_set: str,
    language_pair: str,
    data_root: Path | None,
) -> Any:
    try:
        from mt_metrics_eval.data import EvalSet
    except ImportError as exc:
        raise MTMetricsEvalAdapterError(
            "mt-metrics-eval is not installed; install the official Google Research checkout "
            "and download its data separately before using this adapter."
        ) from exc

    kwargs: dict[str, Any] = {
        "read_stored_metric_scores": False,
        "read_stored_ratings": True,
    }
    if data_root is not None:
        kwargs["path"] = str(data_root)
    try:
        return EvalSet(test_set, language_pair, **kwargs)
    except (AssertionError, OSError, ValueError) as exc:
        raise MTMetricsEvalAdapterError(
            f"Could not load mt-metrics-eval EvalSet {test_set}/{language_pair}: {exc}"
        ) from exc


def _library_version() -> str:
    try:
        return metadata.version("mt-metrics-eval")
    except metadata.PackageNotFoundError:
        return "unknown"


def _select_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    buckets = {
        severity: sorted(
            (record for record in records if record["gold"]["max_severity"] == severity),
            key=lambda record: record["digest"],
        )
        for severity in SEVERITY_ORDER
    }
    selected: list[dict[str, Any]] = []
    while len(selected) < limit and any(buckets.values()):
        for severity in SEVERITY_ORDER:
            if buckets[severity] and len(selected) < limit:
                selected.append(buckets[severity].pop(0))
    return selected


def build_mtme_mqm_pack(
    test_set: str,
    language_pair: str,
    rating_set: str,
    dataset_revision: str,
    output_path: Path,
    *,
    data_root: Path | None = None,
    limit: int = 50,
    systems: list[str] | None = None,
    evalset_factory: Callable[[str, str, Path | None], Any] | None = None,
    library_version: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, bounded MQM pack from an already-downloaded EvalSet."""
    for label, value in (
        ("test_set", test_set),
        ("language_pair", language_pair),
        ("rating_set", rating_set),
        ("dataset_revision", dataset_revision),
    ):
        if not value.strip():
            raise MTMetricsEvalAdapterError(f"{label} must be non-empty.")
    if limit <= 0:
        raise MTMetricsEvalAdapterError("limit must be greater than zero.")

    loader = evalset_factory or _load_evalset
    evalset = loader(test_set, language_pair, data_root)
    available_ratings = sorted(str(name) for name in evalset.rating_names)
    if rating_set not in available_ratings:
        available = ", ".join(available_ratings) or "none"
        raise MTMetricsEvalAdapterError(
            f"Unknown rating set {rating_set!r}; available: {available}"
        )
    ratings = evalset.Ratings(rating_set)
    if not isinstance(ratings, dict):
        raise MTMetricsEvalAdapterError(f"Rating set {rating_set!r} did not return system ratings.")
    try:
        rater_ids = evalset.RaterIdsPerSeg(rating_set)
    except (AttributeError, KeyError, TypeError) as exc:
        raise MTMetricsEvalAdapterError(
            f"Rating set {rating_set!r} is missing rater provenance."
        ) from exc
    if not isinstance(rater_ids, dict):
        raise MTMetricsEvalAdapterError(
            f"Rating set {rating_set!r} did not return rater provenance."
        )

    selected_systems = sorted(set(systems) if systems else ratings)
    unknown_systems = sorted(set(selected_systems) - set(ratings))
    if unknown_systems:
        raise MTMetricsEvalAdapterError(
            f"Rating set {rating_set!r} has no systems: {', '.join(unknown_systems)}"
        )

    try:
        references = evalset.all_refs[evalset.std_ref]
        docs = evalset.DocsPerSeg()
        domains = evalset.DomainsPerSeg()
    except (AttributeError, KeyError, TypeError) as exc:
        raise MTMetricsEvalAdapterError(
            "EvalSet is missing source/reference/document metadata."
        ) from exc

    segment_count = len(evalset.src)
    if not (len(references) == len(docs) == len(domains) == segment_count):
        raise MTMetricsEvalAdapterError("EvalSet source/reference/document lengths do not match.")

    records: list[dict[str, Any]] = []
    for system in selected_systems:
        system_ratings = ratings[system]
        system_raters = rater_ids.get(system)
        if system_raters is None:
            raise MTMetricsEvalAdapterError(
                f"Rating set {rating_set!r} has no rater provenance for system {system!r}."
            )
        outputs = evalset.sys_outputs.get(system)
        if outputs is None:
            raise MTMetricsEvalAdapterError(
                f"EvalSet has ratings but no output for system {system!r}."
            )
        if not (len(system_ratings) == len(system_raters) == len(outputs) == segment_count):
            raise MTMetricsEvalAdapterError(f"Segment length mismatch for system {system!r}.")
        for index, rating in enumerate(system_ratings):
            if rating is None:
                continue
            errors = _field(rating, "errors")
            if not isinstance(errors, list):
                raise MTMetricsEvalAdapterError(
                    f"Rating errors must be a list for {system!r} segment {index}."
                )
            gold, serialized_errors = _gold(errors)
            identity = {
                "test_set": test_set,
                "language_pair": language_pair,
                "rating_set": rating_set,
                "system": system,
                "segment_index": index,
                "source": evalset.src[index],
                "candidate": outputs[index],
                "reference": references[index],
                "errors": serialized_errors,
            }
            digest = _stable_digest(identity)
            records.append(
                {
                    "digest": digest,
                    "gold": gold,
                    "case": {
                        "id": f"mtme-{test_set}-{language_pair}-{digest[:12]}",
                        "origin_suite": "mqm",
                        "input": {
                            "language_pair": language_pair,
                            "source": evalset.src[index],
                            "reference": references[index],
                            "candidate": outputs[index],
                        },
                        "gold": gold,
                        "provenance": {
                            "source_id": "mt-metrics-eval",
                            "dataset_revision": dataset_revision,
                            "test_set": test_set,
                            "rating_set": rating_set,
                            "system": system,
                            "rater": system_raters[index],
                            "segment_index": index,
                            "document": docs[index],
                            "domain": domains[index],
                            "source_key_sha256": digest,
                            "mqm_errors": serialized_errors,
                        },
                    },
                }
            )

    if not records:
        raise MTMetricsEvalAdapterError(
            f"Rating set {rating_set!r} contains no rated segments for the selected systems."
        )
    chosen = _select_records(records, min(limit, len(records)))
    cases = [record["case"] for record in chosen]
    content_sha256 = _stable_digest(cases)
    pack = {
        "schema_version": 1,
        "id": f"mtme-mqm.{test_set}.{language_pair}.{rating_set}.{content_sha256[:12]}",
        "suite": "mqm",
        "description": "Bounded MQM cases adapted from mt-metrics-eval; human ratings are gold.",
        "adapter": {
            "name": "mt-metrics-eval-mqm",
            "revision": ADAPTER_REVISION,
            "library_version": library_version or _library_version(),
            "dataset_revision": dataset_revision,
            "test_set": test_set,
            "language_pair": language_pair,
            "rating_set": rating_set,
            "standard_reference": evalset.std_ref,
            "systems": selected_systems,
            "available_rated_case_count": len(records),
            "selected_case_count": len(cases),
            "selection_algorithm": "severity-round-robin-sha256-v1",
            "content_sha256": content_sha256,
        },
        "cases": cases,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return pack

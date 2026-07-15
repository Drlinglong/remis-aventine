"""Bounded ACES and SPAN-ACES adapters for calibrated pairwise judging."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ADAPTER_REVISION = "aces-span-v1"
DATASET_KINDS = {"aces", "span-aces"}
BASE_FIELDS = (
    "source",
    "good-translation",
    "incorrect-translation",
    "reference",
    "phenomena",
    "langpair",
)
SPAN_FIELDS = ("ID", "incorrect-translation-annotated", "annotation-method")
_SPAN_TAG = re.compile(r"</?v>")


class ACESAdapterError(ValueError):
    """Raised when ACES data cannot be converted without guessing."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_annotated_translation(value: str) -> tuple[str, list[dict[str, Any]]]:
    clean_parts: list[str] = []
    spans: list[dict[str, Any]] = []
    cursor = 0
    clean_length = 0
    span_start: int | None = None
    for match in _SPAN_TAG.finditer(value):
        text = value[cursor : match.start()]
        clean_parts.append(text)
        clean_length += len(text)
        if match.group() == "<v>":
            if span_start is not None:
                raise ACESAdapterError("SPAN-ACES contains nested <v> markers.")
            span_start = clean_length
        else:
            if span_start is None:
                raise ACESAdapterError("SPAN-ACES contains an unmatched </v> marker.")
            clean = "".join(clean_parts)
            spans.append(
                {
                    "start": span_start,
                    "end": clean_length,
                    "text": clean[span_start:clean_length],
                }
            )
            span_start = None
        cursor = match.end()
    tail = value[cursor:]
    clean_parts.append(tail)
    if span_start is not None:
        raise ACESAdapterError("SPAN-ACES contains an unmatched <v> marker.")
    return "".join(clean_parts), spans


def _validate_row(row: Any, line_number: int, dataset_kind: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ACESAdapterError(f"ACES line {line_number} must be a JSON object.")
    required = BASE_FIELDS + (SPAN_FIELDS if dataset_kind == "span-aces" else ())
    missing = [field for field in required if field not in row]
    if missing:
        raise ACESAdapterError(f"ACES line {line_number} is missing fields: {', '.join(missing)}")
    for field in BASE_FIELDS:
        if not isinstance(row[field], str) or not row[field]:
            raise ACESAdapterError(
                f"ACES line {line_number} field {field!r} must be a non-empty string."
            )
    if dataset_kind == "span-aces":
        for field in ("incorrect-translation-annotated", "annotation-method"):
            if not isinstance(row[field], str) or not row[field]:
                raise ACESAdapterError(
                    f"ACES line {line_number} field {field!r} must be a non-empty string."
                )
    return row


def _read_records(
    source_path: Path,
    dataset_kind: str,
    language_pairs: set[str] | None,
    phenomena: set[str] | None,
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    total_rows = 0
    try:
        stream = source_path.open(encoding="utf-8")
    except OSError as exc:
        raise ACESAdapterError(f"Could not open ACES source: {source_path}") from exc
    with stream:
        for line_number, line in enumerate(stream, start=1):
            total_rows += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ACESAdapterError(
                    f"Invalid ACES JSON on line {line_number}: {exc.msg}"
                ) from exc
            row = _validate_row(row, line_number, dataset_kind)
            if language_pairs is not None and row["langpair"] not in language_pairs:
                continue
            if phenomena is not None and row["phenomena"] not in phenomena:
                continue
            digest = _stable_digest(row)
            records.append({"row": row, "digest": digest, "line_number": line_number})
    return records, total_rows


def _select_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        row = record["row"]
        groups[(row["langpair"], row["phenomena"])].append(record)
    for group in groups.values():
        group.sort(key=lambda record: record["digest"])

    group_order = sorted(groups, key=lambda key: _stable_digest(key))
    selected: list[dict[str, Any]] = []
    while len(selected) < limit and any(groups.values()):
        for key in group_order:
            if groups[key] and len(selected) < limit:
                selected.append(groups[key].pop(0))
    return selected


def _case(record: dict[str, Any], dataset_kind: str, dataset_revision: str) -> dict[str, Any]:
    row = record["row"]
    digest = record["digest"]
    good_is_a = int(digest, 16) % 2 == 0
    good = row["good-translation"]
    incorrect = row["incorrect-translation"]
    incorrect_candidate = "candidate_b" if good_is_a else "candidate_a"
    gold: dict[str, Any] = {
        "mode": "pairwise",
        "verdict": "candidate_a" if good_is_a else "candidate_b",
        "max_severity": "major",
        "primary_category": "accuracy",
        "phenomenon": row["phenomena"],
    }
    provenance: dict[str, Any] = {
        "source_id": dataset_kind,
        "dataset_revision": dataset_revision,
        "source_line": record["line_number"],
        "source_key_sha256": digest,
    }
    if dataset_kind == "span-aces":
        annotated = row["incorrect-translation-annotated"]
        span_text, spans = _parse_annotated_translation(annotated)
        gold["span_annotation"] = {
            "incorrect_candidate": incorrect_candidate,
            "annotated_translation": annotated,
            "annotation_method": row["annotation-method"],
            "text_without_markers": span_text,
            "spans": spans,
            "aligned_to_incorrect_translation": span_text == incorrect,
        }
        provenance["upstream_id"] = row["ID"]

    return {
        "id": f"{dataset_kind}-{row['langpair']}-{digest[:12]}",
        "origin_suite": "aces",
        "input": {
            "language_pair": row["langpair"],
            "source": row["source"],
            "reference": row["reference"],
            "candidate_a": good if good_is_a else incorrect,
            "candidate_b": incorrect if good_is_a else good,
        },
        "gold": gold,
        "provenance": provenance,
    }


def build_aces_pack(
    source_path: Path,
    output_path: Path,
    dataset_kind: str,
    dataset_revision: str,
    expected_sha256: str,
    *,
    limit: int = 50,
    language_pairs: list[str] | None = None,
    phenomena: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, bounded ACES or SPAN-ACES pairwise judge pack."""
    if dataset_kind not in DATASET_KINDS:
        raise ACESAdapterError(f"Unsupported ACES dataset kind: {dataset_kind!r}")
    if not dataset_revision.strip():
        raise ACESAdapterError("dataset_revision must be non-empty.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ACESAdapterError("expected_sha256 must contain exactly 64 hexadecimal characters.")
    if limit <= 0:
        raise ACESAdapterError("limit must be greater than zero.")
    actual_sha256 = _sha256(source_path)
    if actual_sha256.lower() != expected_sha256.lower():
        raise ACESAdapterError(
            f"ACES SHA-256 mismatch: expected {expected_sha256.lower()}, received {actual_sha256}"
        )

    pair_filter = set(language_pairs) if language_pairs else None
    phenomenon_filter = set(phenomena) if phenomena else None
    records, total_rows = _read_records(source_path, dataset_kind, pair_filter, phenomenon_filter)
    if not records:
        raise ACESAdapterError("No ACES rows match the selected filters.")
    chosen = _select_records(records, min(limit, len(records)))
    cases = [_case(record, dataset_kind, dataset_revision) for record in chosen]
    content_sha256 = _stable_digest(cases)
    pack = {
        "schema_version": 1,
        "id": f"{dataset_kind}.{dataset_revision}.{content_sha256[:12]}",
        "suite": "aces",
        "description": (
            f"Bounded {dataset_kind} contrastive cases; the preferred candidate is upstream gold."
        ),
        "adapter": {
            "name": "aces-span-aces",
            "revision": ADAPTER_REVISION,
            "dataset_kind": dataset_kind,
            "dataset_revision": dataset_revision,
            "source_sha256": actual_sha256,
            "source_row_count": total_rows,
            "matching_row_count": len(records),
            "selected_case_count": len(cases),
            "language_pair_filters": sorted(pair_filter) if pair_filter else [],
            "phenomenon_filters": sorted(phenomenon_filter) if phenomenon_filter else [],
            "selection_algorithm": "language-pair-phenomenon-round-robin-sha256-v1",
            "candidate_order_algorithm": "source-row-sha256-parity-v1",
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

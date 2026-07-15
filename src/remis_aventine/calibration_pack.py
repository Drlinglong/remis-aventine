"""Build a small, reproducible calibration pack from external MQM and ACES data."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

PACK_REVISION = "multilingual-48-v1"

SOURCE_FILES = {
    "aces": {
        "relative_path": Path("aces/challenge_set.jsonl"),
        "sha256": "f4dc0df4f8ade8e94adf691f78f3cba62a266515aded09f1e53e433943c1dd93",
        "url": "https://huggingface.co/datasets/nikitam/ACES/resolve/main/data/challenge_set.jsonl",
        "license": "CC-BY-NC-SA-4.0",
    },
    "mqm-ende": {
        "relative_path": Path("wmt-mqm-human-evaluation/mqm_generalMT2022_ende.tsv"),
        "sha256": "82acffc68ab61a5efeb98f7e09fec45bf49d9aaafba72c9b4cf378b7ec5dee85",
        "url": "https://raw.githubusercontent.com/google/wmt-mqm-human-evaluation/main/generalMT2022/ende/mqm_generalMT2022_ende.tsv",
        "license": "Apache-2.0",
    },
    "mqm-zhen": {
        "relative_path": Path("wmt-mqm-human-evaluation/mqm_generalMT2022_zhen.tsv"),
        "sha256": "f7905f799c47a9a2510996dac62d1fa9ce0a5d74e772bfff4029febd58f5cad0",
        "url": "https://raw.githubusercontent.com/google/wmt-mqm-human-evaluation/main/generalMT2022/zhen/mqm_generalMT2022_zhen.tsv",
        "license": "Apache-2.0",
    },
    "mqm-enru": {
        "relative_path": Path("wmt-mqm-human-evaluation/mqm_generalMT2022_enru.tsv"),
        "sha256": "3f50f6f0356c4b2624cf5ccd5982268b9c1afbbb229e045f5b13f2fd886b00b8",
        "url": "https://raw.githubusercontent.com/google/wmt-mqm-human-evaluation/main/generalMT2022/enru/mqm_generalMT2022_enru.tsv",
        "license": "Apache-2.0",
    },
}

MQM_SLOTS = {
    "ende": [("none", None), ("minor", None), ("major", "accuracy"), ("major", None)],
    "zhen": [("none", None), ("minor", None), ("major", "accuracy"), ("major", None)],
    "enru": [("none", None), ("minor", None), ("major", None), ("critical", None)],
}

ACES_SLOTS = {
    "en-es": ["addition", "omission", "hallucination-number-level-3"],
    "es-fr": [
        "lexical-overlap",
        "hallucination-named-entity-level-3",
        "hallucination-number-level-3",
    ],
    "fr-ru": [
        "commonsense-only-ref-ambiguous",
        "commonsense-src-and-ref-ambiguous",
        "commonsense-only-ref-ambiguous",
    ],
    "ru-de": [
        "commonsense-only-ref-ambiguous",
        "commonsense-src-and-ref-ambiguous",
        "commonsense-src-and-ref-ambiguous",
    ],
    "de-ja": [
        "lexical-overlap",
        "hallucination-named-entity-level-2",
        "hallucination-number-level-3",
    ],
    "ja-ko": ["copy-source", "hallucination-named-entity-level-3", "hallucination-number-level-3"],
    "ko-zh": [
        "hallucination-named-entity-level-1",
        "hallucination-number-level-2",
        "hallucination-named-entity-level-3",
    ],
    "zh-en": ["antonym-replacement", "xnli-omission-contradiction", "xnli-addition-contradiction"],
}


class CalibrationPackError(ValueError):
    """Raised when upstream data cannot reproduce the declared pack."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_key(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_source_cache(source_root: Path) -> dict[str, dict[str, Any]]:
    """Verify every external source before any row is selected."""
    verified: dict[str, dict[str, Any]] = {}
    for source_id, metadata in SOURCE_FILES.items():
        path = source_root / metadata["relative_path"]
        if not path.is_file():
            raise CalibrationPackError(f"Missing external source: {path}")
        actual = _sha256(path)
        if actual != metadata["sha256"]:
            raise CalibrationPackError(
                f"SHA-256 mismatch for {source_id}: expected "
                f"{metadata['sha256']}, received {actual}"
            )
        verified[source_id] = {
            "path": str(path),
            "sha256": actual,
            "url": metadata["url"],
            "license": metadata["license"],
        }
    return verified


def _severity(rows: list[dict[str, str]]) -> str:
    values = {(row.get("severity") or "").strip().lower() for row in rows}
    for severity in ("critical", "major", "minor"):
        if severity in values:
            return severity
    return "none"


def _category(raw: str | None) -> str:
    category = (raw or "").strip().lower()
    for prefix in ("accuracy", "terminology", "fluency", "style", "locale"):
        if category.startswith(prefix):
            return prefix
    if category in {"mistranslation", "omission", "addition", "wrong_named_entity"}:
        return "accuracy"
    if category in {"grammar", "agreement", "punctuation", "word_order", "unnatural_flow"}:
        return "fluency"
    return "none" if category in {"", "no-error"} else "other"


def _read_mqm(path: Path) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            key = tuple(
                row.get(name, "")
                for name in ("system", "doc_id", "seg_id", "rater", "source", "target")
            )
            groups[key].append(row)

    records = []
    for key, rows in groups.items():
        severity = _severity(rows)
        severe_rows = [row for row in rows if (row.get("severity") or "").lower() == severity]
        primary_raw = (severe_rows or rows)[0].get("category")
        records.append(
            {
                "key": key,
                "source": key[4],
                "target": key[5],
                "system": key[0],
                "rater": key[3],
                "severity": severity,
                "category": _category(primary_raw),
                "phenomenon": (primary_raw or "no-error").strip().lower().replace("/", "."),
            }
        )
    return records


def _select_mqm(source_root: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    language_pairs = {"ende": "en-de", "zhen": "zh-en", "enru": "en-ru"}
    for dataset, slots in MQM_SLOTS.items():
        records = _read_mqm(source_root / SOURCE_FILES[f"mqm-{dataset}"]["relative_path"])
        used: set[str] = set()
        for slot_index, (severity, category) in enumerate(slots, start=1):
            eligible = [
                record
                for record in records
                if record["severity"] == severity
                and (category is None or record["category"] == category)
                and _stable_key(record["key"]) not in used
            ]
            if not eligible:
                raise CalibrationPackError(f"No MQM row for {dataset} {severity} {category}")
            selected = min(eligible, key=lambda record: _stable_key(record["key"]))
            source_key = _stable_key(selected["key"])
            used.add(source_key)
            case_id = f"mqm-{language_pairs[dataset]}-{slot_index:02d}-{source_key[:10]}"
            cases.append(
                {
                    "id": case_id,
                    "origin_suite": "mqm",
                    "input": {
                        "language_pair": language_pairs[dataset],
                        "source": selected["source"],
                        "candidate": selected["target"],
                    },
                    "gold": {
                        "mode": "single",
                        "verdict": "pass" if severity == "none" else "fail",
                        "max_severity": severity,
                        "primary_category": selected["category"],
                        "phenomenon": selected["phenomenon"],
                    },
                    "provenance": {
                        "source_id": f"mqm-{dataset}",
                        "source_key_sha256": source_key,
                        "system": selected["system"],
                        "rater": selected["rater"],
                    },
                }
            )
    return cases


def _select_aces(source_root: Path) -> list[dict[str, Any]]:
    wanted = {(pair, phenomenon) for pair, slots in ACES_SLOTS.items() for phenomenon in slots}
    rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    path = source_root / SOURCE_FILES["aces"]["relative_path"]
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row["langpair"], row["phenomena"])
            if key in wanted:
                rows[key].append(row)

    cases: list[dict[str, Any]] = []
    used_counts: dict[tuple[str, str], int] = defaultdict(int)
    for pair, slots in ACES_SLOTS.items():
        for slot_index, phenomenon in enumerate(slots, start=1):
            key = (pair, phenomenon)
            eligible = sorted(rows[key], key=_stable_key)
            selected_index = used_counts[key]
            used_counts[key] += 1
            if selected_index >= len(eligible):
                raise CalibrationPackError(f"Not enough ACES rows for {pair} {phenomenon}")
            selected = eligible[selected_index]
            source_key = _stable_key(selected)
            good_is_a = int(source_key, 16) % 2 == 0
            candidate_a = (
                selected["good-translation"] if good_is_a else selected["incorrect-translation"]
            )
            candidate_b = (
                selected["incorrect-translation"] if good_is_a else selected["good-translation"]
            )
            cases.append(
                {
                    "id": f"aces-{pair}-{slot_index:02d}-{source_key[:10]}",
                    "origin_suite": "aces",
                    "input": {
                        "language_pair": pair,
                        "source": selected["source"],
                        "reference": selected["reference"],
                        "candidate_a": candidate_a,
                        "candidate_b": candidate_b,
                    },
                    "gold": {
                        "mode": "pairwise",
                        "verdict": "candidate_a" if good_is_a else "candidate_b",
                        "max_severity": "major",
                        "primary_category": "accuracy",
                        "phenomenon": phenomenon,
                    },
                    "provenance": {
                        "source_id": "aces",
                        "source_key_sha256": source_key,
                    },
                }
            )
    return cases


def build_calibration_pack(
    source_root: Path, output_path: Path, remis_fixture_path: Path
) -> dict[str, Any]:
    """Create the fixed 48-case pack without committing external source text."""
    verified = verify_source_cache(source_root)
    remis = json.loads(remis_fixture_path.read_text(encoding="utf-8"))
    remis_cases = remis.get("cases")
    if not isinstance(remis_cases, list) or len(remis_cases) != 12:
        raise CalibrationPackError("The Remis calibration fixture must contain exactly 12 cases.")
    for case in remis_cases:
        case["origin_suite"] = "remis"
        case.setdefault("provenance", {"source_id": "aventine-authored"})
        case.pop("judge_output", None)

    cases = _select_mqm(source_root) + _select_aces(source_root) + remis_cases
    holdout_ids = {
        case["id"] for case in sorted(cases, key=lambda item: _stable_key(item["id"]))[:12]
    }
    for case in cases:
        case["partition"] = "holdout" if case["id"] in holdout_ids else "calibration"

    pack = {
        "schema_version": 1,
        "id": PACK_REVISION,
        "suite": "multilingual-calibration",
        "description": "12 MQM + 24 ACES + 12 Aventine-authored Remis cases.",
        "selection": {
            "algorithm": "sha256-lexicographic-v1",
            "calibration_count": 36,
            "holdout_count": 12,
            "aces_ab_swap": True,
        },
        "sources": verified,
        "cases": cases,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return pack

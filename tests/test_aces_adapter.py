from __future__ import annotations

import hashlib
import json

import pytest

from remis_aventine.adapters.aces import ACESAdapterError, build_aces_pack


def _row(index: int, pair: str, phenomenon: str, annotated: str) -> dict:
    return {
        "ID": index,
        "source": f"source {index}",
        "good-translation": f"good {index}",
        "incorrect-translation": f"bad {index}",
        "reference": f"reference {index}",
        "phenomena": phenomenon,
        "langpair": pair,
        "incorrect-translation-annotated": annotated,
        "annotation-method": "manual",
    }


def _write_jsonl(path, rows) -> str:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_span_aces_pack_is_bounded_covered_and_reproducible(tmp_path) -> None:
    source = tmp_path / "span.jsonl"
    digest = _write_jsonl(
        source,
        [
            _row(1, "en-de", "addition", "<v>bad</v> 1"),
            _row(2, "en-de", "addition", "<v>different</v> text"),
            _row(3, "ja-ko", "omission", "<v>bad</v> 3"),
            _row(4, "fr-ru", "number", "bad 4"),
        ],
    )
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = build_aces_pack(
        source,
        first_path,
        "span-aces",
        "fixture-revision",
        digest,
        limit=3,
    )
    second = build_aces_pack(
        source,
        second_path,
        "span-aces",
        "fixture-revision",
        digest,
        limit=3,
    )

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert first["adapter"]["source_row_count"] == 4
    assert first["adapter"]["matching_row_count"] == 4
    assert first["adapter"]["selection_algorithm"].startswith("language-pair-phenomenon")
    assert len(first["cases"]) == 3
    assert len({case["input"]["language_pair"] for case in first["cases"]}) == 3
    for case in first["cases"]:
        assert case["origin_suite"] == "aces"
        verdict = case["gold"]["verdict"]
        assert (
            case["input"][verdict]
            == case["input"]["candidate_a" if verdict == "candidate_a" else "candidate_b"]
        )
        assert case["input"][verdict].startswith("good")
        annotation = case["gold"]["span_annotation"]
        assert annotation["incorrect_candidate"] != verdict
        assert "annotated_translation" not in case["input"]

    aligned = next(case for case in first["cases"] if case["provenance"]["upstream_id"] == 1)
    annotation = aligned["gold"]["span_annotation"]
    assert annotation["aligned_to_incorrect_translation"] is True
    assert annotation["spans"] == [{"start": 0, "end": 3, "text": "bad"}]


def test_build_aces_pack_filters_language_and_omits_span_gold(tmp_path) -> None:
    source = tmp_path / "aces.jsonl"
    rows = [
        {
            key: value
            for key, value in _row(1, "en-de", "addition", "x").items()
            if key
            not in {
                "ID",
                "incorrect-translation-annotated",
                "annotation-method",
            }
        },
        {
            key: value
            for key, value in _row(2, "ja-ko", "omission", "x").items()
            if key
            not in {
                "ID",
                "incorrect-translation-annotated",
                "annotation-method",
            }
        },
    ]
    digest = _write_jsonl(source, rows)

    pack = build_aces_pack(
        source,
        tmp_path / "pack.json",
        "aces",
        "revision",
        digest,
        language_pairs=["ja-ko"],
    )

    assert len(pack["cases"]) == 1
    assert pack["cases"][0]["input"]["language_pair"] == "ja-ko"
    assert "span_annotation" not in pack["cases"][0]["gold"]


def test_aces_pack_rejects_hash_mismatch(tmp_path) -> None:
    source = tmp_path / "aces.jsonl"
    source.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ACESAdapterError, match="SHA-256 mismatch"):
        build_aces_pack(source, tmp_path / "out.json", "aces", "revision", "0" * 64)


@pytest.mark.parametrize("annotated", ["<v>bad", "bad</v>", "<v>a<v>b</v></v>"])
def test_span_aces_rejects_unbalanced_or_nested_markers(tmp_path, annotated) -> None:
    source = tmp_path / "span.jsonl"
    digest = _write_jsonl(source, [_row(1, "en-de", "addition", annotated)])

    with pytest.raises(ACESAdapterError, match="marker|nested"):
        build_aces_pack(
            source,
            tmp_path / "out.json",
            "span-aces",
            "revision",
            digest,
        )


def test_aces_pack_rejects_empty_filter_result(tmp_path) -> None:
    source = tmp_path / "aces.jsonl"
    row = {
        key: value
        for key, value in _row(1, "en-de", "addition", "x").items()
        if key
        not in {
            "ID",
            "incorrect-translation-annotated",
            "annotation-method",
        }
    }
    digest = _write_jsonl(source, [row])

    with pytest.raises(ACESAdapterError, match="No ACES rows"):
        build_aces_pack(
            source,
            tmp_path / "out.json",
            "aces",
            "revision",
            digest,
            phenomena=["missing"],
        )

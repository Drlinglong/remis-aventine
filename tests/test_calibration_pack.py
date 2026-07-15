from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import remis_aventine.calibration_pack as pack_module
from remis_aventine.calibration_pack import CalibrationPackError, build_calibration_pack


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_mqm(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "system\tdoc\tdoc_id\tseg_id\trater\tsource\ttarget\tcategory\tseverity\n"
        "sys\tdoc\t1\t1\tr1\tClean source\tClean target\tNo-error\tNo-error\n"
        "sys\tdoc\t1\t2\tr1\tMinor source\tMinor target\tFluency/Grammar\tminor\n"
        "sys\tdoc\t1\t3\tr1\tMajor source\tMajor target\tAccuracy/Omission\tmajor\n"
        "sys\tdoc\t1\t4\tr1\tCritical source\tCritical target\tmistranslation\tcritical\n",
        encoding="utf-8",
    )


def _write_aces(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "source": f"source {index}",
            "good-translation": f"good {index}",
            "incorrect-translation": f"bad {index}",
            "reference": f"reference {index}",
            "phenomena": phenomenon,
            "langpair": "en-es",
        }
        for index, phenomenon in enumerate(("addition", "omission", "number"), start=1)
    ]
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def _write_remis(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": f"remis-{index}",
                        "input": {"source": "x", "candidate": "y"},
                        "gold": {
                            "mode": "single",
                            "verdict": "pass",
                            "max_severity": "none",
                            "primary_category": "none",
                            "phenomenon": "clean",
                        },
                    }
                    for index in range(12)
                ]
            }
        ),
        encoding="utf-8",
    )


def test_build_calibration_pack_from_verified_sources(tmp_path, monkeypatch) -> None:
    source_root = tmp_path / "sources"
    mqm_path = source_root / "mqm.tsv"
    aces_path = source_root / "aces.jsonl"
    remis_path = tmp_path / "remis.json"
    output_path = tmp_path / "pack.json"
    _write_mqm(mqm_path)
    _write_aces(aces_path)
    _write_remis(remis_path)

    monkeypatch.setattr(
        pack_module,
        "SOURCE_FILES",
        {
            "aces": {
                "relative_path": Path("aces.jsonl"),
                "sha256": _digest(aces_path),
                "url": "https://example.test/aces",
                "license": "test",
            },
            "mqm-enru": {
                "relative_path": Path("mqm.tsv"),
                "sha256": _digest(mqm_path),
                "url": "https://example.test/mqm",
                "license": "test",
            },
        },
    )
    monkeypatch.setattr(
        pack_module,
        "MQM_SLOTS",
        {"enru": [("none", None), ("minor", None), ("major", "accuracy"), ("critical", None)]},
    )
    monkeypatch.setattr(
        pack_module,
        "ACES_SLOTS",
        {"en-es": ["addition", "omission", "number"]},
    )

    pack = build_calibration_pack(source_root, output_path, remis_path)

    assert len(pack["cases"]) == 19
    assert sum(case["partition"] == "holdout" for case in pack["cases"]) == 12
    assert {case["origin_suite"] for case in pack["cases"]} == {"mqm", "aces", "remis"}
    assert output_path.is_file()
    mqm_cases = [case for case in pack["cases"] if case["origin_suite"] == "mqm"]
    assert {case["gold"]["max_severity"] for case in mqm_cases} == {
        "none",
        "minor",
        "major",
        "critical",
    }


def test_source_cache_rejects_hash_mismatch(tmp_path, monkeypatch) -> None:
    path = tmp_path / "source.txt"
    path.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(
        pack_module,
        "SOURCE_FILES",
        {
            "source": {
                "relative_path": Path("source.txt"),
                "sha256": "0" * 64,
                "url": "https://example.test",
                "license": "test",
            }
        },
    )

    with pytest.raises(CalibrationPackError, match="SHA-256 mismatch"):
        pack_module.verify_source_cache(tmp_path)


def test_source_cache_rejects_missing_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        pack_module,
        "SOURCE_FILES",
        {
            "source": {
                "relative_path": Path("missing"),
                "sha256": "0" * 64,
                "url": "https://example.test",
                "license": "test",
            }
        },
    )

    with pytest.raises(CalibrationPackError, match="Missing external source"):
        pack_module.verify_source_cache(tmp_path)


def test_remis_fixture_requires_twelve_cases(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(pack_module, "SOURCE_FILES", {})
    monkeypatch.setattr(pack_module, "MQM_SLOTS", {})
    monkeypatch.setattr(pack_module, "ACES_SLOTS", {})
    fixture = tmp_path / "remis.json"
    fixture.write_text('{"cases": []}', encoding="utf-8")

    with pytest.raises(CalibrationPackError, match="exactly 12"):
        build_calibration_pack(tmp_path, tmp_path / "output.json", fixture)

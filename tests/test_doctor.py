from __future__ import annotations

from remis_aventine.doctor import build_doctor_report


def test_doctor_finds_remis_benchmark_runner(tmp_path) -> None:
    runner = tmp_path / "scripts" / "developer_tools" / "evaluate_translation_quality.py"
    runner.parent.mkdir(parents=True)
    runner.touch()

    report = build_doctor_report(tmp_path)

    assert report["ready"] is True
    assert report["checks"]["remis"]["status"] == "available"


def test_doctor_reports_invalid_remis_root(tmp_path) -> None:
    report = build_doctor_report(tmp_path)

    assert report["ready"] is True
    assert report["checks"]["remis"]["status"] == "unavailable"

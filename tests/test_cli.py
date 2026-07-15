from __future__ import annotations

import json
from pathlib import Path

import pytest

import remis_aventine.cli as cli
from remis_aventine.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_RECIPE = PROJECT_ROOT / "examples" / "recipes" / "remis-lm-studio.example.json"
FAKE_MQM = PROJECT_ROOT / "examples" / "calibration" / "fake-mqm-v1.json"


def test_validate_recipe_cli_emits_json(capsys) -> None:
    exit_code = main(["validate-recipe", str(EXAMPLE_RECIPE), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["valid"] is True
    assert payload["schema"] == "recipe-manifest.schema.json"
    assert captured.err == ""


def test_validate_recipe_cli_reports_invalid_document(tmp_path, capsys) -> None:
    invalid_recipe = tmp_path / "invalid.json"
    invalid_recipe.write_text('{"schema_version": 1}', encoding="utf-8")

    exit_code = main(["validate-recipe", str(invalid_recipe), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 2
    assert payload["valid"] is False
    assert payload["issues"]
    assert captured.out == ""


def test_doctor_cli_does_not_require_optional_integrations(capsys) -> None:
    exit_code = main(["doctor", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["checks"]["remis"]["status"] == "not_configured"


def test_validate_recipe_cli_emits_text(capsys) -> None:
    exit_code = main(["validate-recipe", str(EXAMPLE_RECIPE)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("valid:")
    assert captured.err == ""


def test_invalid_recipe_cli_emits_readable_text(tmp_path, capsys) -> None:
    invalid_recipe = tmp_path / "invalid.json"
    invalid_recipe.write_text('{"schema_version": 1}', encoding="utf-8")

    exit_code = main(["validate-recipe", str(invalid_recipe)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("error:")
    assert "- $:" in captured.err


def test_missing_recipe_cli_reports_io_error(tmp_path, capsys) -> None:
    missing_recipe = tmp_path / "missing.json"

    exit_code = main(["validate-recipe", str(missing_recipe), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 2
    assert payload["issues"] == []


def test_doctor_cli_emits_text(capsys) -> None:
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Aventine core ready: true" in captured.out
    assert "- python: ready" in captured.out


def test_doctor_cli_propagates_core_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "build_doctor_report",
        lambda _root: {
            "ready": False,
            "checks": {"python": {"status": "unsupported", "detail": "Python is too old."}},
        },
    )

    exit_code = main(["doctor", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert json.loads(captured.out)["ready"] is False


def test_validate_result_cli(tmp_path, capsys) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "smoke-001",
                "suite": "remis",
                "recipe": {"id": "example", "sha256": "a" * 64},
                "started_at": "2026-07-15T00:00:00Z",
                "finished_at": "2026-07-15T00:00:01Z",
                "cases": [],
                "summary": {},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["validate-result", str(result_path), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["schema"] == "run-result.schema.json"


def test_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert captured.out.startswith("aventine ")


def test_validate_judge_cli(tmp_path, capsys) -> None:
    fixture = json.loads(FAKE_MQM.read_text(encoding="utf-8"))
    judge_path = tmp_path / "judge.json"
    judge_path.write_text(json.dumps(fixture["cases"][0]["judge_output"]), encoding="utf-8")

    exit_code = main(["validate-judge", str(judge_path), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["schema"] == "judge-result.schema.json"


def test_summarize_calibration_cli_emits_json_and_text(capsys) -> None:
    exit_code = main(["summarize-calibration", str(FAKE_MQM), "--json"])
    json_output = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(json_output.out)["major_error_recall"] == 0.5

    exit_code = main(["summarize-calibration", str(FAKE_MQM)])
    text_output = capsys.readouterr()

    assert exit_code == 0
    assert "valid judge outputs: 4/5" in text_output.out


def test_summarize_calibration_cli_reports_missing_file(tmp_path, capsys) -> None:
    exit_code = main(["summarize-calibration", str(tmp_path / "missing.json"), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert json.loads(captured.err)["error"]


def test_adapt_remis_result_cli(tmp_path, capsys) -> None:
    input_path = tmp_path / "remis.json"
    output_path = tmp_path / "aventine.json"
    input_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "benchmark": "Fake Remis benchmark",
                "fixture_sha256": "f" * 64,
                "created_at_utc": "2026-07-15T01:00:01Z",
                "provider": "lm_studio",
                "model_id": "fake/model",
                "model_label": "Fake Model",
                "track": "translation",
                "summary": {"case_count": 1, "elapsed_seconds": 1},
                "results": [
                    {
                        "id": "case-1",
                        "execution_failure": None,
                        "elapsed_seconds": 1,
                        "outputs": ["译文"],
                        "score": {
                            "parsed": True,
                            "item_count_match": True,
                            "hard_pass": True,
                            "items": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "adapt-remis-result",
            str(input_path),
            str(output_path),
            "--recipe-id",
            "test.recipe",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["converted"] is True
    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8"))["recipe"]["id"] == "test.recipe"


def test_adapt_remis_result_cli_reports_invalid_input(tmp_path, capsys) -> None:
    input_path = tmp_path / "remis.json"
    input_path.write_text("{}", encoding="utf-8")

    exit_code = main(["adapt-remis-result", str(input_path), str(tmp_path / "output.json")])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("error:")


def test_build_remis_pairwise_pack_cli(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "pack.json"
    monkeypatch.setattr(
        cli,
        "build_remis_pairwise_pack",
        lambda *_args: {"cases": [{"id": "soft"}], "policy_cases": [{"id": "hard"}]},
    )

    exit_code = main(
        ["build-remis-pairwise-pack", "left.json", "right.json", str(output), "--json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["judge_case_count"] == 1
    assert payload["hard_policy_case_count"] == 1


def test_report_remis_pairwise_cli(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_remis_pairwise_report",
        lambda *_args: {
            "summary": {
                "case_count": 2,
                "left_win_count": 1,
                "right_win_count": 0,
                "tie_count": 0,
                "neither_count": 0,
                "unresolved_count": 1,
                "hard_validation_decision_count": 1,
                "judge_position_inconsistent_count": 0,
            }
        },
    )

    exit_code = main(
        [
            "report-remis-pairwise",
            "judged.json",
            str(tmp_path / "report.json"),
            str(tmp_path / "report.md"),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["reported"] is True
    assert payload["unresolved_count"] == 1


def test_build_calibration_pack_cli(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "build_calibration_pack",
        lambda *_args: {
            "id": "pack-v1",
            "cases": [
                {"partition": "calibration"},
                {"partition": "holdout"},
            ],
        },
    )

    exit_code = main(
        ["build-calibration-pack", str(tmp_path), str(tmp_path / "pack.json"), "--json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["case_count"] == 2
    assert payload["holdout_count"] == 1


def test_build_mtme_mqm_pack_cli(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_builder(test_set, language_pair, rating_set, dataset_revision, output, **kwargs):
        selected.update(
            test_set=test_set,
            language_pair=language_pair,
            rating_set=rating_set,
            dataset_revision=dataset_revision,
            output=output,
            **kwargs,
        )
        return {
            "id": "mtme-pack",
            "cases": [{"id": "one"}],
            "adapter": {
                "available_rated_case_count": 10,
                "content_sha256": "a" * 64,
            },
        }

    monkeypatch.setattr(cli, "build_mtme_mqm_pack", fake_builder)
    output = tmp_path / "pack.json"

    exit_code = main(
        [
            "build-mtme-mqm-pack",
            "wmt23",
            "en-de",
            "mqm.merged",
            "mtme-v2",
            str(output),
            "--limit",
            "20",
            "--system",
            "system-a",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["case_count"] == 1
    assert selected["limit"] == 20
    assert selected["systems"] == ["system-a"]
    assert selected["rating_set"] == "mqm.merged"


def test_build_aces_pack_cli(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_builder(source, output, kind, revision, expected_sha, **kwargs):
        selected.update(
            source=source,
            output=output,
            kind=kind,
            revision=revision,
            expected_sha=expected_sha,
            **kwargs,
        )
        return {
            "id": "aces-pack",
            "cases": [{"id": "one"}],
            "adapter": {"matching_row_count": 100, "content_sha256": "b" * 64},
        }

    monkeypatch.setattr(cli, "build_aces_pack", fake_builder)
    source = tmp_path / "span.jsonl"
    output = tmp_path / "pack.json"

    exit_code = main(
        [
            "build-aces-pack",
            str(source),
            str(output),
            "--kind",
            "span-aces",
            "--dataset-revision",
            "b497a645",
            "--expected-sha256",
            "a" * 64,
            "--limit",
            "20",
            "--language-pair",
            "ja-ko",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["case_count"] == 1
    assert selected["kind"] == "span-aces"
    assert selected["limit"] == 20
    assert selected["language_pairs"] == ["ja-ko"]


def test_run_judge_cli(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_judge(_path, provider):
        selected["provider"] = provider
        return object()

    monkeypatch.setattr(cli, "judge_from_environment", fake_judge)
    monkeypatch.setattr(
        cli,
        "run_judge_pack",
        lambda *_args, **_kwargs: {
            "cases": [{"id": "case"}],
            "run": {
                "planned_call_count": 1,
                "failure_count": 0,
                "estimated_cost_rmb": 0.01,
            },
        },
    )

    exit_code = main(
        [
            "run-judge",
            "input.json",
            str(tmp_path / "output.json"),
            "--provider",
            "xai",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["completed"] is True
    assert payload["planned_call_count"] == 1
    assert selected["provider"] == "xai"


def test_run_metric_cli(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_run(*args, **kwargs):
        selected["args"] = args
        selected["kwargs"] = kwargs
        return {
            "metric": {"name": "metricx-24", "mode": "qe"},
            "summary": {
                "case_count": 1,
                "mean_score": 0.25,
                "minimum_score": 0.25,
                "maximum_score": 0.25,
            },
        }

    monkeypatch.setattr(cli, "run_external_metric", fake_run)
    output = tmp_path / "metric.json"
    exit_code = main(
        [
            "run-metric",
            "pack.json",
            str(output),
            "--metric",
            "metricx-24",
            "--runtime-python",
            "python.exe",
            "--model-path",
            "model.bin",
            "--model-id",
            "google/model",
            "--model-sha256",
            "a" * 64,
            "--mode",
            "qe",
            "--tokenizer-path",
            "tokenizer",
            "--metricx-source",
            "source",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["metric"] == "metricx-24"
    assert selected["kwargs"]["mode"] == "qe"


def test_run_metric_cli_reports_runtime_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "run_external_metric",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(cli.ExternalMetricError("no GPU")),
    )
    exit_code = main(
        [
            "run-metric",
            "pack.json",
            "result.json",
            "--metric",
            "xcomet",
            "--runtime-python",
            "python.exe",
            "--model-path",
            "model.ckpt",
            "--model-id",
            "Unbabel/XCOMET-XL",
            "--model-sha256",
            "b" * 64,
            "--hf-home",
            ".",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "no GPU" in captured.err


def test_run_metric_cli_emits_text(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "run_external_metric",
        lambda *_args, **_kwargs: {
            "metric": {"name": "xcomet", "mode": "reference"},
            "summary": {
                "case_count": 2,
                "mean_score": 0.75,
                "minimum_score": 0.5,
                "maximum_score": 1.0,
            },
        },
    )
    exit_code = main(
        [
            "run-metric",
            "pack.json",
            "result.json",
            "--metric",
            "xcomet",
            "--runtime-python",
            "python.exe",
            "--model-path",
            "model.ckpt",
            "--model-id",
            "Unbabel/XCOMET-XL",
            "--model-sha256",
            "b" * 64,
            "--hf-home",
            ".",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "metric run: xcomet (reference)" in captured.out
    assert "mean score: 0.75" in captured.out

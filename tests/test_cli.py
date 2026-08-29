from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_run_remis_google_ai_studio_cli_preserves_explicit_recipe(
    monkeypatch, tmp_path, capsys
) -> None:
    selected = {}

    def fake_run(*args, **kwargs):
        selected["args"] = args
        selected["kwargs"] = kwargs
        return {
            "completed": True,
            "raw_output": str(args[3]),
            "run_output": str(args[4]),
            "run_id": "remis-google-run",
            "case_count": 7,
        }

    monkeypatch.setattr(cli, "run_remis_google_ai_studio_isolated", fake_run)
    raw_output = tmp_path / "raw.json"
    run_output = tmp_path / "run.json"

    exit_code = main(
        [
            "run-remis-google-ai-studio",
            "fixture.json",
            str(raw_output),
            str(run_output),
            "--remis-root",
            "J:/Remis",
            "--runtime-python",
            "K:/MiniConda/python.exe",
            "--model",
            "gemini-3.6-flash",
            "--reasoning-effort",
            "high",
            "--max-output-tokens",
            "16000",
            "--case-id",
            "smoke-case",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["run_id"] == "remis-google-run"
    assert selected["args"][0] == Path("K:/MiniConda/python.exe")
    assert selected["kwargs"]["model"] == "gemini-3.6-flash"
    assert selected["kwargs"]["reasoning_effort"] == "high"
    assert selected["kwargs"]["max_output_tokens"] == 16_000
    assert selected["kwargs"]["case_ids"] == ("smoke-case",)


def test_run_remis_riva_lm_studio_cli_records_native_recipe(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_run(*args, **kwargs):
        selected["args"] = args
        selected["kwargs"] = kwargs
        return {
            "completed": True,
            "raw_output": str(args[3]),
            "run_output": str(args[4]),
            "run_id": "remis-riva-run",
            "model_id": "riva-v2-q8",
            "case_count": 1,
        }

    monkeypatch.setattr(cli, "run_remis_riva_lm_studio_isolated", fake_run)
    raw_output = tmp_path / "raw.json"
    run_output = tmp_path / "run.json"

    exit_code = main(
        [
            "run-remis-riva-lm-studio",
            "fixture.json",
            str(raw_output),
            str(run_output),
            "--remis-root",
            "J:/Remis",
            "--runtime-python",
            "K:/MiniConda/python.exe",
            "--model",
            "auto",
            "--quantization",
            "Q8_0",
            "--case-id",
            "stellaris_proclamation_style",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["run_id"] == "remis-riva-run"
    assert selected["args"][0] == Path("K:/MiniConda/python.exe")
    assert selected["kwargs"]["model"] == "auto"
    assert selected["kwargs"]["quantization"] == "Q8_0"
    assert selected["kwargs"]["temperature"] == 0.0
    assert selected["kwargs"]["case_ids"] == ("stellaris_proclamation_style",)


def test_run_judge_cli_json_keeps_stdout_machine_readable(monkeypatch, tmp_path, capsys) -> None:
    fixture = {
        "schema_version": 1,
        "id": "pack-v1",
        "suite": "mixed",
        "cases": [
            {
                "id": "case-1",
                "input": {"language_pair": "en-zh", "source": "Hello", "candidate": "你好"},
                "gold": {"mode": "single", "verdict": "pass"},
            }
        ],
    }
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(fixture), encoding="utf-8")

    class FakeJudge:
        provider = "fake"
        provider_label = "Fake"
        model_id = "fake"
        profile = "fake"
        prompt_revision = "fake"
        max_tokens = 100
        thinking = "disabled"
        reasoning_effort = "none"

        def empty_usage(self):
            return {"cache_hit_input_tokens": 0, "cache_miss_input_tokens": 0, "output_tokens": 0}

        def cost_fields(self, usage, prior_run):
            return {
                "estimated_cost_rmb": 0.0,
                "prior_estimated_cost_rmb": float(prior_run.get("estimated_cost_rmb", 0.0)),
                "cumulative_estimated_cost_rmb": 0.0,
            }

        def evaluate(self, case):
            return {
                "schema_version": 1,
                "case_id": case["id"],
                "judge": {
                    "profile": "fake",
                    "model": "fake",
                    "prompt_revision": "fake",
                    "calibration_revision": "pack-v1",
                },
                "evaluation": {
                    "mode": "single",
                    "verdict": "pass",
                    "confidence": "high",
                    "errors": [],
                    "rationale": "ok",
                    "limitations": [],
                },
            }, {"cache_hit_input_tokens": 0, "cache_miss_input_tokens": 0, "output_tokens": 0}

    monkeypatch.setattr(cli, "judge_from_environment", lambda *_args: FakeJudge())

    exit_code = main(
        [
            "run-judge",
            str(input_path),
            str(output_path),
            "--logical-result-budget",
            "1",
            "--http-attempt-budget",
            "1",
            "--result-retry-budget",
            "0",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["completed"] is True
    assert "judge_progress" in captured.err
    assert json.loads(output_path.read_text(encoding="utf-8"))["run"]["status"] == "completed"


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


def test_build_metric_pack_cli(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "build_metric_pack_from_calibration",
        lambda *_args: {
            "id": "metric.pack",
            "cases": [{"id": "a"}, {"id": "b"}],
            "adapter": {
                "source_case_count": 2,
                "selected_source_case_count": 1,
                "skipped_case_counts": {"missing_reference": 1},
            },
        },
    )
    exit_code = main(["build-metric-pack", "source.json", str(tmp_path / "pack.json"), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["hypothesis_count"] == 2
    assert payload["selected_source_case_count"] == 1


def test_report_metric_calibration_cli(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_metric_calibration_report",
        lambda *_args: {
            "hypothesis_count": 4,
            "single": {"case_count": 0},
            "pairwise": {"case_count": 2, "accuracy": 0.5},
        },
    )
    exit_code = main(
        [
            "report-metric-calibration",
            "pack.json",
            "result.json",
            str(tmp_path / "report.json"),
            str(tmp_path / "report.md"),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["pairwise_accuracy"] == 0.5


def test_report_evidence_alignment_cli(monkeypatch, tmp_path, capsys) -> None:
    selected = {}

    def fake_report(*args):
        selected["args"] = args
        return {
            "judge": {"case_count": 50, "effective_accuracy": 0.76},
            "review_queue": [{"case_id": "hard"}],
            "metrics": {"xcomet": {"pairwise_accuracy": 0.76}},
        }

    monkeypatch.setattr(cli, "write_evidence_alignment_report", fake_report)
    exit_code = main(
        [
            "report-evidence-alignment",
            "calibration.json",
            "judge.json",
            str(tmp_path / "report.json"),
            str(tmp_path / "report.md"),
            "--metric",
            "metric-pack.json",
            "metric-result.json",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["judge_effective_accuracy"] == 0.76
    assert payload["review_queue_count"] == 1
    assert selected["args"][2][0][0] == Path("metric-pack.json")


def test_report_evidence_alignment_cli_reports_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_evidence_alignment_report",
        lambda *_args: (_ for _ in ()).throw(cli.EvidenceAlignmentError("bad join")),
    )

    exit_code = main(
        [
            "report-evidence-alignment",
            "calibration.json",
            "judge.json",
            "report.json",
            "report.md",
            "--metric",
            "metric-pack.json",
            "metric-result.json",
        ]
    )

    assert exit_code == 2
    assert "bad join" in capsys.readouterr().err


def test_build_pilot_aggregate_cli_emits_versioned_summary(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_pilot_aggregate",
        lambda *_args: {
            "score_version": "pilot-score-v0.1",
            "entries": [{"profile_id": "a"}, {"profile_id": "b"}],
        },
    )
    output_json = tmp_path / "aggregate.json"
    output_markdown = tmp_path / "aggregate.md"
    exit_code = main(
        [
            "build-pilot-aggregate",
            "manifest.json",
            str(output_json),
            str(output_markdown),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "built": True,
        "output_json": str(output_json),
        "output_markdown": str(output_markdown),
        "score_version": "pilot-score-v0.1",
        "profile_count": 2,
    }


def test_build_pilot_aggregate_cli_reports_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_pilot_aggregate",
        lambda *_args: (_ for _ in ()).throw(cli.PilotAggregateError("bad tournament")),
    )

    assert (
        main(
            [
                "build-pilot-aggregate",
                "manifest.json",
                "aggregate.json",
                "aggregate.md",
            ]
        )
        == 2
    )
    assert "bad tournament" in capsys.readouterr().err


def test_build_v03_leaderboard_cli_writes_website_artifact(monkeypatch, tmp_path, capsys) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"runs": [], "matches": []}', encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "build_v03_leaderboard",
        lambda *_args, **_kwargs: {
            "status": "complete",
            "score_version": "multilingual-pilot-v0.3-60soft-40hard",
            "profiles": [{}, {}],
        },
    )
    output = tmp_path / "leaderboard.json"

    exit_code = main(["build-v03-leaderboard", str(manifest), str(output), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output.is_file()
    assert payload["profile_count"] == 2
    assert payload["status"] == "complete"


def test_estimate_v03_campaign_cli_reports_judges_separately(capsys) -> None:
    exit_code = main(
        [
            "estimate-v03-campaign",
            "--contestants",
            "2",
            "--topology",
            "single-anchor",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["expected_calls"]["contestant"] == 740
    assert payload["expected_calls"]["soft_judges"] == 1532
    assert payload["pricing_kind"] == "caller-supplied-reserve-not-provider-quote"


def test_integrated_adapter_commands_emit_readable_text(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "run_remis_google_ai_studio_isolated",
        lambda *_args, **_kwargs: {
            "run_id": "google-run",
            "case_count": 2,
            "raw_output": "google-raw.json",
            "run_output": "google-run.json",
        },
    )
    google_args = SimpleNamespace(
        runtime_python=Path("python.exe"),
        remis_root=Path("remis"),
        fixture=Path("fixture.json"),
        raw_output=Path("raw.json"),
        run_output=Path("run.json"),
        model="gemini",
        label=None,
        reasoning_effort=None,
        max_output_tokens=None,
        track="stable",
        case_ids=None,
        env_file=None,
        recipe_id=None,
        json=False,
    )
    assert cli._run_remis_google(google_args) == 0
    assert "Google AI Studio run: google-run" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "run_remis_riva_lm_studio_isolated",
        lambda *_args, **_kwargs: {
            "run_id": "riva-run",
            "model_id": "riva-v2",
            "case_count": 3,
            "raw_output": "riva-raw.json",
            "run_output": "riva-run.json",
        },
    )
    riva_args = SimpleNamespace(
        runtime_python=Path("python.exe"),
        remis_root=Path("remis"),
        fixture=Path("fixture.json"),
        raw_output=Path("raw.json"),
        run_output=Path("run.json"),
        model="auto",
        label=None,
        base_url="http://127.0.0.1:1234/v1",
        max_output_tokens=512,
        temperature=0.0,
        request_timeout_seconds=30,
        quantization="Q8_0",
        track="stable",
        case_ids=None,
        recipe_id=None,
        json=False,
    )
    assert cli._run_remis_riva(riva_args) == 0
    output = capsys.readouterr().out
    assert "Riva LM Studio run: riva-run" in output
    assert "model: riva-v2" in output


@pytest.mark.parametrize(
    ("target", "error_type", "runner"),
    [
        ("run_remis_google_ai_studio_isolated", cli.GoogleAIStudioAdapterError, "google"),
        ("run_remis_riva_lm_studio_isolated", cli.RivaLMStudioAdapterError, "riva"),
    ],
)
def test_integrated_adapter_commands_report_runtime_errors(
    monkeypatch, capsys, target, error_type, runner
) -> None:
    monkeypatch.setattr(
        cli,
        target,
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error_type("runtime unavailable")),
    )
    common = {
        "runtime_python": Path("python.exe"),
        "remis_root": Path("remis"),
        "fixture": Path("fixture.json"),
        "raw_output": Path("raw.json"),
        "run_output": Path("run.json"),
        "model": "auto",
        "label": None,
        "max_output_tokens": 512,
        "track": "stable",
        "case_ids": None,
        "recipe_id": None,
        "json": False,
    }
    if runner == "google":
        args = SimpleNamespace(**common, reasoning_effort=None, env_file=None)
        exit_code = cli._run_remis_google(args)
    else:
        args = SimpleNamespace(
            **common,
            base_url="http://127.0.0.1:1234/v1",
            temperature=0.0,
            request_timeout_seconds=30,
            quantization="Q8_0",
        )
        exit_code = cli._run_remis_riva(args)
    assert exit_code == 2
    assert "runtime unavailable" in capsys.readouterr().err


def test_integrated_reporting_commands_emit_readable_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "build_remis_pairwise_pack",
        lambda *_args: {"cases": [{}, {}], "policy_cases": [{}]},
    )
    assert (
        cli._build_remis_pairwise(
            SimpleNamespace(
                left=Path("left.json"),
                right=Path("right.json"),
                output=tmp_path / "pairwise.json",
                json=False,
            )
        )
        == 0
    )
    assert "2 judge cases" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "write_remis_pairwise_report",
        lambda *_args: {
            "summary": {"left_win_count": 2, "right_win_count": 1, "unresolved_count": 1}
        },
    )
    assert (
        cli._report_remis_pairwise(
            SimpleNamespace(
                input=Path("input.json"),
                output_json=tmp_path / "report.json",
                output_markdown=tmp_path / "report.md",
                json=False,
            )
        )
        == 0
    )
    assert "left 2, right 1, unresolved 1" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "build_metric_pack_from_calibration",
        lambda *_args: {
            "id": "metric-pack",
            "cases": [{}, {}],
            "adapter": {
                "source_case_count": 3,
                "selected_source_case_count": 2,
                "skipped_case_counts": {"missing_reference": 1},
            },
        },
    )
    assert (
        cli._build_metric_pack(
            SimpleNamespace(
                input=Path("calibration.json"), output=tmp_path / "metric.json", json=False
            )
        )
        == 0
    )
    assert "source cases: 2/3" in capsys.readouterr().out


def test_integrated_analysis_reports_emit_readable_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "write_metric_calibration_report",
        lambda *_args: {
            "hypothesis_count": 4,
            "single": {"case_count": 2},
            "pairwise": {"case_count": 1, "accuracy": 0.75},
        },
    )
    assert (
        cli._report_metric_calibration(
            SimpleNamespace(
                pack=Path("pack.json"),
                result=Path("result.json"),
                output_json=tmp_path / "metric-report.json",
                output_markdown=tmp_path / "metric-report.md",
                json=False,
            )
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "4 hypotheses" in output
    assert "pairwise accuracy: 0.75" in output

    monkeypatch.setattr(
        cli,
        "write_evidence_alignment_report",
        lambda *_args: {
            "judge": {"case_count": 5, "effective_accuracy": 0.8},
            "review_queue": [{}, {}],
            "metrics": {},
        },
    )
    assert (
        cli._report_evidence_alignment(
            SimpleNamespace(
                calibration_pack=Path("calibration.json"),
                judge_result=Path("judge.json"),
                metric=[],
                output_json=tmp_path / "evidence.json",
                output_markdown=tmp_path / "evidence.md",
                json=False,
            )
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "evidence alignment: 5 cases" in output
    assert "review queue: 2" in output


def test_v03_campaign_cli_reports_invalid_budget(capsys) -> None:
    exit_code = main(["estimate-v03-campaign", "--contestants", "1"])

    assert exit_code == 2
    assert capsys.readouterr().err.startswith("error:")


def test_integrated_pack_builders_emit_readable_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "build_calibration_pack",
        lambda *_args: {
            "id": "calibration-pack",
            "cases": [{"partition": "calibration"}, {"partition": "holdout"}],
        },
    )
    assert (
        cli._build_pack(
            SimpleNamespace(
                source_root=tmp_path,
                output=tmp_path / "calibration.json",
                remis_fixture=None,
                json=False,
            )
        )
        == 0
    )
    assert "calibration/holdout: 1/1" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "build_mtme_mqm_pack",
        lambda *_args, **_kwargs: {
            "id": "mtme-pack",
            "cases": [{}, {}],
            "adapter": {"available_rated_case_count": 8, "content_sha256": "a" * 64},
        },
    )
    assert (
        cli._build_mtme_pack(
            SimpleNamespace(
                test_set="wmt23",
                language_pair="en-de",
                rating_set="mqm",
                dataset_revision="revision",
                output=tmp_path / "mtme.json",
                data_root=None,
                limit=None,
                systems=None,
                json=False,
            )
        )
        == 0
    )
    assert "selected cases: 2/8" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "build_aces_pack",
        lambda *_args, **_kwargs: {
            "id": "aces-pack",
            "cases": [{}],
            "adapter": {"matching_row_count": 6, "content_sha256": "b" * 64},
        },
    )
    assert (
        cli._build_aces_pack(
            SimpleNamespace(
                input=tmp_path / "aces.jsonl",
                output=tmp_path / "aces.json",
                kind="span-aces",
                dataset_revision="revision",
                expected_sha256="b" * 64,
                limit=None,
                language_pairs=None,
                phenomena=None,
                json=False,
            )
        )
        == 0
    )
    assert "selected cases: 1/6" in capsys.readouterr().out


def test_integrated_adaptation_emits_readable_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "adapt_remis_result",
        lambda *_args, **_kwargs: {"run_id": "adapted-run", "summary": {"case_count": 4}},
    )
    assert (
        cli._adapt_remis(
            tmp_path / "input.json",
            tmp_path / "output.json",
            recipe_id=None,
            as_json=False,
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "run: adapted-run" in output
    assert "cases: 4" in output


def test_integrated_judge_emits_progress_and_exact_cost(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "judge_from_environment", lambda *_args: object())

    def fake_run(*_args, **kwargs):
        kwargs["progress"]({"completed": 1})
        return {
            "cases": [{}],
            "run": {
                "planned_call_count": 2,
                "failure_count": 0,
                "exact_cost_usd": 0.02,
            },
        }

    monkeypatch.setattr(cli, "run_judge_pack", fake_run)
    args = SimpleNamespace(
        env_file=None,
        provider="openai",
        input=tmp_path / "input.json",
        output=tmp_path / "output.json",
        limit=None,
        case_ids=None,
        max_calls=None,
        workers=1,
        resume_from=None,
        logical_result_budget=None,
        http_attempt_budget=None,
        result_retry_budget=None,
        checkpoint_path=None,
        json=False,
    )
    assert cli._run_judge(args) == 0
    captured = capsys.readouterr()
    assert "judge run: 1 cases, 2 calls" in captured.out
    assert "exact cost: USD 0.02" in captured.out
    assert "judge progress:" in captured.err


def test_v03_leaderboard_loads_structural_resolutions(monkeypatch, tmp_path, capsys) -> None:
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pack.json").write_text("{}", encoding="utf-8")
    (tmp_path / "judge.json").write_text("{}", encoding="utf-8")
    (tmp_path / "structural.json").write_text(
        '{"resolutions": [{"case_id": "case-1"}]}', encoding="utf-8"
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "runs": ["run.json"],
                "matches": [{"pack": "pack.json", "judge_report": "judge.json"}],
                "structural_resolutions": "structural.json",
            }
        ),
        encoding="utf-8",
    )
    observed = {}

    def fake_build(runs, matches, *, structural_resolutions):
        observed.update(runs=runs, matches=matches, structural=structural_resolutions)
        return {"status": "complete", "score_version": "score", "profiles": [{}]}

    monkeypatch.setattr(cli, "build_v03_leaderboard", fake_build)
    output = tmp_path / "leaderboard.json"
    assert (
        cli._build_v03_leaderboard(SimpleNamespace(manifest=manifest, output=output, json=False))
        == 0
    )
    assert observed["structural"] == [{"case_id": "case-1"}]
    assert output.is_file()
    assert "profile_count" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("target", "helper", "namespace"),
    [
        (
            "build_calibration_pack",
            cli._build_pack,
            SimpleNamespace(
                source_root=Path("source"),
                output=Path("output.json"),
                remis_fixture=None,
                json=False,
            ),
        ),
        (
            "build_mtme_mqm_pack",
            cli._build_mtme_pack,
            SimpleNamespace(
                test_set="wmt23",
                language_pair="en-de",
                rating_set="mqm",
                dataset_revision="revision",
                output=Path("output.json"),
                data_root=None,
                limit=None,
                systems=None,
                json=False,
            ),
        ),
        (
            "build_aces_pack",
            cli._build_aces_pack,
            SimpleNamespace(
                input=Path("input.jsonl"),
                output=Path("output.json"),
                kind="span-aces",
                dataset_revision="revision",
                expected_sha256="a" * 64,
                limit=None,
                language_pairs=None,
                phenomena=None,
                json=False,
            ),
        ),
        (
            "build_metric_pack_from_calibration",
            cli._build_metric_pack,
            SimpleNamespace(input=Path("input.json"), output=Path("output.json"), json=False),
        ),
    ],
)
def test_integrated_pack_builders_report_io_errors(
    monkeypatch, capsys, target, helper, namespace
) -> None:
    monkeypatch.setattr(
        cli, target, lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("read failed"))
    )
    assert helper(namespace) == 2
    assert "read failed" in capsys.readouterr().err

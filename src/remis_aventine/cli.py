"""Command-line interface for Aventine."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from remis_aventine import __version__
from remis_aventine.adapters.aces import ACESAdapterError, build_aces_pack
from remis_aventine.adapters.mt_metrics_eval import (
    MTMetricsEvalAdapterError,
    build_mtme_mqm_pack,
)
from remis_aventine.adapters.remis import RemisCompatibilityError, adapt_remis_result
from remis_aventine.calibration import CalibrationFixtureError, summarize_calibration_fixture
from remis_aventine.calibration_pack import CalibrationPackError, build_calibration_pack
from remis_aventine.doctor import build_doctor_report
from remis_aventine.judge import JudgeRunError, judge_from_environment, run_judge_pack
from remis_aventine.remis_pairwise import (
    RemisPairwiseError,
    build_remis_pairwise_pack,
    write_remis_pairwise_report,
)
from remis_aventine.validation import DocumentValidationError, validate_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aventine",
        description="Validate and inspect reproducible translation-recipe artifacts.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Inspect the local environment without downloading data or running models.",
    )
    doctor_parser.add_argument(
        "--remis-root",
        type=Path,
        help="Optional path to a Remis checkout used by the compatibility adapter.",
    )
    doctor_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    recipe_parser = subparsers.add_parser(
        "validate-recipe",
        help="Validate a translation recipe manifest.",
    )
    recipe_parser.add_argument("path", type=Path)
    recipe_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    result_parser = subparsers.add_parser(
        "validate-result",
        help="Validate an Aventine run-result artifact.",
    )
    result_parser.add_argument("path", type=Path)
    result_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    judge_parser = subparsers.add_parser(
        "validate-judge",
        help="Validate a structured judge result.",
    )
    judge_parser.add_argument("path", type=Path)
    judge_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    summary_parser = subparsers.add_parser(
        "summarize-calibration",
        help="Calculate deterministic metrics for a calibration fixture.",
    )
    summary_parser.add_argument("path", type=Path)
    summary_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    adapter_parser = subparsers.add_parser(
        "adapt-remis-result",
        help="Convert a Remis translation-quality artifact into an Aventine run result.",
    )
    adapter_parser.add_argument("input", type=Path)
    adapter_parser.add_argument("output", type=Path)
    adapter_parser.add_argument(
        "--recipe-id",
        help="Override the deterministic compatibility recipe id.",
    )
    adapter_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    remis_pairwise_parser = subparsers.add_parser(
        "build-remis-pairwise-pack",
        help="Build a hard-veto-aware judge pack from two adapted Remis runs.",
    )
    remis_pairwise_parser.add_argument("left", type=Path)
    remis_pairwise_parser.add_argument("right", type=Path)
    remis_pairwise_parser.add_argument("output", type=Path)
    remis_pairwise_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    remis_report_parser = subparsers.add_parser(
        "report-remis-pairwise",
        help="Write JSON and Markdown reports from a Remis pairwise pack or judge run.",
    )
    remis_report_parser.add_argument("input", type=Path)
    remis_report_parser.add_argument("output_json", type=Path)
    remis_report_parser.add_argument("output_markdown", type=Path)
    remis_report_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    pack_parser = subparsers.add_parser(
        "build-calibration-pack",
        help="Build the fixed 48-case pack from an already-downloaded external source cache.",
    )
    pack_parser.add_argument("source_root", type=Path)
    pack_parser.add_argument("output", type=Path)
    pack_parser.add_argument(
        "--remis-fixture",
        type=Path,
        default=Path("examples/calibration/remis-synthetic-v1.json"),
    )
    pack_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    mtme_parser = subparsers.add_parser(
        "build-mtme-mqm-pack",
        help="Build a bounded MQM judge pack from an installed mt-metrics-eval dataset.",
    )
    mtme_parser.add_argument("test_set", help="EvalSet name, for example wmt23.")
    mtme_parser.add_argument("language_pair", help="EvalSet language pair, for example en-de.")
    mtme_parser.add_argument("rating_set", help="Exact EvalSet rating name.")
    mtme_parser.add_argument("dataset_revision", help="Pinned external dataset revision label.")
    mtme_parser.add_argument("output", type=Path)
    mtme_parser.add_argument("--data-root", type=Path)
    mtme_parser.add_argument("--limit", type=int, default=50)
    mtme_parser.add_argument("--system", action="append", dest="systems")
    mtme_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    aces_parser = subparsers.add_parser(
        "build-aces-pack",
        help="Build a bounded pairwise pack from a pinned ACES or SPAN-ACES JSONL file.",
    )
    aces_parser.add_argument("input", type=Path)
    aces_parser.add_argument("output", type=Path)
    aces_parser.add_argument("--kind", choices=("aces", "span-aces"), required=True)
    aces_parser.add_argument("--dataset-revision", required=True)
    aces_parser.add_argument("--expected-sha256", required=True)
    aces_parser.add_argument("--limit", type=int, default=50)
    aces_parser.add_argument("--language-pair", action="append", dest="language_pairs")
    aces_parser.add_argument("--phenomenon", action="append", dest="phenomena")
    aces_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    judge_run_parser = subparsers.add_parser(
        "run-judge",
        help="Run a bounded remote judge over a calibration pack.",
    )
    judge_run_parser.add_argument("input", type=Path)
    judge_run_parser.add_argument("output", type=Path)
    judge_run_parser.add_argument("--limit", type=int)
    judge_run_parser.add_argument("--case-id", action="append", dest="case_ids")
    judge_run_parser.add_argument("--max-calls", type=int, default=100)
    judge_run_parser.add_argument("--workers", type=int, default=1)
    judge_run_parser.add_argument(
        "--provider", choices=("deepseek", "xai", "google"), default="deepseek"
    )
    judge_run_parser.add_argument("--resume-from", type=Path)
    judge_run_parser.add_argument("--env-file", type=Path, default=Path(".env"))
    judge_run_parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

    return parser


def _emit(payload: dict[str, Any], *, as_json: bool, stream: Any | None = None) -> None:
    output = stream if stream is not None else sys.stdout
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=output)
        return

    if payload.get("valid") is True:
        print(f"valid: {payload['path']} ({payload['schema']})", file=output)
        return

    if "checks" in payload:
        print(f"Aventine core ready: {str(payload['ready']).lower()}", file=output)
        for name, check in payload["checks"].items():
            print(f"- {name}: {check['status']} - {check['detail']}", file=output)
        return

    print(f"error: {payload['error']}", file=output)
    for issue in payload.get("issues", []):
        print(f"- {issue}", file=output)


def _validate(path: Path, schema_name: str, *, as_json: bool) -> int:
    try:
        validate_document(path, schema_name)
    except (DocumentValidationError, OSError) as exc:
        issues = list(exc.issues) if isinstance(exc, DocumentValidationError) else []
        payload = {
            "valid": False,
            "path": str(path),
            "schema": schema_name,
            "error": str(exc),
            "issues": issues,
        }
        _emit(payload, as_json=as_json, stream=sys.stderr)
        return 2

    _emit(
        {"valid": True, "path": str(path), "schema": schema_name},
        as_json=as_json,
    )
    return 0


def _emit_command_error(exc: Exception, *, as_json: bool) -> int:
    payload = {"error": str(exc)}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
    else:
        print(f"error: {exc}", file=sys.stderr)
    return 2


def _summarize_calibration(path: Path, *, as_json: bool) -> int:
    try:
        summary = summarize_calibration_fixture(path)
    except (CalibrationFixtureError, OSError) as exc:
        return _emit_command_error(exc, as_json=as_json)
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"calibration: {summary['fixture_id']} ({summary['suite']})")
        print(f"- valid judge outputs: {summary['valid_judge_count']}/{summary['case_count']}")
        print(f"- verdict accuracy: {summary['verdict_accuracy']}")
        print(f"- major error recall: {summary['major_error_recall']}")
        print(f"- false-good rate: {summary['false_good_rate']}")
    return 0


def _adapt_remis(
    input_path: Path,
    output_path: Path,
    *,
    recipe_id: str | None,
    as_json: bool,
) -> int:
    try:
        converted = adapt_remis_result(input_path, output_path, recipe_id=recipe_id)
    except (DocumentValidationError, RemisCompatibilityError, OSError) as exc:
        return _emit_command_error(exc, as_json=as_json)
    payload = {
        "converted": True,
        "input": str(input_path),
        "output": str(output_path),
        "run_id": converted["run_id"],
        "case_count": converted["summary"]["case_count"],
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"converted: {input_path} -> {output_path}")
        print(f"- run: {payload['run_id']}")
        print(f"- cases: {payload['case_count']}")
    return 0


def _build_remis_pairwise(args: argparse.Namespace) -> int:
    try:
        pack = build_remis_pairwise_pack(args.left, args.right, args.output)
    except (RemisPairwiseError, OSError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "built": True,
        "output": str(args.output),
        "judge_case_count": len(pack["cases"]),
        "hard_policy_case_count": len(pack["policy_cases"]),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Remis pairwise pack: {payload['judge_case_count']} judge cases, "
            f"{payload['hard_policy_case_count']} hard-policy cases"
        )
    return 0


def _report_remis_pairwise(args: argparse.Namespace) -> int:
    try:
        report = write_remis_pairwise_report(
            args.input, args.output_json, args.output_markdown
        )
    except (CalibrationFixtureError, RemisPairwiseError, OSError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "reported": True,
        "output_json": str(args.output_json),
        "output_markdown": str(args.output_markdown),
        **report["summary"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"Remis pairwise report: left {payload['left_win_count']}, "
            f"right {payload['right_win_count']}, unresolved {payload['unresolved_count']}"
        )
    return 0


def _build_pack(args: argparse.Namespace) -> int:
    try:
        pack = build_calibration_pack(args.source_root, args.output, args.remis_fixture)
    except (CalibrationPackError, OSError, json.JSONDecodeError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "built": True,
        "id": pack["id"],
        "output": str(args.output),
        "case_count": len(pack["cases"]),
        "calibration_count": sum(case["partition"] == "calibration" for case in pack["cases"]),
        "holdout_count": sum(case["partition"] == "holdout" for case in pack["cases"]),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"built: {payload['id']} -> {payload['output']}")
        print(f"- cases: {payload['case_count']}")
        print(f"- calibration/holdout: {payload['calibration_count']}/{payload['holdout_count']}")
    return 0


def _build_mtme_pack(args: argparse.Namespace) -> int:
    try:
        pack = build_mtme_mqm_pack(
            args.test_set,
            args.language_pair,
            args.rating_set,
            args.dataset_revision,
            args.output,
            data_root=args.data_root,
            limit=args.limit,
            systems=args.systems,
        )
    except (MTMetricsEvalAdapterError, OSError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "built": True,
        "id": pack["id"],
        "output": str(args.output),
        "case_count": len(pack["cases"]),
        "available_rated_case_count": pack["adapter"]["available_rated_case_count"],
        "content_sha256": pack["adapter"]["content_sha256"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"built: {payload['id']} -> {payload['output']}")
        print(f"- selected cases: {payload['case_count']}/{payload['available_rated_case_count']}")
        print(f"- content SHA-256: {payload['content_sha256']}")
    return 0


def _build_aces_pack(args: argparse.Namespace) -> int:
    try:
        pack = build_aces_pack(
            args.input,
            args.output,
            args.kind,
            args.dataset_revision,
            args.expected_sha256,
            limit=args.limit,
            language_pairs=args.language_pairs,
            phenomena=args.phenomena,
        )
    except (ACESAdapterError, OSError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "built": True,
        "id": pack["id"],
        "output": str(args.output),
        "case_count": len(pack["cases"]),
        "matching_row_count": pack["adapter"]["matching_row_count"],
        "content_sha256": pack["adapter"]["content_sha256"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"built: {payload['id']} -> {payload['output']}")
        print(f"- selected cases: {payload['case_count']}/{payload['matching_row_count']}")
        print(f"- content SHA-256: {payload['content_sha256']}")
    return 0


def _run_judge(args: argparse.Namespace) -> int:
    try:
        judge = judge_from_environment(args.env_file, args.provider)
        result = run_judge_pack(
            args.input,
            args.output,
            judge,
            limit=args.limit,
            case_ids=args.case_ids,
            max_calls=args.max_calls,
            workers=args.workers,
            resume_from=args.resume_from,
        )
    except (CalibrationFixtureError, JudgeRunError, OSError) as exc:
        return _emit_command_error(exc, as_json=args.json)
    payload = {
        "completed": True,
        "output": str(args.output),
        "case_count": len(result["cases"]),
        **result["run"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"judge run: {payload['case_count']} cases, {payload['planned_call_count']} calls")
        print(f"- failures: {payload['failure_count']}")
        if "exact_cost_usd" in payload:
            print(f"- exact cost: USD {payload['exact_cost_usd']}")
        else:
            print(f"- estimated cost: RMB {payload['estimated_cost_rmb']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "doctor":
        report = build_doctor_report(args.remis_root)
        _emit(report, as_json=args.json)
        return 0 if report["ready"] else 1
    if args.command == "validate-recipe":
        return _validate(args.path, "recipe-manifest.schema.json", as_json=args.json)
    if args.command == "validate-result":
        return _validate(args.path, "run-result.schema.json", as_json=args.json)
    if args.command == "validate-judge":
        return _validate(args.path, "judge-result.schema.json", as_json=args.json)
    if args.command == "summarize-calibration":
        return _summarize_calibration(args.path, as_json=args.json)
    if args.command == "adapt-remis-result":
        return _adapt_remis(
            args.input,
            args.output,
            recipe_id=args.recipe_id,
            as_json=args.json,
        )
    if args.command == "build-remis-pairwise-pack":
        return _build_remis_pairwise(args)
    if args.command == "report-remis-pairwise":
        return _report_remis_pairwise(args)
    if args.command == "build-calibration-pack":
        return _build_pack(args)
    if args.command == "build-mtme-mqm-pack":
        return _build_mtme_pack(args)
    if args.command == "build-aces-pack":
        return _build_aces_pack(args)
    if args.command == "run-judge":
        return _run_judge(args)

    raise AssertionError(f"Unhandled command: {args.command}")  # pragma: no cover

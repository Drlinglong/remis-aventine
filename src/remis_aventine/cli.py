"""Command-line interface for Aventine."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from remis_aventine import __version__
from remis_aventine.doctor import build_doctor_report
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

    raise AssertionError(f"Unhandled command: {args.command}")  # pragma: no cover

"""JSON document loading and schema validation."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class DocumentValidationError(ValueError):
    """Raised when a document cannot be parsed or does not satisfy its schema."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = tuple(issues or [])


def load_schema(schema_name: str) -> dict[str, Any]:
    schema_path = resources.files("remis_aventine.schemas").joinpath(schema_name)
    if not schema_path.is_file():
        raise FileNotFoundError(f"Unknown Aventine schema: {schema_name}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _error_path(error: Any) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
    )


def validate_document(path: Path, schema_name: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DocumentValidationError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        issues = [f"{_error_path(error)}: {error.message}" for error in errors]
        raise DocumentValidationError(
            f"Document does not satisfy {schema_name}.",
            issues,
        )
    return document

"""Read-only environment diagnostics for Aventine."""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path
from typing import Any


def _optional_module(module_name: str) -> dict[str, str]:
    available = importlib.util.find_spec(module_name) is not None
    return {
        "status": "available" if available else "not_installed",
        "detail": f"Optional module '{module_name}' "
        + ("is importable." if available else "is not installed."),
    }


def _remis_check(remis_root: Path | None) -> dict[str, str]:
    configured_root = remis_root or (
        Path(os.environ["REMIS_ROOT"]) if os.environ.get("REMIS_ROOT") else None
    )
    if configured_root is None:
        return {
            "status": "not_configured",
            "detail": "Set --remis-root or REMIS_ROOT to probe the optional Remis adapter.",
        }

    expected_runner = (
        configured_root / "scripts" / "developer_tools" / "evaluate_translation_quality.py"
    )
    if expected_runner.is_file():
        return {
            "status": "available",
            "detail": f"Found the Remis benchmark runner under {configured_root}.",
        }
    return {
        "status": "unavailable",
        "detail": f"No Remis benchmark runner found under {configured_root}.",
    }


def build_doctor_report(remis_root: Path | None = None) -> dict[str, Any]:
    python_ready = sys.version_info >= (3, 11)
    return {
        "schema_version": 1,
        "ready": python_ready,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "checks": {
            "python": {
                "status": "ready" if python_ready else "unsupported",
                "detail": "Python 3.11 or newer is required.",
            },
            "remis": _remis_check(remis_root),
            "mt_metrics_eval": _optional_module("mt_metrics_eval"),
            "comet": _optional_module("comet"),
        },
    }

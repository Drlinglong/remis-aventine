"""Isolated worker for the Riva Translate v2 LM Studio execution adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from remis_aventine.adapters.riva_lm_studio import (
    RivaLMStudioAdapterError,
    run_remis_riva_lm_studio,
)


def _required_string(document: dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RivaLMStudioAdapterError(f"Worker request requires {key!r}.")
    return value


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        if not isinstance(request, dict):
            raise RivaLMStudioAdapterError("Worker request must be a JSON object.")
        result = run_remis_riva_lm_studio(
            Path(_required_string(request, "remis_root")),
            Path(_required_string(request, "fixture_path")),
            Path(_required_string(request, "raw_output_path")),
            Path(_required_string(request, "run_output_path")),
            model=_required_string(request, "model"),
            label=request.get("label"),
            base_url=_required_string(request, "base_url"),
            max_output_tokens=request.get("max_output_tokens"),
            temperature=request.get("temperature"),
            request_timeout_seconds=request.get("request_timeout_seconds"),
            quantization=_required_string(request, "quantization"),
            track=_required_string(request, "track"),
            case_ids=tuple(request.get("case_ids") or ()),
            recipe_id=request.get("recipe_id"),
        )
    except (RivaLMStudioAdapterError, OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

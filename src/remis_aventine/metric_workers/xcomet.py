"""xCOMET worker. This module is executed by the isolated COMET runtime."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
from pathlib import Path
from typing import Any


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--hf-home", type=Path, required=True)
    parser.add_argument("--mode", choices=("reference",), required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    return parser


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "__dict__"):
        return _json_value(vars(value))
    return value


def main() -> int:
    args = _parser().parse_args()
    os.environ["HF_HOME"] = str(args.hf_home)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import torch
    from comet import load_from_checkpoint

    pack = json.loads(args.input.read_text(encoding="utf-8"))
    torch.set_float32_matmul_precision("high")
    model = load_from_checkpoint(str(args.model))
    data = [
        {"src": case["source"], "mt": case["hypothesis"], "ref": case["reference"]}
        for case in pack["cases"]
    ]
    prediction = model.predict(
        data,
        batch_size=args.batch_size,
        gpus=1 if torch.cuda.is_available() else 0,
        progress_bar=False,
    )
    spans = getattr(prediction.metadata, "error_spans", None)
    results = []
    for index, (case, score) in enumerate(
        zip(pack["cases"], prediction.scores, strict=True)
    ):
        result = {"id": case["id"], "score": float(score)}
        if spans is not None:
            result["error_spans"] = _json_value(spans[index])
        results.append(result)

    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    output = {
        "runtime": {
            "python": platform.python_version(),
            "packages": {
                "torch": importlib.metadata.version("torch"),
                "unbabel-comet": importlib.metadata.version("unbabel-comet"),
                "transformers": importlib.metadata.version("transformers"),
                "sentencepiece": importlib.metadata.version("sentencepiece"),
            },
            "device": device,
        },
        "cases": results,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

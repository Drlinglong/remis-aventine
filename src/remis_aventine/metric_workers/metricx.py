"""MetricX-24 worker. This module is executed by the isolated MetricX runtime."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--metricx-source", type=Path, required=True)
    parser.add_argument("--mode", choices=("qe", "reference"), required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    return parser


def _version(name: str) -> str:
    return importlib.metadata.version(name)


def main() -> int:
    args = _parser().parse_args()
    sys.path.insert(0, str(args.metricx_source))

    import torch
    import transformers
    from metricx24.models import MT5ForRegression

    pack = json.loads(args.input.read_text(encoding="utf-8"))
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        args.tokenizer, local_files_only=True, use_fast=False
    )
    model = MT5ForRegression.from_pretrained(args.model, torch_dtype="auto", local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    results = []
    for start in range(0, len(pack["cases"]), args.batch_size):
        cases = pack["cases"][start : start + args.batch_size]
        texts = []
        for case in cases:
            text = f"source: {case['source']} candidate: {case['hypothesis']}"
            if args.mode == "reference":
                text += f" reference: {case['reference']}"
            texts.append(text)
        encoded_rows = [
            tokenizer(text, max_length=1536, truncation=True, padding=False) for text in texts
        ]
        for row in encoded_rows:
            row["input_ids"] = row["input_ids"][:-1]
            row["attention_mask"] = row["attention_mask"][:-1]
        batch = tokenizer.pad(encoded_rows, padding=True, return_tensors="pt")
        batch = {name: value.to(device) for name, value in batch.items()}
        with torch.inference_mode():
            scores = model(**batch).predictions.float().cpu().tolist()
        results.extend(
            {"id": case["id"], "score": float(score)}
            for case, score in zip(cases, scores, strict=True)
        )

    output = {
        "runtime": {
            "python": platform.python_version(),
            "packages": {
                "torch": _version("torch"),
                "transformers": _version("transformers"),
                "sentencepiece": _version("sentencepiece"),
                "protobuf": _version("protobuf"),
            },
            "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        },
        "cases": results,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

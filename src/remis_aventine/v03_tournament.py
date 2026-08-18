"""Build hard-veto-aware blinded pairwise evidence for Aventine v0.3."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from remis_aventine.validation import validate_payload


class V03TournamentError(ValueError):
    """Raised when contestant artifacts cannot be compared reproducibly."""


def _sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _identity(run: dict[str, Any], side: str) -> dict[str, Any]:
    identity = run.get("execution_identity")
    digest = run.get("execution_identity_sha256")
    if not isinstance(identity, dict) or not identity or digest != _sha256(identity):
        raise V03TournamentError(f"{side} run lacks a valid execution identity.")
    if not isinstance(identity.get("model_family"), str) or not identity["model_family"]:
        raise V03TournamentError(f"{side} run lacks model_family.")
    return identity


def _exam_items(exam: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for task in exam.get("translation_tasks", []):
        references = task.get("reference")
        for index, source in enumerate(task.get("source_items", [])):
            item_id = f"{task['id']}::{index}"
            reference = references[index] if isinstance(references, list) else None
            items[item_id] = {
                "item_id": item_id,
                "case_id": task["case_id"],
                "origin": task["origin"],
                "language_pair": f"{task['source_lang']}->{task['target_lang']}",
                "source": source["text"] if isinstance(source, dict) else source,
                "reference": reference,
                "context": task.get("context", ""),
                "focus": deepcopy(task.get("focus", [])),
            }
    return items


def _run_items(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for result in run.get("results", []):
        job_id = result.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise V03TournamentError("Every run result requires a job_id.")
        for item in (result.get("validation") or {}).get("items", []):
            item_id = item.get("item_id")
            occurrence_id = f"{job_id}::{item_id}"
            if not isinstance(item_id, str) or occurrence_id in flattened:
                raise V03TournamentError("Run contains missing or duplicate item IDs.")
            flattened[occurrence_id] = {**item, "base_item_id": item_id, "job_id": job_id}
    return flattened


def build_v03_pairwise_pack(
    exam: dict[str, Any], left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    """Align two frozen runs and separate hard veto, structural review, and soft judging."""
    if left.get("status") != "completed" or right.get("status") != "completed":
        raise V03TournamentError("Both contestant runs must be completed.")
    for field in ("exam_sha256", "plan_sha256", "planned_call_count"):
        if left.get(field) != right.get(field):
            raise V03TournamentError(f"Contestant runs disagree on {field}.")
    left_identity = _identity(left, "Left")
    right_identity = _identity(right, "Right")
    if left["execution_identity_sha256"] == right["execution_identity_sha256"]:
        raise V03TournamentError("Pairwise comparison requires two distinct recipes.")

    exam_items = _exam_items(exam)
    left_items = _run_items(left)
    right_items = _run_items(right)
    if set(left_items) != set(right_items):
        raise V03TournamentError("Contestant runs contain different item sets.")
    unknown = {
        item["base_item_id"]
        for item in left_items.values()
        if item["base_item_id"] not in exam_items
    }
    if unknown:
        raise V03TournamentError(f"Run items are absent from the exam: {sorted(unknown)!r}")

    cases = []
    hard_decisions = []
    structural_queue = []
    for occurrence_id in sorted(left_items):
        left_item = left_items[occurrence_id]
        right_item = right_items[occurrence_id]
        item_id = left_item["base_item_id"]
        if right_item["base_item_id"] != item_id:
            raise V03TournamentError("Aligned occurrences contain different base item IDs.")
        evidence = exam_items[item_id]
        left_route = left_item["classification"]["route"]
        right_route = right_item["classification"]["route"]
        base = {
            "id": occurrence_id,
            "item_id": item_id,
            "job_id": left_item["job_id"],
            "direction": evidence["language_pair"],
            "origin": evidence["origin"],
            "left_route": left_route,
            "right_route": right_route,
        }
        if "hard_fail" in {left_route, right_route}:
            winner = (
                "tie"
                if left_route == right_route
                else "candidate_b"
                if left_route == "hard_fail"
                else "candidate_a"
            )
            hard_decisions.append({**base, "winner": winner})
            continue
        if "structural_judges" in {left_route, right_route}:
            structural_queue.append(
                {
                    **base,
                    "source": evidence["source"],
                    "candidate_a": left_item["output"],
                    "candidate_b": right_item["output"],
                    "left_review_queue": left_item["classification"].get(
                        "structural_review_queue", []
                    ),
                    "right_review_queue": right_item["classification"].get(
                        "structural_review_queue", []
                    ),
                }
            )
            continue
        cases.append(
            {
                "id": occurrence_id,
                "item_id": item_id,
                "job_id": left_item["job_id"],
                "evaluation_mode": "pairwise",
                "stratum": f"{evidence['language_pair']}:{evidence['origin']}",
                "candidate_families": [
                    left_identity["model_family"],
                    right_identity["model_family"],
                ],
                "input": {
                    "language_pair": evidence["language_pair"],
                    "source": evidence["source"],
                    "reference": evidence["reference"],
                    "context": evidence["context"],
                    "focus": evidence["focus"],
                    "candidate_a": left_item["output"],
                    "candidate_b": right_item["output"],
                },
            }
        )
    pack = {
        "schema_version": 1,
        "protocol": "aventine-v0.3-pairwise",
        "exam_sha256": left["exam_sha256"],
        "plan_sha256": left["plan_sha256"],
        "candidate_identities": {
            "candidate_a": deepcopy(left_identity),
            "candidate_b": deepcopy(right_identity),
        },
        "soft_judge_cases": cases,
        "deterministic_hard_decisions": hard_decisions,
        "structural_review_queue": structural_queue,
        "counts": {
            "soft_judge": len(cases),
            "deterministic_hard": len(hard_decisions),
            "structural_review": len(structural_queue),
            "total": len(left_items),
        },
    }
    pack["sha256"] = _sha256(pack)
    validate_payload(pack, "v03-pairwise-pack.schema.json")
    return pack


__all__ = ["V03TournamentError", "build_v03_pairwise_pack"]

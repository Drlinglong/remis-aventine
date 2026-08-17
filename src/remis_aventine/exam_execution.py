"""Deterministic planning and checkpointed execution for frozen multilingual exams."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

V03_DIRECTIONS = (
    "zh-CN->en",
    "en->zh-CN",
    "zh-CN->ja",
    "zh-CN->ko",
    "zh-CN->de",
    "zh-CN->ru",
    "zh-CN->fr",
    "zh-CN->es",
    "zh-CN->pt-BR",
    "zh-CN->tr",
    "en->ja",
    "en->ko",
    "en->de",
    "en->ru",
    "en->fr",
    "en->es",
    "en->pt-BR",
    "en->tr",
)


class ExamExecutionError(ValueError):
    """Raised when an exam or resumable execution artifact is inconsistent."""


class BudgetExceeded(ExamExecutionError):
    """Raised before a call which could exceed the configured budget."""


@dataclass(frozen=True)
class ExecutionPlan:
    """A content-addressed sequence of contestant calls."""

    exam_id: str
    exam_sha256: str
    repetitions: int
    directions: tuple[str, ...]
    jobs: tuple[dict[str, Any], ...]
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "exam_id": self.exam_id,
            "exam_sha256": self.exam_sha256,
            "repetitions": self.repetitions,
            "directions": list(self.directions),
            "jobs": deepcopy(list(self.jobs)),
            "sha256": self.sha256,
        }


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def load_exam(path: Path) -> dict[str, Any]:
    """Load a frozen exam and enforce the v0.3 public execution boundary."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExamExecutionError(f"Invalid exam JSON: {exc.msg}") from exc
    if not isinstance(document, dict):
        raise ExamExecutionError("Exam must be a JSON object.")
    if document.get("status") != "ready-for-authorized-pilot":
        raise ExamExecutionError("Exam is not frozen for an authorized pilot.")
    directions = document.get("directions")
    if directions != list(V03_DIRECTIONS):
        raise ExamExecutionError("Exam directions do not match the frozen 18-direction policy.")
    if not isinstance(document.get("translation_tasks"), list):
        raise ExamExecutionError("Exam requires translation_tasks.")
    if not isinstance(document.get("execution_packs"), list):
        raise ExamExecutionError("Exam requires execution_packs.")
    return document


def _selected_directions(exam: dict[str, Any], requested: Iterable[str] | None) -> tuple[str, ...]:
    allowed = tuple(exam["directions"])
    selected = allowed if requested is None else tuple(dict.fromkeys(requested))
    unknown = sorted(set(selected) - set(allowed))
    if unknown:
        raise ExamExecutionError(f"Unknown directions: {', '.join(unknown)}")
    if not selected:
        raise ExamExecutionError("At least one direction is required.")
    return tuple(direction for direction in allowed if direction in selected)


def build_execution_plan(
    exam: dict[str, Any],
    *,
    directions: Iterable[str] | None = None,
    repetitions: int | None = None,
) -> ExecutionPlan:
    """Expand translation packs into stable, repeat-aware paid-call jobs."""
    selected = _selected_directions(exam, directions)
    configured_repetitions = exam.get("policy", {}).get("contestant_repetitions")
    repeats = configured_repetitions if repetitions is None else repetitions
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ExamExecutionError("repetitions must be a positive integer.")

    tasks = {task.get("id"): task for task in exam["translation_tasks"]}
    if None in tasks or len(tasks) != len(exam["translation_tasks"]):
        raise ExamExecutionError("Translation task IDs must be non-empty and unique.")

    jobs: list[dict[str, Any]] = []
    for repeat in range(1, repeats + 1):
        for pack in exam["execution_packs"]:
            if pack.get("mode") != "translation":
                continue
            direction = f"{pack.get('source_lang')}->{pack.get('target_lang')}"
            if direction not in selected:
                continue
            task_ids = pack.get("task_ids")
            if not isinstance(task_ids, list) or not task_ids:
                raise ExamExecutionError(f"Execution pack {pack.get('id')!r} has no tasks.")
            try:
                pack_tasks = [deepcopy(tasks[task_id]) for task_id in task_ids]
            except KeyError as exc:
                raise ExamExecutionError(
                    f"Execution pack {pack.get('id')!r} references unknown task {exc.args[0]!r}."
                ) from exc
            jobs.append(
                {
                    "id": f"{pack['id']}::repeat-{repeat}",
                    "pack_id": pack["id"],
                    "repeat": repeat,
                    "direction": direction,
                    "source_lang": pack["source_lang"],
                    "target_lang": pack["target_lang"],
                    "context": pack.get("context", ""),
                    "tasks": pack_tasks,
                }
            )

    if not jobs:
        raise ExamExecutionError("Selection produced no translation jobs.")
    exam_payload = deepcopy(exam)
    exam_hash = canonical_sha256(exam_payload)
    plan_payload = {
        "exam_id": exam.get("exam_id"),
        "exam_sha256": exam_hash,
        "repetitions": repeats,
        "directions": list(selected),
        "jobs": jobs,
    }
    return ExecutionPlan(
        exam_id=str(exam.get("exam_id")),
        exam_sha256=exam_hash,
        repetitions=repeats,
        directions=selected,
        jobs=tuple(jobs),
        sha256=canonical_sha256(plan_payload),
    )


def estimate_plan_cost(plan: ExecutionPlan, cost_per_call_usd: float) -> float:
    if cost_per_call_usd < 0:
        raise ExamExecutionError("cost_per_call_usd must be non-negative.")
    return round(len(plan.jobs) * cost_per_call_usd, 10)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_execution_plan(
    plan: ExecutionPlan,
    output_path: Path,
    transport: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    max_cost_usd: float,
    reserve_per_call_usd: float,
) -> dict[str, Any]:
    """Execute jobs once, checkpoint each response, and resume by plan fingerprint.

    ``reserve_per_call_usd`` is charged against the cap before transport is
    invoked. Exact provider cost, when returned as ``cost_usd``, replaces the
    reserve for subsequent calls. This makes a cap conservative without
    pretending estimates are observed spend.
    """
    if max_cost_usd < 0 or reserve_per_call_usd < 0:
        raise ExamExecutionError("Budget values must be non-negative.")
    if output_path.exists():
        report = json.loads(output_path.read_text(encoding="utf-8"))
        if report.get("plan_sha256") != plan.sha256:
            raise ExamExecutionError("Checkpoint belongs to a different execution plan.")
    else:
        report = {
            "schema_version": 1,
            "status": "running",
            "plan_sha256": plan.sha256,
            "exam_id": plan.exam_id,
            "exam_sha256": plan.exam_sha256,
            "directions": list(plan.directions),
            "repetitions": plan.repetitions,
            "planned_call_count": len(plan.jobs),
            "max_cost_usd": max_cost_usd,
            "reserve_per_call_usd": reserve_per_call_usd,
            "results": [],
        }
        _atomic_json(output_path, report)

    completed = {result["job_id"] for result in report["results"]}
    for job in plan.jobs:
        if job["id"] in completed:
            continue
        observed = sum(
            float(result["cost_usd"])
            for result in report["results"]
            if result.get("cost_usd") is not None
        )
        unknown_count = sum(result.get("cost_usd") is None for result in report["results"])
        committed = observed + unknown_count * reserve_per_call_usd
        if committed + reserve_per_call_usd > max_cost_usd:
            report["status"] = "budget_stopped"
            report["committed_cost_usd"] = round(committed, 10)
            _atomic_json(output_path, report)
            raise BudgetExceeded(f"Next call would exceed USD {max_cost_usd:.6f} budget cap.")
        response = transport(deepcopy(job))
        if not isinstance(response, dict):
            raise ExamExecutionError("Transport must return a JSON object.")
        cost = response.get("cost_usd")
        if cost is not None and (not isinstance(cost, (int, float)) or cost < 0):
            raise ExamExecutionError("Transport cost_usd must be non-negative or null.")
        report["results"].append({"job_id": job["id"], **deepcopy(response)})
        _atomic_json(output_path, report)

    report["status"] = "completed"
    report["completed_call_count"] = len(report["results"])
    report["observed_cost_usd"] = round(
        sum(float(result.get("cost_usd") or 0) for result in report["results"]), 10
    )
    report["cost_observation_count"] = sum(
        result.get("cost_usd") is not None for result in report["results"]
    )
    _atomic_json(output_path, report)
    return report


__all__ = [
    "BudgetExceeded",
    "ExamExecutionError",
    "ExecutionPlan",
    "V03_DIRECTIONS",
    "build_execution_plan",
    "canonical_sha256",
    "estimate_plan_cost",
    "load_exam",
    "run_execution_plan",
]

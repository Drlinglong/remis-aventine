"""Build a versioned Pilot Score aggregate from real Aventine artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from remis_aventine.tournament_scoring import (
    COVERAGE_POLICY_VERSION,
    PILOT_SCORE_VERSION,
    RECOVERABLE_TRANSLATION_MULTIPLIER,
    STAGE_POLICY_VERSION,
    calculate_decision_coverage,
    compute_pilot_score,
)


class PilotAggregateError(ValueError):
    """Raised when aggregate inputs do not form a comparable tournament."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotAggregateError(f"Unable to read JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotAggregateError(f"Expected a JSON object in {path}.")
    return value


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _hard_case_value(case: dict[str, Any]) -> Decimal:
    if case.get("execution_status") != "completed":
        return Decimal("0")
    hard = case.get("hard_validation") or {}
    metrics = case.get("automatic_metrics") or {}
    item_count_match = bool(metrics.get("item_count_match"))
    contract_pass = bool(metrics.get("parsed")) and item_count_match
    if bool(hard.get("passed")) and contract_pass:
        return Decimal("1")
    if case.get("track") == "translation" and item_count_match:
        return RECOVERABLE_TRANSLATION_MULTIPLIER
    return Decimal("0")


def _sum_usage(cases: list[dict[str, Any]]) -> dict[str, int]:
    keys = ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens")
    return {
        key: sum(int((case.get("usage") or {}).get(key) or 0) for case in cases) for key in keys
    }


def build_pilot_aggregate(manifest_path: Path) -> dict[str, Any]:
    """Consume three-run profiles and blinded pairwise reports."""

    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        raise PilotAggregateError("Pilot aggregate manifest schema_version must be 1.")
    base = manifest_path.parent
    profiles = manifest.get("profiles")
    report_values = manifest.get("pairwise_reports")
    if not isinstance(profiles, list) or len(profiles) < 2:
        raise PilotAggregateError("At least two profiles are required.")
    if not isinstance(report_values, list) or not report_values:
        raise PilotAggregateError("pairwise_reports must contain at least one report path.")

    states: dict[str, dict[str, Any]] = {}
    recipe_to_profile: dict[str, str] = {}
    fixture_hashes: set[str] = set()
    expected_run_count = int(manifest.get("expected_run_count", 3))

    for profile in profiles:
        if not isinstance(profile, dict):
            raise PilotAggregateError("Every profile entry must be an object.")
        profile_id = str(profile.get("id") or "").strip()
        run_values = profile.get("runs")
        if not profile_id or profile_id in states:
            raise PilotAggregateError(f"Invalid or duplicate profile id: {profile_id!r}.")
        if not isinstance(run_values, list) or len(run_values) != expected_run_count:
            raise PilotAggregateError(
                f"Profile {profile_id!r} must provide exactly {expected_run_count} runs."
            )
        runs = [_read_json(_resolve(base, str(value))) for value in run_values]
        if any(run.get("suite") != "remis" for run in runs):
            raise PilotAggregateError(f"Profile {profile_id!r} contains a non-Remis run.")
        recipe_ids = {str((run.get("recipe") or {}).get("id") or "") for run in runs}
        if len(recipe_ids) != 1 or "" in recipe_ids:
            raise PilotAggregateError(f"Profile {profile_id!r} runs do not share one recipe id.")
        recipe_id = recipe_ids.pop()
        if recipe_id in recipe_to_profile:
            raise PilotAggregateError(f"Recipe id {recipe_id!r} maps to more than one profile.")
        recipe_to_profile[recipe_id] = profile_id

        all_cases = [case for run in runs for case in run.get("cases", [])]
        if len(all_cases) == 0:
            raise PilotAggregateError(f"Profile {profile_id!r} has no cases.")
        for run in runs:
            snapshot = (run.get("recipe") or {}).get("snapshot") or {}
            if snapshot.get("fixture_sha256"):
                fixture_hashes.add(str(snapshot["fixture_sha256"]))
        hard_points = sum((_hard_case_value(case) for case in all_cases), Decimal("0"))
        hard_reliability = hard_points / Decimal(len(all_cases))
        states[profile_id] = {
            "definition": profile,
            "recipe_id": recipe_id,
            "runs": runs,
            "cases": all_cases,
            "hard_points": hard_points,
            "hard_reliability": hard_reliability,
            "soft": defaultdict(int),
            "opponents": set(),
        }

    if len(fixture_hashes) != 1:
        raise PilotAggregateError("All runs must share one frozen fixture hash.")

    judge_configs: dict[str, dict[str, Any]] = {}
    judge_telemetry = defaultdict(int)
    seen_pairs: set[tuple[str, str]] = set()
    for report_value in report_values:
        report_path = _resolve(base, str(report_value))
        report = _read_json(report_path)
        if report.get("suite") != "remis-pairwise-report":
            raise PilotAggregateError(f"Not a Remis pairwise report: {report_path}")
        recipes = report.get("recipes") or {}
        left_recipe = str((recipes.get("left") or {}).get("id") or "")
        right_recipe = str((recipes.get("right") or {}).get("id") or "")
        try:
            left = recipe_to_profile[left_recipe]
            right = recipe_to_profile[right_recipe]
        except KeyError as exc:
            raise PilotAggregateError(
                f"Report {report_path} references an unknown tournament recipe."
            ) from exc
        pair = tuple(sorted((left, right)))
        if pair in seen_pairs:
            raise PilotAggregateError(f"Duplicate pairwise report for {pair}.")
        seen_pairs.add(pair)
        states[left]["opponents"].add(right)
        states[right]["opponents"].add(left)

        judge_run = report.get("judge_run") or {}
        judge_telemetry["report_count"] += 1
        judge_telemetry["http_attempt_count"] += int(judge_run.get("http_attempt_count") or 0)
        judge_telemetry["failure_count"] += int(judge_run.get("failure_count") or 0)
        judge_telemetry["estimated_cost_micrormb"] += round(
            float(judge_run.get("estimated_cost_rmb") or 0) * 1_000_000
        )
        config = judge_run.get("configuration") or {}
        judge_config = {
            "provider": config.get("provider") or judge_run.get("provider"),
            "model": config.get("model") or judge_run.get("model"),
            "profile": config.get("profile") or judge_run.get("profile"),
            "prompt_revision": config.get("prompt_revision") or judge_run.get("prompt_revision"),
            "reasoning_effort": config.get("reasoning_effort") or judge_run.get("reasoning_effort"),
        }
        judge_configs[json.dumps(judge_config, sort_keys=True)] = judge_config

        for case in report.get("cases", []):
            source = str(case.get("decision_source") or "")
            winner = str(case.get("winner") or "")
            for profile_id in (left, right):
                states[profile_id]["soft"]["planned"] += 1
            if source != "judge_position_consistent":
                if source == "hard_validation":
                    states[left]["soft"]["hard_veto"] += 1
                    states[right]["soft"]["hard_veto"] += 1
                else:
                    states[left]["soft"]["unresolved"] += 1
                    states[right]["soft"]["unresolved"] += 1
                continue
            for profile_id in (left, right):
                states[profile_id]["soft"]["eligible"] += 1
                states[profile_id]["soft"]["resolved"] += 1
            if winner == "left":
                states[left]["soft"]["wins"] += 1
                states[right]["soft"]["losses"] += 1
            elif winner == "right":
                states[right]["soft"]["wins"] += 1
                states[left]["soft"]["losses"] += 1
            elif winner == "tie":
                states[left]["soft"]["ties"] += 1
                states[right]["soft"]["ties"] += 1
            else:
                raise PilotAggregateError(
                    f"Consistent judge decision in {report_path} has winner {winner!r}."
                )

    expected_opponents = len(states) - 1
    hard_case_counts = {len(state["cases"]) for state in states.values()}
    if len(hard_case_counts) != 1:
        raise PilotAggregateError("All profiles must provide the same number of hard cases.")
    entries: list[dict[str, Any]] = []
    for profile_id, state in states.items():
        if len(state["opponents"]) != expected_opponents:
            raise PilotAggregateError(
                f"Profile {profile_id!r} has {len(state['opponents'])}/{expected_opponents} "
                "pairwise opponents."
            )
        soft = state["soft"]
        resolved = soft["resolved"]
        if resolved == 0:
            raise PilotAggregateError(f"Profile {profile_id!r} has no resolved soft decisions.")
        soft_preference = (
            Decimal(soft["wins"]) + Decimal("0.5") * Decimal(soft["ties"])
        ) / Decimal(resolved)
        score = compute_pilot_score(soft_preference, state["hard_reliability"])
        coverage = calculate_decision_coverage(
            planned_decisions=soft["planned"],
            eligible_decisions=soft["planned"],
            resolved_decisions=resolved,
        )
        cases = state["cases"]
        definition = state["definition"]
        entries.append(
            {
                "profile_id": profile_id,
                "label": definition.get("label") or profile_id,
                "provider": definition.get("provider"),
                "model_id": definition.get("model_id"),
                "reasoning_label": definition.get("reasoning_label"),
                "recipe_id": state["recipe_id"],
                "run_artifacts": [
                    {
                        "run_id": run.get("run_id"),
                        "recipe_sha256": (run.get("recipe") or {}).get("sha256"),
                    }
                    for run in state["runs"]
                ],
                "score": score.to_dict(),
                "hard_reliability": {
                    "policy_version": STAGE_POLICY_VERSION,
                    "value": float(state["hard_reliability"]),
                    "points": float(state["hard_points"]),
                    "sample_count": len(cases),
                    "run_count": len(state["runs"]),
                    "hard_pass_count": sum(
                        bool((case.get("hard_validation") or {}).get("passed"))
                        and bool((case.get("automatic_metrics") or {}).get("parsed"))
                        and bool((case.get("automatic_metrics") or {}).get("item_count_match"))
                        for case in cases
                    ),
                },
                "soft_preference": {
                    "value": float(soft_preference),
                    "wins": soft["wins"],
                    "losses": soft["losses"],
                    "ties": soft["ties"],
                    "resolved_count": resolved,
                    "hard_veto_excluded_count": soft["hard_veto"],
                    "unresolved_count": soft["unresolved"],
                    "coverage": coverage.to_dict(),
                },
                "telemetry": {
                    "elapsed_seconds": round(
                        sum(
                            float((run.get("summary") or {}).get("elapsed_seconds") or 0)
                            for run in state["runs"]
                        ),
                        3,
                    ),
                    "usage": _sum_usage(cases),
                },
            }
        )

    entries.sort(key=lambda item: (-item["score"]["score"], item["profile_id"]))
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank
    return {
        "schema_version": 1,
        "suite": "remis-pilot-aggregate",
        "aggregate_id": manifest.get("aggregate_id") or manifest_path.stem,
        "score_version": PILOT_SCORE_VERSION,
        "preview": True,
        "fixture_sha256": next(iter(fixture_hashes)),
        "policies": {
            "score": PILOT_SCORE_VERSION,
            "stage": STAGE_POLICY_VERSION,
            "coverage": COVERAGE_POLICY_VERSION,
            "soft_preference": "judge-position-consistent-v0.1",
            "translation_failure_multiplier": float(RECOVERABLE_TRANSLATION_MULTIPLIER),
        },
        "sample_design": {
            "runs_per_profile": expected_run_count,
            "hard_cases_per_profile": hard_case_counts.pop(),
            "pairwise_repeat": 1,
            "profile_count": len(entries),
        },
        "judge_configurations": list(judge_configs.values()),
        "judge_telemetry": {
            "report_count": judge_telemetry["report_count"],
            "http_attempt_count": judge_telemetry["http_attempt_count"],
            "failure_count": judge_telemetry["failure_count"],
            "estimated_cost_rmb": round(judge_telemetry["estimated_cost_micrormb"] / 1_000_000, 6),
        },
        "entries": entries,
    }


def render_pilot_markdown(aggregate: dict[str, Any]) -> str:
    lines = [
        f"# {aggregate['aggregate_id']}",
        "",
        f"PREVIEW aggregate · `{aggregate['score_version']}` · {aggregate['fixture_sha256'][:12]}",
        "",
        "| Rank | Recipe | Score | Soft | Hard | W-L-T | Coverage | Time |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for entry in aggregate["entries"]:
        soft = entry["soft_preference"]
        hard = entry["hard_reliability"]
        coverage = soft["coverage"]["coverage"]
        lines.append(
            f"| {entry['rank']} | {entry['label']} | {entry['score']['score']:.2f} | "
            f"{100 * soft['value']:.1f}% | {100 * hard['value']:.1f}% | "
            f"{soft['wins']}-{soft['losses']}-{soft['ties']} | {100 * coverage:.1f}% | "
            f"{entry['telemetry']['elapsed_seconds']:.1f}s |"
        )
    lines.extend(
        [
            "",
            "Soft Preference 只计入双顺序一致的盲化裁决；硬门槛直接判定与未决样本不混入语言偏好。",
            "Hard Reliability 使用三轮结果：翻译阶段可恢复的硬校验或结构化失败计 0.67，"
            "修复阶段失败计 0。",
            "",
        ]
    )
    return "\n".join(lines)


def write_pilot_aggregate(
    manifest_path: Path, output_json: Path, output_markdown: Path
) -> dict[str, Any]:
    aggregate = build_pilot_aggregate(manifest_path)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(render_pilot_markdown(aggregate), encoding="utf-8")
    return aggregate

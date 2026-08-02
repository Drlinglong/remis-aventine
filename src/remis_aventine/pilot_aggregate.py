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

ANCHORED_SCORE_VERSION = "pilot-score-v0.2-anchored"
ANCHORED_SELECTION_MODE = "anchor-panel"
ANCHORED_SOFT_POLICY_VERSION = "judge-position-consistent-anchor-panel-v0.2"


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


def _wilson_interval(successes: Decimal, sample_count: int) -> dict[str, float | int]:
    """Return a deterministic 95% Wilson interval for a fractional match score."""
    if sample_count <= 0:
        return {"confidence": 0.95, "sample_count": 0, "lower": 0.0, "upper": 1.0}
    n = Decimal(sample_count)
    p = successes / n
    z = Decimal("1.96")
    z2 = z * z
    denominator = Decimal("1") + z2 / n
    center = (p + z2 / (Decimal("2") * n)) / denominator
    margin = z * (p * (Decimal("1") - p) / n + z2 / (Decimal("4") * n * n)).sqrt() / denominator
    return {
        "confidence": 0.95,
        "sample_count": sample_count,
        "lower": float(max(Decimal("0"), center - margin).quantize(Decimal("0.000001"))),
        "upper": float(min(Decimal("1"), center + margin).quantize(Decimal("0.000001"))),
    }


def _selection(manifest: dict[str, Any], profile_ids: set[str]) -> dict[str, Any]:
    policy = manifest.get("selection_policy")
    if policy is None:
        return {
            "mode": "round-robin",
            "revision": "round-robin-sha256-v1",
            "anchors": [],
            "challengers": sorted(profile_ids),
            "score_version": PILOT_SCORE_VERSION,
            "soft_policy": "judge-position-consistent-v0.1",
        }
    if not isinstance(policy, dict) or policy.get("mode") != ANCHORED_SELECTION_MODE:
        raise PilotAggregateError(
            f"selection_policy.mode must be {ANCHORED_SELECTION_MODE!r} when provided."
        )
    anchors = policy.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 3:
        raise PilotAggregateError("anchor-panel selection requires exactly three anchors.")
    normalized_anchors = [str(value).strip() for value in anchors]
    if "" in normalized_anchors or len(set(normalized_anchors)) != 3:
        raise PilotAggregateError("anchor-panel anchors must be three unique profile ids.")
    unknown = set(normalized_anchors) - profile_ids
    if unknown:
        raise PilotAggregateError(f"anchor-panel references unknown anchors: {sorted(unknown)}.")
    challengers = sorted(profile_ids - set(normalized_anchors))
    if not challengers:
        raise PilotAggregateError("anchor-panel requires at least one challenger profile.")
    revision = str(policy.get("revision") or "").strip()
    if not revision:
        raise PilotAggregateError("anchor-panel selection requires a non-empty revision.")
    return {
        "mode": ANCHORED_SELECTION_MODE,
        "revision": revision,
        "anchors": normalized_anchors,
        "challengers": challengers,
        "score_version": ANCHORED_SCORE_VERSION,
        "soft_policy": ANCHORED_SOFT_POLICY_VERSION,
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
    profile_ids = [
        str(profile.get("id") or "").strip() for profile in profiles if isinstance(profile, dict)
    ]
    selection = _selection(manifest, set(profile_ids))
    anchor_ids = set(selection["anchors"])
    challenger_ids = set(selection["challengers"])

    for profile in profiles:
        if not isinstance(profile, dict):
            raise PilotAggregateError("Every profile entry must be an object.")
        profile_id = str(profile.get("id") or "").strip()
        run_values = profile.get("runs")
        if not profile_id or profile_id in states:
            raise PilotAggregateError(f"Invalid or duplicate profile id: {profile_id!r}.")
        required_run_count = (
            1
            if selection["mode"] == ANCHORED_SELECTION_MODE and profile_id in anchor_ids
            else expected_run_count
        )
        if not isinstance(run_values, list) or len(run_values) != required_run_count:
            raise PilotAggregateError(
                f"Profile {profile_id!r} must provide exactly {required_run_count} runs."
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
        recipe_hashes = {str((run.get("recipe") or {}).get("sha256") or "") for run in runs}
        if len(recipe_hashes) != 1 or "" in recipe_hashes:
            raise PilotAggregateError(f"Profile {profile_id!r} runs do not share one recipe SHA.")
        run_ids = {str(run.get("run_id") or "") for run in runs}
        if "" in run_ids or len(run_ids) != len(runs):
            raise PilotAggregateError(f"Profile {profile_id!r} runs require unique run ids.")

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
            "recipe_sha256": recipe_hashes.pop(),
            "run_ids": run_ids,
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
        for side_name, profile_id in (("left", left), ("right", right)):
            reported = recipes.get(side_name) or {}
            if (
                reported.get("sha256") != states[profile_id]["recipe_sha256"]
                or reported.get("run_id") not in states[profile_id]["run_ids"]
            ):
                raise PilotAggregateError(
                    f"Report {report_path} {side_name} provenance does not match selected runs."
                )
        pair = tuple(sorted((left, right)))
        if pair in seen_pairs:
            raise PilotAggregateError(f"Duplicate pairwise report for {pair}.")
        seen_pairs.add(pair)
        if selection["mode"] == ANCHORED_SELECTION_MODE and not (
            (left in anchor_ids and right in challenger_ids)
            or (right in anchor_ids and left in challenger_ids)
        ):
            raise PilotAggregateError(
                f"Anchor-panel report {report_path} must connect one anchor and one challenger."
            )
        states[left]["opponents"].add(right)
        states[right]["opponents"].add(left)

        judge_run = report.get("judge_run") or {}
        judge_telemetry["report_count"] += 1
        judge_telemetry["http_attempt_count"] += int(
            judge_run.get("cumulative_http_attempt_count")
            or judge_run.get("http_attempt_count")
            or 0
        )
        judge_telemetry["failure_count"] += int(judge_run.get("failure_count") or 0)
        judge_telemetry["estimated_cost_micrormb"] += round(
            float(
                judge_run.get("cumulative_estimated_cost_rmb")
                or judge_run.get("estimated_cost_rmb")
                or 0
            )
            * 1_000_000
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
            if source == "hard_validation":
                states[left]["soft"]["hard_veto"] += 1
                states[right]["soft"]["hard_veto"] += 1
                continue
            for profile_id in (left, right):
                states[profile_id]["soft"]["planned"] += 1
            if source != "judge_position_consistent":
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

    hard_case_counts = {len(states[profile_id]["cases"]) for profile_id in challenger_ids}
    if len(hard_case_counts) != 1:
        raise PilotAggregateError("All profiles must provide the same number of hard cases.")
    entries: list[dict[str, Any]] = []
    entry_ids = selection["challengers"]
    for profile_id in entry_ids:
        state = states[profile_id]
        required_opponents = (
            anchor_ids
            if selection["mode"] == ANCHORED_SELECTION_MODE
            else set(states) - {profile_id}
        )
        if state["opponents"] != required_opponents:
            raise PilotAggregateError(
                f"Profile {profile_id!r} has pairwise opponents "
                f"{sorted(state['opponents'])}; expected {sorted(required_opponents)}."
            )
        soft = state["soft"]
        resolved = soft["resolved"]
        if resolved == 0:
            raise PilotAggregateError(f"Profile {profile_id!r} has no resolved soft decisions.")
        soft_preference = (
            Decimal(soft["wins"]) + Decimal("0.5") * Decimal(soft["ties"])
        ) / Decimal(resolved)
        score = compute_pilot_score(
            soft_preference,
            state["hard_reliability"],
            score_version=selection["score_version"],
        )
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
                **(
                    {"model_provenance": definition["model_provenance"]}
                    if definition.get("model_provenance") is not None
                    else {}
                ),
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
                    **(
                        {
                            "confidence_interval": _wilson_interval(
                                Decimal(soft["wins"]) + Decimal("0.5") * Decimal(soft["ties"]),
                                resolved,
                            ),
                            "status": (
                                "complete" if coverage.coverage == Decimal("1") else "provisional"
                            ),
                            "opponents": sorted(state["opponents"]),
                        }
                        if selection["mode"] == ANCHORED_SELECTION_MODE
                        else {}
                    ),
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
    sample_design = {
        "runs_per_profile": expected_run_count,
        "hard_cases_per_profile": hard_case_counts.pop(),
        "pairwise_repeat": 1,
        "profile_count": len(entries),
    }
    if selection["mode"] == ANCHORED_SELECTION_MODE:
        sample_design.update(
            {
                "profile_count": len(states),
                "scored_profile_count": len(entries),
                "anchor_count": len(anchor_ids),
                "challenger_count": len(challenger_ids),
            }
        )

    aggregate = {
        "schema_version": 1,
        "suite": "remis-pilot-aggregate",
        "aggregate_id": manifest.get("aggregate_id") or manifest_path.stem,
        "score_version": selection["score_version"],
        "preview": True,
        "fixture_sha256": next(iter(fixture_hashes)),
        "policies": {
            "score": selection["score_version"],
            "stage": STAGE_POLICY_VERSION,
            "coverage": COVERAGE_POLICY_VERSION,
            "soft_preference": selection["soft_policy"],
            "translation_failure_multiplier": float(RECOVERABLE_TRANSLATION_MULTIPLIER),
        },
        "sample_design": sample_design,
        "judge_configurations": list(judge_configs.values()),
        "judge_telemetry": {
            "report_count": judge_telemetry["report_count"],
            "http_attempt_count": judge_telemetry["http_attempt_count"],
            "failure_count": judge_telemetry["failure_count"],
            "estimated_cost_rmb": round(judge_telemetry["estimated_cost_micrormb"] / 1_000_000, 6),
        },
        "entries": entries,
    }
    if selection["mode"] == ANCHORED_SELECTION_MODE:
        aggregate["selection_policy"] = {
            "mode": selection["mode"],
            "revision": selection["revision"],
            "placement_scope": "challengers-only",
            "anchors": [
                {
                    "profile_id": profile_id,
                    "label": states[profile_id]["definition"].get("label") or profile_id,
                    "recipe_id": states[profile_id]["recipe_id"],
                    "recipe_sha256": states[profile_id]["recipe_sha256"],
                }
                for profile_id in selection["anchors"]
            ],
            "challengers": selection["challengers"],
        }
    return aggregate


def render_pilot_markdown(aggregate: dict[str, Any]) -> str:
    selection = aggregate.get("selection_policy") or {}
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
            *(
                [
                    "Anchor panel："
                    + "、".join(anchor["label"] for anchor in selection.get("anchors", [])),
                    "Placement scope：本表排名只比较本批 challengers，不等同于全榜单名次。",
                ]
                if selection.get("mode") == ANCHORED_SELECTION_MODE
                else []
            ),
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

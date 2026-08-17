"""Aventine v0.3 routing policy for recipe contracts and game syntax."""

from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from typing import Any

PROTECTED_TOKEN_RE = re.compile(r"\$[^$\r\n]+\$|\[[^\[\]\r\n]+\]|§.|#!|#[A-Za-z][\w.-]*|\\n")

PUNCTUATION_PATTERNS = {
    "ascii_before_cjk_open_quote": re.compile(r'["\'](?=[“‘])'),
    "ascii_after_cjk_close_quote": re.compile(r'(?<=[”’])["\']'),
    "escaped_unicode_quote": re.compile(r"\\[“”‘’]"),
}

_SYNTAX_FAILURE_CODES = frozenset(
    {
        "validation_format_marker_parity_mismatch",
        "validation_mismatched_tags",
        "validation_unknown_formatting_tag",
        "validation_unclosed_color_tag",
        "validation_invalid_concept_syntax",
    }
)
_VARIABLE_PARITY_CODES = frozenset(
    {
        "validation_variable_parity_mismatch",
        "validation_vic3_variable_parity_mismatch",
    }
)


def protected_token_delta(source: str, output: str) -> dict[str, Any]:
    source = (source or "").replace("[[*QT*]]", "")
    output = (output or "").replace("[[*QT*]]", "")
    expected = Counter(PROTECTED_TOKEN_RE.findall(source))
    actual = Counter(PROTECTED_TOKEN_RE.findall(output))
    missing = sorted((expected - actual).elements())
    extra = sorted((actual - expected).elements())
    return {"passed": not missing and not extra, "missing": missing, "extra": extra}


def punctuation_warnings(text: str) -> list[dict[str, Any]]:
    """Return high-signal warnings; punctuation never vetoes a result here."""
    warnings = []
    for code, pattern in PUNCTUATION_PATTERNS.items():
        matches = [match.group(0) for match in pattern.finditer(text or "")]
        if matches:
            warnings.append({"code": code, "count": len(matches), "matches": matches})
    for opening, closing, code in (
        ("“", "”", "cjk_double_quote_imbalance"),
        ("‘", "’", "cjk_single_quote_imbalance"),
    ):
        if text.count(opening) != text.count(closing):
            warnings.append(
                {
                    "code": code,
                    "opening_count": text.count(opening),
                    "closing_count": text.count(closing),
                }
            )
    return warnings


def classify_structural_result(
    *,
    source: str,
    raw_contract_pass: bool,
    final_contract_pass: bool,
    final_output: str,
    normalization_operations: list[dict[str, Any]] | None = None,
    validator_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Separate recipe recovery, deterministic failure, and judgeable suspicion.

    Error-level variable-count findings are deliberately routed to structural
    adjudication when the final text remains syntactically legal. Other
    error-level findings remain hard failures.
    """
    if not isinstance(raw_contract_pass, bool) or not isinstance(final_contract_pass, bool):
        raise ValueError("Contract pass fields must be booleans.")
    findings = deepcopy(validator_findings or [])
    token_delta = protected_token_delta(source, final_output)
    deterministic_failures: list[dict[str, Any]] = []
    suspicious: list[dict[str, Any]] = []
    warnings = punctuation_warnings(final_output)

    if not final_contract_pass:
        deterministic_failures.append({"code": "final_contract_failure"})

    for finding in findings:
        code = finding.get("code")
        level = str(finding.get("level", "")).lower()
        if code in _VARIABLE_PARITY_CODES:
            suspicious.append(finding)
        elif code in _SYNTAX_FAILURE_CODES or level == "error":
            deterministic_failures.append(finding)
        else:
            warnings.append(finding)

    if not token_delta["passed"] and not any(
        finding.get("code") in _VARIABLE_PARITY_CODES for finding in suspicious
    ):
        suspicious.append({"code": "protected_token_count_changed", **token_delta})

    if deterministic_failures:
        route = "hard_fail"
        hard_pass = False
    elif suspicious:
        route = "structural_judges"
        hard_pass = None
    else:
        route = "pass"
        hard_pass = True

    return {
        "raw_contract_pass": raw_contract_pass,
        "normalization_applied": bool(normalization_operations),
        "normalization_operations": deepcopy(normalization_operations or []),
        "final_contract_pass": final_contract_pass,
        "token_delta": token_delta,
        "route": route,
        "hard_pass": hard_pass,
        "deterministic_failures": deterministic_failures,
        "structural_review_queue": suspicious,
        "punctuation_warnings": warnings,
    }


def resolve_structural_judges(
    classification: dict[str, Any], decisions: list[str]
) -> dict[str, Any]:
    """Resolve two independent structural decisions without a casting vote."""
    result = deepcopy(classification)
    if result.get("route") != "structural_judges":
        if decisions:
            raise ValueError("Judge decisions are only valid for structural_judges routes.")
        return result
    if len(decisions) != 2 or any(
        value not in {"acceptable", "lost_or_added"} for value in decisions
    ):
        raise ValueError("Exactly two structural decisions are required.")
    result["structural_judge_decisions"] = list(decisions)
    if decisions[0] == decisions[1]:
        result["route"] = "pass" if decisions[0] == "acceptable" else "hard_fail"
        result["hard_pass"] = decisions[0] == "acceptable"
        result["resolution"] = "judge_agreement"
    else:
        result["route"] = "unresolved"
        result["hard_pass"] = None
        result["resolution"] = "judge_disagreement"
    return result


__all__ = [
    "classify_structural_result",
    "protected_token_delta",
    "punctuation_warnings",
    "resolve_structural_judges",
]

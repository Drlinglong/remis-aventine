from __future__ import annotations

import pytest

from remis_aventine.structural_validation import (
    classify_structural_result,
    protected_token_delta,
    punctuation_warnings,
    resolve_structural_judges,
)


def test_syntax_break_is_deterministic_failure() -> None:
    result = classify_structural_result(
        source="§HText§!",
        raw_contract_pass=True,
        final_contract_pass=True,
        final_output="§H文本",
        validator_findings=[{"level": "error", "code": "validation_format_marker_parity_mismatch"}],
    )

    assert result["route"] == "hard_fail"
    assert result["hard_pass"] is False


def test_legal_variable_count_change_goes_to_two_structural_judges() -> None:
    result = classify_structural_result(
        source="[Name] saw [Name].",
        raw_contract_pass=True,
        final_contract_pass=True,
        final_output="[Name]到场了。",
        validator_findings=[{"level": "error", "code": "validation_variable_parity_mismatch"}],
    )

    assert result["route"] == "structural_judges"
    assert result["hard_pass"] is None
    assert resolve_structural_judges(result, ["acceptable", "acceptable"])["hard_pass"] is True
    assert (
        resolve_structural_judges(result, ["lost_or_added", "lost_or_added"])["hard_pass"] is False
    )
    unresolved = resolve_structural_judges(result, ["acceptable", "lost_or_added"])
    assert unresolved["route"] == "unresolved"
    assert unresolved["hard_pass"] is None


def test_parser_recovery_is_recorded_without_failing_final_delivery() -> None:
    result = classify_structural_result(
        source="[[*QT*]]Text[[*QT*]]",
        raw_contract_pass=False,
        final_contract_pass=True,
        final_output="“文本”",
        normalization_operations=[{"operation": "repair_quote_placeholder_spacing"}],
    )

    assert result["raw_contract_pass"] is False
    assert result["normalization_applied"] is True
    assert result["final_contract_pass"] is True
    assert result["route"] == "pass"
    assert result["hard_pass"] is True


def test_clean_result_passes_and_warnings_do_not_veto() -> None:
    result = classify_structural_result(
        source="Text",
        raw_contract_pass=True,
        final_contract_pass=True,
        final_output='"“文本”"',
    )

    assert result["route"] == "pass"
    assert result["hard_pass"] is True
    assert result["punctuation_warnings"]


def test_protected_token_delta_tracks_multiplicity() -> None:
    assert protected_token_delta("[Name] [Name] $term$", "[Name] $term$") == {
        "passed": False,
        "missing": ["[Name]"],
        "extra": [],
    }


def test_punctuation_hygiene_only_reports_high_signal_shapes() -> None:
    codes = {item["code"] for item in punctuation_warnings("\\“Text” and “open")}
    assert "escaped_unicode_quote" in codes
    assert "cjk_double_quote_imbalance" in codes


def test_structural_resolution_rejects_bad_decision_contract() -> None:
    clean = classify_structural_result(
        source="Text",
        raw_contract_pass=True,
        final_contract_pass=True,
        final_output="文本",
    )
    with pytest.raises(ValueError, match="only valid"):
        resolve_structural_judges(clean, ["acceptable"])

    suspicious = classify_structural_result(
        source="[Name] [Name]",
        raw_contract_pass=True,
        final_contract_pass=True,
        final_output="[Name]",
    )
    with pytest.raises(ValueError, match="Exactly two"):
        resolve_structural_judges(suspicious, ["acceptable"])

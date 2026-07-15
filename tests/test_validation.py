from __future__ import annotations

import json
from pathlib import Path

import pytest

from remis_aventine.validation import (
    DocumentValidationError,
    load_schema,
    validate_document,
    validate_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_RECIPE = PROJECT_ROOT / "examples" / "recipes" / "remis-lm-studio.example.json"


def test_example_recipe_matches_schema() -> None:
    document = validate_document(EXAMPLE_RECIPE, "recipe-manifest.schema.json")

    assert document["validator_policy"]["mode"] == "veto"
    assert [stage["kind"] for stage in document["stages"]] == ["translate", "repair"]


def test_veto_policy_requires_validator_profile(tmp_path) -> None:
    document = json.loads(EXAMPLE_RECIPE.read_text(encoding="utf-8"))
    document["validator_policy"] = {"mode": "veto"}
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document(path, "recipe-manifest.schema.json")

    assert any("profile" in issue for issue in exc_info.value.issues)


def test_disabled_validators_do_not_require_profile(tmp_path) -> None:
    document = json.loads(EXAMPLE_RECIPE.read_text(encoding="utf-8"))
    document["validator_policy"] = {"mode": "disabled"}
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    validated = validate_document(path, "recipe-manifest.schema.json")

    assert validated["validator_policy"] == {"mode": "disabled"}


def test_invalid_json_has_location(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(DocumentValidationError, match="line 1, column 2"):
        validate_document(path, "recipe-manifest.schema.json")


def test_unknown_schema_is_rejected() -> None:
    with pytest.raises(FileNotFoundError, match="Unknown Aventine schema"):
        load_schema("missing.schema.json")


def test_judge_schema_accepts_single_result_and_rejects_wrong_candidate() -> None:
    fixture = json.loads(
        (PROJECT_ROOT / "examples" / "calibration" / "fake-mqm-v1.json").read_text(encoding="utf-8")
    )
    judge = fixture["cases"][1]["judge_output"]

    assert validate_payload(judge, "judge-result.schema.json")["evaluation"]["verdict"] == "fail"

    judge["evaluation"]["errors"][0]["candidate"] = "candidate_a"
    with pytest.raises(DocumentValidationError) as exc_info:
        validate_payload(judge, "judge-result.schema.json")

    assert any("candidate" in issue for issue in exc_info.value.issues)

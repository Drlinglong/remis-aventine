from __future__ import annotations

import copy
import json

import pytest

from remis_aventine.adapters.remis import (
    RemisCompatibilityError,
    adapt_remis_result,
    convert_remis_result,
)
from remis_aventine.validation import validate_payload


def _remis_artifact() -> dict:
    return {
        "schema_version": 1,
        "benchmark": "Synthetic Remis benchmark",
        "fixture_sha256": "f" * 64,
        "created_at_utc": "2026-07-15T01:00:12.500000Z",
        "provider": "lm_studio",
        "model_id": "example/model",
        "model_label": "Example Model",
        "track": "all",
        "policy": {"first_pass_format_failure": "measurement"},
        "summary": {"case_count": 3, "elapsed_seconds": 12.5},
        "results": [
            {
                "id": "hard-failure",
                "track": "translation",
                "source_file": "fixture.yml",
                "source_sha256": "a" * 64,
                "source_lang": "en",
                "target_lang": "zh-CN",
                "prompt_sha256": "b" * 64,
                "focus": ["protected tokens"],
                "execution_failure": None,
                "elapsed_seconds": 4.0,
                "raw_response": "must not be copied",
                "outputs": ["candidate"],
                "score": {
                    "parsed": True,
                    "item_count_match": True,
                    "hard_pass": False,
                    "quality_constraint_pass": False,
                    "items": [
                        {
                            "key": "entry:0",
                            "validation": [{"code": "missing_tag"}],
                            "token_parity": {
                                "passed": False,
                                "missing": ["§!"],
                                "extra": [],
                            },
                        }
                    ],
                },
            },
            {
                "id": "structured-failure",
                "track": "translation",
                "execution_failure": None,
                "elapsed_seconds": 3.0,
                "outputs": None,
                "score": {"parsed": False, "item_count_match": False},
            },
            {
                "id": "execution-failure",
                "track": "repair",
                "execution_failure": "provider timeout",
                "elapsed_seconds": 5.5,
                "outputs": None,
                "score": None,
            },
        ],
    }


def test_convert_remis_result_normalizes_status_and_provenance() -> None:
    converted = convert_remis_result(_remis_artifact())

    validate_payload(converted, "run-result.schema.json")
    assert converted["run_id"] == "remis-20260715T010012Z-example-model"
    assert converted["started_at"] == "2026-07-15T01:00:00Z"
    assert converted["recipe"]["provenance"] == "compatibility_snapshot"
    assert converted["recipe"]["id"] == "remis.lm-studio.example-model.all"
    assert len(converted["recipe"]["sha256"]) == 64
    assert [case["execution_status"] for case in converted["cases"]] == [
        "completed",
        "structured_output_failure",
        "execution_failure",
    ]
    assert converted["summary"]["hard_pass_count"] == 0
    assert converted["summary"]["structured_output_failure_count"] == 1
    assert converted["cases"][0]["hard_validation"]["passed"] is False
    assert converted["cases"][1]["hard_validation"]["passed"] is None
    assert converted["cases"][0]["hard_validation"]["findings"][0]["code"] == "missing_tag"
    assert all("raw_response" not in case for case in converted["cases"])


def test_recipe_snapshot_hash_is_stable_and_override_is_supported() -> None:
    first = convert_remis_result(_remis_artifact(), recipe_id="custom.recipe")
    second = convert_remis_result(_remis_artifact(), recipe_id="custom.recipe")

    assert first["recipe"] == second["recipe"]
    assert first["recipe"]["id"] == "custom.recipe"


def test_openrouter_model_id_is_safe_in_recipe_identity() -> None:
    artifact = _remis_artifact()
    artifact.update(
        provider="openrouter",
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
        model_label="Nemotron 3 Ultra",
    )

    first = convert_remis_result(artifact)
    second = convert_remis_result(artifact)

    assert first["recipe"]["id"] == ("remis.openrouter.nvidia-nemotron-3-ultra-550b-a55b-free.all")
    assert first["recipe"]["snapshot"]["model_id"] == artifact["model_id"]
    assert len(first["recipe"]["sha256"]) == 64
    assert first["recipe"] == second["recipe"]


def test_public_artifact_drops_sensitive_fields_before_snapshot_hash() -> None:
    clean = _remis_artifact()
    clean.update(
        provider="openrouter",
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
        model_label="Nemotron 3 Ultra",
    )
    with_sensitive_fields = copy.deepcopy(clean)
    with_sensitive_fields["policy"].update(
        {
            "endpoint": "https://openrouter.example/v1/chat/completions",
            "OPENROUTER_API_KEY": "sk-test-openrouter",
            "raw_response": "provider payload",
            "nested": {"authorization": "Bearer secret"},
        }
    )
    with_sensitive_fields["summary"].update(
        {
            "endpoint": "https://summary.example",
            "credentials": {"token": "secret-token"},
            "raw_response": "summary payload",
        }
    )
    with_sensitive_fields["results"][0]["outputs"] = [
        {
            "text": "candidate",
            "endpoint": "https://output.example",
            "api_key": "sk-test-output",
            "raw_response": "output payload",
        }
    ]
    with_sensitive_fields["results"][0]["score"].update(
        {
            "endpoint": "https://score.example",
            "api_key": "sk-test-score",
            "raw_response": "score payload",
        }
    )
    with_sensitive_fields["results"][0]["score"]["items"][0]["validation"][0].update(
        {
            "endpoint": "https://finding.example",
            "credential": "finding-secret",
            "raw_response": "finding payload",
        }
    )

    clean_converted = convert_remis_result(clean)
    converted = convert_remis_result(with_sensitive_fields)
    serialized = json.dumps(converted, ensure_ascii=False, sort_keys=True)

    assert converted["recipe"] == clean_converted["recipe"]
    assert converted["recipe"]["snapshot"]["policy"] == {"first_pass_format_failure": "measurement"}
    assert converted["summary"]["source_summary"] == {
        "case_count": 3,
        "elapsed_seconds": 12.5,
    }
    assert converted["cases"][0]["candidate_outputs"] == [{"text": "candidate"}]
    for marker in (
        "openrouter.example",
        "sk-test-openrouter",
        "summary.example",
        "secret-token",
        "provider payload",
        "output payload",
        "finding-secret",
    ):
        assert marker not in serialized


def test_adapter_preserves_safe_pairwise_and_repair_evidence() -> None:
    artifact = _remis_artifact()
    result = artifact["results"][0]
    result.update(
        track="repair",
        broken_translation=["旧译"],
        reference_translation=["新译"],
        injected_errors=[{"code": "missing_token", "item": 0}],
        broken_validation=[{"code": "missing_token"}],
    )
    result["score"]["items"][0]["source"] = "source"
    result["score"]["valid_items_unchanged"] = False

    converted = convert_remis_result(artifact)
    case = converted["cases"][0]

    assert converted["environment"]["adapter_revision"] == "remis-translation-quality-v3"
    assert case["source_inputs"] == ["source"]
    assert case["repair_evidence"]["broken_translation"] == ["旧译"]
    assert case["repair_evidence"]["reference_translation"] == ["新译"]
    assert "raw_response" not in case


def test_adapter_writes_valid_result(tmp_path) -> None:
    input_path = tmp_path / "remis.json"
    output_path = tmp_path / "nested" / "aventine.json"
    input_path.write_text(json.dumps(_remis_artifact()), encoding="utf-8")

    converted = adapt_remis_result(input_path, output_path)

    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8")) == converted


def test_adapter_reports_invalid_json(tmp_path) -> None:
    input_path = tmp_path / "broken.json"
    input_path.write_text("{", encoding="utf-8")

    with pytest.raises(RemisCompatibilityError, match="line 1, column 2"):
        adapt_remis_result(input_path, tmp_path / "output.json")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data.update(schema_version=2), "schema_version 1"),
        (lambda data: data.update(results={}), "results must be an array"),
        (lambda data: data.update(provider=""), "provider"),
        (lambda data: data.update(created_at_utc="yesterday"), "Invalid Remis"),
        (lambda data: data.update(summary=[]), "summary must be an object"),
        (
            lambda data: data["summary"].update(elapsed_seconds=-1),
            "elapsed_seconds must be non-negative",
        ),
        (lambda data: data["results"].append("invalid"), "entry must be an object"),
    ],
)
def test_adapter_rejects_unsupported_contracts(mutate, message) -> None:
    artifact = _remis_artifact()
    mutate(artifact)

    with pytest.raises(RemisCompatibilityError, match=message):
        convert_remis_result(artifact)


def test_adapter_rejects_non_object() -> None:
    with pytest.raises(RemisCompatibilityError, match="must be a JSON object"):
        convert_remis_result([])  # type: ignore[arg-type]

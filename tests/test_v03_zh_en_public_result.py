import copy
import json
from pathlib import Path

import pytest

from remis_aventine.validation import (
    DocumentValidationError,
    validate_document,
    validate_payload,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "web" / "public" / "data" / "v03-zh-en-results.json"
SCHEMA_NAME = "v03-zh-en-public-result.schema.json"


def test_published_zh_en_result_satisfies_its_public_contract() -> None:
    payload = validate_document(RESULT, SCHEMA_NAME)

    assert payload["artifact_id"] == "v0.3-zh-en-results"
    assert payload["protocol"] == "aventine-v0.3-zh-en-balanced-degree4-sample20-60soft-40hard"
    assert payload["score_version"] == "v0.3-zh-en-60soft-40hard"
    assert payload["direction_count"] == 2
    assert payload["contestant_count"] == len(payload["profiles"]) == 17
    assert (
        payload["soft_resolved_count"] + payload["soft_unresolved_count"]
        == payload["soft_case_count"]
    )
    assert len({profile["model_id"] for profile in payload["profiles"]}) == 17
    assert len({profile["execution_identity_sha256"] for profile in payload["profiles"]}) == 17


def test_published_zh_en_contract_is_strict_and_distinct_from_multilingual_contract() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    modified = copy.deepcopy(payload)
    modified["unexpected_contract_field"] = True

    with pytest.raises(DocumentValidationError) as exc_info:
        validate_payload(modified, SCHEMA_NAME)

    assert any("Additional properties are not allowed" in issue for issue in exc_info.value.issues)
    with pytest.raises(DocumentValidationError):
        validate_payload(payload, "v03-public-result.schema.json")

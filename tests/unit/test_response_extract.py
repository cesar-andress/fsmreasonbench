"""Tests for submission JSON extraction from model text."""

from __future__ import annotations

import json

import pytest

from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.runners.response_extract import extract_submission_payload


def _c2_payload(*, item_id: str = "abc") -> dict:
    return {
        "item_id": item_id,
        "verdict": True,
        "certificate": {
            "certificate_type": "trace_witness",
            "version": "1.0",
            "payload": {
                "trace": ["a"],
                "state_sequence": ["q0", "q1"],
            },
        },
    }


def test_extract_fenced_json() -> None:
    payload = _c2_payload()
    raw = "```json\n" + json.dumps(payload) + "\n```"
    assert extract_submission_payload(raw) == payload


def test_extract_prose_before_and_after_json() -> None:
    payload = _c2_payload()
    raw = "Here is my answer:\n" + json.dumps(payload) + "\nDone."
    assert extract_submission_payload(raw) == payload


def test_extract_first_balanced_object_when_trailing_prose() -> None:
    payload = _c2_payload()
    raw = json.dumps(payload) + '\nExtra note: {"ignored": true}'
    assert extract_submission_payload(raw) == payload


def test_extract_certificate_json_object_string() -> None:
    certificate = {
        "certificate_type": "trace_witness",
        "version": "1.0",
        "payload": {"trace": ["a"], "state_sequence": ["q0", "q1"]},
    }
    payload = {
        "item_id": "abc",
        "verdict": True,
        "certificate": json.dumps(certificate),
    }
    extracted = extract_submission_payload(json.dumps(payload))
    assert extracted["certificate"] == certificate
    result = parse_submission(extracted, "C2")
    assert result.extractable is True


def test_certificate_plain_text_remains_not_extractable() -> None:
    payload = {
        "item_id": "abc",
        "verdict": True,
        "certificate": "not valid json object text",
    }
    extracted = extract_submission_payload(json.dumps(payload))
    assert extracted["certificate"] == "not valid json object text"
    result = parse_submission(extracted, "C2")
    assert result.extractable is False
    assert "certificate must be an object" in result.errors


def test_certificate_null_remains_not_extractable() -> None:
    payload = {"item_id": "abc", "verdict": True, "certificate": None}
    extracted = extract_submission_payload(json.dumps(payload))
    assert extracted["certificate"] is None
    result = parse_submission(extracted, "F1")
    assert result.extractable is False


def test_certificate_list_remains_not_extractable() -> None:
    payload = {"item_id": "abc", "verdict": False, "certificate": []}
    extracted = extract_submission_payload(json.dumps(payload))
    result = parse_submission(extracted, "F1")
    assert result.extractable is False


def test_truncated_fenced_json_returns_raw_string() -> None:
    raw = '```json\n{"item_id": "x", "verdict": false, "certificate": {'
    extracted = extract_submission_payload(raw)
    assert isinstance(extracted, str)


@pytest.mark.parametrize(
    ("provider", "expected_phrase"),
    [
        ("gemini", "Return ONLY one JSON object"),
        ("ollama", None),
        (None, None),
    ],
)
def test_render_prompt_gemini_strict_contract(
    provider: str | None,
    expected_phrase: str | None,
) -> None:
    from fsmreasonbench.generator.reachability import generate_reachability_item
    from fsmreasonbench.runners.prompts import render_prompt

    item = generate_reachability_item(42)
    prompt = render_prompt(item, provider=provider)
    if expected_phrase is None:
        assert "Return ONLY one JSON object" not in prompt
    else:
        assert expected_phrase in prompt
        assert "responseMimeType" not in prompt

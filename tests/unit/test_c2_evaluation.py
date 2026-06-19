"""End-to-end C2 evaluation: parser, scoring, transcripts, rescore."""

import json

import pytest

from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.parser import parse_c2_response
from fsmreasonbench.evaluator.scorer import score_c2_item
from fsmreasonbench.evaluator.transcript import record_transcript, rescore_transcript
from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_item,
)

EXAMPLES = pytest.mark.parametrize(
    "item_path",
    [
        "examples/item_C2_reachability_seed42.json",
    ],
)


def _load_example_item(name: str):
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    return load_item(root / name)


def test_extractable_correct_positive_scores_correct() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }
    record = score_c2_item(item, submission)
    assert record.extractable is True
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


def test_extractable_correct_negative_scores_correct() -> None:
    item = generate_reachability_item(
        43,
        ReachabilityGeneratorConfig(state_count=6),
        force_positive=False,
    )
    assert item.answer_key["verdict"] is False
    submission = {
        "item_id": item.item_id,
        "verdict": False,
        "certificate": item.answer_key["certificate"],
    }
    record = score_c2_item(item, submission)
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


def test_wrong_verdict_gives_verdict_wrong() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    submission = {
        "item_id": item.item_id,
        "verdict": not item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }
    record = score_c2_item(item, submission)
    assert record.extractable is True
    assert record.verdict_correct is False
    assert record.failure_stage == FailureStage.VERDICT_WRONG


def test_invalid_certificate_gives_certificate_invalid() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    certificate = json.loads(json.dumps(item.answer_key["certificate"]))
    certificate["payload"]["state_sequence"] = ["q0", "q0", "q3"]
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": certificate,
    }
    record = score_c2_item(item, submission)
    assert record.extractable is True
    assert record.verdict_correct is True
    assert record.certificate_valid is False
    assert record.failure_stage == FailureStage.CERTIFICATE_INVALID


def test_malformed_response_not_extractable() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    record = score_c2_item(item, {"verdict": True})
    assert record.extractable is False
    assert record.verdict_correct is None
    assert record.certificate_valid is None
    assert record.failure_stage == FailureStage.NOT_EXTRACTABLE
    assert record.parse_errors


def test_inconsistent_certificate_type_is_still_extractable() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    payload = {
        "item_id": item.item_id,
        "verdict": True,
        "certificate": {
            "certificate_type": "unreachability_witness",
            "version": "1.0",
            "payload": {"reachable_states": ["q0"], "target_state": "q1"},
        },
    }
    result = parse_c2_response(payload)
    assert result.extractable
    record = score_c2_item(item, payload)
    assert record.extractable
    assert record.failure_stage == FailureStage.CERTIFICATE_INVALID


def test_rescore_reproduces_identical_scoring_record() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }
    transcript = record_transcript(item, submission)
    rescored = rescore_transcript(transcript)
    assert rescored.to_dict() == transcript.scoring_record.to_dict()


def test_transcript_records_parsed_submission_when_extractable() -> None:
    item = _load_example_item("examples/item_C2_reachability_seed42.json")
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }
    transcript = record_transcript(item, submission)
    assert transcript.parsed_submission is not None
    assert transcript.scoring_record.fully_correct is True

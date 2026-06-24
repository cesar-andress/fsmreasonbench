"""Hostile audit tests for F1 equivalence_witness verification."""

from __future__ import annotations

import copy

import pytest

from fsmreasonbench.certificates.separation import build_equivalence_witness_certificate
from fsmreasonbench.evaluator.f1_equivalence_witness_verifier_audit import run_audit_battery
from fsmreasonbench.evaluator.failure_taxonomy import classify_certificate_errors
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.models.fsm import ExecutableFSM, Transition
from fsmreasonbench.runtime.dfa_minimize import minimized_dfa_hash
from fsmreasonbench.verifier.separation import verify_equivalence_witness_certificate


def _equivalent_item(seed: int = 21):
    return generate_separation_item(
        seed,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )


def test_audit_battery_all_pass() -> None:
    payload = run_audit_battery()
    assert payload["summary"]["all_passed"], payload["checks"]


def test_gold_equivalence_witness_passes() -> None:
    item = _equivalent_item()
    result = verify_equivalence_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.answer_key["certificate"],
    )
    assert result.valid


def test_independently_recomputed_witness_passes() -> None:
    item = _equivalent_item(33)
    certificate = {
        "certificate_type": "equivalence_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_hash_A": minimized_dfa_hash(item.fsm_a),
            "minimized_hash_B": minimized_dfa_hash(item.fsm_b),
        },
    }
    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, certificate)
    assert result.valid


def test_wrong_hash_fails_without_semantic_non_equivalence_label() -> None:
    item = _equivalent_item(41)
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["minimized_hash_A"] = "deadbeef"
    result = verify_equivalence_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        certificate,
    )
    assert not result.valid
    assert any("minimized_hash_A mismatch" in err for err in result.errors)
    assert classify_certificate_errors(tuple(result.errors)) == "equivalence_hash_mismatch"
    assert not any("non-equivalent" in err for err in result.errors)


def test_non_equivalent_pair_rejected_semantically() -> None:
    eq = _equivalent_item(45)
    ne = generate_separation_item(9)
    certificate = {
        "certificate_type": "equivalence_witness",
        "version": "1.0",
        "fsm_ids": [ne.fsm_a.fsm_id, ne.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_hash_A": eq.answer_key["certificate"]["payload"]["minimized_hash_A"],
            "minimized_hash_B": eq.answer_key["certificate"]["payload"]["minimized_hash_B"],
        },
    }
    result = verify_equivalence_witness_certificate(
        ne.fsm_a,
        ne.fsm_b,
        certificate,
    )
    assert not result.valid
    assert any("non-equivalent" in err for err in result.errors)


def test_equivalence_witness_on_non_equivalent_pair_fails() -> None:
    ne = generate_separation_item(11)
    certificate = build_equivalence_witness_certificate(ne.fsm_a, ne.fsm_b)
    result = verify_equivalence_witness_certificate(ne.fsm_a, ne.fsm_b, certificate)
    assert not result.valid
    assert any("non-equivalent" in err for err in result.errors)


def test_irrelevant_hashes_fail() -> None:
    item = _equivalent_item(47)
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["minimized_hash_A"] = "0" * 64
    certificate["payload"]["minimized_hash_B"] = "1" * 64
    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, certificate)
    assert not result.valid


def test_rebuilt_equivalent_certificate_passes() -> None:
    item = _equivalent_item(49)
    rebuilt = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, rebuilt)
    assert result.valid


def test_alternative_proof_fields_do_not_bypass_hash_contract() -> None:
    item = _equivalent_item(51)
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["minimized_hash_A"] = "deadbeef"
    certificate["payload"]["bijection"] = [{"from": "q0", "to": "s0"}]
    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, certificate)
    assert not result.valid


@pytest.mark.parametrize(
    ("mutator", "expected_fragment"),
    [
        (lambda cert: cert | {"certificate_type": "distinguishing_trace"}, "unsupported"),
        (lambda cert: cert | {"fsm_ids": ["x", "y"]}, "fsm_ids mismatch"),
        (
            lambda cert: {**cert, "payload": {**cert["payload"], "equivalent": False}},
            "equivalent must be true",
        ),
        (
            lambda cert: {
                **cert,
                "payload": {**cert["payload"], "minimized_hash_A": "bad"},
            },
            "minimized_hash_A mismatch",
        ),
    ],
)
def test_certificate_mutations_rejected(mutator, expected_fragment: str) -> None:
    item = _equivalent_item(53)
    certificate = mutator(copy.deepcopy(item.answer_key["certificate"]))
    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, certificate)
    assert not result.valid
    assert any(expected_fragment.lower() in err.lower() for err in result.errors)


def _flip_accepting(fsm: ExecutableFSM, state: str) -> ExecutableFSM:
    accepting = set(fsm.accepting_states)
    if state in accepting:
        accepting.remove(state)
    else:
        accepting.add(state)
    return ExecutableFSM(
        fsm_id=fsm.fsm_id,
        fsm_type=fsm.fsm_type,
        states=fsm.states,
        initial_state=fsm.initial_state,
        input_alphabet=fsm.input_alphabet,
        transitions=fsm.transitions,
        accepting_states=tuple(sorted(accepting)),
        metadata=dict(fsm.metadata),
    )


def test_fsm_accepting_mutation_rejected() -> None:
    item = _equivalent_item(55)
    broken_b = _flip_accepting(item.fsm_b, item.fsm_b.initial_state)
    certificate = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_equivalence_witness_certificate(item.fsm_a, broken_b, certificate)
    assert not result.valid
    assert any("non-equivalent" in err for err in result.errors)


def test_fsm_transition_mutation_rejected() -> None:
    item = _equivalent_item(57)
    first = item.fsm_b.transitions[0]
    broken_b = ExecutableFSM(
        fsm_id=item.fsm_b.fsm_id,
        fsm_type=item.fsm_b.fsm_type,
        states=tuple(dict.fromkeys((*item.fsm_b.states, "__broken__"))),
        initial_state=item.fsm_b.initial_state,
        input_alphabet=item.fsm_b.input_alphabet,
        transitions=(
            Transition(first.from_state, first.input_symbol, "__broken__"),
            *(t for t in item.fsm_b.transitions if t != first),
        ),
        accepting_states=item.fsm_b.accepting_states,
        metadata=dict(item.fsm_b.metadata),
    )
    certificate = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_equivalence_witness_certificate(item.fsm_a, broken_b, certificate)
    assert not result.valid

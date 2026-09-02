"""Contract verification tests including minimized_dfa adversarial cases."""

from __future__ import annotations

import copy

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.clean_v2.condition import ContractId
from fsmreasonbench.clean_v2.contracts import verify_certificate_for_contract
from fsmreasonbench.clean_v2.contracts.minimized_dfa import is_minimal_dfa, verify_minimized_dfa_contract
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.models.fsm import ExecutableFSM, Transition
from fsmreasonbench.models.serialization import fsm_to_dict
from fsmreasonbench.runtime.dfa_minimize import minimize_dfa


def _eq_item(repo_root):
    items = load_items_jsonl(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    return next(item for item in items if item.answer_key["verdict"] is True)


def test_bisimulation_accepts_semantic_relation(repo_root):
    item = _eq_item(repo_root)
    cert = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_certificate_for_contract(
        item.fsm_a, item.fsm_b, cert, contract=ContractId.BISIMULATION
    )
    assert result.valid


def test_minimized_dfa_accepts_renamed_minimal_machines(repo_root):
    item = _eq_item(repo_root)
    min_a = minimize_dfa(item.fsm_a)
    min_b = minimize_dfa(item.fsm_b)
    assert is_minimal_dfa(min_a)
    cert = {
        "certificate_type": "minimized_dfa_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_a": fsm_to_dict(min_a, include_metadata=False),
            "minimized_b": fsm_to_dict(min_b, include_metadata=False),
        },
    }
    result = verify_minimized_dfa_contract(item.fsm_a, item.fsm_b, cert)
    assert result.valid, result.errors


def test_minimized_dfa_rejects_non_minimal(repo_root):
    item = _eq_item(repo_root)
    # Use original (generally non-minimal / with unreachable) as submitted machine.
    cert = {
        "certificate_type": "minimized_dfa_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_a": fsm_to_dict(item.fsm_a, include_metadata=False),
            "minimized_b": fsm_to_dict(minimize_dfa(item.fsm_b), include_metadata=False),
        },
    }
    result = verify_minimized_dfa_contract(item.fsm_a, item.fsm_b, cert)
    # Original machines from generator often have unreachable extras / non-minimal form.
    assert result.valid is False
    assert any("minimization" in err for err in result.errors)


def test_minimized_dfa_rejects_behaviorally_wrong(repo_root):
    item = _eq_item(repo_root)
    min_a = minimize_dfa(item.fsm_a)
    # Flip accepting states to break language.
    broken = ExecutableFSM(
        fsm_id=min_a.fsm_id,
        fsm_type=min_a.fsm_type,
        states=min_a.states,
        initial_state=min_a.initial_state,
        input_alphabet=min_a.input_alphabet,
        transitions=min_a.transitions,
        accepting_states=tuple(s for s in min_a.states if s not in min_a.accepting_states)[:1]
        or min_a.states[:1],
    )
    cert = {
        "certificate_type": "minimized_dfa_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_a": fsm_to_dict(broken, include_metadata=False),
            "minimized_b": fsm_to_dict(minimize_dfa(item.fsm_b), include_metadata=False),
        },
    }
    result = verify_minimized_dfa_contract(item.fsm_a, item.fsm_b, cert)
    assert result.valid is False


def test_minimized_dfa_rejects_valid_a_invalid_b(repo_root):
    item = _eq_item(repo_root)
    min_a = minimize_dfa(item.fsm_a)
    bad_b = copy.deepcopy(fsm_to_dict(minimize_dfa(item.fsm_b), include_metadata=False))
    bad_b["transitions"] = []
    cert = {
        "certificate_type": "minimized_dfa_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "minimized_a": fsm_to_dict(min_a, include_metadata=False),
            "minimized_b": bad_b,
        },
    }
    result = verify_minimized_dfa_contract(item.fsm_a, item.fsm_b, cert)
    assert result.valid is False


def test_digest_control_roundtrip(repo_root):
    from fsmreasonbench.certificates.separation import build_equivalence_witness_certificate

    item = _eq_item(repo_root)
    cert = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_certificate_for_contract(
        item.fsm_a, item.fsm_b, cert, contract=ContractId.DIGEST_CONTROL
    )
    assert result.valid

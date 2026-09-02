"""Contract verification and burden metadata for clean_v2."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.clean_v2.condition import ContractId
from fsmreasonbench.clean_v2.contracts.bisimulation import verify_bisimulation_contract
from fsmreasonbench.clean_v2.contracts.digest_control import verify_digest_control_contract
from fsmreasonbench.clean_v2.contracts.minimized_dfa import verify_minimized_dfa_contract
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.verifier.result import VerifyResult


def verify_certificate_for_contract(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
    *,
    contract: ContractId,
) -> VerifyResult:
    if contract == ContractId.BISIMULATION:
        return verify_bisimulation_contract(fsm_a, fsm_b, certificate)
    if contract == ContractId.MINIMIZED_DFA:
        return verify_minimized_dfa_contract(fsm_a, fsm_b, certificate)
    if contract == ContractId.DIGEST_CONTROL:
        return verify_digest_control_contract(fsm_a, fsm_b, certificate)
    raise ValueError(contract)


def contract_burden_metadata(certificate: dict[str, Any] | None) -> dict[str, Any]:
    """Descriptive burden fields — not a synthetic complexity score."""
    if not isinstance(certificate, dict):
        return {
            "serialized_certificate_bytes": 0,
            "field_count": 0,
            "relation_pair_count": None,
            "represented_state_count": None,
            "represented_transition_count": None,
            "sequence_length": None,
        }
    blob = json.dumps(certificate, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload = certificate.get("payload")
    payload_obj = payload if isinstance(payload, dict) else {}

    relation_pair_count = None
    pairs = payload_obj.get("pairs")
    if isinstance(pairs, list):
        relation_pair_count = len(pairs)

    represented_state_count = None
    represented_transition_count = None
    for key in ("minimized_a", "minimized_b"):
        machine = payload_obj.get(key)
        if isinstance(machine, dict):
            states = machine.get("states")
            transitions = machine.get("transitions")
            if isinstance(states, list):
                represented_state_count = (represented_state_count or 0) + len(states)
            if isinstance(transitions, list):
                represented_transition_count = (represented_transition_count or 0) + len(
                    transitions
                )

    sequence_length = None
    trace = payload_obj.get("trace")
    if isinstance(trace, list):
        sequence_length = len(trace)

    def _count_fields(obj: Any) -> int:
        if isinstance(obj, dict):
            return sum(_count_fields(value) for value in obj.values()) + len(obj)
        if isinstance(obj, list):
            return sum(_count_fields(value) for value in obj)
        return 0

    return {
        "serialized_certificate_bytes": len(blob),
        "field_count": _count_fields(certificate),
        "relation_pair_count": relation_pair_count,
        "represented_state_count": represented_state_count,
        "represented_transition_count": represented_transition_count,
        "sequence_length": sequence_length,
    }

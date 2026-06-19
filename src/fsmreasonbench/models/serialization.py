"""Canonical JSON serialization and content hashing for FSM objects."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition


def _sorted_unique(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values))


def fsm_to_dict(fsm: ExecutableFSM, *, include_metadata: bool = True) -> dict[str, Any]:
    """Convert FSM to a JSON-serializable dict in canonical field order."""
    data: dict[str, Any] = {
        "fsm_id": fsm.fsm_id,
        "fsm_type": fsm.fsm_type.value,
        "states": _sorted_unique(fsm.states),
        "initial_state": fsm.initial_state,
        "input_alphabet": _sorted_unique(fsm.input_alphabet),
        "transitions": [
            transition.to_dict()
            for transition in sorted(
                fsm.transitions,
                key=lambda transition: (
                    transition.from_state,
                    transition.input_symbol,
                    transition.to_state,
                    transition.output or "",
                ),
            )
        ],
    }
    if fsm.accepting_states:
        data["accepting_states"] = _sorted_unique(fsm.accepting_states)
    if fsm.output_alphabet:
        data["output_alphabet"] = _sorted_unique(fsm.output_alphabet)
    if include_metadata and fsm.metadata:
        data["metadata"] = fsm.metadata
    return data


def fsm_from_dict(data: dict[str, Any]) -> ExecutableFSM:
    """Parse FSM from JSON-compatible dict."""
    transitions = tuple(Transition.from_dict(entry) for entry in data["transitions"])
    return ExecutableFSM(
        fsm_id=data["fsm_id"],
        fsm_type=FSMType(data["fsm_type"]),
        states=tuple(_sorted_unique(data["states"])),
        initial_state=data["initial_state"],
        input_alphabet=tuple(_sorted_unique(data["input_alphabet"])),
        transitions=transitions,
        accepting_states=tuple(_sorted_unique(data.get("accepting_states", []))),
        output_alphabet=tuple(_sorted_unique(data.get("output_alphabet", []))),
        metadata=dict(data.get("metadata", {})),
    )


def canonical_json(obj: dict[str, Any]) -> str:
    """Serialize dict to canonical JSON (sorted keys, minimal separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(obj: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical JSON encoding."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def fsm_content_hash(fsm: ExecutableFSM, *, include_metadata: bool = False) -> str:
    """Content hash of FSM for cohort manifests (metadata excluded by default)."""
    return content_hash(fsm_to_dict(fsm, include_metadata=include_metadata))

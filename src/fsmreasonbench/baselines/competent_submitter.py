"""Competent submitter baseline: R1-style step-simulator ceiling with reasoning logs."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.acceptance import accepts_trace
from fsmreasonbench.runtime.dfa_minimize import minimized_dfa_hash
from fsmreasonbench.runtime.reachability import reachable_states
from fsmreasonbench.runtime.simulation import simulate

__all__ = [
    "CompetentSubmitterRun",
    "build_competent_submission",
    "run_competent_submitter",
    "serialize_competent_submission",
]


@dataclass(frozen=True, slots=True)
class CompetentSubmitterRun:
    """Evaluator-facing submission plus auditable reasoning log."""

    submission: dict[str, Any]
    reasoning_log: tuple[dict[str, Any], ...]


def build_competent_submission(item: BenchmarkItem) -> CompetentSubmitterRun:
    """
    Build a model-shaped submission using only evaluatee-visible fields.

    Uses runtime step simulation (``simulate``, ``reachable_states``,
    ``accepts_trace``, ``minimized_dfa_hash``) — not ``fsmreasonbench.oracle``.
    Does not read ``answer_key.certificate``.
    """
    if item.family == "C2":
        return _build_c2_competent_submission(
            item_id=item.item_id,
            fsm=item.fsm,
            target_state=item.question["target_state"],
        )
    if item.family == "F1":
        if item.fsm_b is None:
            raise ValueError("F1 competent submitter requires fsm_b")
        return _build_f1_competent_submission(
            item_id=item.item_id,
            fsm_a=item.fsm_a,
            fsm_b=item.fsm_b,
        )
    raise ValueError(f"unsupported family for competent submitter: {item.family!r}")


def serialize_competent_submission(run: CompetentSubmitterRun) -> str:
    """Serialize submission the way model batch runners store raw responses."""
    return json.dumps(run.submission, sort_keys=True)


def run_competent_submitter(item: BenchmarkItem) -> CompetentSubmitterRun:
    """Return submission JSON string and reasoning log for one item."""
    return build_competent_submission(item)


def _build_c2_competent_submission(
    *,
    item_id: str,
    fsm: ExecutableFSM,
    target_state: str,
) -> CompetentSubmitterRun:
    log: list[dict[str, Any]] = [
        {
            "step": "read_question",
            "fsm_id": fsm.fsm_id,
            "initial_state": fsm.initial_state,
            "target_state": target_state,
        }
    ]

    if target_state == fsm.initial_state:
        simulation = simulate(fsm, ())
        log.append(
            {
                "step": "simulate_empty_trace",
                "state_sequence": list(simulation.state_sequence),
                "conclusion": "target equals initial state; reachable",
            }
        )
        certificate = _c2_trace_certificate(
            fsm,
            trace=(),
            state_sequence=simulation.state_sequence,
        )
        return CompetentSubmitterRun(
            submission={
                "item_id": item_id,
                "verdict": True,
                "certificate": certificate,
            },
            reasoning_log=tuple(log),
        )

    explored = reachable_states(fsm)
    log.append(
        {
            "step": "enumerate_reachable_states",
            "reachable_states": sorted(explored),
        }
    )

    if target_state not in explored:
        log.append(
            {
                "step": "conclude_unreachable",
                "target_state": target_state,
                "reason": "target not in reachable set",
            }
        )
        certificate = _c2_unreachability_certificate(fsm, explored, target_state)
        return CompetentSubmitterRun(
            submission={
                "item_id": item_id,
                "verdict": False,
                "certificate": certificate,
            },
            reasoning_log=tuple(log),
        )

    parent: dict[str, tuple[str | None, str | None]] = {fsm.initial_state: (None, None)}
    queue: deque[str] = deque([fsm.initial_state])
    while queue:
        state = queue.popleft()
        for symbol in fsm.input_alphabet:
            successor = _dfa_successor(fsm, state, symbol)
            if successor is None or successor in parent:
                continue
            parent[successor] = (state, symbol)
            log.append(
                {
                    "step": "bfs_expand",
                    "from_state": state,
                    "symbol": symbol,
                    "to_state": successor,
                }
            )
            if successor == target_state:
                trace, state_sequence = _reconstruct_path(parent, target_state)
                simulation = simulate(fsm, trace)
                log.append(
                    {
                        "step": "simulate_witness_trace",
                        "trace": list(trace),
                        "state_sequence": list(simulation.state_sequence),
                        "conclusion": "witness trace reaches target",
                    }
                )
                certificate = _c2_trace_certificate(
                    fsm,
                    trace=simulation.trace,
                    state_sequence=simulation.state_sequence,
                    branching_choices=simulation.branching_choices,
                )
                return CompetentSubmitterRun(
                    submission={
                        "item_id": item_id,
                        "verdict": True,
                        "certificate": certificate,
                    },
                    reasoning_log=tuple(log),
                )
            queue.append(successor)

    raise RuntimeError("internal error: target in reachable set but BFS found no path")


def _build_f1_competent_submission(
    *,
    item_id: str,
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
) -> CompetentSubmitterRun:
    _assert_dfa_pair(fsm_a, fsm_b)
    log: list[dict[str, Any]] = [
        {
            "step": "read_question",
            "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
            "alphabet": list(fsm_a.input_alphabet),
        }
    ]

    hash_a = minimized_dfa_hash(fsm_a)
    hash_b = minimized_dfa_hash(fsm_b)
    log.append(
        {
            "step": "compare_minimized_language_hashes",
            "minimized_hash_A": hash_a,
            "minimized_hash_B": hash_b,
        }
    )

    if hash_a == hash_b:
        log.append(
            {
                "step": "conclude_equivalent",
                "reason": "minimized language hashes match",
            }
        )
        certificate = {
            "certificate_type": "equivalence_witness",
            "version": "1.0",
            "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
            "verdict_supported": True,
            "payload": {
                "equivalent": True,
                "minimized_hash_A": hash_a,
                "minimized_hash_B": hash_b,
            },
        }
        return CompetentSubmitterRun(
            submission={
                "item_id": item_id,
                "verdict": True,
                "certificate": certificate,
            },
            reasoning_log=tuple(log),
        )

    witness = _shortest_distinguishing_trace(fsm_a, fsm_b, log)
    if witness is None:
        raise RuntimeError("internal error: hash mismatch but no distinguishing trace")

    log.append(
        {
            "step": "simulate_distinguishing_trace",
            "trace": list(witness["trace"]),
            "acceptance_A": witness["acceptance_a"],
            "acceptance_B": witness["acceptance_b"],
            "conclusion": "acceptance differs; machines not equivalent",
        }
    )
    certificate = {
        "certificate_type": "distinguishing_trace",
        "version": "1.0",
        "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
        "verdict_supported": False,
        "payload": {
            "trace": list(witness["trace"]),
            "acceptance": {
                "A": witness["acceptance_a"],
                "B": witness["acceptance_b"],
            },
        },
    }
    return CompetentSubmitterRun(
        submission={
            "item_id": item_id,
            "verdict": False,
            "certificate": certificate,
        },
        reasoning_log=tuple(log),
    )


def _shortest_distinguishing_trace(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    log: list[dict[str, Any]],
) -> dict[str, Any] | None:
    start = (fsm_a.initial_state, fsm_b.initial_state)
    initial = _witness_if_distinguishing(fsm_a, fsm_b, start, ())
    if initial is not None:
        log.append(
            {
                "step": "product_bfs_found_witness",
                "trace": list(initial["trace"]),
                "pair": list(start),
            }
        )
        return initial

    queue: deque[tuple[tuple[str, str], tuple[str, ...]]] = deque([(start, ())])
    visited = {start}
    while queue:
        pair, trace = queue.popleft()
        for symbol in fsm_a.input_alphabet:
            next_a = _dfa_successor(fsm_a, pair[0], symbol)
            next_b = _dfa_successor(fsm_b, pair[1], symbol)
            if next_a is None or next_b is None:
                continue
            successor = (next_a, next_b)
            if successor in visited:
                continue
            visited.add(successor)
            extended = trace + (symbol,)
            log.append(
                {
                    "step": "product_bfs_expand",
                    "symbol": symbol,
                    "from_pair": list(pair),
                    "to_pair": list(successor),
                    "trace_prefix": list(extended),
                }
            )
            witness = _witness_if_distinguishing(fsm_a, fsm_b, successor, extended)
            if witness is not None:
                log.append(
                    {
                        "step": "product_bfs_found_witness",
                        "trace": list(witness["trace"]),
                        "pair": list(successor),
                    }
                )
                return witness
            queue.append((successor, extended))
    return None


def _witness_if_distinguishing(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    pair: tuple[str, str],
    trace: tuple[str, ...],
) -> dict[str, Any] | None:
    acceptance_a = pair[0] in fsm_a.accepting_states
    acceptance_b = pair[1] in fsm_b.accepting_states
    if acceptance_a == acceptance_b:
        return None
    if trace:
        sim_a = accepts_trace(fsm_a, trace)
        sim_b = accepts_trace(fsm_b, trace)
        if sim_a != acceptance_a or sim_b != acceptance_b:
            raise RuntimeError("acceptance mismatch between pair state and trace replay")
    return {
        "trace": trace,
        "acceptance_a": acceptance_a,
        "acceptance_b": acceptance_b,
    }


def _c2_trace_certificate(
    fsm: ExecutableFSM,
    *,
    trace: tuple[str, ...],
    state_sequence: tuple[str, ...],
    branching_choices: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "trace": list(trace),
        "state_sequence": list(state_sequence),
        "accepting": True,
    }
    if branching_choices is not None:
        payload["branching_choices"] = list(branching_choices)
    return {
        "certificate_type": "trace_witness",
        "version": "1.0",
        "fsm_id": fsm.fsm_id,
        "verdict_supported": True,
        "payload": payload,
    }


def _c2_unreachability_certificate(
    fsm: ExecutableFSM,
    explored: frozenset[str],
    target_state: str,
) -> dict[str, Any]:
    return {
        "certificate_type": "unreachability_witness",
        "version": "1.0",
        "fsm_id": fsm.fsm_id,
        "verdict_supported": False,
        "payload": {
            "reachable_states": sorted(explored),
            "target_state": target_state,
        },
    }


def _reconstruct_path(
    parent: dict[str, tuple[str | None, str | None]],
    target_state: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    trace_rev: list[str] = []
    state = target_state
    while True:
        prev, symbol = parent[state]
        if prev is None:
            break
        trace_rev.append(symbol)
        state = prev
    trace = tuple(reversed(trace_rev))
    state_sequence = [target_state]
    state = target_state
    for symbol in reversed(trace):
        prev, _ = parent[state]
        if prev is None:
            raise RuntimeError("broken parent chain")
        state = prev
        state_sequence.append(state)
    state_sequence.reverse()
    return trace, tuple(state_sequence)


def _dfa_successor(fsm: ExecutableFSM, state: str, symbol: str) -> str | None:
    if fsm.fsm_type != FSMType.DFA:
        raise ValueError("competent submitter supports DFA only in this slice")
    successors = fsm.transitions_from(state, symbol)
    if len(successors) != 1:
        return None
    return successors[0].to_state


def _assert_dfa_pair(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> None:
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        raise ValueError("F1 competent submitter supports DFA pairs only")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        raise ValueError("DFA pair must share input alphabet")

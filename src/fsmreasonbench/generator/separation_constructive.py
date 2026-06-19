"""Constructive F1 DFA non-equivalence pair builder."""

from __future__ import annotations

import random
import uuid

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition


def construct_separation_dfa_pair(
    seed: int,
    k: int,
    *,
    alphabet_size: int,
) -> tuple[ExecutableFSM, ExecutableFSM]:
    """
    Build two chain-like DFAs whose shortest distinguishing trace has length k.

    Both machines follow a seeded symbol sequence w of length k through matching
    states. Prefixes shorter than k agree on acceptance; after w, A rejects and B
    accepts. Non-w transitions route to a shared non-accepting sink.
    """
    if k < 0:
        raise ValueError("distinguishing trace length must be >= 0")

    rng = random.Random(seed)
    alphabet_size = max(alphabet_size, 1)
    alphabet = tuple(chr(ord("a") + index) for index in range(alphabet_size))
    witness_symbols = tuple(rng.choice(alphabet) for _ in range(k))

    chain_states = tuple(f"q{index}" for index in range(k + 1))
    sink = "sink"
    states = chain_states + (sink,)
    initial_state = chain_states[0]

    transitions: list[Transition] = []
    for index in range(k):
        current = chain_states[index]
        step_symbol = witness_symbols[index]
        transitions.append(
            Transition(from_state=current, input_symbol=step_symbol, to_state=chain_states[index + 1])
        )
        for symbol in alphabet:
            if symbol != step_symbol:
                transitions.append(
                    Transition(from_state=current, input_symbol=symbol, to_state=sink)
                )

    if k == 0:
        for symbol in alphabet:
            transitions.append(
                Transition(from_state=initial_state, input_symbol=symbol, to_state=sink)
            )
    else:
        final_state = chain_states[k]
        for symbol in alphabet:
            transitions.append(
                Transition(from_state=final_state, input_symbol=symbol, to_state=sink)
            )

    for symbol in alphabet:
        transitions.append(Transition(from_state=sink, input_symbol=symbol, to_state=sink))

    accepting_a: tuple[str, ...] = ()
    accepting_b = (chain_states[k],)

    metadata = {
        "generator_seed": seed,
        "construction": "chain_sink",
        "distinguishing_trace_length": k,
        "witness_symbols": list(witness_symbols),
    }

    fsm_a = _make_constructive_fsm(
        seed=seed,
        label="A",
        states=states,
        initial_state=initial_state,
        alphabet=alphabet,
        transitions=tuple(transitions),
        accepting_states=accepting_a,
        metadata=metadata,
    )
    fsm_b = _make_constructive_fsm(
        seed=seed + 1,
        label="B",
        states=states,
        initial_state=initial_state,
        alphabet=alphabet,
        transitions=tuple(transitions),
        accepting_states=accepting_b,
        metadata=metadata,
    )
    return fsm_a, fsm_b


def _make_constructive_fsm(
    *,
    seed: int,
    label: str,
    states: tuple[str, ...],
    initial_state: str,
    alphabet: tuple[str, ...],
    transitions: tuple[Transition, ...],
    accepting_states: tuple[str, ...],
    metadata: dict[str, object],
) -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id=str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"fsmreasonbench:separation:{label}:{seed}")
        ),
        fsm_type=FSMType.DFA,
        states=states,
        initial_state=initial_state,
        input_alphabet=alphabet,
        transitions=transitions,
        accepting_states=accepting_states,
        metadata={
            **metadata,
            "label": label,
        },
    )

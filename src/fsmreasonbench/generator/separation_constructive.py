"""Constructive F1 DFA non-equivalence pair builders."""

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


def construct_separation_decoy_dfa_pair(
    seed: int,
    k: int,
    *,
    alphabet_size: int,
) -> tuple[ExecutableFSM, ExecutableFSM]:
    """
    Build two DFAs with controlled shortest distinguishing trace length k.

    A and B agree on acceptance for every trace shorter than k. They diverge on a
    seeded witness trace of length k. Decoy branches rejoin the witness prefix
    or enter equivalent non-accepting subgraphs; A and B may differ in topology
    without introducing a shorter distinguishing trace.
    """
    if k < 0:
        raise ValueError("distinguishing trace length must be >= 0")

    rng = random.Random(seed)
    alphabet_size = max(alphabet_size, 1)
    alphabet = tuple(chr(ord("a") + index) for index in range(alphabet_size))
    witness_symbols = tuple(rng.choice(alphabet) for _ in range(k))

    chain_states = tuple(f"q{index}" for index in range(k + 1))
    initial_state = chain_states[0]
    states: set[str] = set(chain_states)
    transitions_a: list[Transition] = []
    transitions_b: list[Transition] = []

    def add_a(from_state: str, input_symbol: str, to_state: str) -> None:
        states.add(from_state)
        states.add(to_state)
        transitions_a.append(
            Transition(from_state=from_state, input_symbol=input_symbol, to_state=to_state)
        )

    def add_b(from_state: str, input_symbol: str, to_state: str) -> None:
        states.add(from_state)
        states.add(to_state)
        transitions_b.append(
            Transition(from_state=from_state, input_symbol=input_symbol, to_state=to_state)
        )

    def add_both(from_state: str, input_symbol: str, to_state: str) -> None:
        add_a(from_state, input_symbol, to_state)
        add_b(from_state, input_symbol, to_state)

    if k == 0:
        _add_zero_length_decoys(
            rng=rng,
            current=initial_state,
            alphabet=alphabet,
            add_both=add_both,
        )
    else:
        for index in range(k):
            current = chain_states[index]
            step_symbol = witness_symbols[index]
            next_state = chain_states[index + 1]
            add_both(current, step_symbol, next_state)
            _add_decoy_hub(
                rng=rng,
                position=index,
                current=current,
                step_symbol=step_symbol,
                next_state=next_state,
                alphabet=alphabet,
                add_a=add_a,
                add_b=add_b,
                add_both=add_both,
                allow_b_shortcut=index < k - 1,
            )

        final_state = chain_states[k]
        _add_post_witness_region(
            final_state=final_state,
            alphabet=alphabet,
            add_both=add_both,
        )

    accepting_a: tuple[str, ...] = ()
    accepting_b = (chain_states[k],)

    metadata = {
        "generator_seed": seed,
        "construction": "decoy_prefix",
        "distinguishing_trace_length": k,
        "witness_symbols": list(witness_symbols),
    }

    ordered_states = tuple(sorted(states))
    fsm_a = _make_constructive_fsm(
        seed=seed,
        label="A",
        states=ordered_states,
        initial_state=initial_state,
        alphabet=alphabet,
        transitions=tuple(transitions_a),
        accepting_states=accepting_a,
        metadata=metadata,
    )
    fsm_b = _make_constructive_fsm(
        seed=seed + 1,
        label="B",
        states=ordered_states,
        initial_state=initial_state,
        alphabet=alphabet,
        transitions=tuple(transitions_b),
        accepting_states=accepting_b,
        metadata=metadata,
    )
    return fsm_a, fsm_b


def _add_zero_length_decoys(
    *,
    rng: random.Random,
    current: str,
    alphabet: tuple[str, ...],
    add_both,
) -> None:
    """Add non-accepting decoy loops for k=0 without creating length-1 witnesses."""
    hang_state = "hang_0"
    spill_state = "spill_0"
    shuffled = list(alphabet)
    rng.shuffle(shuffled)
    anchor = shuffled[0]
    add_both(hang_state, anchor, hang_state)
    for symbol in alphabet:
        add_both(current, symbol, hang_state)
    for symbol in alphabet:
        if symbol == anchor:
            continue
        add_both(hang_state, symbol, spill_state)
        add_both(spill_state, symbol, spill_state)


def _add_decoy_hub(
    *,
    rng: random.Random,
    position: int,
    current: str,
    step_symbol: str,
    next_state: str,
    alphabet: tuple[str, ...],
    add_a,
    add_b,
    add_both,
    allow_b_shortcut: bool,
) -> None:
    """Add decoy branches and local traps around one witness step."""
    non_step = [symbol for symbol in alphabet if symbol != step_symbol]
    rng.shuffle(non_step)
    if not non_step:
        return

    decoy_count = max(1, len(non_step) // 2)
    decoy_symbols = non_step[:decoy_count]
    hang_symbols = non_step[decoy_count:]

    for decoy_symbol in decoy_symbols:
        decoy_state = f"dec_{position}_{decoy_symbol}"
        loop_state = f"loop_{position}_{decoy_symbol}"
        add_a(current, decoy_symbol, decoy_state)
        if allow_b_shortcut:
            add_b(current, decoy_symbol, next_state)
        else:
            add_b(current, decoy_symbol, decoy_state)
        add_a(decoy_state, step_symbol, next_state)
        add_b(decoy_state, step_symbol, next_state)
        for filler in alphabet:
            if filler in (step_symbol,):
                continue
            add_a(decoy_state, filler, loop_state)
            add_b(decoy_state, filler, loop_state)
            add_both(loop_state, filler, loop_state)

    if hang_symbols:
        hang_state = f"hang_{position}"
        spill_state = f"spill_{position}"
        anchor = hang_symbols[0]
        add_both(hang_state, anchor, hang_state)
        for hang_symbol in hang_symbols:
            add_both(current, hang_symbol, hang_state)
        for spill_symbol in alphabet:
            if spill_symbol == anchor:
                continue
            add_both(hang_state, spill_symbol, spill_state)
            add_both(spill_state, spill_symbol, spill_state)


def _add_post_witness_region(
    *,
    final_state: str,
    alphabet: tuple[str, ...],
    add_both,
) -> None:
    """Route post-witness transitions through a small non-sink tail graph."""
    if len(alphabet) == 1:
        tail_state = "tail_0"
        add_both(final_state, alphabet[0], tail_state)
        add_both(tail_state, alphabet[0], tail_state)
        return

    tail_a = "tail_0"
    tail_b = "tail_1"
    add_both(final_state, alphabet[0], tail_a)
    add_both(final_state, alphabet[1], tail_b)
    for symbol in alphabet[2:]:
        add_both(final_state, symbol, tail_b)
    add_both(tail_a, alphabet[0], tail_a)
    for symbol in alphabet[1:]:
        add_both(tail_a, symbol, tail_b)
    add_both(tail_b, alphabet[0], tail_a)
    for symbol in alphabet[1:]:
        add_both(tail_b, symbol, tail_b)


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

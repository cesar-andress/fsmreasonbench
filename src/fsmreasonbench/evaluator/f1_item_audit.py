"""Diagnostics for F1 item difficulty and constructive-generator regularity."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.simulation import simulate


@dataclass(frozen=True, slots=True)
class F1ItemDiagnostics:
    """Per-item F1 difficulty and regularity signals."""

    item_id: str
    gold_distinguishing_trace: tuple[str, ...]
    trace_length: int
    alphabet_distribution: dict[str, int]
    simple_repeated_pattern: bool
    branching_along_witness: tuple[int, ...]
    sink_transition_ratio: float
    final_acceptance_only_difference: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "gold_distinguishing_trace": list(self.gold_distinguishing_trace),
            "trace_length": self.trace_length,
            "alphabet_distribution": dict(self.alphabet_distribution),
            "simple_repeated_pattern": self.simple_repeated_pattern,
            "branching_along_witness": list(self.branching_along_witness),
            "sink_transition_ratio": self.sink_transition_ratio,
            "final_acceptance_only_difference": self.final_acceptance_only_difference,
        }


@dataclass(frozen=True, slots=True)
class F1AuditSummary:
    """Aggregate metrics over a batch of F1 items."""

    n_items: int
    repeated_trace_rate: float
    final_acceptance_only_rate: float
    average_branching_along_witness: float
    sink_transition_ratio: float
    unique_gold_traces: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_items": self.n_items,
            "repeated_trace_rate": self.repeated_trace_rate,
            "final_acceptance_only_rate": self.final_acceptance_only_rate,
            "average_branching_along_witness": self.average_branching_along_witness,
            "sink_transition_ratio": self.sink_transition_ratio,
            "unique_gold_traces": self.unique_gold_traces,
        }


def audit_f1_item(item: BenchmarkItem) -> F1ItemDiagnostics:
    """Compute diagnostics for one F1 benchmark item."""
    if item.family != "F1":
        raise ValueError(f"expected F1 item, got {item.family!r}")
    if item.fsm_b is None:
        raise ValueError("F1 item missing fsm_b")

    trace = _gold_distinguishing_trace(item)
    fsm_a = item.fsm_a
    fsm_b = item.fsm_b
    sink_states = _detect_sink_states(fsm_a, fsm_b)

    return F1ItemDiagnostics(
        item_id=item.item_id,
        gold_distinguishing_trace=trace,
        trace_length=len(trace),
        alphabet_distribution=dict(Counter(trace)),
        simple_repeated_pattern=is_simple_repeated_pattern(trace),
        branching_along_witness=branching_along_witness(fsm_a, trace),
        sink_transition_ratio=sink_transition_ratio(fsm_a, fsm_b, sink_states),
        final_acceptance_only_difference=differ_only_final_acceptance(fsm_a, fsm_b, trace),
    )


def summarize_f1_audit(diagnostics: list[F1ItemDiagnostics]) -> F1AuditSummary:
    """Aggregate per-item diagnostics into summary metrics."""
    if not diagnostics:
        return F1AuditSummary(
            n_items=0,
            repeated_trace_rate=0.0,
            final_acceptance_only_rate=0.0,
            average_branching_along_witness=0.0,
            sink_transition_ratio=0.0,
            unique_gold_traces=0,
        )

    n = len(diagnostics)
    repeated = sum(1 for row in diagnostics if row.simple_repeated_pattern)
    final_only = sum(1 for row in diagnostics if row.final_acceptance_only_difference)
    branching_values = [
        value
        for row in diagnostics
        for value in row.branching_along_witness
    ]
    avg_branching = sum(branching_values) / len(branching_values) if branching_values else 0.0
    avg_sink = sum(row.sink_transition_ratio for row in diagnostics) / n
    unique_traces = len({row.gold_distinguishing_trace for row in diagnostics})

    return F1AuditSummary(
        n_items=n,
        repeated_trace_rate=repeated / n,
        final_acceptance_only_rate=final_only / n,
        average_branching_along_witness=avg_branching,
        sink_transition_ratio=avg_sink,
        unique_gold_traces=unique_traces,
    )


def audit_f1_items_jsonl(items_path: str) -> dict[str, Any]:
    """Load F1 items JSONL and return audit payload."""
    items = load_items_jsonl(items_path)
    if not items:
        raise ValueError("items JSONL is empty")
    if any(item.family != "F1" for item in items):
        raise ValueError("all items must be family F1")

    diagnostics = [audit_f1_item(item) for item in items]
    summary = summarize_f1_audit(diagnostics)
    return {
        "source": items_path,
        "summary": summary.to_dict(),
        "items": [row.to_dict() for row in diagnostics],
    }


def write_f1_audit_report(items_path: str, out_path: str) -> dict[str, Any]:
    """Audit F1 items and write JSON report."""
    payload = audit_f1_items_jsonl(items_path)
    dump_json(out_path, payload)
    return payload


def _gold_distinguishing_trace(item: BenchmarkItem) -> tuple[str, ...]:
    certificate = item.answer_key["certificate"]
    payload = certificate["payload"]
    trace = payload.get("trace")
    if not isinstance(trace, list) or not trace:
        raise ValueError(f"item {item.item_id} missing gold distinguishing trace")
    return tuple(str(symbol) for symbol in trace)


def is_simple_repeated_pattern(trace: tuple[str, ...]) -> bool:
    """
    Return True when the trace is a short repeating motif.

    Covers constant traces, strict alternation, and any period-1..len//2 repeat.
    """
    if len(trace) <= 1:
        return True
    if len(set(trace)) == 1:
        return True
    if len(trace) >= 2 and trace[0] != trace[1]:
        if all(trace[index] == trace[index % 2] for index in range(len(trace))):
            return True
    for period in range(1, len(trace) // 2 + 1):
        unit = trace[:period]
        if all(trace[index] == unit[index % period] for index in range(len(trace))):
            return True
    return False


def branching_along_witness(fsm: ExecutableFSM, trace: tuple[str, ...]) -> tuple[int, ...]:
    """Count distinct outgoing symbols at each state along the witness prefix."""
    if not trace:
        return (len(_outgoing_symbols(fsm, fsm.initial_state)),)

    simulation = simulate(fsm, trace)
    prefix_states = simulation.state_sequence[:-1]
    return tuple(len(_outgoing_symbols(fsm, state)) for state in prefix_states)


def sink_transition_ratio(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    sink_states: set[str],
) -> float:
    """Fraction of transitions in A and B whose target is a sink state."""
    transitions = tuple(fsm_a.transitions) + tuple(fsm_b.transitions)
    if not transitions:
        return 0.0
    sink_hits = sum(1 for transition in transitions if transition.to_state in sink_states)
    return sink_hits / len(transitions)


def differ_only_final_acceptance(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    trace: tuple[str, ...],
) -> bool:
    """True when A and B share topology and differ only on acceptance at the witness end."""
    if fsm_a.states != fsm_b.states:
        return False
    if fsm_a.initial_state != fsm_b.initial_state:
        return False
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        return False
    if _transition_set(fsm_a) != _transition_set(fsm_b):
        return False

    final_state = simulate(fsm_a, trace).state_sequence[-1]
    accept_a = set(fsm_a.accepting_states)
    accept_b = set(fsm_b.accepting_states)
    return accept_a.symmetric_difference(accept_b) == {final_state} and final_state in accept_b


def _detect_sink_states(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> set[str]:
    sinks: set[str] = set()
    if "sink" in fsm_a.states:
        sinks.add("sink")
    for fsm in (fsm_a, fsm_b):
        for state in fsm.states:
            if _is_universal_sink_state(fsm, state):
                sinks.add(state)
    return sinks


def _is_universal_sink_state(fsm: ExecutableFSM, state: str) -> bool:
    outgoing = [transition for transition in fsm.transitions if transition.from_state == state]
    if not outgoing:
        return False
    return all(transition.to_state == state for transition in outgoing)


def _outgoing_symbols(fsm: ExecutableFSM, state: str) -> set[str]:
    return {
        transition.input_symbol
        for transition in fsm.transitions
        if transition.from_state == state
    }


def _transition_set(fsm: ExecutableFSM) -> set[tuple[str, str, str]]:
    return {
        (transition.from_state, transition.input_symbol, transition.to_state)
        for transition in fsm.transitions
    }

"""Reference track agents for C2 and F1 (evaluator instrumentation, not model baselines)."""

from __future__ import annotations

import json
from collections import deque
from typing import Any

from fsmreasonbench.baselines.competent_submitter import build_competent_submission
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId, TrackRunResult
from fsmreasonbench.tracks.solver_tools import SolverToolRegistry
from fsmreasonbench.tracks.step_simulator import StepSimulator


def run_r0_agent(item: BenchmarkItem) -> TrackRunResult:
    """
    R0 reference agent: inline reasoning via runtime procedures, no tool calls.

    Reuses competent_submitter decision logic but records scratchpad-only audit log.
    """
    audit = AuditLogBuilder(TrackId.R0)
    audit.scratchpad(
        "read_question",
        "loaded evaluatee-visible item fields",
        details={"item_id": item.item_id, "family": item.family},
    )
    competent_run = build_competent_submission(item)
    for index, entry in enumerate(competent_run.reasoning_log):
        audit.scratchpad(
            entry.get("step", f"reasoning_{index}"),
            entry.get("conclusion", entry.get("step", "reasoning step")),
            details={
                key: value
                for key, value in entry.items()
                if key not in {"step", "conclusion"}
            },
        )
    audit.scratchpad(
        "construct_submission",
        "assembled public submission envelope without tool invocations",
    )
    raw_response = json.dumps(competent_run.submission, sort_keys=True)
    scoring_record = score_item(item, raw_response)
    audit_log = audit.build()
    return TrackRunResult(
        track=TrackId.R0,
        raw_response=raw_response,
        audit_log=audit_log,
        scoring_record=scoring_record,
    )


def run_r1_agent(item: BenchmarkItem) -> TrackRunResult:
    """R1 reference agent: solve using StepSimulator calls only."""
    audit = AuditLogBuilder(TrackId.R1)
    audit.scratchpad(
        "read_question",
        "loaded evaluatee-visible item fields",
        details={"item_id": item.item_id, "family": item.family},
    )
    if item.family == "C2":
        submission = _r1_solve_c2(item, audit)
    elif item.family == "F1":
        if item.fsm_b is None:
            raise ValueError("F1 track agent requires fsm_b")
        submission = _r1_solve_f1(item, audit)
    else:
        raise ValueError(f"unsupported family for R1 agent: {item.family!r}")

    audit.certificate_step(
        "assemble submission envelope from step-derived witness",
        details={"certificate_type": submission["certificate"]["certificate_type"]},
    )
    raw_response = json.dumps(submission, sort_keys=True)
    scoring_record = score_item(item, raw_response)
    return TrackRunResult(
        track=TrackId.R1,
        raw_response=raw_response,
        audit_log=audit.build(),
        scoring_record=scoring_record,
    )


def run_r2_agent(item: BenchmarkItem) -> TrackRunResult:
    """R2 reference agent: solver delegation with separated certificate assembly."""
    audit = AuditLogBuilder(TrackId.R2)
    solvers = SolverToolRegistry(audit=audit)
    audit.scratchpad(
        "read_question",
        "loaded evaluatee-visible item fields",
        details={"item_id": item.item_id, "family": item.family},
    )

    if item.family == "C2":
        submission = _r2_solve_c2(item, solvers, audit)
    elif item.family == "F1":
        if item.fsm_b is None:
            raise ValueError("F1 track agent requires fsm_b")
        submission = _r2_solve_f1(item, solvers, audit)
    else:
        raise ValueError(f"unsupported family for R2 agent: {item.family!r}")

    raw_response = json.dumps(submission, sort_keys=True)
    scoring_record = score_item(item, raw_response)
    return TrackRunResult(
        track=TrackId.R2,
        raw_response=raw_response,
        audit_log=audit.build(),
        scoring_record=scoring_record,
    )


def _r1_solve_c2(item: BenchmarkItem, audit: AuditLogBuilder) -> dict[str, Any]:
    simulator = StepSimulator(item.fsm, audit=audit)
    target_state = item.question["target_state"]
    initial = item.fsm.initial_state

    if target_state == initial:
        audit.scratchpad("decide", "target is initial state")
        certificate = {
            "certificate_type": "trace_witness",
            "version": "1.0",
            "fsm_id": item.fsm.fsm_id,
            "verdict_supported": True,
            "payload": {
                "trace": [],
                "state_sequence": [initial],
                "accepting": True,
            },
        }
        return {"item_id": item.item_id, "verdict": True, "certificate": certificate}

    parent: dict[str, tuple[str | None, str | None]] = {initial: (None, None)}
    queue: deque[str] = deque([initial])
    while queue:
        state = queue.popleft()
        for symbol in item.fsm.input_alphabet:
            step = simulator.step(state, symbol)
            if not step.get("success"):
                continue
            successor = step["next_state"]
            if successor in parent:
                continue
            parent[successor] = (state, symbol)
            if successor == target_state:
                trace, state_sequence = _reconstruct_path(parent, target_state)
                certificate = {
                    "certificate_type": "trace_witness",
                    "version": "1.0",
                    "fsm_id": item.fsm.fsm_id,
                    "verdict_supported": True,
                    "payload": {
                        "trace": list(trace),
                        "state_sequence": list(state_sequence),
                        "accepting": True,
                    },
                }
                audit.scratchpad(
                    "decide",
                    "target reachable via logged step exploration",
                    details={"trace": list(trace)},
                )
                return {
                    "item_id": item.item_id,
                    "verdict": True,
                    "certificate": certificate,
                }
            queue.append(successor)

    reachable = sorted(parent.keys())
    audit.scratchpad(
        "decide",
        "target unreachable after step-only exploration",
        details={"reachable_states": reachable},
    )
    certificate = {
        "certificate_type": "unreachability_witness",
        "version": "1.0",
        "fsm_id": item.fsm.fsm_id,
        "verdict_supported": False,
        "payload": {
            "reachable_states": reachable,
            "target_state": target_state,
        },
    }
    return {"item_id": item.item_id, "verdict": False, "certificate": certificate}


def _r1_solve_f1(item: BenchmarkItem, audit: AuditLogBuilder) -> dict[str, Any]:
    sim_a = StepSimulator(item.fsm_a, audit=audit)
    sim_b = StepSimulator(item.fsm_b, audit=audit)
    start = (item.fsm_a.initial_state, item.fsm_b.initial_state)
    witness = _r1_product_search(sim_a, sim_b, start, (), item.fsm_a, item.fsm_b)
    if witness is None:
        from fsmreasonbench.runtime.dfa_minimize import minimized_dfa_hash

        hash_a = minimized_dfa_hash(item.fsm_a)
        hash_b = minimized_dfa_hash(item.fsm_b)
        audit.scratchpad("decide", "no distinguishing trace found via step exploration")
        certificate = {
            "certificate_type": "equivalence_witness",
            "version": "1.0",
            "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
            "verdict_supported": True,
            "payload": {
                "equivalent": True,
                "minimized_hash_A": hash_a,
                "minimized_hash_B": hash_b,
            },
        }
        return {"item_id": item.item_id, "verdict": True, "certificate": certificate}

    audit.scratchpad(
        "decide",
        "distinguishing trace found via step exploration",
        details={"trace": list(witness["trace"])},
    )
    certificate = {
        "certificate_type": "distinguishing_trace",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "verdict_supported": False,
        "payload": {
            "trace": list(witness["trace"]),
            "acceptance": {
                "A": witness["acceptance_a"],
                "B": witness["acceptance_b"],
            },
        },
    }
    return {"item_id": item.item_id, "verdict": False, "certificate": certificate}


def _r1_product_search(
    sim_a: StepSimulator,
    sim_b: StepSimulator,
    pair: tuple[str, str],
    trace: tuple[str, ...],
    fsm_a,
    fsm_b,
) -> dict[str, Any] | None:
    acceptance_a = pair[0] in fsm_a.accepting_states
    acceptance_b = pair[1] in fsm_b.accepting_states
    if acceptance_a != acceptance_b:
        return {
            "trace": trace,
            "acceptance_a": acceptance_a,
            "acceptance_b": acceptance_b,
        }

    queue: deque[tuple[tuple[str, str], tuple[str, ...]]] = deque([(pair, trace)])
    visited = {pair}
    while queue:
        current_pair, current_trace = queue.popleft()
        for symbol in fsm_a.input_alphabet:
            step_a = sim_a.step(current_pair[0], symbol)
            step_b = sim_b.step(current_pair[1], symbol)
            if not step_a.get("success") or not step_b.get("success"):
                continue
            successor = (step_a["next_state"], step_b["next_state"])
            if successor in visited:
                continue
            visited.add(successor)
            extended = current_trace + (symbol,)
            acceptance_a = successor[0] in fsm_a.accepting_states
            acceptance_b = successor[1] in fsm_b.accepting_states
            if acceptance_a != acceptance_b:
                return {
                    "trace": extended,
                    "acceptance_a": acceptance_a,
                    "acceptance_b": acceptance_b,
                }
            queue.append((successor, extended))
    return None


def _r2_solve_c2(
    item: BenchmarkItem,
    solvers: SolverToolRegistry,
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    target_state = item.question["target_state"]
    reachable = solvers.is_reachable(item.fsm, target_state)
    audit.certificate_step(
        "invoke solver.reachability_certificate",
        details={"target_state": target_state},
    )
    certificate = solvers.reachability_certificate(item.fsm, target_state)
    audit.certificate_step(
        "bind verdict to solver reachability result",
        details={"verdict": reachable},
    )
    return {
        "item_id": item.item_id,
        "verdict": reachable,
        "certificate": certificate,
    }


def _r2_solve_f1(
    item: BenchmarkItem,
    solvers: SolverToolRegistry,
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    separation = solvers.check_separation(item.fsm_a, item.fsm_b)
    if separation["equivalent"]:
        audit.certificate_step("invoke solver.equivalence_certificate")
        certificate = solvers.equivalence_certificate(item.fsm_a, item.fsm_b)
        audit.certificate_step("bind verdict true for equivalent DFAs")
        return {
            "item_id": item.item_id,
            "verdict": True,
            "certificate": certificate,
        }

    audit.certificate_step("invoke solver.distinguishing_certificate")
    certificate = solvers.distinguishing_certificate(item.fsm_a, item.fsm_b)
    audit.certificate_step("bind verdict false for non-equivalent DFAs")
    return {
        "item_id": item.item_id,
        "verdict": False,
        "certificate": certificate,
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
    for _symbol in reversed(trace):
        prev, _ = parent[state]
        if prev is None:
            raise RuntimeError("broken parent chain")
        state = prev
        state_sequence.append(state)
    state_sequence.reverse()
    return trace, tuple(state_sequence)

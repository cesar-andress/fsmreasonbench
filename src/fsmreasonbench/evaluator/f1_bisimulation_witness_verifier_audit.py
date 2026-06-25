"""Hostile audit battery for F1 bisimulation_witness verification (Experiment A1)."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.dfa_minimize import complete_dfa
from fsmreasonbench.verifier.separation import verify_bisimulation_witness_certificate

CODE_PATHS = {
    "parser": "src/fsmreasonbench/evaluator/parser.py::_validate_bisimulation_witness_payload",
    "scorer": "src/fsmreasonbench/evaluator/scorer_f1.py::score_f1_item → verify_f1_certificate",
    "semantic_verifier": "src/fsmreasonbench/verifier/separation.py::verify_bisimulation_witness_certificate",
    "relation_builder": "src/fsmreasonbench/runtime/bisimulation.py::compute_bisimulation_pairs",
    "certificate_builder": "src/fsmreasonbench/certificates/separation.py::build_bisimulation_witness_certificate",
}


@dataclass(frozen=True, slots=True)
class AuditCheckResult:
    check_id: str
    title: str
    passed: bool
    detail: str


def _equivalent_item(seed: int = 21):
    return generate_separation_item(
        seed,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )


def _non_equivalent_item(seed: int = 7):
    return generate_separation_item(seed)


def _mutate_pairs(certificate: dict[str, Any], pairs: list[dict[str, str]]) -> dict[str, Any]:
    mutated = copy.deepcopy(certificate)
    mutated.setdefault("payload", {})["pairs"] = pairs
    return mutated


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


def run_bisimulation_audit_battery() -> dict[str, Any]:
    checks: list[AuditCheckResult] = []

    def record(check_id: str, title: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            checks.append(AuditCheckResult(check_id, title, True, "passed"))
        except AssertionError as exc:
            checks.append(
                AuditCheckResult(check_id, title, False, str(exc) or "assertion failed")
            )

    eq_item = _equivalent_item()
    ne_item = _non_equivalent_item()
    gold = build_bisimulation_witness_certificate(eq_item.fsm_a, eq_item.fsm_b)
    gold_pairs = gold["payload"]["pairs"]

    record(
        "A",
        "Oracle bisimulation_witness passes",
        lambda: _assert_valid(eq_item.fsm_a, eq_item.fsm_b, gold),
    )
    record(
        "B",
        "Independently rebuilt witness passes",
        lambda: _assert_valid(
            eq_item.fsm_a,
            eq_item.fsm_b,
            build_bisimulation_witness_certificate(eq_item.fsm_a, eq_item.fsm_b),
        ),
    )
    record(
        "C",
        "Missing initial state pair fails",
        lambda: _assert_invalid(
            eq_item.fsm_a,
            eq_item.fsm_b,
            _mutate_pairs(gold, gold_pairs[1:]),
        ),
    )
    record(
        "D",
        "Non-equivalent DFAs fail semantically",
        lambda: _assert_invalid(
            ne_item.fsm_a,
            ne_item.fsm_b,
            {
                **gold,
                "fsm_ids": [ne_item.fsm_a.fsm_id, ne_item.fsm_b.fsm_id],
            },
        ),
    )
    record(
        "E",
        "Acceptance mismatch in pair fails",
        lambda: _assert_invalid_with(
            eq_item.fsm_a,
            _flip_accepting(eq_item.fsm_b, eq_item.fsm_b.initial_state),
            gold,
            expected_substrings=("acceptance mismatch",),
        ),
    )
    initial_pair = {
        "state_a": complete_dfa(eq_item.fsm_a).initial_state,
        "state_b": complete_dfa(eq_item.fsm_b).initial_state,
    }
    non_initial_pairs = [p for p in gold_pairs if p != initial_pair]
    reduced_pairs = [p for p in gold_pairs if p != non_initial_pairs[-1]] if non_initial_pairs else gold_pairs[:1]

    record(
        "F",
        "Incomplete relation fails",
        lambda: _assert_invalid_with(
            eq_item.fsm_a,
            eq_item.fsm_b,
            _mutate_pairs(gold, reduced_pairs),
            expected_substrings=("transition inconsistency",),
        ),
    )
    record(
        "G",
        "Swapped fsm_ids fails",
        lambda: _assert_invalid(
            eq_item.fsm_a,
            eq_item.fsm_b,
            {**gold, "fsm_ids": [eq_item.fsm_b.fsm_id, eq_item.fsm_a.fsm_id]},
        ),
    )
    record(
        "H",
        "Malformed pairs payload fails",
        lambda: _assert_invalid(
            eq_item.fsm_a,
            eq_item.fsm_b,
            {**gold, "payload": {"equivalent": True, "pairs": "not-an-array"}},
        ),
    )
    record(
        "I",
        "Extra invalid unreachable pair fails",
        lambda: _assert_invalid_with(
            eq_item.fsm_a,
            eq_item.fsm_b,
            _mutate_pairs(
                gold,
                [
                    *gold_pairs,
                    {"state_a": "__bogus__", "state_b": "__bogus__"},
                ],
            ),
            expected_substrings=("unknown state", "transition inconsistency"),
        ),
    )
    record(
        "J",
        "Wrong certificate_type fails",
        lambda: _assert_invalid(
            eq_item.fsm_a,
            eq_item.fsm_b,
            {**gold, "certificate_type": "equivalence_witness"},
        ),
    )

    passed = sum(1 for check in checks if check.passed)
    return {
        "experiment": "f1_bisimulation_witness_verifier_audit",
        "code_paths": CODE_PATHS,
        "checks": [
            {
                "check_id": c.check_id,
                "title": c.title,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in checks
        ],
        "summary": {
            "total": len(checks),
            "passed": passed,
            "failed": len(checks) - passed,
            "all_passed": passed == len(checks),
        },
        "paper_validity_sentence": (
            "An F1 bisimulation_witness is valid iff the benchmark DFAs are semantically "
            "equivalent and the submitter supplies a state-pair relation containing the "
            "initial pair, preserving acceptance on every pair, and closed under paired "
            "transitions on the shared alphabet — with no hash digest required."
        ),
    }


def _assert_valid(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM, certificate: dict[str, Any]) -> None:
    result = verify_bisimulation_witness_certificate(fsm_a, fsm_b, certificate)
    assert result.valid, result.errors


def _assert_invalid(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM, certificate: dict[str, Any]) -> None:
    result = verify_bisimulation_witness_certificate(fsm_a, fsm_b, certificate)
    assert not result.valid, result.errors


def _assert_invalid_with(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
    *,
    expected_substrings: tuple[str, ...],
) -> None:
    result = verify_bisimulation_witness_certificate(fsm_a, fsm_b, certificate)
    assert not result.valid, result.errors
    joined = " ".join(result.errors).lower()
    assert any(fragment.lower() in joined for fragment in expected_substrings), result.errors


def render_bisimulation_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# F1 bisimulation_witness Verifier Audit",
        "",
        "Hostile audit of the constructible equivalence witness path (Experiment A1).",
        "",
        "| ID | Title | Result | Detail |",
        "|----|-------|--------|--------|",
    ]
    for check in payload["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(
            f"| {check['check_id']} | {check['title']} | {status} | {check['detail']} |"
        )
    summary = payload["summary"]
    lines.extend(
        [
            "",
            f"**Summary:** {summary['passed']}/{summary['total']} checks passed.",
            "",
            "## Paper validity sentence",
            "",
            f"> {payload['paper_validity_sentence']}",
            "",
        ]
    )
    return "\n".join(lines)


def export_f1_bisimulation_witness_verifier_audit(
    *,
    markdown_path: str,
    json_path: str,
) -> dict[str, Any]:
    from pathlib import Path
    import json as json_module

    payload = run_bisimulation_audit_battery()
    markdown = Path(markdown_path)
    js = Path(json_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    js.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_bisimulation_audit_markdown(payload), encoding="utf-8")
    js.write_text(json_module.dumps(payload, indent=2), encoding="utf-8")
    return payload

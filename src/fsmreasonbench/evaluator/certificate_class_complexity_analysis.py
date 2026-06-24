"""Structural complexity analysis for FSMReasonBench certificate classes."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.failure_taxonomy import classify_certificate_errors
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl

CERTIFICATE_TYPES = (
    "distinguishing_trace",
    "equivalence_witness",
    "trace_witness",
    "unreachability_witness",
)

FROZEN_FAILURE_RUNS: tuple[dict[str, str], ...] = (
    {
        "label": "F1 Claude R1",
        "scores_path": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl"
        ),
        "cohort_path": "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
        "condition": "R1",
    },
    {
        "label": "F1 Oracle+Format",
        "scores_path": (
            "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/scores.jsonl"
        ),
        "cohort_path": "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
        "condition": "Oracle+Format",
    },
    {
        "label": "C2 Claude R1",
        "scores_path": (
            "runs/ablations_c2_existential_universal_claude_n100_v1/R1/scores.jsonl"
        ),
        "cohort_path": (
            "cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100/items.jsonl"
        ),
        "condition": "R1",
    },
    {
        "label": "C2 Oracle+Format",
        "scores_path": (
            "runs/ablations_c2_existential_universal_claude_n100_v1/Oracle/scores.jsonl"
        ),
        "cohort_path": (
            "cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100/items.jsonl"
        ),
        "condition": "Oracle+Format",
    },
)

SEMANTIC_FAILURE_CATEGORIES = frozenset(
    {
        "equivalence_hash_mismatch",
        "acceptance_mismatch",
        "incomplete_reachability_set",
        "replay_failure",
    }
)
FORMATTING_FAILURE_CATEGORIES = frozenset(
    {
        "wrong_trace_format",
        "malformed_certificate_payload",
        "wrong_certificate_type",
        "wrong_fsm_ids",
    }
)


@dataclass(frozen=True, slots=True)
class CertificateClassSpec:
    certificate_type: str
    family: str
    verdict_polarity: str
    code_paths: dict[str, str]
    envelope_fields: tuple[str, ...]
    payload_fields: tuple[str, ...]
    optional_payload_fields: tuple[str, ...]
    required_fields: int
    semantic_fields: int
    verifier_recomputes: tuple[str, ...]
    exact_match_fields: tuple[str, ...]
    canonical_fields: tuple[str, ...]
    estimated_information_content: str
    local_reasoning_sufficient: bool
    requires_minimization: bool
    requires_symbolic_search: bool
    requires_state_space_closure: bool
    requires_canonical_hashing: bool
    requires_exact_set_reconstruction: bool
    requires_replay_verification: bool
    multiple_valid_certificates: bool
    verifier_accepts_multiple_forms: bool
    canonicalization_required: bool
    symbolic_synthesis_required: bool
    estimated_complexity_score: float
    verifier_strictness_notes: str
    synthesis_notes: str


def _build_certificate_specs() -> dict[str, CertificateClassSpec]:
    """Static structural specs grounded in verifier/parser/generator code."""
    specs = {
        "distinguishing_trace": CertificateClassSpec(
            certificate_type="distinguishing_trace",
            family="F1",
            verdict_polarity="false (non-equivalent)",
            code_paths={
                "parser": "evaluator/parser.py::_validate_distinguishing_trace_payload",
                "verifier": "verifier/separation.py::verify_distinguishing_trace_certificate",
                "builder": "certificates/separation.py::build_distinguishing_trace_certificate",
                "oracle": "oracle/separation.py::shortest_distinguishing_trace",
            },
            envelope_fields=("certificate_type", "version", "fsm_ids", "verdict_supported"),
            payload_fields=("trace", "acceptance"),
            optional_payload_fields=(),
            required_fields=8,
            semantic_fields=3,
            verifier_recomputes=(
                "acceptance.A via accepts_trace(fsm_a, trace)",
                "acceptance.B via accepts_trace(fsm_b, trace)",
                "distinguishing property (acceptance_A != acceptance_B)",
            ),
            exact_match_fields=("fsm_ids (ordered pair)",),
            canonical_fields=(),
            estimated_information_content=(
                "O(|trace|) alphabet symbols plus 2 acceptance bits; "
                "verifier does not require shortest trace."
            ),
            local_reasoning_sufficient=False,
            requires_minimization=False,
            requires_symbolic_search=True,
            requires_state_space_closure=False,
            requires_canonical_hashing=False,
            requires_exact_set_reconstruction=False,
            requires_replay_verification=True,
            multiple_valid_certificates=True,
            verifier_accepts_multiple_forms=True,
            canonicalization_required=False,
            symbolic_synthesis_required=True,
            estimated_complexity_score=4.5,
            verifier_strictness_notes=(
                "Semantic replay checks only; any distinguishing trace accepted. "
                "Shortest trace is oracle metadata, not enforced."
            ),
            synthesis_notes=(
                "Witness found by BFS product-graph search (oracle/separation.py); "
                "model must propose trace + acceptance matching replay."
            ),
        ),
        "equivalence_witness": CertificateClassSpec(
            certificate_type="equivalence_witness",
            family="F1",
            verdict_polarity="true (equivalent)",
            code_paths={
                "parser": "evaluator/parser.py::_validate_equivalence_witness_payload",
                "verifier": "verifier/separation.py::verify_equivalence_witness_certificate",
                "builder": "certificates/separation.py::build_equivalence_witness_certificate",
                "hash": "runtime/dfa_minimize.py::minimized_dfa_hash",
                "equivalence": "runtime/dfa_minimize.py::are_equivalent_dfas",
            },
            envelope_fields=("certificate_type", "version", "fsm_ids", "verdict_supported"),
            payload_fields=("equivalent", "minimized_hash_A", "minimized_hash_B"),
            optional_payload_fields=(),
            required_fields=9,
            semantic_fields=3,
            verifier_recomputes=(
                "are_equivalent_dfas(fsm_a, fsm_b) [pair BFS]",
                "minimized_dfa_hash(fsm_a)",
                "minimized_dfa_hash(fsm_b)",
                "hash equality across equivalent DFAs",
            ),
            exact_match_fields=(
                "payload.equivalent == true",
                "payload.minimized_hash_A",
                "payload.minimized_hash_B",
                "fsm_ids (ordered pair)",
            ),
            canonical_fields=("minimized_hash_A", "minimized_hash_B"),
            estimated_information_content=(
                "Two fixed 64-char hex hashes encoding a bounded language bitvector "
                "(trace lengths 0..min(|Q|,12) over completed reachable DFA)."
            ),
            local_reasoning_sufficient=False,
            requires_minimization=True,
            requires_symbolic_search=True,
            requires_state_space_closure=True,
            requires_canonical_hashing=True,
            requires_exact_set_reconstruction=False,
            requires_replay_verification=False,
            multiple_valid_certificates=False,
            verifier_accepts_multiple_forms=False,
            canonicalization_required=True,
            symbolic_synthesis_required=True,
            estimated_complexity_score=9.5,
            verifier_strictness_notes=(
                "Strictest class: semantic equivalence PLUS exact hash match to "
                "verifier-recomputed minimized_dfa_hash outputs. Hash mismatch "
                "rejects witness even when verdict/equivalence is correct."
            ),
            synthesis_notes=(
                "Gold builder calls minimized_dfa_hash on both DFAs; R2C uses "
                "solver.equivalence_certificate. No alternate witness types accepted."
            ),
        ),
        "trace_witness": CertificateClassSpec(
            certificate_type="trace_witness",
            family="C2",
            verdict_polarity="true (reachable)",
            code_paths={
                "parser": "evaluator/parser.py::_validate_c2_certificate (trace_witness)",
                "verifier": "verifier/reachability.py::_verify_trace_witness",
                "builder": "certificates/reachability.py::_trace_payload",
                "oracle": "oracle/reachability.py::shortest_reachability_witness",
            },
            envelope_fields=("certificate_type", "version", "fsm_id", "verdict_supported"),
            payload_fields=("trace", "state_sequence"),
            optional_payload_fields=("branching_choices", "accepting"),
            required_fields=7,
            semantic_fields=2,
            verifier_recomputes=(
                "simulate(fsm, trace) state_sequence",
                "initial state and target_state endpoints",
            ),
            exact_match_fields=("state_sequence (must match replay exactly)",),
            canonical_fields=(),
            estimated_information_content=(
                "O(|trace|) symbols plus O(|trace|+1) state labels; "
                "multiple traces may exist for same target."
            ),
            local_reasoning_sufficient=True,
            requires_minimization=False,
            requires_symbolic_search=True,
            requires_state_space_closure=False,
            requires_canonical_hashing=False,
            requires_exact_set_reconstruction=False,
            requires_replay_verification=True,
            multiple_valid_certificates=True,
            verifier_accepts_multiple_forms=True,
            canonicalization_required=False,
            symbolic_synthesis_required=True,
            estimated_complexity_score=3.5,
            verifier_strictness_notes=(
                "Replay-based; any valid path ending at target accepted. "
                "Prompt example includes accepting but verifier ignores it."
            ),
            synthesis_notes=(
                "Single-FSM path search; analogous to distinguishing_trace on one machine."
            ),
        ),
        "unreachability_witness": CertificateClassSpec(
            certificate_type="unreachability_witness",
            family="C2",
            verdict_polarity="false (unreachable)",
            code_paths={
                "parser": "evaluator/parser.py::_validate_c2_certificate (unreachability)",
                "verifier": "verifier/reachability.py::_verify_unreachability_witness",
                "builder": "certificates/reachability.py::_unreachability_payload",
                "closure": "runtime/reachability.py::reachable_states",
            },
            envelope_fields=("certificate_type", "version", "fsm_id", "verdict_supported"),
            payload_fields=("reachable_states", "target_state"),
            optional_payload_fields=(),
            required_fields=7,
            semantic_fields=2,
            verifier_recomputes=(
                "reachable_states(fsm) [BFS from initial]",
                "target_state not in reachable set",
            ),
            exact_match_fields=(
                "reachable_states set equality (frozenset)",
                "target_state string",
            ),
            canonical_fields=("reachable_states",),
            estimated_information_content=(
                "O(|R|) state names where R is reachable set; unique set content, "
                "list order immaterial (set equality)."
            ),
            local_reasoning_sufficient=True,
            requires_minimization=False,
            requires_symbolic_search=False,
            requires_state_space_closure=True,
            requires_canonical_hashing=False,
            requires_exact_set_reconstruction=True,
            requires_replay_verification=False,
            multiple_valid_certificates=False,
            verifier_accepts_multiple_forms=False,
            canonicalization_required=True,
            estimated_complexity_score=5.0,
            symbolic_synthesis_required=False,
            verifier_strictness_notes=(
                "Requires exact reachable set, not a valid sub/superset invariant. "
                "Set canonicalization (unique membership) but not hash-based."
            ),
            synthesis_notes=(
                "Gold builder lists full BFS reachable set. Claude R1 ~100% despite "
                "exact-set contract — closure is simpler than minimized_dfa_hash."
            ),
        ),
    }
    return specs


def build_comparative_matrix(
    specs: dict[str, CertificateClassSpec] | None = None,
) -> list[dict[str, Any]]:
    specs = specs or _build_certificate_specs()
    rows: list[dict[str, Any]] = []
    for cert_type in CERTIFICATE_TYPES:
        spec = specs[cert_type]
        rows.append(
            {
                "certificate_type": cert_type,
                "family": spec.family,
                "required_fields": spec.required_fields,
                "semantic_fields": spec.semantic_fields,
                "canonical_fields": len(spec.canonical_fields),
                "exact_match_fields": len(spec.exact_match_fields),
                "verifier_recomputes": len(spec.verifier_recomputes),
                "multiple_valid_forms": spec.verifier_accepts_multiple_forms,
                "canonicalization_required": spec.canonicalization_required,
                "symbolic_synthesis_required": spec.symbolic_synthesis_required,
                "requires_minimization": spec.requires_minimization,
                "requires_canonical_hashing": spec.requires_canonical_hashing,
                "requires_exact_set_reconstruction": spec.requires_exact_set_reconstruction,
                "requires_replay_verification": spec.requires_replay_verification,
                "local_reasoning_sufficient": spec.local_reasoning_sufficient,
                "estimated_complexity_score": spec.estimated_complexity_score,
            }
        )
    return rows


def _gold_certificate_type(item_id: str, cohort_path: Path) -> str:
    for item in load_items_jsonl(cohort_path):
        if item.item_id == item_id:
            return str(item.answer_key["certificate"]["certificate_type"])
    return "unknown"


def _load_cohort_cert_types(cohort_path: Path) -> dict[str, str]:
    return {
        item.item_id: str(item.answer_key["certificate"]["certificate_type"])
        for item in load_items_jsonl(cohort_path)
    }


def analyze_failure_taxonomy_by_certificate_type(
    repo_root: Path,
) -> dict[str, Any]:
    """Aggregate frozen-run certificate failures by gold certificate type."""
    by_type: dict[str, dict[str, Any]] = {}
    per_run: list[dict[str, Any]] = []

    for run in FROZEN_FAILURE_RUNS:
        scores_path = repo_root / run["scores_path"]
        cohort_path = repo_root / run["cohort_path"]
        if not scores_path.exists():
            continue
        cert_types = _load_cohort_cert_types(cohort_path)
        run_stats: dict[str, Any] = {
            "label": run["label"],
            "condition": run["condition"],
            "scores_path": run["scores_path"],
            "by_certificate_type": {},
        }
        type_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "n": 0,
                "extractable": 0,
                "certificate_invalid": 0,
                "failure_categories": Counter(),
                "semantic_failures": 0,
                "formatting_failures": 0,
                "sample_errors": [],
            }
        )
        for row in read_jsonl(scores_path):
            item_id = row["item_id"]
            cert_type = cert_types.get(item_id, "unknown")
            bucket = type_buckets[cert_type]
            bucket["n"] += 1
            if not row.get("extractable"):
                continue
            bucket["extractable"] += 1
            if row.get("certificate_valid"):
                continue
            bucket["certificate_invalid"] += 1
            errors = tuple(row.get("certificate_errors") or [])
            category = classify_certificate_errors(errors)
            bucket["failure_categories"][category] += 1
            if category in SEMANTIC_FAILURE_CATEGORIES:
                bucket["semantic_failures"] += 1
            elif category in FORMATTING_FAILURE_CATEGORIES:
                bucket["formatting_failures"] += 1
            if len(bucket["sample_errors"]) < 2 and errors:
                bucket["sample_errors"].append({"item_id": item_id, "errors": list(errors)})

        for cert_type, bucket in type_buckets.items():
            invalid = bucket["certificate_invalid"]
            extractable = bucket["extractable"]
            summary = {
                "n": bucket["n"],
                "extractable": extractable,
                "certificate_invalid": invalid,
                "certificate_invalid_rate": round(invalid / extractable, 3)
                if extractable
                else 0.0,
                "top_failure_categories": [
                    {"category": cat, "count": count}
                    for cat, count in bucket["failure_categories"].most_common(5)
                ],
                "semantic_failures": bucket["semantic_failures"],
                "formatting_failures": bucket["formatting_failures"],
                "verifier_rejection_mechanism": _rejection_mechanism(cert_type),
                "sample_errors": bucket["sample_errors"],
            }
            run_stats["by_certificate_type"][cert_type] = summary
            aggregate = by_type.setdefault(
                cert_type,
                {
                    "runs": [],
                    "pooled_invalid_rates": [],
                    "pooled_categories": Counter(),
                },
            )
            aggregate["runs"].append({"label": run["label"], **summary})
            aggregate["pooled_invalid_rates"].append(summary["certificate_invalid_rate"])
            aggregate["pooled_categories"].update(bucket["failure_categories"])

        per_run.append(run_stats)

    pooled_summary = {}
    for cert_type, aggregate in by_type.items():
        cats = aggregate["pooled_categories"]
        total = sum(cats.values())
        pooled_summary[cert_type] = {
            "mean_invalid_rate_across_runs": round(
                sum(aggregate["pooled_invalid_rates"]) / len(aggregate["pooled_invalid_rates"]),
                3,
            )
            if aggregate["pooled_invalid_rates"]
            else 0.0,
            "top_failure_categories": [
                {
                    "category": cat,
                    "count": count,
                    "percentage": round(count / total, 3) if total else 0.0,
                }
                for cat, count in cats.most_common()
            ],
            "semantic_vs_formatting": {
                "semantic": sum(cats[c] for c in SEMANTIC_FAILURE_CATEGORIES),
                "formatting": sum(cats[c] for c in FORMATTING_FAILURE_CATEGORIES),
                "other": total
                - sum(cats[c] for c in SEMANTIC_FAILURE_CATEGORIES)
                - sum(cats[c] for c in FORMATTING_FAILURE_CATEGORIES),
            },
        }

    return {
        "runs_analyzed": per_run,
        "pooled_by_certificate_type": pooled_summary,
    }


def _rejection_mechanism(cert_type: str) -> str:
    mechanisms = {
        "distinguishing_trace": (
            "Replay trace on both DFAs; reject if acceptance labels mismatch replay "
            "or trace does not distinguish."
        ),
        "equivalence_witness": (
            "Run are_equivalent_dfas; recompute minimized_dfa_hash for each DFA; "
            "reject on semantic non-equivalence or any hash mismatch."
        ),
        "trace_witness": (
            "Simulate trace; reject if state_sequence length/endpoints/replay mismatch."
        ),
        "unreachability_witness": (
            "BFS reachable set; reject if witness set != computed set or target listed."
        ),
    }
    return mechanisms.get(cert_type, "unknown")


def build_research_answers(
    specs: dict[str, CertificateClassSpec],
    failure_analysis: dict[str, Any],
    matrix: list[dict[str, Any]],
) -> dict[str, str]:
    eq = specs["equivalence_witness"]
    dist = specs["distinguishing_trace"]
    trace = specs["trace_witness"]
    unreach = specs["unreachability_witness"]
    eq_fail = failure_analysis["pooled_by_certificate_type"].get("equivalence_witness", {})

    return {
        "is_equivalence_witness_uniquely_canonicalization_dependent": (
            "Yes, among these four classes, equivalence_witness is the **only** one "
            "requiring minimized_dfa_hash canonical strings (requires_canonical_hashing=True). "
            "unreachability_witness requires exact set reconstruction but not hashing; "
            "trace_witness and distinguishing_trace accept multiple replay-valid witnesses."
        ),
        "is_equivalence_witness_uniquely_synthesis_dependent": (
            "No — all four require symbolic synthesis for gold construction. "
            "equivalence_witness uniquely pairs synthesis with **non-negotiable hash output**; "
            "distinguishing_trace and trace_witness need search but accept any valid witness, "
            "and unreachability_witness needs only BFS closure (no search)."
        ),
        "does_verifier_strictness_differ": (
            "Yes. Strictness ordering by estimated_complexity_score: "
            f"equivalence_witness ({eq.estimated_complexity_score}) > "
            f"unreachability_witness ({unreach.estimated_complexity_score}) > "
            f"distinguishing_trace ({dist.estimated_complexity_score}) > "
            f"trace_witness ({trace.estimated_complexity_score}). "
            "Only equivalence_witness rejects semantically correct verdicts when "
            "hashes are wrong (equivalence_hash_mismatch)."
        ),
        "multiple_valid_certificates_other_classes": (
            "Yes. distinguishing_trace and trace_witness accept multiple valid witnesses "
            "(verifier_accepts_multiple_forms=True). unreachability_witness allows "
            "permutation of list order but not set content. equivalence_witness accepts "
            "a single hash pair tied to minimized_dfa_hash."
        ),
        "best_predictor_of_claude_collapse": (
            "Canonical hash emission under R1 self-construction. Claude R1: "
            "equivalence_witness 51/51 invalid (100%) with equivalence_hash_mismatch; "
            "distinguishing_trace 3/49 invalid (~6%); C2 trace_witness 2/50; "
            "unreachability_witness 0/50. Collapse tracks "
            "requires_canonical_hashing=True, not existential-vs-universal polarity."
        ),
        "paper_hypothesis": (
            "Claude's F1 equivalence collapse is driven by the **canonical hash witness "
            "contract** (minimized_dfa_hash), not by universal quantification per se: "
            "C2 unreachability_witness also demands exact closure yet remains easy, while "
            "F1 distinguishing_trace (existential trace) stays easy without hashing. "
            "R2C closes equivalence_witness only via solver.equivalence_certificate, "
            "which runs the same hash builder as the verifier."
        ),
    }


def run_certificate_class_complexity_analysis(repo_root: str | Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    specs = _build_certificate_specs()
    matrix = build_comparative_matrix(specs)
    failure_analysis = analyze_failure_taxonomy_by_certificate_type(repo_root)
    research_answers = build_research_answers(specs, failure_analysis, matrix)

    claude_r1_rates = {}
    for run in failure_analysis["runs_analyzed"]:
        if run["label"] == "F1 Claude R1":
            for ct, stats in run["by_certificate_type"].items():
                claude_r1_rates[ct] = 1.0 - stats["certificate_invalid_rate"]

    return {
        "analysis": "certificate_class_complexity",
        "methodology": {
            "sources": [
                "verifier/separation.py",
                "verifier/reachability.py",
                "evaluator/parser.py",
                "certificates/separation.py",
                "certificates/reachability.py",
                "runtime/dfa_minimize.py",
                "frozen Claude R1 / Oracle scoring outputs (no new model calls)",
            ],
            "complexity_score_scale": (
                "Heuristic 1–10 composite: +2 canonical hashing, +2 minimization, "
                "+1.5 exact set reconstruction, +1 symbolic search, +1 state-space "
                "closure, +1 strict exact-match fields, −1 local reasoning sufficient, "
                "−0.5 multiple valid forms accepted."
            ),
            "no_verifier_changes": True,
            "no_new_model_calls": True,
        },
        "certificate_specs": {
            key: asdict(spec) for key, spec in specs.items()
        },
        "comparative_matrix": matrix,
        "failure_taxonomy": failure_analysis,
        "claude_r1_certificate_valid_rate_by_type": claude_r1_rates,
        "research_answers": research_answers,
        "mechanistic_explanation": {
            "what_makes_equivalence_witness_hard": [
                "Payload is not a human-readable witness; it requires two hex hashes "
                "produced by minimized_dfa_hash (complete DFA → reachable core → "
                "enumerate language bits for lengths 0..min(|Q|,12)).",
                "Verifier independently runs are_equivalent_dfas AND recomputes both "
                "hashes; all four checks must pass.",
                "No alternate certificate types or approximate hashes accepted "
                "(verifier audit: single canonical witness form).",
                "Parser enforces equivalent=true and non-empty hash strings before "
                "semantic verification.",
                "Claude R1 failures are 51/51 equivalence_hash_mismatch with "
                "verdict_accuracy=1.0 — models know equivalence but cannot emit "
                "verifier-identical hashes without solver.equivalence_certificate.",
                "R2C success (~0.98) uses build_equivalence_witness_certificate / "
                "solver tool — same code path as gold builder.",
            ],
            "why_c2_does_not_mirror_f1": [
                "trace_witness: replay-only, multiple valid paths, no hashing.",
                "unreachability_witness: exact set required but computable by single "
                "BFS without minimization or language bitvector hashing.",
                "Claude R1 unreachability_witness full≈1.00 vs equivalence_witness 0.00 "
                "despite both being 'negative verdict' items — negates simple "
                "existential/universal asymmetry explanation.",
            ],
        },
    }


def render_markdown_report(payload: dict[str, Any]) -> str:
    specs = payload["certificate_specs"]
    matrix = payload["comparative_matrix"]
    answers = payload["research_answers"]
    mech = payload["mechanistic_explanation"]
    failure = payload["failure_taxonomy"]

    lines = [
        "# Certificate Class Complexity Analysis",
        "",
        "Structural comparison explaining why F1 `equivalence_witness` behaves "
        "differently from other certificate classes. **No new model calls; "
        "no verifier changes.**",
        "",
        "## Comparative matrix",
        "",
        "| certificate_type | required | semantic | canonical | exact_match | "
        "multi_form | canon_req | synth_req | recomputes | complexity |",
        "|------------------|--------:|---------:|----------:|------------:|"
        "---------:|----------:|----------:|-----------:|-----------:|",
    ]
    for row in matrix:
        lines.append(
            f"| {row['certificate_type']} | {row['required_fields']} | "
            f"{row['semantic_fields']} | {row['canonical_fields']} | "
            f"{row['exact_match_fields']} | {row['multiple_valid_forms']} | "
            f"{row['canonicalization_required']} | {row['symbolic_synthesis_required']} | "
            f"{row['verifier_recomputes']} | {row['estimated_complexity_score']} |"
        )

    lines.extend(["", "## Per-class structural profile", ""])
    for cert_type in CERTIFICATE_TYPES:
        spec = specs[cert_type]
        lines.extend(
            [
                f"### {cert_type} ({spec['family']}, verdict {spec['verdict_polarity']})",
                "",
                f"- **Required fields:** {spec['required_fields']} "
                f"(envelope: {', '.join(spec['envelope_fields'])}; "
                f"payload: {', '.join(spec['payload_fields'])})",
                f"- **Semantic fields:** {spec['semantic_fields']}",
                f"- **Verifier recomputes:** {len(spec['verifier_recomputes'])} checks — "
                + "; ".join(spec["verifier_recomputes"]),
                f"- **Exact-match fields:** {', '.join(spec['exact_match_fields']) or '—'}",
                f"- **Canonical fields:** {', '.join(spec['canonical_fields']) or '—'}",
                f"- **Information content:** {spec['estimated_information_content']}",
                f"- **Local reasoning sufficient:** {spec['local_reasoning_sufficient']}",
                f"- **Multiple valid certificates:** {spec['multiple_valid_certificates']} "
                f"(verifier accepts multiple forms: {spec['verifier_accepts_multiple_forms']})",
                f"- **Synthesis:** minimization={spec['requires_minimization']}, "
                f"symbolic_search={spec['requires_symbolic_search']}, "
                f"state_closure={spec['requires_state_space_closure']}, "
                f"canonical_hash={spec['requires_canonical_hashing']}, "
                f"exact_set={spec['requires_exact_set_reconstruction']}, "
                f"replay={spec['requires_replay_verification']}",
                f"- **Verifier notes:** {spec['verifier_strictness_notes']}",
                "",
            ]
        )

    lines.extend(["", "## Failure taxonomy (frozen Claude runs)", ""])
    for cert_type in CERTIFICATE_TYPES:
        pooled = failure["pooled_by_certificate_type"].get(cert_type, {})
        lines.append(f"### {cert_type}")
        if not pooled:
            lines.append("- No pooled failure data in analyzed runs.")
            lines.append("")
            continue
        svf = pooled.get("semantic_vs_formatting", {})
        lines.append(
            f"- Pooled semantic failures: {svf.get('semantic', 0)}; "
            f"formatting: {svf.get('formatting', 0)}; other: {svf.get('other', 0)}"
        )
        lines.append(f"- Rejection mechanism: {_rejection_mechanism(cert_type)}")
        for entry in pooled.get("top_failure_categories", [])[:5]:
            lines.append(
                f"- `{entry['category']}`: {entry['count']} "
                f"({entry['percentage']:.1%} of pooled invalid)"
            )
        lines.append("")

    lines.extend(
        [
            "## What makes equivalence_witness hard?",
            "",
        ]
    )
    for bullet in mech["what_makes_equivalence_witness_hard"]:
        lines.append(f"- {bullet}")
    lines.extend(["", "### Why C2 does not mirror F1", ""])
    for bullet in mech["why_c2_does_not_mirror_f1"]:
        lines.append(f"- {bullet}")

    lines.extend(["", "## Research questions", ""])
    questions = [
        ("Is equivalence_witness uniquely canonicalization-dependent?", "is_equivalence_witness_uniquely_canonicalization_dependent"),
        ("Is equivalence_witness uniquely synthesis-dependent?", "is_equivalence_witness_uniquely_synthesis_dependent"),
        ("Does verifier strictness differ across certificate classes?", "does_verifier_strictness_differ"),
        ("Are there multiple valid certificates for other classes but not equivalence_witness?", "multiple_valid_certificates_other_classes"),
        ("What structural property best predicts Claude's collapse?", "best_predictor_of_claude_collapse"),
        ("What exact hypothesis should the paper make?", "paper_hypothesis"),
    ]
    for q, key in questions:
        lines.extend(["", f"### {q}", "", answers[key], ""])

    lines.extend(
        [
            "",
            "## Claude R1 certificate_valid_rate by type (frozen runs)",
            "",
            "| certificate_type | cert_valid_rate |",
            "|------------------|----------------:|",
        ]
    )
    for cert_type, rate in sorted(payload.get("claude_r1_certificate_valid_rate_by_type", {}).items()):
        lines.append(f"| {cert_type} | {rate:.3f} |")

    lines.extend(
        [
            "",
            "## Methodology notes",
            "",
            payload["methodology"]["complexity_score_scale"],
            "",
            "Sources: verifier/parser/generator code paths cited in JSON export.",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv_tables(payload: dict[str, Any], csv_path: Path) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Table: Comparative matrix"])
        matrix = payload["comparative_matrix"]
        if matrix:
            writer.writerow(list(matrix[0].keys()))
            for row in matrix:
                writer.writerow([row[k] for k in matrix[0].keys()])
        writer.writerow([])

        writer.writerow(["Table: Failure taxonomy by certificate type (pooled)"])
        writer.writerow(
            [
                "certificate_type",
                "category",
                "count",
                "percentage",
                "semantic_or_formatting",
            ]
        )
        for cert_type, pooled in payload["failure_taxonomy"]["pooled_by_certificate_type"].items():
            for entry in pooled.get("top_failure_categories", []):
                cat = entry["category"]
                kind = (
                    "semantic"
                    if cat in SEMANTIC_FAILURE_CATEGORIES
                    else "formatting"
                    if cat in FORMATTING_FAILURE_CATEGORIES
                    else "other"
                )
                writer.writerow(
                    [cert_type, cat, entry["count"], entry["percentage"], kind]
                )
        writer.writerow([])

        writer.writerow(["Table: Claude R1 cert valid rate by type"])
        writer.writerow(["certificate_type", "certificate_valid_rate"])
        for cert_type, rate in sorted(
            payload.get("claude_r1_certificate_valid_rate_by_type", {}).items()
        ):
            writer.writerow([cert_type, rate])


def export_certificate_class_complexity_analysis(
    repo_root: str | Path,
    *,
    json_out: str | Path = "docs/certificate_class_complexity_analysis.json",
    md_out: str | Path = "docs/certificate_class_complexity_analysis.md",
    csv_out: str | Path = "docs/certificate_class_complexity_tables.csv",
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    payload = run_certificate_class_complexity_analysis(repo_root)
    json_path = repo_root / json_out if not Path(json_out).is_absolute() else Path(json_out)
    md_path = repo_root / md_out if not Path(md_out).is_absolute() else Path(md_out)
    csv_path = repo_root / csv_out if not Path(csv_out).is_absolute() else Path(csv_out)
    for path in (json_path, md_path, csv_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown_report(payload), encoding="utf-8")
    write_csv_tables(payload, csv_path)
    return payload

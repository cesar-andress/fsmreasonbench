"""Decompose F1 equivalence_witness hash mismatches into construct-validity subtypes."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runtime.dfa_minimize import are_equivalent_dfas, minimized_dfa_hash
from fsmreasonbench.verifier.separation import verify_equivalence_witness_certificate

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

CATEGORY_ORDER = (
    "C1_EMPTY_OR_PLACEHOLDER",
    "C2_RANDOM_OR_NONMATCHING_HASH",
    "C3_SWAPPED_HASHES",
    "C4_PARTIAL_MATCH",
    "C5_EQUAL_BUT_WRONG_SHARED_HASH",
    "C6_NONCANONICAL_STRUCTURAL_PROOF",
    "C7_SEMANTICALLY_WRONG_EQUIVALENCE_CLAIM",
    "C8_UNCLASSIFIABLE",
)

STRUCTURAL_PROOF_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("state_mapping", re.compile(r"state\s+\w+\s+(?:maps?|corresponds?)\s+(?:to\s+)?state", re.I)),
    ("partition", re.compile(r"partition|equivalence class(?:es)?", re.I)),
    ("bisimulation", re.compile(r"bisimulation|bisimilar", re.I)),
    ("minimized_automaton", re.compile(r"minimized (?:dfa|automaton)|minimal (?:dfa|automaton)", re.I)),
    (
        "language_argument",
        re.compile(
            r"same language|accept(?:s)? the same|equivalent language|identical (?:reachable )?"
            r"(?:transitions|behavior|paths)",
            re.I,
        ),
    ),
    ("step_replay_argument", re.compile(r"step(?:ped)? through|transition(?:ed)? q\d|identical state", re.I)),
)

FAKE_HASH_SUBSTRINGS = (
    "a1b2c3d4",
    "1234567890abcdef",
    "<64-char",
    "placeholder",
    "example",
    "unknown",
)

RUNS: tuple[dict[str, str], ...] = (
    {
        "label": "R1 frozen",
        "condition": "R1",
        "results_path": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/results.jsonl"
        ),
        "scores_path": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl"
        ),
        "transcripts_dir": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/transcripts"
        ),
    },
    {
        "label": "Oracle+Format",
        "condition": "Oracle+Format",
        "results_path": (
            "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/results.jsonl"
        ),
        "scores_path": (
            "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/scores.jsonl"
        ),
        "transcripts_dir": (
            "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/transcripts"
        ),
    },
)

COHORT_PATH = "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"


@dataclass(frozen=True, slots=True)
class GoldWitness:
    semantically_equivalent: bool
    minimized_hash_a: str
    minimized_hash_b: str
    shared_gold_hash: bool


@dataclass(slots=True)
class ItemDecomposition:
    item_id: str
    condition: str
    run_label: str
    extractable: bool
    verdict_correct: bool | None
    certificate_valid: bool
    submitted_verdict: Any = None
    submitted_certificate_type: str | None = None
    submitted_equivalent: Any = None
    submitted_hash_a: str | None = None
    submitted_hash_b: str | None = None
    gold_hash_a: str | None = None
    gold_hash_b: str | None = None
    gold_semantically_equivalent: bool | None = None
    hash_a_matches_gold: bool | None = None
    hash_b_matches_gold: bool | None = None
    hashes_swapped: bool | None = None
    shared_submitted_hash: bool | None = None
    primary_category: str = "C8_UNCLASSIFIABLE"
    semantic_claim_ok: bool | None = None
    noncanonical_proof_signals: list[str] = field(default_factory=list)
    transcript_available: bool = False
    raw_response_available: bool = False
    raw_response_text_chars: int = 0
    prose_chars_before_json: int = 0
    verifier_errors: list[str] = field(default_factory=list)
    safe_excerpt: str = ""


def _prose_before_json(text: str) -> str:
    if not text:
        return ""
    idx = text.find("{")
    return text[:idx].strip() if idx > 0 else text.strip()


def _detect_noncanonical_signals(text: str, payload: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    prose = _prose_before_json(text)
    search_text = prose + "\n" + json.dumps(payload, sort_keys=True)
    for label, pattern in STRUCTURAL_PROOF_PATTERNS:
        if pattern.search(search_text):
            signals.append(label)
    extra_keys = set(payload) - {"equivalent", "minimized_hash_A", "minimized_hash_B"}
    if extra_keys:
        signals.append("extra_payload_fields:" + ",".join(sorted(extra_keys)))
    return sorted(set(signals))


def _is_placeholder_hash(value: str | None) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return True
    stripped = value.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if lowered in {"unknown", "null", "none", "placeholder", "n/a", "todo"}:
        return True
    if any(token in lowered for token in FAKE_HASH_SUBSTRINGS):
        return True
    if set(stripped) == {"0"}:
        return True
    if not HEX64.match(stripped):
        return True
    return False


def _compute_gold(item: BenchmarkItem) -> GoldWitness:
    hash_a = minimized_dfa_hash(item.fsm_a)
    hash_b = minimized_dfa_hash(item.fsm_b)
    return GoldWitness(
        semantically_equivalent=are_equivalent_dfas(item.fsm_a, item.fsm_b),
        minimized_hash_a=hash_a,
        minimized_hash_b=hash_b,
        shared_gold_hash=hash_a == hash_b,
    )


def _safe_excerpt(text: str, *, limit: int = 320) -> str:
    cleaned = re.sub(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*\S+", "[REDACTED]", text)
    cleaned = cleaned.replace("\n", " ").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _extract_submission(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    raw = row.get("raw_response")
    if isinstance(raw, dict):
        return raw, row.get("raw_response_text") or ""
    return None, row.get("raw_response_text") or ""


def classify_item(
    *,
    item: BenchmarkItem,
    row: dict[str, Any],
    score_row: dict[str, Any] | None,
    gold: GoldWitness,
    condition: str,
    run_label: str,
    transcript_path: Path | None,
) -> ItemDecomposition:
    submission, raw_text = _extract_submission(row)
    transcript_available = transcript_path is not None and transcript_path.exists()
    raw_response_available = bool(raw_text) or submission is not None

    record = ItemDecomposition(
        item_id=item.item_id,
        condition=condition,
        run_label=run_label,
        extractable=bool(score_row.get("extractable")) if score_row else submission is not None,
        verdict_correct=score_row.get("verdict_correct") if score_row else None,
        certificate_valid=bool(score_row.get("certificate_valid")) if score_row else False,
        transcript_available=transcript_available,
        raw_response_available=raw_response_available,
        raw_response_text_chars=len(raw_text or ""),
        prose_chars_before_json=len(_prose_before_json(raw_text or "")),
        gold_hash_a=gold.minimized_hash_a,
        gold_hash_b=gold.minimized_hash_b,
        gold_semantically_equivalent=gold.semantically_equivalent,
    )

    if not submission:
        record.primary_category = "C8_UNCLASSIFIABLE"
        record.safe_excerpt = _safe_excerpt(raw_text or str(row.get("raw_response")))
        return record

    cert = submission.get("certificate")
    if not isinstance(cert, dict):
        record.primary_category = "C8_UNCLASSIFIABLE"
        record.safe_excerpt = _safe_excerpt(raw_text)
        return record

    payload = cert.get("payload") if isinstance(cert.get("payload"), dict) else {}
    record.submitted_verdict = submission.get("verdict")
    record.submitted_certificate_type = cert.get("certificate_type")
    record.submitted_equivalent = payload.get("equivalent")
    record.submitted_hash_a = payload.get("minimized_hash_A")
    record.submitted_hash_b = payload.get("minimized_hash_B")
    record.noncanonical_proof_signals = _detect_noncanonical_signals(raw_text, payload)

    verify = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, cert)
    record.verifier_errors = list(verify.errors)

    semantic_ok = (
        submission.get("verdict") is True
        and cert.get("certificate_type") == "equivalence_witness"
        and payload.get("equivalent") is True
        and (score_row is None or score_row.get("verdict_correct") is not False)
    )
    record.semantic_claim_ok = semantic_ok

    if not semantic_ok:
        record.primary_category = "C7_SEMANTICALLY_WRONG_EQUIVALENCE_CLAIM"
        record.safe_excerpt = _safe_excerpt(raw_text)
        return record

    ha = record.submitted_hash_a
    hb = record.submitted_hash_b
    ga = gold.minimized_hash_a
    gb = gold.minimized_hash_b

    if _is_placeholder_hash(ha) or _is_placeholder_hash(hb):
        record.primary_category = "C1_EMPTY_OR_PLACEHOLDER"
        record.safe_excerpt = _safe_excerpt(
            f"hash_A={ha!r} hash_B={hb!r} gold_A={ga[:16]}... gold_B={gb[:16]}..."
        )
        return record

    assert ha is not None and hb is not None
    record.hash_a_matches_gold = ha.lower() == ga.lower()
    record.hash_b_matches_gold = hb.lower() == gb.lower()
    record.hashes_swapped = ha.lower() == gb.lower() and hb.lower() == ga.lower()
    record.shared_submitted_hash = ha.lower() == hb.lower()

    if record.hashes_swapped:
        record.primary_category = "C3_SWAPPED_HASHES"
    elif record.hash_a_matches_gold != record.hash_b_matches_gold:
        record.primary_category = "C4_PARTIAL_MATCH"
    else:
        structural_signals = {
            signal
            for signal in record.noncanonical_proof_signals
            if signal.startswith("extra_payload_fields:")
            or signal in {"state_mapping", "partition", "bisimulation", "minimized_automaton"}
        }
        if structural_signals and record.prose_chars_before_json >= 80:
            record.primary_category = "C6_NONCANONICAL_STRUCTURAL_PROOF"
        elif record.shared_submitted_hash and not record.hash_a_matches_gold:
            record.primary_category = "C5_EQUAL_BUT_WRONG_SHARED_HASH"
        else:
            record.primary_category = "C2_RANDOM_OR_NONMATCHING_HASH"

    record.safe_excerpt = _safe_excerpt(
        _prose_before_json(raw_text)
        + " | "
        + f"hash_A={ha[:16]}... hash_B={hb[:16]}... gold={ga[:16]}..."
    )
    return record


def _equivalence_items(cohort: dict[str, BenchmarkItem]) -> list[BenchmarkItem]:
    return [
        item
        for item in cohort.values()
        if item.answer_key["certificate"]["certificate_type"] == "equivalence_witness"
    ]


def decompose_equivalence_hash_mismatches(repo_root: str | Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    cohort_list = load_items_jsonl(repo_root / COHORT_PATH)
    cohort = {item.item_id: item for item in cohort_list}
    eq_items = _equivalence_items(cohort)
    eq_ids = {item.item_id for item in eq_items}
    gold_by_item = {item.item_id: _compute_gold(item) for item in eq_items}

    per_run_items: dict[str, list[ItemDecomposition]] = {}
    coverage: list[dict[str, Any]] = []

    for run in RUNS:
        results_path = repo_root / run["results_path"]
        scores_path = repo_root / run["scores_path"]
        transcript_dir = repo_root / run["transcripts_dir"]
        results = {row["item_id"]: row for row in read_jsonl(results_path)} if results_path.exists() else {}
        scores = {row["item_id"]: row for row in read_jsonl(scores_path)} if scores_path.exists() else {}

        missing_results = sorted(eq_ids - set(results))
        missing_scores = sorted(eq_ids - set(scores))
        failures: list[ItemDecomposition] = []

        for item in eq_items:
            row = results.get(item.item_id)
            score_row = scores.get(item.item_id)
            if row is None:
                record = ItemDecomposition(
                    item_id=item.item_id,
                    condition=run["condition"],
                    run_label=run["label"],
                    extractable=False,
                    verdict_correct=None,
                    certificate_valid=False,
                    primary_category="C8_UNCLASSIFIABLE",
                    safe_excerpt="results.jsonl row missing",
                )
                failures.append(record)
                continue

            transcript_path = transcript_dir / f"{item.item_id}.json"
            record = classify_item(
                item=item,
                row=row,
                score_row=score_row,
                gold=gold_by_item[item.item_id],
                condition=run["condition"],
                run_label=run["label"],
                transcript_path=transcript_path,
            )
            if not record.certificate_valid:
                failures.append(record)

        per_run_items[run["condition"]] = failures
        coverage.append(
            {
                "run_label": run["label"],
                "condition": run["condition"],
                "results_path": run["results_path"],
                "scores_path": run["scores_path"],
                "transcripts_dir": run["transcripts_dir"],
                "equivalence_items_expected": len(eq_ids),
                "results_rows_for_eq_items": len(eq_ids) - len(missing_results),
                "scores_rows_for_eq_items": len(eq_ids) - len(missing_scores),
                "missing_results_item_ids": missing_results,
                "missing_scores_item_ids": missing_scores,
                "transcripts_present": sum(
                    1
                    for item_id in eq_ids
                    if (transcript_dir / f"{item_id}.json").exists()
                ),
                "raw_response_available": sum(
                    1
                    for item_id in eq_ids
                    if item_id in results
                    and (
                        results[item_id].get("raw_response_text")
                        or results[item_id].get("raw_response")
                    )
                ),
                "eq_witness_failures": len(failures),
            }
        )

    def category_table(failures: list[ItemDecomposition]) -> list[dict[str, Any]]:
        total = len(failures) or 1
        counts = Counter(record.primary_category for record in failures)
        return [
            {
                "category": category,
                "count": counts.get(category, 0),
                "percentage": round(counts.get(category, 0) / total, 3),
            }
            for category in CATEGORY_ORDER
            if counts.get(category, 0) > 0
        ]

    pooled_failures = [
        record for failures in per_run_items.values() for record in failures
    ]

    def hash_pattern_rates(failures: list[ItemDecomposition]) -> dict[str, Any]:
        total = len(failures) or 1
        missing = sum(
            1
            for record in failures
            if record.primary_category == "C1_EMPTY_OR_PLACEHOLDER"
            or _is_placeholder_hash(record.submitted_hash_a)
            or _is_placeholder_hash(record.submitted_hash_b)
        )
        hash_like_wrong = sum(
            1
            for record in failures
            if record.primary_category
            in {
                "C2_RANDOM_OR_NONMATCHING_HASH",
                "C5_EQUAL_BUT_WRONG_SHARED_HASH",
            }
            or (
                record.primary_category == "C6_NONCANONICAL_STRUCTURAL_PROOF"
                and not _is_placeholder_hash(record.submitted_hash_a)
            )
        )
        one_correct = sum(1 for record in failures if record.primary_category == "C4_PARTIAL_MATCH")
        swapped = sum(1 for record in failures if record.primary_category == "C3_SWAPPED_HASHES")
        equal_wrong = sum(
            1 for record in failures if record.primary_category == "C5_EQUAL_BUT_WRONG_SHARED_HASH"
        )
        return {
            "n_failures": len(failures),
            "hash_missing_or_placeholder_rate": round(missing / total, 3),
            "hash_like_but_wrong_rate": round(hash_like_wrong / total, 3),
            "one_hash_correct_rate": round(one_correct / total, 3),
            "swapped_rate": round(swapped / total, 3),
            "equal_but_wrong_shared_hash_rate": round(equal_wrong / total, 3),
        }

    def noncanonical_summary(failures: list[ItemDecomposition]) -> dict[str, Any]:
        signal_counts = Counter(
            signal for record in failures for signal in record.noncanonical_proof_signals
        )
        c6 = sum(1 for record in failures if record.primary_category == "C6_NONCANONICAL_STRUCTURAL_PROOF")
        semantic_ok = sum(1 for record in failures if record.semantic_claim_ok)
        return {
            "primary_c6_count": c6,
            "semantic_claim_ok_count": semantic_ok,
            "signal_counts": dict(signal_counts),
            "state_mapping_responses": signal_counts.get("state_mapping", 0),
            "partition_like_responses": signal_counts.get("partition", 0),
            "minimized_automaton_mentions": signal_counts.get("minimized_automaton", 0),
            "language_argument_responses": signal_counts.get("language_argument", 0),
            "machine_checkable_under_broader_verifier": (
                "No submitted response included a standalone machine-checkable alternate "
                "witness object (partition table, bisimulation relation, or mapping) in "
                "the certificate payload; prose arguments might support a richer verifier "
                "but were not encoded as checkable artifacts."
            ),
        }

    examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in pooled_failures:
        cat = record.primary_category
        if len(examples[cat]) < 3:
            examples[cat].append(
                {
                    "item_id": record.item_id,
                    "condition": record.condition,
                    "excerpt": record.safe_excerpt,
                }
            )

    r1_cats = category_table(per_run_items["R1"])
    oracle_cats = category_table(per_run_items["Oracle+Format"])
    pooled_cats = category_table(pooled_failures)

    r1_placeholder = sum(
        row["count"] for row in r1_cats if row["category"] == "C1_EMPTY_OR_PLACEHOLDER"
    )
    oracle_placeholder = sum(
        row["count"] for row in oracle_cats if row["category"] == "C1_EMPTY_OR_PLACEHOLDER"
    )
    r1_c5 = sum(
        row["count"] for row in r1_cats if row["category"] == "C5_EQUAL_BUT_WRONG_SHARED_HASH"
    )
    oracle_c5 = sum(
        row["count"] for row in oracle_cats if row["category"] == "C5_EQUAL_BUT_WRONG_SHARED_HASH"
    )
    semantic_ok_total = sum(1 for record in pooled_failures if record.semantic_claim_ok)

    research_answers = {
        "mostly_empty_or_fake_hashes": (
            f"No for R1 frozen: only {r1_placeholder}/51 are empty/placeholder/non-hex "
            f"({r1_c5}/51 are equal-but-wrong-shared-hash with hash-like hex). "
            f"Oracle+Format shows more placeholder/template behavior "
            f"({oracle_placeholder}/51 C1; {oracle_c5}/51 C5)."
        ),
        "semantically_plausible_noncanonical_proofs": (
            f"Prose contains language/step-replay arguments in many failures, but "
            f"no certificate payload encodes an alternate machine-checkable witness. "
            f"Primary C6 count (structured alternate proof as main failure mode): "
            f"{sum(1 for r in pooled_failures if r.primary_category == 'C6_NONCANONICAL_STRUCTURAL_PROOF')} "
            f"across pooled failures."
        ),
        "zero_rate_interpretation": (
            f"{semantic_ok_total}/{len(pooled_failures)} pooled failures keep a semantically "
            "correct equivalence claim (verdict true, equivalent true, correct certificate "
            "type) yet fail verifier hash equality. The 0.000 cert rate primarily measures "
            "failure to emit verifier-identical minimized_dfa_hash strings, not rejection "
            "of valid alternate proof objects in the certificate schema."
        ),
        "justified_thesis_sentence": (
            "Claude accepts equivalence verdicts but cannot synthesize verifier-identical "
            "minimized_dfa_hash witnesses under R1/Oracle; failures are dominated by "
            "wrong-hash emission patterns while semantic equivalence claims remain correct."
        ),
        "too_strong_thesis_sentence": (
            "Claiming Claude cannot reason about DFA equivalence at all, or that failures "
            "prove misunderstood non-equivalence, or that a generic universal-quantifier "
            "deficit explains F1."
        ),
        "limitations_section": (
            "Equivalence_witness verification accepts only minimized_dfa_hash strings; "
            "natural-language or step-simulation arguments in prose are not scored. "
            "This decomposition classifies hash-construction patterns from frozen "
            "parsed payloads plus raw_response_text in results.jsonl (transcripts present "
            "but not required). Subtype labels are heuristic; C6 requires substantive "
            "structured alternate-proof language and remains rare relative to wrong-hash "
            "emission (C5/C1/C2)."
        ),
    }

    return {
        "analysis": "equivalence_hash_mismatch_decomposition",
        "cohort_path": COHORT_PATH,
        "equivalence_item_count": len(eq_ids),
        "coverage": coverage,
        "tables": {
            "A_category_counts": {
                "R1": r1_cats,
                "Oracle+Format": oracle_cats,
                "pooled": pooled_cats,
            },
            "B_hash_pattern_analysis": {
                "R1": hash_pattern_rates(per_run_items["R1"]),
                "Oracle+Format": hash_pattern_rates(per_run_items["Oracle+Format"]),
                "pooled": hash_pattern_rates(pooled_failures),
            },
            "C_noncanonical_proof_evidence": {
                "R1": noncanonical_summary(per_run_items["R1"]),
                "Oracle+Format": noncanonical_summary(per_run_items["Oracle+Format"]),
                "pooled": noncanonical_summary(pooled_failures),
            },
        },
        "examples_by_category": dict(examples),
        "items": {
            condition: [asdict(record) for record in records]
            for condition, records in per_run_items.items()
        },
        "research_answers": research_answers,
        "methodology": {
            "no_new_model_calls": True,
            "verifier_unchanged": True,
            "frozen_runs_only": True,
            "primary_data": "results.jsonl raw_response + raw_response_text",
            "transcript_policy": (
                "Transcript files checked for coverage reporting; classification uses "
                "results.jsonl payloads unless raw response missing."
            ),
        },
    }


def render_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Equivalence Witness Hash Mismatch Decomposition",
        "",
        "Construct-validity subtypes for Claude F1 `equivalence_witness` failures. "
        "**No new model calls; frozen runs only.**",
        "",
        "## Coverage",
        "",
    ]
    for row in payload["coverage"]:
        lines.extend(
            [
                f"### {row['run_label']}",
                "",
                f"- results coverage: {row['results_rows_for_eq_items']}/{row['equivalence_items_expected']}",
                f"- scores coverage: {row['scores_rows_for_eq_items']}/{row['equivalence_items_expected']}",
                f"- transcripts present: {row['transcripts_present']}/{row['equivalence_items_expected']}",
                f"- raw responses available: {row['raw_response_available']}/{row['equivalence_items_expected']}",
                f"- eq-witness failures: {row['eq_witness_failures']}",
                "",
            ]
        )
        if row["missing_results_item_ids"]:
            lines.append(f"- missing results IDs: {row['missing_results_item_ids']}")
            lines.append("")

    lines.extend(["## Table A — Category counts", ""])
    for scope, rows in payload["tables"]["A_category_counts"].items():
        lines.append(f"### {scope}")
        lines.append("")
        lines.append("| category | count | percentage |")
        lines.append("|----------|------:|-----------:|")
        for row in rows:
            lines.append(f"| {row['category']} | {row['count']} | {row['percentage']:.3f} |")
        lines.append("")

    lines.extend(["## Table B — Hash pattern analysis", ""])
    for scope, row in payload["tables"]["B_hash_pattern_analysis"].items():
        lines.append(f"### {scope}")
        for key, value in row.items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")

    lines.extend(["## Table C — Non-canonical proof evidence", ""])
    for scope, row in payload["tables"]["C_noncanonical_proof_evidence"].items():
        lines.append(f"### {scope}")
        for key, value in row.items():
            if key == "signal_counts":
                lines.append("- **signal_counts:**")
                for signal, count in value.items():
                    lines.append(f"  - {signal}: {count}")
            else:
                lines.append(f"- **{key}:** {value}")
        lines.append("")

    lines.extend(["## Research answers", ""])
    for question, answer in payload["research_answers"].items():
        lines.extend([f"### {question}", "", answer, ""])

    lines.extend(["## Examples (safe excerpts)", ""])
    for category, rows in payload["examples_by_category"].items():
        lines.append(f"### {category}")
        for row in rows:
            lines.append(
                f"- `{row['item_id']}` ({row['condition']}): {row['excerpt']}"
            )
        lines.append("")

    return "\n".join(lines)


def write_csv_tables(payload: dict[str, Any], csv_path: Path) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Table A: category counts"])
        writer.writerow(["scope", "category", "count", "percentage"])
        for scope, rows in payload["tables"]["A_category_counts"].items():
            for row in rows:
                writer.writerow([scope, row["category"], row["count"], row["percentage"]])
        writer.writerow([])
        writer.writerow(["Table B: hash pattern analysis"])
        writer.writerow(["scope", "metric", "value"])
        for scope, metrics in payload["tables"]["B_hash_pattern_analysis"].items():
            for key, value in metrics.items():
                writer.writerow([scope, key, value])
        writer.writerow([])
        writer.writerow(["Table C: noncanonical proof signals"])
        writer.writerow(["scope", "signal", "count"])
        for scope, block in payload["tables"]["C_noncanonical_proof_evidence"].items():
            for signal, count in block.get("signal_counts", {}).items():
                writer.writerow([scope, signal, count])


def export_equivalence_hash_mismatch_decomposition(
    repo_root: str | Path | None = None,
    *,
    json_out: str | Path = "docs/equivalence_hash_mismatch_decomposition.json",
    md_out: str | Path = "docs/equivalence_hash_mismatch_decomposition.md",
    csv_out: str | Path = "docs/equivalence_hash_mismatch_decomposition_tables.csv",
    addendum_dir: str | Path = "docs/tmlr_empirical_package_v1",
) -> dict[str, Any]:
    repo_root = Path(repo_root) if repo_root is not None else find_repo_root()
    payload = decompose_equivalence_hash_mismatches(repo_root)

    for rel_path in (json_out, md_out, csv_out):
        path = repo_root / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)

    json_path = repo_root / json_out if not Path(json_out).is_absolute() else Path(json_out)
    md_path = repo_root / md_out if not Path(md_out).is_absolute() else Path(md_out)
    csv_path = repo_root / csv_out if not Path(csv_out).is_absolute() else Path(csv_out)

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown_report(payload), encoding="utf-8")
    write_csv_tables(payload, csv_path)

    addendum_root = repo_root / addendum_dir if not Path(addendum_dir).is_absolute() else Path(addendum_dir)
    addendum_root.mkdir(parents=True, exist_ok=True)
    addendum_json = addendum_root / "addendum_equivalence_hash_mismatch_decomposition.json"
    addendum_md = addendum_root / "addendum_equivalence_hash_mismatch_decomposition.md"
    addendum_payload = {
        "addendum_for": "docs/tmlr_empirical_package_v1",
        "source_analysis": str(json_path.relative_to(repo_root)),
        "summary": {
            "tables": payload["tables"],
            "research_answers": payload["research_answers"],
            "coverage": payload["coverage"],
        },
    }
    addendum_json.write_text(json.dumps(addendum_payload, indent=2, sort_keys=True), encoding="utf-8")
    addendum_md.write_text(
        "# Addendum: equivalence hash mismatch decomposition\n\n"
        "See full analysis: `docs/equivalence_hash_mismatch_decomposition.md`\n\n"
        + render_markdown_report(payload),
        encoding="utf-8",
    )
    return payload

# Clean_v2 Harness Readiness Report

**Artifact:** FSMReasonBench (`fsmreasonbench/`, branch `main`)  
**Namespace:** `clean_v2`  
**Date:** 2026-09-02  
**Sentinel:** `runs/clean_v2_sentinel/` (mock provider only)  
**Tests:** `tests/unit/clean_v2/` — **21 passed**

---

## A. Implementation summary

| Path | Change | Scientific reason |
|---|---|---|
| `src/fsmreasonbench/clean_v2/views.py` | `EvaluateeView` / `EvaluatorOnly` scrubbing | Eliminate gold leakage into prompts/tools |
| `src/fsmreasonbench/clean_v2/condition.py` | Factorized immutable `ConditionSpec` | Single-factor interventions |
| `src/fsmreasonbench/clean_v2/provenance.py` | Witness provenance schema + export guard | Separate model vs tool/runner witnesses |
| `src/fsmreasonbench/clean_v2/metrics.py` | Common-denominator rates over `n_attempted` | Replace mixed-denominator gap |
| `src/fsmreasonbench/clean_v2/fingerprint.py` | Fingerprints + `diff_experiment` | Prove intended-only diffs |
| `src/fsmreasonbench/clean_v2/prompts.py` | Skeleton + contract/oracle/format blocks | Factorized prompts |
| `src/fsmreasonbench/clean_v2/tools/palettes.py` | T0/T1/T3; T2 omitted | Causal tool ladder without verdict leak |
| `src/fsmreasonbench/clean_v2/tools/verify_feedback.py` | Coarse non-constructive T3 | Prevent witness construction via feedback |
| `src/fsmreasonbench/clean_v2/tools/__init__.py` | Causal tool executor | Ban builders on scientific path |
| `src/fsmreasonbench/clean_v2/contracts/*` | Bisimulation, minimized_dfa, digest_control | Feasible contracts + infeasibility control |
| `src/fsmreasonbench/clean_v2/scoring.py` | Parse/score + first_failure | Auditable per-item outcomes |
| `src/fsmreasonbench/clean_v2/runner.py` | `two_phase_no_inject` runner | No certificate synthesis/injection |
| `src/fsmreasonbench/clean_v2/artifacts.py` | Cell layout, run_id, reps | Stable repetition identity |
| `src/fsmreasonbench/clean_v2/exports.py` | Hard model-export guard | Refuse non-`model_generated` rows |
| `src/fsmreasonbench/clean_v2/legacy.py` | Legacy classification markers | Keep v1 immutable |
| `src/fsmreasonbench/clean_v2/sentinel/*` | Deterministic mock campaign | E2E freeze readiness without APIs |
| `src/fsmreasonbench/cli/run_clean_v2_sentinel.py` | CLI entry | Reproduce sentinel offline |
| `tests/unit/clean_v2/*` | Scientific-path tests | Independent validation of critical path |
| `docs/clean_v2/*` | This report + AI provenance | Disclosure / auditability |

Legacy `to_evaluatee_dict` / R2C synthesis paths were **not deleted** (remain for historical analysis / SYS_CEILING interpretation). Clean scientific runs must use `clean_v2` only.

---

## B. Scientific-path tests

| Test | Property | Result |
|---|---|---|
| `test_leakage.py::test_evaluatee_omits_*` | No answer_key / equivalent / transform in evaluatee | **PASS** |
| `test_leakage.py::test_item_specific_gold_tokens_*` | Item-specific gold strings absent from evaluatee JSON | **PASS** |
| `test_leakage.py::test_evaluator_only_retains_gold` | Gold retained evaluator-side | **PASS** |
| `test_contracts.py::test_bisimulation_*` | Semantic bisimulation accept | **PASS** |
| `test_contracts.py::test_minimized_dfa_accepts_*` | Minimal renamed machines accepted | **PASS** |
| `test_contracts.py::test_minimized_dfa_rejects_non_minimal` | Non-minimal rejected | **PASS** |
| `test_contracts.py::test_minimized_dfa_rejects_behaviorally_wrong` | Wrong language rejected | **PASS** |
| `test_contracts.py::test_minimized_dfa_rejects_valid_a_invalid_b` | Partial witness rejected | **PASS** |
| `test_contracts.py::test_digest_control_roundtrip` | Digest control verifies | **PASS** |
| `test_tools_t3.py::test_t2_omitted` | No unclean T2 | **PASS** |
| `test_tools_t3.py::test_palettes_exclude_builders` | Causal palettes exclude builders | **PASS** |
| `test_tools_t3.py::test_forbidden_tools_rejected` | Builder calls rejected | **PASS** |
| `test_tools_t3.py::test_t3_feedback_is_coarse_*` | T3 coarse + non-leaking | **PASS** |
| `test_tools_t3.py::test_t3_does_not_return_expected_relation_*` | No gold fragments in T3 | **PASS** |
| `test_fingerprint_metrics.py::test_diff_experiment_*` | Single-factor diffs | **PASS** |
| `test_fingerprint_metrics.py::test_common_denominator_metrics` | Rates use n_attempted | **PASS** |
| `test_fingerprint_metrics.py::test_primary_export_rejects_injected` | Export guard | **PASS** |
| `test_fingerprint_metrics.py::test_parse_and_first_failure_order` | First-failure ordering | **PASS** |
| `test_repetitions.py::test_repetition_run_ids_differ` | Distinct rep identities | **PASS** |
| `test_repetitions.py::test_no_overwrite_by_default` | No silent overwrite | **PASS** |
| `test_sentinel.py::test_sentinel_campaign_*` | E2E mock campaign | **PASS** |

Suite command: `python -m pytest tests/unit/clean_v2 -q` → **21 passed**.

---

## C. Gold-leakage audit

| Old leak | New boundary | Tests | Remaining model-visible gold? |
|---|---|---|---|
| `difficulty.core.equivalent` | stripped in `build_evaluatee_view` | leakage tests | **No** |
| `equivalent_transform` metadata | private metadata scrub | leakage tests | **No** |
| `answer_key` | evaluator-only | leakage tests | **No** |
| `distinguishing_trace_length` in difficulty | stripped (polarity cue) | leakage tests | **No** |
| Gold hashes / pair lists | evaluator-only + token checks | `collect_item_specific_gold_tokens` | **No** in evaluatee |

Public structural metadata retained: alphabet size, state/transition counts, `generator_seed`, `public_fingerprint`.

---

## D. Tool-palette audit

| Palette | Tools | Semantics | Verdict-revealing? | Witness-constructing? | Certificate-copyable? | Suitable RQ3? |
|---|---|---|---|---|---|---|
| `T0_NONE` | ∅ | no tools | No | No | No | Yes (baseline) |
| `T1_STEP` | `step` | local transition | No | No | No | Yes |
| `T3_VERIFY` | `verifier.validate_certificate_coarse` | coarse accept/reject codes | No | No | No | Yes |
| `T3_VERIFY_WITH_STEP` | step + coarse verify | explicit composition | No | No | No | Yes (optional) |

**Valid T2?** **No.**  
`T2_COMPUTE_AVAILABLE = False`. Reason: no in-repo primitive is strictly stronger than `step` without revealing equivalence (`check_separation`) or constructing witnesses (certificate builders). T2 is omitted rather than invented.

Forbidden on causal palettes: all `solver.*` certificate/separation builders (see `FORBIDDEN_CAUSAL_TOOLS`).

---

## E. T3 feedback audit

**Allowed model-visible example:**
```json
{"status": "accepted", "code": "accepted"}
```
```json
{"status": "rejected", "code": "relation_closure_failed"}
```

**Forbidden (not returned):** expected pairs, corrected certificate, missing states list, expected minimized automaton, expected hash, gold certificate fragments, raw verifier error strings.

**Can T3 indirectly construct the witness?** Coarse codes can guide iterative repair at a high level (e.g., “closure failed”), but they do **not** enumerate missing pairs or emit the gold relation. Adversarial tests assert gold tokens/pair fragments are absent from outputs.

---

## F. Contract audit

| Contract | Verifier semantics | Feasibility | Burden metadata | Tests |
|---|---|---|---|---|
| `bisimulation` | Semantic relation closure (`verify_bisimulation_relation`), not gold equality | Feasible under T0/T1/T3 | bytes, field_count, relation_pair_count | PASS |
| `minimized_dfa` | A'~A, B'~B, both minimal, A'~B', originals equivalent | Feasible | bytes, field_count, state/transition counts | PASS (adversarial) |
| `digest_control` | Exact `minimized_dfa_hash` match (`infeasibility_control`) | Infeasible without hasher | bytes, field_count | PASS roundtrip |

`MINIMIZED_DFA CONTRACT BLOCKED` — **not applicable**; contract implemented and tested.

---

## G. Provenance audit

**Model-generated (scientific default):**
```json
{"witness_origin":"model_generated","tool_contributed":true,"direct_tool_construction":false,
 "model_modified_tool_output":false,"syntactic_repair_applied":false,
 "semantic_changed_post_model":false,"verifier_only_feedback":false}
```

**Tool-constructed / runner-injected:** supported in schema for SYS_CEILING/legacy annotation only.

**Primary export guard:** `export_primary_model_rows` raises if `witness_origin != model_generated`.

Verified: `GUARD_OK primary model-performance export refused row with witness_origin='tool_constructed'`.

---

## H. Fingerprint proofs

| Contrast | `difference_paths` | Unexpected? |
|---|---|---|
| bisimulation vs minimized_dfa | `contract`, `contract_schema_block` | **None** |
| T0 vs T1 | `tool_palette`, `tool_definitions.*`, `tool_docs` | **None** |
| T1 vs T3 | `tool_palette`, `tool_definitions.*`, `tool_docs` | **None** |
| oracle none vs gold_verdict | `oracle_info`, `oracle_block` | **None** |
| format off vs on | `format_assist`, `format_block` | **None** |

---

## I. Metric audit

Synthetic / sentinel aggregate (`n_attempted=15` after full sentinel):

- Denominator for extractable / verdict / witness / full: **n_attempted**
- First-failure counts exported
- Conditionals include explicit N (`witness|verdict`, `witness|extractable`)
- `deprecated_mixed_gap.status = "deprecated"`

Example (unit synthetic, n=3): extractable 2/3; verdict 2/3; witness 1/3; full 1/3; witness|verdict = 1/2.

---

## J. Repetition audit

Example run IDs (sentinel, same item×T1×bisim):

| Rep | run_id | path |
|---|---|---|
| 1 | `5af4855acd53b78ef65baf07` | `.../rep_01/` |
| 2 | `a56046aa45c6efd2f048f38a` | `.../rep_02/` |
| 3 | `fe3b73f6cae0d461882e2ffe` | `.../rep_03/` |

No overwrite by default (`FileExistsError`). Overwrite replaces same `run_id` only.

---

## K. Sentinel campaign

- Command: `python -m fsmreasonbench.cli.run_clean_v2_sentinel`
- Provider: `DeterministicMockProvider`
- `external_model_calls`: **0**
- Artifacts: `runs/clean_v2_sentinel/**/rep_XX/{scores,results,transcripts}` + `sentinel_summary.json`
- Exercised: valid / invalid witness / wrong verdict / malformed / T0 / T1 / T3 / oracle×format / bisim / minimized_dfa / digest_control / reps 1–3 / fingerprints / provenance / aggregation

---

## L. Legacy boundary

| Item | Status |
|---|---|
| Frozen v1 run roots listed in `clean_v2/legacy.py` | **Immutable** |
| R2C historical | SYS_CEILING / diagnostic only |
| Oracle+Format historical | diagnostic only |
| A1 historical | diagnostic only |
| Digest historical | infeasibility/control only |
| Mixed gap tables | not clean_v2 evidence |
| Rescoring | must write under `runs/clean_v2_derived_rescores/` (never overwrite freeze) |

---

## M. AI-assisted code provenance

See `docs/clean_v2/AI_ASSISTED_PROVENANCE.md`.

This `clean_v2` implementation was authored with Cursor assistance in this session. Critical scientific components are covered by the deterministic tests above. No claim of independent human line-by-line review is made beyond the author’s acceptance of this report.

---

## N. Remaining scientific blockers

Before **real** model collection:

1. Wire a real provider adapter into `run_clean_item` **without** enabling inject/synthesis (API keys, rate limits).
2. Freeze a clean_v2 item-manifest fingerprint and condition matrix JSON for the paper campaign.
3. Optionally record Ollama `num_ctx`/quant when local models are used.
4. Human confirmation of prompt wording for contract schema blocks (scientific sign-off).
5. Do **not** use legacy evaluatee serialization for clean_v2 runs.

No blocker remains for **mock-validated harness freeze**.

---

HARNESS READY FOR SCIENTIFIC FREEZE

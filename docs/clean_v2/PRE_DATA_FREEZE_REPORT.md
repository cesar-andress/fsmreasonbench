# PRE_DATA FREEZE REPORT — clean_v2 confirmatory design

**Date:** 2026-09-02  
**Repo:** `fsmreasonbench/fsmreasonbench` (`main`)  
**Freeze commit:** `6009e44`  
**Constraint honored:** no real model/API generation calls.

---

## A. Remaining changes implemented

| Area | Change |
|---|---|
| T3 budget | `max_verifier_calls=3` enforced in `execute_clean_tool_plan`; prompts document the cap |
| First-proposal audit | `witness_valid_first` via silent evaluator-only check (`confirmatory/t3_budget.py`); runner attaches audit without mutating model context |
| Scheduler | Full Cartesian shuffle with frozen seed `20260902`; reconstructible ordering; interleaved master schedule |
| Caching policy | Adapter-based A/B/C classification recorded in manifests (Anthropic A disabled; OpenAI C + timestamp sensitivity) |
| Primary outcome | `witness_valid` primary; `witness_valid_first` co-primary diagnostic for T1→T3 only |
| Missingness | Deterministic INFRASTRUCTURE vs EXPERIMENTAL classifier; max_reruns=3; incomplete-cell rule ≥2 |
| Analysis | Item-level paired RD, BCa 10k, sign-flip permutation, Holm×3/model, gates F0a–F0d, classifications |
| Pilot guard | Blinded engineering report builder + validators |
| Provenance | Full audit JSON; decision `REUSE_ALL_51` |
| Manifests | RQ1/RQ2/RQ3/DIGEST/PILOT + confirmatory master |
| Docs | `PRE_SPECIFICATION.md` + this report |

---

## B. T3 budget and first-witness audit

- `MAX_VERIFIER_CALLS = 3` (technically feasible; not impossible).
- Per T3 generation records: `verifier_call_count`, `verifier_call_cap_reached`, `coarse_verifier_responses`, proposal order indices, first complete proposal source, final submitted witness (via normal scoring).
- `witness_valid_first`: silent verify of first complete certificate proposal; not injected into messages/tool outputs.
- Tests: `tests/unit/clean_v2/test_t3_budget_first_witness.py` prove budget cap and evaluatee invisibility of silent computation.
- Interpretation rule frozen: both first+final → construction; final-only → search.

---

## C. Execution-order audit

- Seed: `20260902`.
- Master confirmatory schedule: **3040** tasks (`manifest_confirmatory_master.json`).
- Interleaving (master): `n_conditions=5`, `adjacent_same_condition_rate≈0.224`, `condition_run_length_max=9`, mean planned positions by condition clustered ~1476–1554 (no deterministic wall-clock = condition mapping).
- Reconstruction: `reconstruct_ordering` recovers identical `planned_position` sequence from task multiset + seed (tested).

---

## D. Caching policy

| Provider | Class | Confirmatory action |
|---|---|---|
| Anthropic | A | Disable by omitting `cache_control` (adapter default) |
| OpenAI | C | Cannot disable / not observable in adapter; store timestamps + request IDs; secondary timestamp/cache sensitivity |
| Mock | A | N/A (sentinel only) |

No prompt rewriting to defeat caching.

---

## E. Item provenance audit

File: `docs/clean_v2/ITEM_PROVENANCE_AUDIT.json`  
SHA-256: `37cc8acb4ffa2e2c7bc51b6a597a895b1d874c67e8aeba2ae18ab6a71f1d9d5a`

| Question | Answer |
|---|---|
| Generator | `fsmreasonbench.generator.separation` |
| Version/commit | Cohort commit `76d2212…`; generator tree note `f6eec78…` |
| Parameters | constructive_decoy; equivalent_ratio=0.5; distinguishing_trace_length=3 |
| Seeds | 203001–203100 |
| Reproducible | Yes (deterministic + frozen files) |
| Outcome-selected? | **No** |
| Decision | **`REUSE_ALL_51`** |
| Structure | All eq `\|Q_A\|=5`; all dist `\|Q_A\|=18` (generator design) |
| ID↔structure | Within eq: no variation; full cohort lex↔\|Q_A\| reflects subtype split |
| Public before snapshots | Yes (Zenodo 2026-06-20 / cohort 2026-06-22; snapshots later) |

Pilot items: lexicographic first 5 equivalence IDs (within-eq structure constant).

---

## F. Missingness classifier audit

Module: `confirmatory/missingness.py`  
Frozen categories match the pre-spec INFRASTRUCTURE vs EXPERIMENTAL table.  
Assignment is automatic from machine-readable fields at generation time.  
Tests cover timeout→infrastructure/rerun and safety_refusal→experimental/no-rerun.

---

## G. Experimental units and k

- `k = 5` confirmatory; pilot `k = 2`.
- Observation: item×model×condition×rep.
- Inferential unit: **item within model** (n=51 for RQ2/RQ3), not 255 generations.
- Models: fixed factor, two snapshots; no random-effect generalization.

---

## H. Frozen RQ matrix

| RQ | Items | Conditions | Outcome | Test? |
|---|---|---|---|---|
| RQ1 | 100 | bisimulation_T1 | composition / verdict / bias | No (descriptive) |
| RQ2 | 51 eq | bisimulation_T1 vs minimized_dfa_T1 | witness_valid | Yes (per model) |
| RQ3 | 51 eq | bisimulation T0 / T1 / T3 | witness_valid (+ first for T1→T3) | Yes (per model) |
| DIGEST | 51 eq | digest_control_T1 | F0a gate | Diagnostic |

No confirmatory verdict-accuracy claims from the 51-eq cohort.

---

## I. Statistical pipeline tests

Suite: `tests/unit/clean_v2/` → **35 passed** (includes confirmatory design + T3 budget + prior harness).

Synthetic cases exercised (no real clean_v2 model results):

| Case | Observed behavior |
|---|---|
| Null | F0a pass; RQ2 classification cautious inconclusive / no large effect wording |
| Positive RQ2 | Large positive mean paired RD (~56 pp on toy data) |
| Boundary 0/1 | `both_sides_floor_zero`; classification `not_estimable` |
| Incomplete cells | Item `i5` excluded from RQ3 family |
| Tipping point | Extreme missingness can flip sign → `INCONCLUSIVE DUE TO MISSINGNESS` |
| Holm | Family of three contrasts implemented |
| Search-only T3 | Pipeline reports separate final vs first contrasts + T3 diagnostics |

Boundary fallback method recorded: **Newcombe–Wilson** (Tango not used; no reliable in-repo dependency).

---

## J. Multiplicity implementation

Per model: Holm–Bonferroni α=0.05 over  
(1) RQ2 bisim vs min_dfa, (2) RQ3 T0 vs T1, (3) RQ3 T1 vs T3.  
Intervals remain nominal 95%. Documented in analysis output `holm_note`.  
T1→T3 construction interpretation uses intersection of final and first (gates).

---

## K. Falsification-rule implementation

`confirmatory/analysis/gates.py` implements F0a–F0d and RQ2/RQ3 classification thresholds from the pre-spec (15/10/20 pp rules; search-only wording; not-estimable).

---

## L. Pilot guard

`build_pilot_report` only emits engineering fields.  
`validate_pilot_report` rejects forbidden keys/patterns (`witness_valid_rate`, risk difference, p-values, RQ contrasts, `per_condition` rate tables).  
Test: `test_pilot_guard_blocks_scientific_rates`.

---

## M. PRE_SPECIFICATION review

| File | SHA-256 |
|---|---|
| `docs/clean_v2/PRE_SPECIFICATION.md` | `9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd` |

Tag placeholder: `clean_v2-confirmatory-prespec-v1`.

---

## N. Experiment manifests

| Manifest | Path | n_tasks | file SHA-256 |
|---|---|---|---|
| RQ1 | `docs/clean_v2/manifests/manifest_rq1.json` | 1000 | `5159299ddaac2b76bd82e5a2f774aa4ba1f542e8758f1bb71ea99597712aefd1` |
| RQ2 | `docs/clean_v2/manifests/manifest_rq2.json` | 1020 | `b3a60854538eeb05caffe06ec054bb349f8f807dba0280f8602a658d418f7de3` |
| RQ3 | `docs/clean_v2/manifests/manifest_rq3.json` | 1530 | `32f7216d00d7bc447b26ed6f0e8505c5102711eea84c449a85b445956213b53c` |
| DIGEST | `docs/clean_v2/manifests/manifest_digest.json` | 510 | `6753b79cd8b039d4866ebb6cc455181aa9024db336d7ac40adc6819865fe8942` |
| PILOT | `docs/clean_v2/manifests/manifest_pilot.json` | 100 | `0d96e91c77733b8c9b58b3945658b785a7c2c05790339ebf8bf9d080ec25f76f` |
| MASTER | `docs/clean_v2/manifests/manifest_confirmatory_master.json` | 3040 | `cdfcbe488685cf98099de3cc6cd39d8edd24ae3d6a2c5d2adaa4e2ff58e2f848` |

Index: `docs/clean_v2/manifests/INDEX.json`.  
Item ID freeze: `docs/clean_v2/manifests/ITEM_IDS.json`.

Regenerate (no API): `python -m fsmreasonbench.cli.freeze_clean_v2_confirmatory`.

---

## O. AI-assisted implementation provenance

Confirmatory freeze modules, analysis pipeline, manifests, PRE_SPEC, and this report were implemented with Cursor AI assistance under human direction on 2026-09-02. Prior harness AI provenance remains in `docs/clean_v2/AI_ASSISTED_PROVENANCE.md`. No rewrite of historical Co-authored-by markers.

---

## P. Remaining blockers before pilot

1. Annotate git tag `clean_v2-confirmatory-prespec-v1` on the freeze commit (after this landing).
2. Fill planned collection window dates in PRE_SPEC when pilot starts.
3. Configure provider credentials for wiring only (no scientific unblinding).
4. Run the **blinded engineering pilot** using `manifest_pilot.json` and the pilot report guard (not done in this task).

No remaining statistical/design blockers identified for starting the blinded engineering pilot.

READY FOR BLINDED ENGINEERING PILOT

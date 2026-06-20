# Q1 Readiness Roadmap — FSMReasonBench

**Status:** living document (2026-06-20)  
**Scope:** artifact repo `fsmreasonbench` — not the LaTeX paper repo  
**Audience:** maintainers preparing a Q1-grade benchmark release

This roadmap maps seven publication blockers (E1–E7) to executable milestones (M1–M7). Estimates assume one experienced maintainer familiar with the codebase. Do not treat exploratory cohort results (`v0.1-exploratory`, n=20/family) as Q1 evidence.

---

## 1. Current artifact status

| Area | State | Evidence |
|------|-------|----------|
| Implemented families | **C2, F1 only** | End-to-end generator → oracle → verifier → scorer |
| Frozen cohorts | **2 exploratory** (`v0.1-exploratory`) | C2 level-3 reachability, F1 mixed level-3; n=20 each |
| Public cohort | **Not released** | No `v1.0-public` manifest |
| Evaluation tracks | **R0/R1/R2 implemented** | Ollama track runner + multi-model `run_track_pilot_models` |
| Ceilings | **oracle, reference_submitter, competent_submitter** | Reports under `docs/*_summary.*` |
| Statistical reporting | **Bootstrap CIs from existing runs** | `docs/rate_ci_*` |
| F2–F4, C1 | **Specified, not implemented** | `docs/specification/task_families.md` |
| Frontier panel | **Exploratory pilots only** | `docs/pilot_v*`, capability-surface docs |
| Powered cohorts | **No** | 20 items/family is smoke-test scale |
| Non-obvious finding | **Not established** | Exploratory separation layers exist; no frozen public claim |

**What is already Q1-useful (diagnostic, not sufficient):**

- Four-layer scoring (extractability → verdict → certificate → full)
- Independent verifier (no oracle import in verifier path)
- Oracle ceiling report (`export_oracle_ceiling_report`)
- Reference submitter ceiling (`export_reference_submitter_report`) — contract achievable without gold certificate injection
- Competent submitter ceiling (`export_competent_ceiling_report`) — R1-style step-simulator with reasoning logs
- Bootstrap rate CIs (`export_rate_ci_report`)

---

## 2. Q1 blockers (E1–E7)

| ID | Blocker | Why it blocks Q1 |
|----|---------|------------------|
| **E1** | R1/R2 tracks not on public cohort / panel | Runners + exploratory smoke exist; need powered public cohort + frontier panel |
| **E2** | No competent-reasoner ceiling | M2 threat: “only oracle can satisfy contract” — partially addressed; human/frontier still open |
| **E3** | F2 not implemented | Flagship quota (25%) missing; composition claims unsupported |
| **E4** | No `v1.0-public` cohort | Nothing citable, contamination-controlled, or Zenodo-ready at benchmark scale |
| **E5** | No frontier model panel | No credible comparison to SOTA on frozen public data |
| **E6** | Underpowered cohorts | n=20 cannot support family-level or track-level claims with tight CIs |
| **E7** | No non-obvious finding | Q1 expects a substantive empirical claim beyond “we built a benchmark” |

---

## 3. Milestones M1–M7

| Milestone | Maps to | Summary |
|-----------|---------|---------|
| **M1** | E1 | R1 step-simulator + R2 solver-delegation runners ✅ **implemented**; track pilot for multi-model Δ |
| **M2** | E2 | Competent submitter ceiling + combined ceiling report ✅ **started** |
| **M3** | E3 | F2 non-materialized composition vertical |
| **M4** | E4 | Freeze and validate `v1.0-public` cohort |
| **M5** | E5 | Frontier model panel on public cohort |
| **M6** | E6 | Scale cohorts to powered quotas per manifest spec |
| **M7** | E7 | Pre-registered analysis yielding non-obvious finding |

---

## 4. Required modules, CLIs, and tests (per milestone)

### M1 — R1/R2 tracks (E1)

**Modules**

- `src/fsmreasonbench/runners/r1_step_simulator.py` — bounded `step(state, symbol)` tool API for model prompts
- `src/fsmreasonbench/runners/r2_solver_delegate.py` — allow internal oracle/automata-lib; forbid gold certificate reads
- `src/fsmreasonbench/evaluator/track_guards.py` — enforce track-specific submission rules (extend F2 guard stub)

**CLIs**

- `python -m fsmreasonbench.cli.run_r1_batch`
- `python -m fsmreasonbench.cli.run_r2_batch`

**Tests**

- R1 runner rejects global BFS/oracle imports in evaluatee bundle
- R2 runner allows internal product computation but rejects F2 materialization in output
- Track field recorded in transcripts; rescoring deterministic

**Definition of done:** One C2 and one F1 item scored end-to-end on R0, R1, R2 with distinct runner configs; track logged in transcript metadata.

**Effort:** 2–3 weeks  
**Acceptance impact:** Unblocks track claims in paper; prerequisite for E5 comparisons by track.

---

### M2 — Competent submitter ceiling (E2) ✅

**Modules**

- `src/fsmreasonbench/baselines/competent_submitter.py`
- `src/fsmreasonbench/evaluator/competent_ceiling_report.py`

**CLIs**

- `python -m fsmreasonbench.cli.export_competent_ceiling_report`

**Tests**

- `tests/unit/test_competent_submitter.py`

**Definition of done:** Oracle, reference_submitter, and competent_submitter all reach 1.0 on four metrics for both exploratory cohorts; strict export fails if any ceiling drops below 1.0; report states M2 impact honestly.

**Effort:** 3–5 days (implemented in this pass)  
**Acceptance impact:** Weakens M2 “oracle-only satisfiability” and documents R1-style achievability; does **not** close human/frontier gaps.

**Distinction from reference_submitter (no fake novelty):**

| | reference_submitter | competent_submitter |
|--|---------------------|---------------------|
| Decision code | `fsmreasonbench.oracle.*` | `fsmreasonbench.runtime.*` only |
| Certificates | Public builders (oracle-backed) | Assembled from runtime witnesses + schema |
| Transcripts | None | Structured `reasoning_log` per item |
| Epistemic role | Minimal non-oracle contract achievability | R1 step-simulator archetype |

On current C2/F1 exploratory cohorts, **metric outcomes are expected to match** reference_submitter at 1.0. Incremental evidence is process/architecture coverage, not a higher ceiling.

---

### M3 — F2 non-materialized composition (E3)

**Modules**

- `src/fsmreasonbench/generator/f2_composition.py`
- `src/fsmreasonbench/oracle/composition.py`
- `src/fsmreasonbench/certificates/composition.py`
- `src/fsmreasonbench/verifier/composition.py`
- `src/fsmreasonbench/evaluator/f2_parser.py`

**CLIs**

- Extend `generate_batch --family F2`
- `evaluate_baseline_batch --family F2`
- Materialization guard in parser (reject `product_states`, full transition tables)

**Tests**

- Generator → oracle → verifier roundtrip
- Materialization violations rejected
- R2 internal product allowed; submission stays compressed

**Exact next steps (do not implement until M4 planning stable):**

1. Implement `projected_trace_witness` certificate type + verifier (internal product only).
2. Add F2 item assembly with documented `⊗` operator in question block.
3. Seed one golden `examples/item_F2_*` and self-verify.
4. Add F2 stratum to difficulty ladder (reuse `docs/specification/difficulty_model.md` F2 rows).
5. Generate pilot JSONL (unfrozen) before any public cohort quota.

**Definition of done:** One self-verifying F2 item; batch baseline oracle/random/invalid; F2 guard tested.

**Effort:** 3–4 weeks  
**Acceptance impact:** Required for flagship family balance in public cohort.

---

### M4 — Freeze `v1.0-public` cohort (E4)

**Modules**

- `src/fsmreasonbench/dev/freeze_cohort.py` (or extend existing cohort tooling)
- `cohorts/v1.0-public/` manifests per `cohorts/MANIFEST_SPEC.md`
- `scripts/validate_cohort_integrity.sh` (R1 tier)

**CLIs**

- `python -m fsmreasonbench.cli.validate_cohort --cohort cohorts/v1.0-public/...`
- `python -m fsmreasonbench.cli.export_cohort_fingerprints`

**Tests**

- Integration: all public items pass `validate_cohort`
- Fingerprint stability across re-download
- Contamination metadata present on every item

**Definition of done:** Manifest + sha256sums + README; `validate_cohort` PASS; dataset card updated; release notes `docs/releases/v1.0-public.md`; Zenodo checklist items R1–R2 satisfied.

**Effort:** 2–3 weeks (after M1/M3 scope for families known)  
**Acceptance impact:** Enables citable benchmark; prerequisite for E5/E6/E7.

---

### M5 — Frontier model panel (E5)

**Modules**

- Extend `runners/pilot_models.py` or new `runners/frontier_panel.py`
- Frozen config file listing models, prompts, tracks, seeds

**CLIs**

- `python -m fsmreasonbench.cli.run_frontier_panel --cohort cohorts/v1.0-public/...`

**Tests**

- Smoke: one model, one item, transcript + rescore
- Config hash pinned in report metadata

**Definition of done:** ≥3 frontier models evaluated on full public cohort (or pre-registered subset with justification); scores archived with reproducible config; paper table reproducible via script.

**Effort:** 1–2 weeks compute + 1 week integration (after M4)  
**Acceptance impact:** Core empirical comparison for Q1.

---

### M6 — Adequately powered cohorts (E6)

**Modules**

- Cohort generator driven by `cohorts/MANIFEST_SPEC.md` quotas
- Power analysis script (bootstrap/planned n for target CI width)

**CLIs**

- `python -m fsmreasonbench.cli.plan_cohort_power`
- Batch generation jobs per family/stratum

**Tests**

- Manifest item counts match spec
- Per-stratum minimum n enforced

**Definition of done:** Public cohort meets manifest quotas (flagship ≥85% of 2500 target or justified revision documented); bootstrap CI width pre-specified and met for primary metrics.

**Effort:** 2–4 weeks generation + validation (dominated by F2/F3 if not ready)  
**Acceptance impact:** Statistical credibility for E7.

---

### M7 — Non-obvious finding (E7)

**Modules**

- Analysis notebooks/scripts consuming frozen `scores.jsonl`
- Pre-registration doc in `docs/analysis/preregistration.md`

**CLIs**

- `python -m fsmreasonbench.cli.export_primary_findings`

**Tests**

- Reproduce primary table from archived scores (R4 tier)

**Definition of done:** One primary claim with (a) pre-registered hypothesis, (b) adequate power, (c) bootstrap or exact CI, (d) failure taxonomy support — e.g. “verdict accuracy exceeds certificate_valid_rate by Δ on F1 with tight CI” **on public cohort**, not exploratory n=20.

**Effort:** 1–2 weeks analysis (after M5/M6)  
**Acceptance impact:** Distinguishes benchmark paper from tooling paper.

---

## 5. Dependency order

```text
M2 (competent ceiling) ── independent; done first for M2 evidence
        │
M1 (R1/R2) ──────────────┐
        │                  │
M3 (F2) ───────────────────┼──► M4 (v1.0-public freeze)
        │                  │           │
        └──────────────────┘           ├──► M6 (powered quotas)
                                         │           │
                                         └──► M5 (frontier panel)
                                                     │
                                                     └──► M7 (finding)
```

**Critical path to Q1:** M3 → M4 → M6 → M5 → M7, with M1 parallel before public track claims.

---

## 6. Estimated effort (total)

| Milestone | Effort | Cumulative gate |
|-----------|--------|-----------------|
| M2 | 3–5 days | M2 diagnostic ceilings |
| M1 | 2–3 weeks | Track evaluation |
| M3 | 3–4 weeks | F2 flagship |
| M4 | 2–3 weeks | Public cohort |
| M6 | 2–4 weeks | Power |
| M5 | 2–3 weeks | Model panel |
| M7 | 1–2 weeks | Primary claim |

**Rough total:** 3–4 months of focused engineering + compute, assuming no F3/F4 in v1.0 scope.

---

## 7. Acceptance impact summary

| Milestone | Reviewer concern addressed |
|-----------|----------------------------|
| M2 | Construct validity — contract achievable without oracle injection; R1 simulator path |
| M1 | Track integrity — R1/R2 not vaporware |
| M3 | Family coverage — F2 flagship exists |
| M4 | Reproducibility — citable frozen data |
| M6 | Statistics — n not trivial |
| M5 | Relevance — comparison to strong models |
| M7 | Contribution — more than benchmark description |

---

## 8. Risks and validation gates

| Risk | Mitigation | Gate |
|------|------------|------|
| Exploratory n=20 over-interpreted | Label all current ceiling reports “exploratory only” | No primary claim until M4 |
| Competent ≡ reference at 1.0 | Document honestly in ceiling report | M2 report interpretation section |
| F2 verifier complexity | One certificate type first (`projected_trace_witness`) | M3 self-verify gate |
| Cohort contamination | Fingerprints + holdout policy | M4 `validate_cohort` PASS |
| Model API drift | Pin configs; archive raw responses | M5 transcript archive |
| Finding is obvious | Pre-register on public data | M7 preregistration before peeking |

**Release gate for Zenodo v1.0.0:** M4 + M1 (R1/R2 smoke) + M5 (minimal panel) + M6 (manifest quotas or documented deviation) + M7 (one powered claim).

---

## 9. Recommended next milestone

**After M2 (this pass):** **M1 (R1/R2 runners)** in parallel with **M3 step 1** (F2 projected_trace_witness verifier spike).

Rationale: M1 is the smallest unblock for track integrity claims; M3 is on the critical path for public cohort family mix. Do not run frontier sweeps (M5) until M4 exists.

---

## 10. Commands (M2 deliverables)

```bash
cd fsmreasonbench
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_competent_ceiling_report
pytest -v tests/unit/test_competent_submitter.py
```

Outputs: `docs/competent_ceiling_summary.{json,csv}`, `docs/competent_ceiling_report.md`.

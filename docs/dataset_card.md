---
language:
  - en
tags:
  - formal-methods
  - finite-state-machines
  - reasoning
  - benchmark
  - software-engineering
license: apache-2.0
pretty_name: FSMReasonBench
---

# FSMReasonBench — Dataset Card

**Artifact version:** `1.0.0` (published Zenodo release)  
**Zenodo DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)  
**Card status:** describes the published v1.0.0 empirical slice; adaptable to Hugging Face  
**Normative specification:** [`docs/specification/BENCHMARK_SPEC.md`](specification/BENCHMARK_SPEC.md)

> **C2** (calibration) and an **F1** separation/equivalence slice are implemented end-to-end in
> v1.0.0. Families F2–F4 and calibration C1 are specified but not in the published empirical
> claims. Cite the Zenodo DOI, not git `main`.

---

## Overview

FSMReasonBench is a benchmark for measuring **reasoning over executable finite-state machines**
(FSMs). Each item presents one or more FSMs and a typed question. Evaluatees submit a boolean
verdict and a **verifiable certificate** (witness or artefact). An independent verifier checks
submissions without consulting the generator.

Results are reported as **capability surfaces** stratified by task family, difficulty, and
evaluation track—not as a single scalar leaderboard.

| Resource | Location |
|----------|----------|
| Source repository | `fsmreasonbench/` artifact |
| Normative spec | [`docs/specification/BENCHMARK_SPEC.md`](specification/BENCHMARK_SPEC.md) |
| Record layouts | [`docs/zenodo/DATASET_STRUCTURE.md`](zenodo/DATASET_STRUCTURE.md) |
| JSON schemas | [`schema/`](../../schema/) |
| Illustrative items | [`examples/`](../../examples/) |

---

## Motivation

Many reasoning benchmarks score **answers alone**. FSMReasonBench targets a different failure
mode: models may emit plausible verdicts while submitting certificates that do not replay on the
supplied machines. The benchmark therefore separates **verdict accuracy** from **certificate
validity** and treats certificate correctness as the primary success criterion on flagship tasks.

Design rationale and long-term goals are documented in
[`docs/artifact/artifact_philosophy.md`](artifact/artifact_philosophy.md) and
[`docs/specification/evaluation_protocol.md`](specification/evaluation_protocol.md) §1.

---

## Benchmark Scope

### In scope (normative design)

- Operational reasoning over **DFA**, **NFA**, and bounded **Mealy** machines
- Four flagship families (**F1–F4**) plus calibration (**C1–C2**)
- Certificate-first scoring on flagship tasks
- Difficulty as a formal parameter vector
- Regenerable populations and **future** frozen public cohorts

See [`docs/specification/BENCHMARK_SPEC.md`](specification/BENCHMARK_SPEC.md) §2.

### Implemented in the current artifact

| Tier | Family | Role |
|------|--------|------|
| Calibration | **C2** — basic reachability | Pipeline sanity; non-headline panel |
| Flagship | **F1** — DFA separation / witness | First flagship slice; distinguishing traces and equivalence witnesses |

### Out of scope (current phase)

NL-to-FSM from requirements, FSM repair, timed/probabilistic automata at scale, and
open-ended NL-only specifications. See BENCHMARK_SPEC §2.2.

### Cohort tiers (important)

| Tier | Description | Status |
|------|-------------|--------|
| **On-demand / exploratory** | Seeded generation under `runs/`; pilot batches | Development only; not primary paper evidence |
| **Exploratory freeze** | `cohorts/v0.1-exploratory/` ($n{=}20$) | Historical smoke tier; not the citable v1.0.0 release |
| **Paper cohort (published)** | `cohorts/v0.1-expanded-n100/` ($n{=}100$) | ✅ Frozen in v1.0.0 Zenodo release |
| **Future `1.0-public` tier** | Larger design target in spec | Not the v1.0.0 paper cohort |

### Valid exploratory frozen cohorts (non-public)

These directories pass `validate_cohort`. They are **exploratory** snapshots for reproducibility smoke testing and artifact validation — **not** final public `v1.0-public` cohorts and not citable as benchmark results.

| `cohort_id` | Path | Items | `cohort_fingerprint` |
|-------------|------|-------|----------------------|
| `c2-reachability-level3-v0.1-exploratory` | `cohorts/v0.1-exploratory/c2-reachability-level3/` | 20 C2 (witness length level 3) | `77d3bfa104266396d016415527c2cc74eea545bec2bf1295bf0d2ee1c1086230` |
| `f1-mixed-level3-v0.1-exploratory` | `cohorts/v0.1-exploratory/f1-mixed-level3/` | 20 F1 mixed (equivalent + non-equivalent; $\ell_{\mathrm{dist}}=3$) | `4e1e662307456c871ed8c424a4ba493ab041b3d32530feecdef7c19ffe634a67` |

Validate integrity:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-exploratory/c2-reachability-level3
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-exploratory/f1-mixed-level3
```

Exploratory cohorts must not be treated as the final benchmark dataset. See
[`docs/zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) and
[`cohorts/MANIFEST_SPEC.md`](../../cohorts/MANIFEST_SPEC.md).

---

## Task Families (C2, F1)

Full family definitions: [`docs/specification/task_families.md`](specification/task_families.md).

### C2 — Basic Reachability (calibration)

- **Question:** Is target state `q_t` reachable from `q_0` on the supplied FSM?
- **Verdict:** `true` (reachable) or `false` (unreachable)
- **Certificates:** `trace_witness` (positive) or `unreachability_witness` (negative)
- **Tier:** calibration — reported in a separate panel; not the scientific headline

### F1 — Separation / Witness (flagship, first slice)

- **Question:** Are DFA A and B equivalent?
- **Verdict convention:** `true` = equivalent; `false` = not equivalent
- **Implemented certificates:**
  - `distinguishing_trace` — witness that separates non-equivalent pairs
  - `equivalence_witness` — minimization hash witness for equivalent pairs
- **Generator modes and difficulty controls:** see
  [`docs/specification/task_families.md`](specification/task_families.md) §F1 and
  [`docs/specification/difficulty_model.md`](specification/difficulty_model.md)

F1 items may mix equivalent and non-equivalent pairs in capability-surface configurations.
Audit generated JSONL with `audit_f1_items` before drawing structural conclusions.

---

## Item Structure

Human-readable field reference: [`docs/zenodo/DATASET_STRUCTURE.md`](zenodo/DATASET_STRUCTURE.md).

Each **item** includes:

| Field | Description |
|-------|-------------|
| `item_id` | Stable UUID |
| `family` | `C2` or `F1` (implemented) |
| `family_tier` | `calibration` or `flagship` |
| `question` | Typed prompt payload (`schema/question.schema.json`) |
| `difficulty` | Generator difficulty vector + `generator_seed` |
| `contamination.public_fingerprint` | SHA-256 over evaluatee-visible content |
| `fsm` | Primary FSM (C2) |
| `fsm_a`, `fsm_b` | DFA pair (F1) |

**Evaluatee bundle** (future public release): items **without** `answer_key`.  
**Internal / evaluator use:** full items via `BenchmarkItem.to_full_dict()` include
`answer_key` with gold verdict and oracle certificate.

Example items: [`examples/README.md`](../../examples/README.md).

---

## Certificate Structure

Normative certificate definitions: [`docs/specification/certificate_formats.md`](specification/certificate_formats.md).

Implemented certificate types:

| Family | `certificate_type` | Purpose |
|--------|-------------------|---------|
| C2 | `trace_witness` | Reachable target — replayable trace + state sequence |
| C2 | `unreachability_witness` | Unreachable target — declared reachable-state set |
| F1 | `distinguishing_trace` | Non-equivalence — trace with acceptance on A/B |
| F1 | `equivalence_witness` | Equivalence — minimized language hashes |

All certificates use a typed envelope (`certificate_type`, `payload`, optional `fsm_ids` for F1).
JSON schemas: [`schema/certificate/`](../../schema/certificate/).

The **verifier** re-simulates or recomputes checks independently of the generator and oracle.
Architectural rule: verifier must not import generator code.

---

## Generation Process

Items are produced **deterministically** from generator configuration and integer seeds.

| Family | Generator module | CLI |
|--------|------------------|-----|
| C2 | `fsmreasonbench.generator.reachability` | `python -m fsmreasonbench.cli.generate_one --family C2 --seed <int>` |
| F1 | `fsmreasonbench.generator.separation` | `python -m fsmreasonbench.cli.generate_one --family F1 --seed <int>` |

Batch generation: `python -m fsmreasonbench.cli.generate_batch --family C2|F1 --n <count> --seed <int>`.

Pipeline:

```
GeneratorSpec + seed → FSM construction → question assembly → oracle (gold certificate)
```

Difficulty parameters (witness length, state counts, equivalence mix) are family-specific.
See [`docs/specification/difficulty_model.md`](specification/difficulty_model.md) and
[`docs/zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) §Seed-based generation.

---

## Self-Verification

Every generator-emitted item passes **`self_verify_item()`**
(`fsmreasonbench.items.assembly`) before persistence:

1. Oracle certificate is accepted by the independent verifier
2. Certificate type matches verdict polarity
3. Oracle verdict agrees with a direct re-query

Failure raises `AssertionError` and aborts generation. Exploratory cohort freeze
(`freeze_cohort`) re-runs self-verification on every item before sealing.

Details: [`docs/zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) §Self-verification.

---

## Evaluation Protocol

Normative protocol: [`docs/specification/evaluation_protocol.md`](specification/evaluation_protocol.md).

End-to-end scoring path:

```
raw response → parser (extractability) → verdict check → verifier (certificate) → ScoringRecord
```

Each item receives a single **`failure_stage`**:

| Stage | Meaning |
|-------|---------|
| `not_extractable` | Parser could not extract a schema-valid submission |
| `verdict_wrong` | Extractable, but verdict ≠ gold |
| `certificate_invalid` | Verdict correct (or N/A), but verifier rejects certificate |
| `correct` | Verdict and certificate both correct |

### Evaluation tracks (design vs. current artifact)

| Track | Design intent | Current artifact |
|-------|---------------|------------------|
| R0 — pure reasoning | In-context only | Exploratory local Ollama (no tools, temperature 0) |
| R1 — tool-augmented | Single-step simulator | Not yet implemented |
| R2 — solver delegation | External solvers allowed | Not yet implemented |
| Baselines | oracle / random / invalid | Implemented |

Baselines establish scoring ceiling, separation, and extractability floor.

---

## Metrics

Four **independent rates** are reported on every scored batch:

| Metric | Field | Meaning |
|--------|-------|---------|
| Extractability | `extractability_rate` | Share of parseable submissions |
| Verdict accuracy | `verdict_accuracy` | Correct boolean verdict (when extractable) |
| Certificate validity | `certificate_valid_rate` | Verifier accepts certificate |
| Full correctness | `fully_correct_rate` | Verdict and certificate both correct |

On flagship tasks, **`certificate_valid_rate`** is the primary diagnostic; verdict-only
success must not be interpreted as verified reasoning.

Scoring dimensions table: [`docs/specification/evaluation_protocol.md`](specification/evaluation_protocol.md).
Implementation: `fsmreasonbench.evaluator.scorer`.

---

## Failure Taxonomy

For items at stage `certificate_invalid`, verifier errors are classified into interpretable
categories (e.g. `acceptance_mismatch`, `replay_failure`, `wrong_trace_format`).

| Tool | Purpose |
|------|---------|
| `failure_taxonomy` CLI | Single-run taxonomy from scores + results JSONL |
| `failure_taxonomy_batch` CLI | Aggregate taxonomy across a run tree |

Implementation: `fsmreasonbench.evaluator.failure_taxonomy`.

Illustrative exploratory report (not a final result):
[`docs/f1_mixed_failure_taxonomy_report.md`](f1_mixed_failure_taxonomy_report.md).

---

## Capability Surface Methodology

FSMReasonBench reports performance as **curves and matrices** over difficulty levels and models,
not a single leaderboard scalar.

| Workflow | CLI / module |
|----------|--------------|
| Baseline capability surface | `run_capability_surface` |
| Multi-model capability surface | `run_capability_surface_models` |
| Plotting | `plot_capability_surface` |
| Report export | `export_capability_surface_report` |

Exploratory summaries in `docs/` (e.g. `pilot_v0_*`, `pilot_v1_*`, `capability_surface_report.md`)
illustrate reporting format only. Raw run data lives under gitignored `runs/`.

Methodology aligns with BENCHMARK_SPEC §capability surfaces and
[`docs/specification/difficulty_model.md`](specification/difficulty_model.md).

---

## Reproducibility

| Mechanism | Deterministic? | Reference |
|-----------|----------------|-----------|
| Item generation (seed + spec) | Yes | [`docs/zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) |
| Scoring / rescore | Yes | `rescore_transcript` CLI |
| LLM evaluatee responses | No | Archive transcripts for replay |
| Exploratory cohort freeze | Yes (within snapshot) | `freeze_cohort` / `validate_cohort` CLIs |

Future public release requirements (manifest, bundle split, pinned environment) are tracked in
[`docs/zenodo/RELEASE_CHECKLIST.md`](zenodo/RELEASE_CHECKLIST.md) and
[`docs/artifact/reproducibility_policy.md`](artifact/reproducibility_policy.md).

---

## Known Limitations

- **Partial implementation:** only C2 and F1 are end-to-end; full F1–F4 + C1–C2 specification exceeds current code.
- **Exploratory cohorts:** on-demand batches and `0.1-exploratory` freezes are not the final public dataset; two valid exploratory snapshots exist for smoke testing (`cohorts/v0.1-exploratory/`), but metrics may change when a public cohort is published.
- **Generator bias:** constructive generators may introduce structural regularities; F1 audits and generator revisions mitigate but do not eliminate this risk.
- **Certificate contract:** scores bound success to supported certificate formats, not informal proof styles.
- **Model coverage:** early exploratory runs use a small local open-weight model set; results do not generalize broadly.
- **Verdict overstatement risk:** high verdict accuracy with low certificate validity is an expected pattern under test—not evidence of verified reasoning.

Threats and design principles are discussed in the companion paper draft (`paper/sections/`).

---

## Ethical Considerations

- **Intended use:** research on formal reasoning, verification-aware evaluation, and capability measurement—not deployment certification of safety-critical systems.
- **Misuse:** scores on partial or exploratory cohorts should not be used to rank products for production without frozen protocol and broader model coverage.
- **Data composition:** items are synthetically generated; no personal data or copyrighted text corpora are included in item content.
- **Contamination:** each item carries a public fingerprint for leakage detection; see
  [`docs/artifact/contamination_policy.md`](artifact/contamination_policy.md).
- **Transparency:** layered metrics and failure taxonomy expose formatting vs. reasoning vs. certificate errors separately.

---

## Release Status

| Milestone | Status |
|-----------|--------|
| Core infrastructure (FSM, oracle, verifier) | Available in development artifact |
| C2 reachability vertical | Implemented |
| F1 separation / equivalence slice | Implemented (in progress — generator and audit tooling evolving) |
| F2–F4 flagship families | Specified, not implemented |
| C1 calibration | Specified, not implemented |
| Frozen public cohort | **Not yet published** |
| Exploratory cohort freeze (`0.1-exploratory`) | Implemented; two valid cohorts in `cohorts/v0.1-exploratory/` |
| Final benchmark scores / paper claims | **Not available** — awaiting frozen **public** cohort (`1.0-public`) |

Release planning: [`docs/zenodo/RELEASE_CHECKLIST.md`](zenodo/RELEASE_CHECKLIST.md),
[`docs/IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md),
[`PROJECT_STATUS.md`](../../PROJECT_STATUS.md).

---

## Citation

Cite the published Zenodo release:

**DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)

See [`CITATION.cff`](../../CITATION.cff) at the repository root. Include cohort identifier
`v0.1-expanded-n100` and version pins from [`releases/1.0.0/release_manifest.json`](../../releases/1.0.0/release_manifest.json)
when reproducing paper analyses.

---

## Additional documentation

| Topic | Document |
|-------|----------|
| Implementation roadmap | [`docs/IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) |
| Versioning | [`docs/versioning_policy.md`](versioning_policy.md) |
| Release policy | [`docs/artifact/release_policy.md`](artifact/release_policy.md) |
| Examples and CLIs | [`examples/README.md`](../../examples/README.md) |
| Project status | [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) |

# FSMReasonBench — Normative Benchmark Specification (v2.0-draft)

**Status:** published (v1.0.0 — DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937))  
**Version:** 1.0.0 (empirical release; normative spec v2 lineage)  
**Last updated:** 2026-06-20  
**Citable archive:** Zenodo tarball per `releases/1.0.0/release_manifest.json`

This document is the authoritative specification for FSMReasonBench. The **Zenodo release
tarball** defined by `releases/<benchmark_version>/release_manifest.json` is the citable
source of truth; git `main` is a development surface only.

Implementations, cohorts, and evaluation tooling MUST conform to this specification unless
explicitly versioned otherwise.

**Design note:** v2 supersedes the v1 **T1–T7** task taxonomy. Legacy T-families are
not headline tasks; their operational content is absorbed into **F1–F4** (flagship)
and **C1–C2** (calibration).

---

## 1. Vision

FSMReasonBench evaluates **reasoning over executable finite-state machines** (FSMs)—not
tool orchestration alone, not open-ended NL synthesis, not repair. The benchmark measures
whether systems can **produce checkable evidence** (witnesses, compositional arguments,
constructed artefacts, formal queries) whose correctness is established by **independent
decision procedures**.

The scientific object is **capability on durable reasoning surfaces**, not a single scalar
leaderboard score. Results are reported as **capability profiles** stratified by flagship
family, evaluation track, and difficulty vector.

Long-term artifact properties: **regenerable populations**, **frozen comparable cohorts** on
**Zenodo**, **four-axis version pins**, and **contamination controls**.

See [`../artifact/artifact_philosophy.md`](../artifact/artifact_philosophy.md).

---

## 2. Scientific scope

### 2.1 In scope

- Operational reasoning over **DFA**, **NFA**, and **bounded Mealy** machines
- Four **flagship families** (F1–F4) as primary measurement spine
- Two **calibration families** (C1–C2) for literacy and drift detection
- Certificate-first scoring where the submitted artefact—not a bare verdict—is primary
- Three evaluation tracks: pure reasoning, tool-augmented, solver-delegation
- Difficulty as a formal parameter vector
- Hidden-probe and oracle-backed verification for F3/F4

### 2.2 Out of scope (v1)

| Excluded | Reason |
|----------|--------|
| NL-to-FSM generation from requirements | Different competence; F3 is constrained construction over a formal target |
| FSM repair / completion | Explicitly excluded |
| Timed, probabilistic, or pushdown automata | Scope control |
| Open-ended natural-language-only specifications | Not exactly scorable |
| Real-world codebases with implicit FSMs | Contamination and reproducibility |
| Unbounded LTL/CTL model checking | Deferred |
| T1–T7 as independent headline tasks | Superseded by F1–F4 spine (see §5) |

---

## 3. Core principles

1. **Certificate-first flagship tasks** — For F1–F4, a valid submitted artefact outweighs a correct verdict alone.
2. **Exact ground truth** — Oracles and verifiers use exact decision procedures; never LLM-as-judge for primary scoring.
3. **Answer extractability** — Submissions must be machine-parseable; free text is supplementary.
4. **Independent verification** — Verifier module is separate from generator and oracle.
5. **Regenerable population** — `generator_spec + seed → item` is deterministic.
6. **Frozen comparable cohorts** — Content-addressed manifests on Zenodo.
7. **Contamination resistance** — Fingerprints, seed embargo, optional holdout.
8. **Capability surfaces** — Report multi-dimensional profiles; discourage single-number rankings.
9. **Zenodo-first archival** — Citable releases are immutable deposits with checksums, not git branches.

---

## 4. Task taxonomy

### 4.1 Flagship families (headline)

| ID | Name | Primary submitted object |
|----|------|--------------------------|
| **F1** | Separation / Witness | Verifiable witness (preferably shortest or constraint-optimal) |
| **F2** | Non-materialized Composition | Projected trace, compositional witness, or bounded structural argument |
| **F3** | Constructive Synthesis | Small FSM artefact satisfying a formal target |
| **F4** | Formalization Fidelity | Formal query over a given FSM; scored via semantic equivalence or hidden probes |

Full definitions: [`task_families.md`](task_families.md).

### 4.2 Calibration layer (non-headline)

| ID | Name | Role |
|----|------|------|
| **C1** | Trace / Membership | Operational literacy; parser and simulator sanity |
| **C2** | Basic Reachability | Reachability literacy; not sufficient for reasoning claims |

Calibration items MUST NOT dominate cohort quotas or paper abstract claims.

**Recommended cohort share:** calibration ≤ 15% of public cohort; flagship ≥ 85%.

---

## 5. Superseded design (T1–T7)

The initial v1 draft defined seven independent task families T1–T7 (membership,
reachability, safety, equivalence, containment, diagnosis, composition). That design
is **superseded** because:

- Many T-tasks collapse to **decision-procedure invocation** under tool access.
- Boolean verdicts dominate; witnesses are secondary.
- Composition (T7) encourages **explicit product materialization**.

**Migration map (informative, not normative for scoring):**

| Legacy | Absorbed into |
|--------|---------------|
| T3, T4, T5 (negative instances) | **F1** Separation / Witness |
| T7 | **F2** Non-materialized Composition |
| — (new) | **F3** Constructive Synthesis |
| — (new) | **F4** Formalization Fidelity |
| T1 | **C1** calibration |
| T2 | **C2** calibration |

---

## 6. Evaluation tracks

Three tracks MUST be declared with every submission. They measure different constructs.

| Track | ID | Permitted capabilities | Construct measured |
|-------|-----|------------------------|-------------------|
| Pure reasoning | **R0** | In-context only; no code, no REPL, no external tools | Internal simulation and deduction |
| Tool-augmented reasoning | **R1** | Single-step `step(state, symbol)` simulator; no global search libraries, model checkers, or SMT | Disciplined operational reasoning with bounded aid |
| Solver delegation | **R2** | Arbitrary code, automata libraries, model checkers, SMT | Pipeline orchestration and solver use |

**Normative rules:**

- Claims about **reasoning capability** MUST use **R0** and/or **R1** on flagship families.
- **R2** establishes an upper bound and procedural baseline; it MUST NOT be the sole evidence for reasoning claims.
- **F2** in R2 MUST still forbid explicit full product enumeration in the submitted certificate (solver may use products internally).

### 6.1 Track–family eligibility

| Family | R0 | R1 | R2 |
|--------|:--:|:--:|:--:|
| F1 | ✓ | ✓ | ✓ |
| F2 | ✓* | ✓ | ✓ |
| F3 | ✓* | ✓* | ✓ |
| F4 | ✓ | ✓ | ✓ |
| C1 | ✓ | ✓ | ✓ |
| C2 | ✓ | ✓ | ✓ |

\* Size-bounded strata only; see [`difficulty_model.md`](difficulty_model.md).

---

## 7. Scoring philosophy

FSMReasonBench distinguishes two correctness dimensions:

| Dimension | Definition |
|-----------|------------|
| **Answer extractability** | Submission is parseable, typed, and contains all required fields |
| **Certificate / artefact correctness** | Independent verifier accepts the submitted witness, FSM, query, or argument |

For **flagship families F1–F4**, certificate/artefact correctness is **primary**.
For **calibration C1–C2**, verdict correctness may be primary for sanity checks only.

**Capability surfaces** (required reporting):

- Per-family score matrices (F1–F4, C1–C2)
- Per-track slices (R0, R1, R2)
- Per difficulty stratum
- Cross-family “profile” plots (not a single leaderboard rank)

See [`evaluation_protocol.md`](evaluation_protocol.md).

---

## 8. Difficulty model

Each item carries a difficulty vector including family-specific parameters.
Definitions: [`difficulty_model.md`](difficulty_model.md).

---

## 9. Item lifecycle

```
GeneratorSpec + Seed → Instance Generator → Question Instantiator
                                              ↓
                                    Oracle (decision procedure)
                                              ↓
                              Reference certificate / artefact
                                              ↓
                                         Benchmark Item
                                              ↓
                              Cohort Freezer → Manifest + Hashes
                                              ↓
                         Evaluation → Capability surface report
```

### 9.1 Benchmark item (logical schema)

| Field | Required | Description |
|-------|----------|-------------|
| `item_id` | yes | Stable UUID within cohort |
| `cohort_id` | yes | Same as `cohort_version`, e.g., `1.0-public` |
| `family` | yes | F1–F4 or C1–C2 |
| `family_tier` | yes | `flagship` or `calibration` |
| `track_stratum` | yes | R0 / R1 / R2 eligibility |
| `difficulty` | yes | Difficulty vector |
| `fsm` | yes* | Primary FSM (*F3 may omit until synthesis target) |
| `presentation` | yes | Human and machine views |
| `question` | yes | Typed question |
| `answer_key` | evaluator only | Reference artefact + oracle metadata |
| `hidden_probes` | F4 only | Evaluator-only probe set |
| `contamination` | yes | Public fingerprint; seed reference |

---

## 10. Zenodo release model

FSMReasonBench is designed as a **long-lived citable artifact** (≥ 5 years). Every published
benchmark release MUST pin four version axes:

| Axis | Example | Governs |
|------|---------|---------|
| `benchmark_version` | `1.0.0` | This specification and governance docs |
| `cohort_version` | `1.0-public` | Frozen item set + manifest |
| `schema_version` | `1.0.0` | `schema/*.schema.json` |
| `verifier_version` | `1.0.0` | Independent verifier behaviour |

Optional: `generator_version` for regeneration claims after seed embargo.

**Normative policies:**

- [`../artifact/release_policy.md`](../artifact/release_policy.md)
- [`../artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md)
- [`../artifact/contamination_policy.md`](../artifact/contamination_policy.md)
- [`../artifact/archival_policy.md`](../artifact/archival_policy.md)
- [`../versioning_policy.md`](../versioning_policy.md)

### 10.1 Repository layer separation

| Layer | Path | Citable content |
|-------|------|-----------------|
| Specification | `docs/specification/`, `docs/artifact/` | Yes (in tarball) |
| Declarative spec | `spec/generator/`, `spec/oracle/` | Yes |
| Schema | `schema/` | Yes |
| Frozen cohort | `cohorts/` + Zenodo evaluatee bundle | Yes |
| Generator impl | `src/fsmreasonbench/generator/` | Yes (for regeneration) |
| Verifier impl | `src/fsmreasonbench/verifier/` | **Required** in primary tarball |
| Evaluator impl | `src/fsmreasonbench/evaluator/` | Yes |
| Paper manuscript | `../paper/` | **No** — separate citation |

### 10.2 Release bundles (Zenodo)

| Bundle | Contents | Access |
|--------|----------|--------|
| **Primary** | evaluatee cohort, spec, schema, verifier, scripts, manifest | Public DOI |
| **Evaluator supplement** | answer keys, F4 hidden probes | Public or embargoed |
| **Embargo package** | generation seeds | Post-embargo date |
| **Paper reproduction** | archived submissions, table provenance | Supplement DOI |

Evaluatee and evaluator bundles MUST NOT be merged in the primary download.

---

## 11. Frozen cohorts and regenerable populations

### 11.1 Regenerable population

All items producible from `spec/generator/`, `spec/oracle/`, and deterministic seed.
Regeneration is **R3 reproducibility** (after embargo); not required for scoring frozen cohort.

### 11.2 Frozen cohort

Immutable subset for comparative evaluation:

- `cohort_version` (e.g., `1.0-public`)
- Manifest: `cohorts/<cohort_version>.manifest.json` — see [`../../cohorts/MANIFEST_SPEC.md`](../../cohorts/MANIFEST_SPEC.md)
- SHA-256 per evaluatee item; quota flagship ≥ 85%, calibration ≤ 15%

### 11.3 Cohort integrity (R1)

Researchers MUST be able to validate integrity from Zenodo tarball alone:

```bash
./scripts/validate_cohort_integrity.sh --manifest cohorts/1.0-public.manifest.json
```

---

## 12. Contamination strategy

Normative detail: [`../artifact/contamination_policy.md`](../artifact/contamination_policy.md).

Summary:

1. Public fingerprint per item (published in manifest)
2. Seed embargo until date in `release_manifest.json`
3. No pre-release public item dumps
4. Optional holdout cohort (separate DOI)
5. F4 hidden probes evaluator-only

---

## 13. Versioning

Four-axis model: see [`../versioning_policy.md`](../versioning_policy.md).

| Change | benchmark_version bump |
|--------|------------------------|
| F1–F4 semantics or primary scoring | MAJOR |
| New optional schema fields | MINOR |
| Verifier bugfix, identical acceptance on golden tests | PATCH (verifier_version) |

Submissions MUST declare: `benchmark_version`, `cohort_version`, `schema_version`,
`verifier_version`, `track`, `system_description`.

**Draft `-draft` specs are not citable on Zenodo.**

---

## 14. Conformance

A conformant **Zenodo release** provides:

1. Pinned `release_manifest.json` with SHA256SUMS
2. Normative spec snapshot matching `benchmark_version`
3. Independent verifier passing `tests/golden/`
4. Cohort manifest validating offline
5. Scripts for R1 (integrity), R2 (verification), R4 (table reproduction)
6. No dependency on unpublished code or live APIs for R1–R2–R4

A conformant **implementation** additionally:

1. Validates items against pinned `schema/`
2. Verifies F1–F4 certificates without importing generator
3. Enforces F2 non-materialization on submissions
4. Reports capability surfaces with required stratifications
5. Treats C1–C2 as calibration, not headline metrics

---

## 15. References

- [`task_families.md`](task_families.md)
- [`certificate_formats.md`](certificate_formats.md)
- [`difficulty_model.md`](difficulty_model.md)
- [`evaluation_protocol.md`](evaluation_protocol.md)
- [`../artifact/artifact_philosophy.md`](../artifact/artifact_philosophy.md)
- [`../artifact/repository_layout.md`](../artifact/repository_layout.md)
- [`../versioning_policy.md`](../versioning_policy.md)

# FSMReasonBench — Zenodo preparation

**Status:** pre-release draft  
**Purpose:** working notes for a future Zenodo deposit; not a published release.

This folder documents how the artifact will be packaged, structured, and reproduced once a
public cohort is frozen. It does **not** contain Zenodo metadata, assigned version numbers,
or frozen datasets.

---

## Overview

FSMReasonBench is a benchmark for **reasoning over executable finite-state machines**
(DFA, NFA, bounded Mealy). Flagship tasks require **verifiable certificates or artefacts**,
not boolean verdicts alone. Scoring separates four measurement layers:

1. **Extractability** — parseable, schema-valid submission
2. **Verdict accuracy** — declared verdict matches gold (when extractable)
3. **Certificate validity** — independent verifier accepts the certificate
4. **Full correctness** — verdict and certificate both correct

The companion specification lives in [`docs/specification/BENCHMARK_SPEC.md`](../specification/BENCHMARK_SPEC.md).
Normative archival policies live under [`docs/artifact/`](../artifact/).

---

## Current status

| Aspect | State |
|--------|-------|
| Release readiness | **Pre-release draft** — development on `main`; not citable |
| Implemented families | **C2** (calibration reachability), **F1** (flagship DFA non-equivalence / distinguishing trace) |
| Frozen public cohort | **Not yet** — exploratory runs under `runs/` are gitignored |
| Zenodo record / DOI | **Not created** |
| Version pins | **Not assigned** — see [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) |

Development artifacts (generators, verifiers, evaluators, baselines) are functional for C2
and F1 end-to-end. Families F2–F4 and calibration C1 are specified but not implemented.

---

## Implemented families (artifact snapshot)

| Tier | Family | Certificate type(s) | Role |
|------|--------|---------------------|------|
| Calibration | **C2** | `trace_witness`, `unreachability_witness` | Operational literacy; pipeline sanity |
| Flagship | **F1** | `distinguishing_trace` | First flagship vertical; separation witness |

Example items: [`examples/`](../../examples/). Schema files: [`schema/`](../../schema/).

---

## Documents in this folder

| File | Contents |
|------|----------|
| [`DATASET_STRUCTURE.md`](DATASET_STRUCTURE.md) | JSON record layouts for items, keys, certificates, transcripts, scores |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Seed-based generation, self-verification, oracle checks, transcript re-scoring |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Gate checklist for a future Zenodo release |

---

## Related repository documentation

| Document | Role |
|----------|------|
| [`docs/artifact/release_policy.md`](../artifact/release_policy.md) | Target tarball layout and version axes |
| [`docs/artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md) | Reproducibility tiers (R1–R4) |
| [`docs/artifact/zenodo_checklist.md`](../artifact/zenodo_checklist.md) | Extended pre-upload gate (normative) |
| [`docs/artifact/archival_policy.md`](../artifact/archival_policy.md) | Evaluatee vs evaluator bundle split |
| [`docs/specification/certificate_formats.md`](../specification/certificate_formats.md) | Certificate type reference |

---

## What is explicitly out of scope here

- Zenodo `.zenodo.json` or other platform metadata files
- Assigned `benchmark_version`, `cohort_version`, or DOI
- Frozen cohort manifests or checksum files
- Paper results or model evaluation claims

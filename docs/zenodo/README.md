# FSMReasonBench — Zenodo archive documentation

> **Auditors:** [`../../REVIEWER.md`](../../REVIEWER.md) · [`../REVIEWER.md`](../REVIEWER.md)

**Active software title:** FSMReasonBench: Witness-Aware Evaluation for Verifier-Gated Reasoning Systems  
**Concept DOI:** [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347)  
**v1.0.0 version DOI:** [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)  
**v2.0.0:** preparation under [`../../releases/2.0.0/`](../../releases/2.0.0/) (version DOI after archival)

This folder documents how archival deposits are packaged, structured, and reproduced.
Git `main` remains a development surface; **prefer Zenodo DOIs** for citation.

---

## Overview

FSMReasonBench evaluates **verifier-gated reasoning** on executable finite-state tasks with
**machine-checkable witnesses**. Scoring separates four measurement layers:

1. **Extractability** — parseable, schema-valid submission
2. **Verdict accuracy** — declared verdict matches gold (when extractable)
3. **Witness validity** — independent verifier accepts the witness (legacy schema: `certificate_*`)
4. **Full correctness** — extractable + correct verdict + accepted witness

Normative specification: [`docs/specification/BENCHMARK_SPEC.md`](../specification/BENCHMARK_SPEC.md)  
Archival policies: [`docs/artifact/`](../artifact/)

---

## Release status

| Aspect | State |
|--------|-------|
| Concept DOI | ✅ [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347) |
| v1.0.0 version DOI | ✅ [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |
| v1.0.0 manifest | ✅ [`releases/1.0.0/release_manifest.json`](../../releases/1.0.0/release_manifest.json) |
| v2.0.0 manifest | ✅ prep [`releases/2.0.0/release_manifest.json`](../../releases/2.0.0/release_manifest.json) |
| Calibration cohort | ✅ `v0.1-expanded-n100` |
| Implemented families (empirical) | **C2**, **F1** end-to-end |
| Families F2–F4, C1 | Specified; not in headline empirical claims |

---

## Documents in this folder

| File | Contents |
|------|----------|
| [`DATASET_STRUCTURE.md`](DATASET_STRUCTURE.md) | JSON record layouts |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Replication commands and tiers |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Pre-release gate checklist |
| [`../tosem/ZENODO_RELEASE_NOTES.md`](../tosem/ZENODO_RELEASE_NOTES.md) | Historical v1 deposit notes (legacy path) |

Historical notes that mention a prior journal target describe the **v1.0.0** deposit context and are
retained as archival documentation, not as the current public software identity.

# FSMReasonBench — Zenodo archive documentation

**Published release:** FSMReasonBench **v1.0.0**  
**Zenodo DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)

This folder documents how the published artifact is packaged, structured, and reproduced.
Git `main` remains a development surface; **cite the Zenodo DOI**, not the git URL.

---

## Overview

FSMReasonBench evaluates **reasoning over executable finite-state machines** with
**verifiable certificates**. Scoring separates four measurement layers:

1. **Extractability** — parseable, schema-valid submission
2. **Verdict accuracy** — declared verdict matches gold (when extractable)
3. **Certificate validity** — independent verifier accepts the certificate
4. **Full correctness** — verdict and certificate both correct

Normative specification: [`docs/specification/BENCHMARK_SPEC.md`](../specification/BENCHMARK_SPEC.md)  
Archival policies: [`docs/artifact/`](../artifact/)

---

## v1.0.0 release status

| Aspect | State |
|--------|-------|
| Zenodo record / DOI | ✅ [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348) |
| Release manifest | ✅ [`releases/1.0.0/release_manifest.json`](../../releases/1.0.0/release_manifest.json) |
| Paper cohort | ✅ `v0.1-expanded-n100` under [`cohorts/`](../../cohorts/v0.1-expanded-n100/) |
| Implemented families (empirical) | **C2**, **F1** end-to-end |
| Families F2–F4, C1 | Specified; not in v1.0.0 headline claims |

---

## Documents in this folder

| File | Contents |
|------|----------|
| [`DATASET_STRUCTURE.md`](DATASET_STRUCTURE.md) | JSON record layouts |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Replication commands and tiers |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Pre-release gate checklist (completed for v1.0.0) |

---

## Related documentation

| Document | Role |
|----------|------|
| [`README-RELEASE.md`](../../README-RELEASE.md) | Tarball quickstart |
| [`docs/tmlr_empirical_package_v1/README.md`](../tmlr_empirical_package_v1/README.md) | Paper tables and frozen runs |
| [`docs/artifact/release_policy.md`](../artifact/release_policy.md) | Deposit structure |

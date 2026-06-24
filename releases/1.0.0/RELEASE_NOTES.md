# FSMReasonBench v1.0.0 — Frozen Evaluation Release

**Released:** 2026-06-20  
**Zenodo DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)  
**Author:** César Andrés

## Summary

First public archival release of the FSMReasonBench evaluation artifact: verifier, scoring
pipeline, frozen cohort `v0.1-expanded-n100`, paper-support analyses, and offline reproduction
exports for the companion empirical study on certificate synthesis under auditable verification
contracts.

## Version pins

See [`release_manifest.json`](release_manifest.json):

- `benchmark_version`: `1.0.0`
- `cohort_version`: `v0.1-expanded-n100`
- `schema_version`: `1.0.0`
- `verifier_version`: `1.0.0`

## Included empirical scope

- **C2** reachability calibration (`trace_witness`, `unreachability_witness`)
- **F1** mixed separation/equivalence (`distinguishing_trace`, `equivalence_witness`)
- Claude Sonnet primary campaign and attribution ablations on identical item IDs
- Verifier audit, hash-mismatch decomposition, bootstrap/McNemar uncertainty exports

## Not included as headline claims

- Families F2–F4, calibration C1 (specified only)
- Exploratory `v0.1-exploratory` ($n{=}20$) pilots as primary evidence
- Contaminated or incomplete frontier runs (documented exclusions)

## Citation

See repository root [`CITATION.cff`](../../CITATION.cff).

## Reproduce

[`README-RELEASE.md`](../../README-RELEASE.md) and [`docs/zenodo/REPRODUCIBILITY.md`](../../docs/zenodo/REPRODUCIBILITY.md).

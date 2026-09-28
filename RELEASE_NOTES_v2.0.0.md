# FSMReasonBench v2.0.0 — release notes

**Status:** published archival release.  
**Version DOI:** [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350)  
**Concept DOI:** [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347)  
**GitHub:** [Release v2.0.0](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v2.0.0)

## Summary

FSMReasonBench v2.0.0 consolidates the witness-aware layered evaluation protocol as venue-neutral
research software: extractability, verdict accuracy, witness validity, full correctness, failure
stages, witness contracts, and tool-access conditions.

## Major changes

- Public identity and Zenodo/CITATION metadata aligned to the layered evaluation framework
- Offline reproduction entry point `scripts/reproduce_archived_tables.sh`
- Documentation clarifies single-pass archived cells vs repeated-generation performance estimation
- AI-assisted development disclosure retained without rewriting git history

## Reproducibility contents

- Frozen cohort manifests (`cohorts/v0.1-expanded-n100/`)
- Deterministic verifiers and scoring
- Archived evaluation outputs under `runs/`
- Offline analysis/table regeneration scripts
- Statistical exports (bootstrap / McNemar) regenerable from archived scores

The release supports offline regeneration and verification of reported analyses from the
archived/frozen outputs provided in the repository. It does **not** claim full proprietary-model
re-execution or repeated-generation reproducibility.

## Compatibility / migration

- Legacy export module and directory names (`tosem_*`, `tmlr_*`) remain callable for path stability
- Machine-readable `certificate_*` fields remain valid; protocol terminology prefers *witness*
- No intentional change to frozen numerical rates in this release

## Citation

Cite the version-specific DOI [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350).

Historical v1.0.0 deposit: [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937).

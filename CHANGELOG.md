# Changelog

All notable changes to the FSMReasonBench research software are documented here.

## [2.0.0] — preparation (tag not yet created)

Venue-neutral release consolidation for the witness-aware layered evaluation framework.
Archived experimental outputs and frozen cohort manifests are retained; no new model executions
are introduced in this version.

### Added

- `.zenodo.json` as authoritative GitHub→Zenodo metadata for the v2.0.0 deposit
- `scripts/reproduce_archived_tables.sh` venue-neutral entry point for offline table regeneration
- `releases/2.0.0/release_manifest.json` version pins (version DOI pending archival)
- `RELEASE_NOTES_v2.0.0.md` draft GitHub release body
- `release/v2.0.0_manifest.md` high-level release content inventory
- Explicit AI-assisted development note in the top-level README

### Changed

- Public software title and short description aligned to witness-aware layered evaluation
- `CITATION.cff`, `ARTIFACT_VERSION`, `pyproject.toml`, and package `__version__` set to `2.0.0`
- README rewritten as venue-neutral research software documentation
- Reviewer/reproduction entry points no longer framed as a journal-specific submission package
- Citation guidance uses the Zenodo **concept DOI** until the v2.0.0 version DOI is minted

### Reproducibility

- Frozen cohort `v0.1-expanded-n100`, archived `runs/`, and offline export scripts retained
- Legacy path names (`tosem_*`, `tmlr_*`) kept for command/path stability; documented as historical identifiers
- Legacy `certificate_*` schema field names preserved for archived output compatibility

### Not in this release

- No new model generations, stochastic repetitions, or regenerated canonical rates
- No version-specific Zenodo DOI yet (created only after tag + archival)

## [1.0.0] — 2026-06-20

Initial public archival release (Zenodo DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)).
Frozen calibration cohort, deterministic verifiers, archived frontier and open-weight evaluation
outputs, and offline analysis exports. Historical release metadata used a TOSEM-oriented deposit
description; that naming is retained only as historical record for v1.0.0.

# RELEASE_PREP_v2.0.0

**Phase:** preparation only (no tag, no GitHub Release, no Zenodo mint).  
**Date:** 2026-09-28  
**Branch:** `main` (unchanged)  
**HEAD before prep:** `57ed5246cce43006ca0b5f57170ff4c50c05e1c3`

## Existing release history

| Item | Value |
|------|-------|
| Tags | `v1.0.0`, `tosem-artifact-v1.0`, `clean_v2-confirmatory-prespec-v1` |
| Highest semver tag | `v1.0.0` |
| Zenodo version DOI (v1.0.0) | `10.5281/zenodo.20897937` (verified via Zenodo API) |
| Zenodo concept DOI | `10.5281/zenodo.20836347` (verified via Zenodo API) |
| Prior Zenodo title | FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines |
| Prior Zenodo description | TOSEM-oriented (historical record; not edited on Zenodo in this phase) |

## DOI strategy (prep)

- **A.** Existing version DOI: `10.5281/zenodo.20897937` (v1.0.0 only; preserved in historical docs/`releases/1.0.0/`)
- **B.** Concept DOI: `10.5281/zenodo.20836347` — used as current citation target in README/`CITATION.cff`/`.zenodo.json` until v2 is minted
- **C.** Future v2.0.0 version DOI: **does not exist yet** — not fabricated

## Public identity updates

- Title: **FSMReasonBench: Witness-Aware Evaluation for Verifier-Gated Reasoning Systems**
- Version sources: `2.0.0` / `v2.0.0` in `pyproject.toml`, `__version__`, `CITATION.cff`, `.zenodo.json`, `ARTIFACT_VERSION`, `releases/2.0.0/`
- README rewritten venue-neutral; single-pass archived-cell scope stated
- Created `.zenodo.json`, `CHANGELOG.md`, `RELEASE_NOTES_v2.0.0.md`, `release/v2.0.0_manifest.md`
- Neutral wrapper: `scripts/reproduce_archived_tables.sh` → legacy `reproduce_tosem_tables.sh`

## Legacy path policy

Kept (reproducibility): `tosem_*` / `tmlr_*` modules, scripts, and docs directories. Documented as
legacy identifiers. Not renamed.

## certificate_* compatibility

Preserved. Protocol prose uses *witness*; schema/export fields may remain `certificate_*`.

## Pre-existing dirty WIP (not in this commit)

Stashed as `wip-pre-v2.0.0-prep` before edits. Contained rate/CI formatting changes under A1/tmlr
exports and evaluator code. **Must not enter the v2.0.0 tag** until scientifically reviewed.
Restore with `git stash list` / `git stash pop` after release prep if needed.

## Offline checks

| Check | Result |
|-------|--------|
| `.zenodo.json` JSON parse | PASS |
| `CITATION.cff` via `cffconvert` | PASS |
| `pytest` export/reproduce unit tests | PASS (8) |
| `artifact_health` | PASS |
| Frozen `runs/.../summary.json` SHA-256 | UNCHANGED |
| Test-touched package manifests/figures | restored via `git checkout` |
| Secret scan (API keys / private key blocks) | PASS (0 findings) |

## License consistency

LICENSE / `.zenodo.json` / `CITATION.cff` / `pyproject.toml` = Apache-2.0.

## Hard stops observed

1. Do not tag until prep SHA is inspected.
2. Pre-existing WIP stash may alter A1 rates if popped — review before tagging.
3. GitHub remote description/topics currently empty — recommend updating after tag (not changed in this phase).

## Recommended tag target

After this prep commit is pushed and inspected: tag **that commit SHA** as `v2.0.0` (immutable).

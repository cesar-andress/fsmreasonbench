# Reviewer / auditor quickstart

You are verifying **FSMReasonBench v2.0.0** archived layered metrics.

**→ Full guide:** [`docs/REVIEWER.md`](docs/REVIEWER.md)  
**→ Offline regeneration details:** [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md)
(legacy directory name retained for path stability)

## Verify the software version

```bash
cat ARTIFACT_VERSION
cat releases/2.0.0/release_manifest.json
```

Expected: `version: v2.0.0` and DOI `10.5281/zenodo.23004350`.

| Surface | Identifier |
|---------|------------|
| **v2.0.0 version DOI** | [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350) |
| **Concept DOI** | [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347) |
| **Historical v1.0.0** | [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |

## Regenerate archived tables (≈5 minutes, no API keys)

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_archived_tables.sh
```

**Success:** script exits 0; see `docs/tosem_empirical_package_v1/package_manifest.json`.

**Optional check:**

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

## What you do not need

- Model API keys
- Re-running inference campaigns
- Manuscript source (to audit reported **numbers** from archived exports)

## Scope note

Archived cells are frozen single-pass evaluations under recorded configurations. Offline checks
verify analysis regeneration from those archives; they do not estimate repeated-generation variance.

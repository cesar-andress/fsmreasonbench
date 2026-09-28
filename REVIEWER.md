# Reviewer / auditor quickstart

You are verifying **FSMReasonBench** archived layered metrics.

**→ Full guide:** [`docs/REVIEWER.md`](docs/REVIEWER.md)  
**→ Offline regeneration details:** [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md)
(legacy directory name retained for path stability)

## Verify the software version

```bash
cat ARTIFACT_VERSION
cat releases/2.0.0/release_manifest.json
```

For the immutable **v1.0.0** archival deposit, use Zenodo
[10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) or tag `v1.0.0`.
The **concept DOI** for all versions is [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347).

If you cloned GitHub `main`, confirm `ARTIFACT_VERSION` matches the release you intend to audit.

## Regenerate archived tables (≈5 minutes, no API keys)

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_archived_tables.sh
```

**Success:** script exits 0; see `docs/tosem_empirical_package_v1/package_manifest.json`
(and `paper/tables/` when this repo is checked out beside the manuscript tree).

**Optional check:**

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

## What you do not need

- Model API keys (OpenAI, Anthropic, etc.)
- Re-running inference campaigns
- Manuscript source (to audit reported **numbers** from archived exports)

## Scope note

Archived cells are frozen single-pass evaluations under recorded configurations. Offline checks
verify analysis regeneration from those archives; they do not estimate repeated-generation variance.

# Reviewer quickstart

You opened the **Zenodo v1.0.0** deposit (DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)).

**→ Full 5-minute guide:** [`docs/REVIEWER.md`](docs/REVIEWER.md)  
**→ Detailed reproduction tiers:** [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md)

## Verify the frozen snapshot

```bash
cat ARTIFACT_VERSION          # must show version v1.0.0 and DOI 10.5281/zenodo.20897937
cat releases/1.0.0/release_manifest.json
```

If you cloned **GitHub `main`** instead of downloading Zenodo, you may **not** be on the archival
snapshot. Use the [Zenodo tarball](https://doi.org/10.5281/zenodo.20897937) or GitHub release
[`FSMReasonBench v1.0.0`](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0).

## Reproduce paper tables (≈5 minutes, no API keys)

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

**Success:** script exits 0; LaTeX tables appear under `paper/tables/` (monorepo) or see export
manifest at `docs/tosem_empirical_package_v1/package_manifest.json`.

**Optional check:**

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

## What you do not need

- Model API keys (OpenAI, Anthropic)
- Re-running inference campaigns
- The companion manuscript source (to audit reported **numbers**)

## Frozen vs. development

| Surface | Role |
|---------|------|
| **Zenodo v1.0.0** | Cite and reproduce **paper numbers** |
| **GitHub release `v1.0.0`** | Tag-aligned mirror of Zenodo |
| **GitHub `main`** | Post-freeze development — **not** the archival snapshot |

See [`docs/artifact/FROZEN_VS_DEVELOPMENT.md`](docs/artifact/FROZEN_VS_DEVELOPMENT.md).

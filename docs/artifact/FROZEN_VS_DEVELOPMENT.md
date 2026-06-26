# Frozen archival release vs. GitHub development

## Cite and reproduce paper numbers from

| Surface | Identifier | Use |
|---------|------------|-----|
| **Zenodo** | DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937), version **v1.0.0** | **Primary archival deposit** — tarball reviewers download |
| **GitHub release** | [`FSMReasonBench v1.0.0`](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0) | Tag-aligned mirror of the Zenodo snapshot |
| **Release manifest** | [`releases/1.0.0/release_manifest.json`](../releases/1.0.0/release_manifest.json) | Version pins (`benchmark_version`, `cohort_version`, `verifier_version`) |
| **Version stamp** | [`ARTIFACT_VERSION`](../ARTIFACT_VERSION) | One-line check at repository root |

Run `./scripts/reproduce_tosem_tables.sh` against **only** these surfaces when auditing TOSEM tables.

## Ongoing development (not the archival snapshot)

| Surface | URL | Use |
|---------|-----|-----|
| **GitHub `main`** | https://github.com/cesar-andress/fsmreasonbench/tree/main | Post-freeze engineering — new exporters, docs, optional experiments |
| **Unreleased branches** | — | Contributor work; **not citable** for v1.0.0 paper claims |

Changes on `main` do **not** retroactively alter the Zenodo v1.0.0 deposit. A new empirical snapshot
requires a **new Zenodo version** and an explicit manuscript freeze update.

## Quick self-check

```bash
# After cloning or extracting:
grep -E '^(version|doi):' ARTIFACT_VERSION
git describe --tags --exact-match 2>/dev/null || echo "Not on a release tag — confirm Zenodo tarball"
```

If `ARTIFACT_VERSION` does not show `v1.0.0` and DOI `10.5281/zenodo.20897937`, stop before
auditing paper numbers.

See also [`github_vs_zenodo.md`](github_vs_zenodo.md) for governance rationale.

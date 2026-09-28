# Frozen archival release vs. GitHub development

## Cite and regenerate archived analyses from

| Surface | Identifier | Use |
|---------|------------|-----|
| **Zenodo v2.0.0** | [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350) | **Current archival deposit** |
| **Zenodo concept DOI** | [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347) | All-versions software citation |
| **Zenodo v1.0.0** | [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) | Historical archival deposit |
| **GitHub tag `v2.0.0`** | release tag | Tag-aligned with the v2 deposit |
| **Release manifests** | `releases/2.0.0/`, `releases/1.0.0/` | Version pins |
| **Version stamp** | [`../../ARTIFACT_VERSION`](../../ARTIFACT_VERSION) | One-line check at repository root |

Run `./scripts/reproduce_archived_tables.sh` against an archival surface when auditing frozen rates.

## Ongoing development (not an archival snapshot by itself)

| Surface | URL | Use |
|---------|-----|-----|
| **GitHub `main`** | https://github.com/cesar-andress/fsmreasonbench/tree/main | Post-freeze engineering |
| **Unreleased branches** | — | Contributor work; cite Zenodo for archival claims |

Changes on `main` do **not** retroactively alter published Zenodo version deposits.

## Quick self-check

```bash
grep -E '^(version|doi):' ARTIFACT_VERSION
git describe --tags --exact-match 2>/dev/null || echo "Not on a release tag — confirm intended snapshot"
```

See also [`github_vs_zenodo.md`](github_vs_zenodo.md) for governance rationale.

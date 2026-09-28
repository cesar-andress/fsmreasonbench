# FSMReasonBench — archival tarball quickstart

This guide applies when you download an archival deposit (Zenodo tarball or GitHub release archive).

**Concept DOI (all versions):** [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347)  
**v1.0.0 version DOI:** [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)

> **Auditors:** follow [`REVIEWER.md`](REVIEWER.md) or [`docs/REVIEWER.md`](docs/REVIEWER.md).

---

## 1. Verify the snapshot

```bash
cat ARTIFACT_VERSION
ls releases/
```

For **v1.0.0** archives expect DOI `10.5281/zenodo.20897937` and cohort `v0.1-expanded-n100`.  
For **v2.0.0** prep/archives, see `releases/2.0.0/release_manifest.json` (version DOI after archival).

If the tarball includes checksums: `sha256sum -c SHA256SUMS`

---

## 2. Install

```bash
pip install -e ".[dev,plot]"
```

Python ≥ 3.11.

---

## 3. Regenerate archived tables (no API keys)

```bash
./scripts/reproduce_archived_tables.sh
```

**Success:** `docs/tosem_empirical_package_v1/package_manifest.json` exists; script exits 0.

Optional: `PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health`

---

## 4. Next steps

| Task | Document |
|------|----------|
| Offline regeneration tiers | [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md) (legacy path name) |
| Documentation index | [`docs/README.md`](docs/README.md) |
| Frozen vs. `main` | [`docs/artifact/FROZEN_VS_DEVELOPMENT.md`](docs/artifact/FROZEN_VS_DEVELOPMENT.md) |

## Citation

[`CITATION.cff`](CITATION.cff)

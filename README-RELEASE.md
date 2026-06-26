# FSMReasonBench — Zenodo tarball quickstart

You downloaded **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines**
**v1.0.0** from Zenodo.

**DOI:** [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)  
**GitHub release (mirror):** [FSMReasonBench v1.0.0](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0)

> **Reviewers:** follow [`REVIEWER.md`](REVIEWER.md) or [`docs/REVIEWER.md`](docs/REVIEWER.md) for the
> full 5-minute audit path.

---

## 1. Verify the frozen snapshot

```bash
cat ARTIFACT_VERSION
cat releases/1.0.0/release_manifest.json
```

Expected: `version: v1.0.0`, DOI `10.5281/zenodo.20897937`, cohort `v0.1-expanded-n100`.

If the tarball includes checksums: `sha256sum -c SHA256SUMS`

---

## 2. Install

```bash
pip install -e ".[dev,plot]"
```

Python ≥ 3.11.

---

## 3. Reproduce TOSEM tables (no API keys)

```bash
./scripts/reproduce_tosem_tables.sh
```

**Success:** `docs/tosem_empirical_package_v1/package_manifest.json` exists; script exits 0.

Optional: `PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health`

---

## 4. Next steps

| Task | Document |
|------|----------|
| Full reproduction tiers | [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md) |
| Documentation index | [`docs/README.md`](docs/README.md) |
| Frozen vs. `main` | [`docs/artifact/FROZEN_VS_DEVELOPMENT.md`](docs/artifact/FROZEN_VS_DEVELOPMENT.md) |
| Score a sample submission | `PYTHONPATH=src python -m fsmreasonbench.cli.score_submission --help` |

## Citation

[`CITATION.cff`](CITATION.cff)

# Reviewer onboarding (≈5 minutes)

This guide is for auditors verifying **FSMReasonBench** archived layered metrics from a Zenodo
deposit or git tag.

**Current archival DOI (v2.0.0):** [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350)  
**Concept DOI (all versions):** [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347)  
**Historical v1.0.0:** [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)

**Goal:** confirm the frozen snapshot and regenerate layered tables from on-disk run outputs —
**without model API calls**.

---

## Step 0 — Confirm the snapshot (30 s)

```bash
cat ARTIFACT_VERSION
python3 -c "import json; m=json.load(open('releases/2.0.0/release_manifest.json')); print(m['benchmark_version'], m['zenodo']['primary_doi'])"
```

For the published **v2.0.0** archive expect `2.0.0` and `10.5281/zenodo.23004350`.

| You opened… | Archived numbers regenerable? |
|-------------|----------------------------|
| Zenodo tarball | **Yes** — archival deposit |
| GitHub release tag | **Yes** when tag-aligned with the deposit |
| GitHub branch `main` | Confirm `ARTIFACT_VERSION`; may include post-freeze development |

Details: [`artifact/FROZEN_VS_DEVELOPMENT.md`](artifact/FROZEN_VS_DEVELOPMENT.md).

---

## Step 1 — Install (1 min)

From the repository root (directory containing `pyproject.toml`):

```bash
pip install -e ".[dev,plot]"
```

Requires **Python ≥ 3.11** (3.12 used in release checks).

---

## Step 2 — Sanity check (30 s)

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

Confirms frozen run summaries expected by the export pipeline are present under `runs/`.

---

## Step 3 — Regenerate archived tables (2–4 min)

```bash
./scripts/reproduce_archived_tables.sh
```

This script:

- reads frozen `combined_summary.json` / `scores.jsonl` under `runs/`
- writes LaTeX tables to `../paper/tables/` when a sibling `paper/` directory exists
- writes JSON manifests under `docs/tosem_empirical_package_v1/` and `docs/a1_constructible_equivalence_v1/`
- **does not** call OpenAI, Anthropic, or Ollama

**Verify success**

```bash
test -f docs/tosem_empirical_package_v1/package_manifest.json && echo OK
ls docs/tosem_empirical_package_v1/package_manifest.json
```

If `../paper/` is absent (Zenodo-only tree), compare exports against manifests — you do not need
the LaTeX manuscript to audit numeric claims.

---

## Step 4 — Optional unit checks (1 min)

```bash
PYTHONPATH=src python3.12 -m pytest \
  tests/unit/test_tosem_empirical_package_export.py \
  tests/unit/test_local_matrix_bootstrap_export.py -q
```

---

## What is FSMReasonBench?

A **frozen evaluation artifact** for verifier-gated formal reasoning on finite-state tasks.
It separates **verdict accuracy**, **witness validity**, and **full correctness** — the layered
metrics used by the witness-aware evaluation protocol.

| Question | Answer |
|----------|--------|
| What is in this deposit? | Cohort `v0.1-expanded-n100`, verifier/scorer, frozen runs, export pipelines |
| Relation to accompanying studies? | **Calibration instrument** for witness-aware layered evaluation |
| Where are run roots listed? | [`EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) (legacy filename) |
| Normative benchmark spec? | [`specification/BENCHMARK_SPEC.md`](specification/BENCHMARK_SPEC.md) |

---

## Directory map (reviewer essentials)

```
ARTIFACT_VERSION          ← software version + DOI pointers (read first)
REVIEWER.md               ← one-screen entry (repo root)
docs/REVIEWER.md          ← this guide
releases/1.0.0/           ← historical release manifest
releases/2.0.0/           ← current prep manifest
cohorts/v0.1-expanded-n100/
runs/                     ← frozen campaign outputs (in Zenodo tarball)
src/fsmreasonbench/       ← verifier, scorer, exporters
scripts/reproduce_archived_tables.sh
docs/tosem/REPRODUCTION.md   ← legacy directory name; offline workflow
docs/tosem_empirical_package_v1/
```

Full layout: [`artifact/repository_layout.md`](artifact/repository_layout.md).

---

## Documentation index

| Document | When to read |
|----------|--------------|
| [`tosem/REPRODUCTION.md`](tosem/REPRODUCTION.md) | Full tiered offline workflow (legacy path) |
| [`tosem/README.md`](tosem/README.md) | Historical companion-study overview (legacy path) |
| [`EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) | Frozen campaign index (artifact mirror; legacy name) |
| [`zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) | Archival policy and replication tiers |
| [`README.md`](../README.md) | Project landing page |
| [`README-RELEASE.md`](../README-RELEASE.md) | Tarball-only quickstart |

**Do not use for archived-number audit:** [`TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](TOSEM_EXPERIMENT_EXTENSION_PLAN.md) (post-freeze plans; may require API keys).

---

## Citation

Cite the v2.0.0 version DOI [10.5281/zenodo.23004350](https://doi.org/10.5281/zenodo.23004350).
The concept DOI [10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347) resolves across versions.
Historical v1.0.0 remains [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937).
See [`CITATION.cff`](../CITATION.cff).

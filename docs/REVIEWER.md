# Reviewer onboarding (≈5 minutes)

This guide is for **ACM TOSEM artifact evaluators** who arrived from the Zenodo DOI
[10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937).

**Goal:** confirm you hold the **frozen v1.0.0 snapshot** and regenerate manuscript tables from
on-disk run outputs — **without model API calls**.

---

## Step 0 — Confirm you are on v1.0.0 (30 s)

```bash
cat ARTIFACT_VERSION
python3 -c "import json; m=json.load(open('releases/1.0.0/release_manifest.json')); print(m['benchmark_version'], m['zenodo']['primary_doi'])"
```

Expected: `1.0.0` and `10.5281/zenodo.20897937`.

| You opened… | Paper numbers reproducible? |
|-------------|----------------------------|
| Zenodo tarball | **Yes** — this is the archival deposit |
| GitHub release [`v1.0.0`](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0) | **Yes** — tag-aligned with Zenodo |
| GitHub branch `main` | **Maybe not** — ongoing development after the freeze |

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

## Step 3 — Regenerate TOSEM tables (2–4 min)

```bash
./scripts/reproduce_tosem_tables.sh
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
metrics used in the companion TOSEM paper.

| Question | Answer |
|----------|--------|
| What is in this deposit? | Cohort `v0.1-expanded-n100`, verifier/scorer, frozen runs, export pipelines |
| Relation to the paper? | **Calibration instrument** for witness-aware layered evaluation (methodology = paper; numbers = this artifact) |
| Where are run roots listed? | [`EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) |
| Normative benchmark spec? | [`specification/BENCHMARK_SPEC.md`](specification/BENCHMARK_SPEC.md) |

---

## Directory map (reviewer essentials)

```
ARTIFACT_VERSION          ← frozen version + DOI (read first)
REVIEWER.md               ← one-screen entry (repo root)
docs/REVIEWER.md          ← this guide
releases/1.0.0/           ← release manifest and notes
cohorts/v0.1-expanded-n100/
runs/                     ← frozen campaign outputs (in Zenodo tarball)
src/fsmreasonbench/       ← verifier, scorer, exporters
scripts/reproduce_tosem_tables.sh
docs/tosem/REPRODUCTION.md
docs/tosem_empirical_package_v1/
```

Full layout: [`artifact/repository_layout.md`](artifact/repository_layout.md).

---

## Documentation index

| Document | When to read |
|----------|--------------|
| [`tosem/REPRODUCTION.md`](tosem/REPRODUCTION.md) | Full tiered workflow, expected outputs, runtime table |
| [`tosem/README.md`](tosem/README.md) | TOSEM companion artifact overview |
| [`EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) | Frozen campaign index (artifact mirror) |
| [`zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) | Archival policy and replication tiers |
| [`README.md`](../README.md) | Project landing page |
| [`README-RELEASE.md`](../README-RELEASE.md) | Tarball-only quickstart |

**Do not use for paper-number audit:** [`TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](TOSEM_EXPERIMENT_EXTENSION_PLAN.md) (post-freeze, requires API keys).

---

## Citation

Use DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) and version **v1.0.0**.
See [`CITATION.cff`](../CITATION.cff).

# FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20897937.svg)](https://doi.org/10.5281/zenodo.20897937)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

**Archival release (cite this):** [Zenodo v1.0.0 — DOI 10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)  
**Companion paper:** ACM TOSEM — witness-aware layered evaluation methodology (calibrated on this artifact)  
**Development:** [GitHub `main`](https://github.com/cesar-andress/fsmreasonbench) — post-release changes; **do not cite `main` for paper numbers**

---

## What is FSMReasonBench?

FSMReasonBench is a **frozen evaluation artifact** for software-engineering research on
**verifier-gated formal reasoning**. It measures whether systems supply **machine-verifiable
witnesses**—replayable traces, separating inputs, or canonical digests—not boolean verdicts alone.

Each item pairs a typed finite-state task with an independent verifier that recomputes the witness
from evaluatee-visible data under a published contract. Scoring exports separate **extractability**,
**verdict accuracy**, **witness validity**, and **full correctness**, plus pipeline-stage failure
labels and a **verdict–witness gap**.

Version **v1.0.0** implements two empirical families (**C2** reachability, **F1**
equivalence/separation) on cohort snapshot **`v0.1-expanded-n100`** ($n{=}100$ items per cell,
$T{=}0.2$).

---

## What does this repository contain?

| Layer | Contents |
|-------|----------|
| **Normative spec** | [`docs/specification/`](docs/specification/) — benchmark definition, evaluation protocol |
| **Cohort** | [`cohorts/v0.1-expanded-n100/`](cohorts/v0.1-expanded-n100/) — frozen item manifests and JSONL |
| **Engine** | [`src/fsmreasonbench/`](src/fsmreasonbench/) — generators, verifier, scorer, runners, exporters |
| **Frozen runs** | [`runs/`](runs/) — pre-computed campaign outputs (`scores.jsonl`, `combined_summary.json`; shipped in Zenodo tarball) |
| **Paper exports** | [`docs/tosem_empirical_package_v1/`](docs/tosem_empirical_package_v1/), [`docs/a1_constructible_equivalence_v1/`](docs/a1_constructible_equivalence_v1/) |
| **Release pins** | [`releases/1.0.0/release_manifest.json`](releases/1.0.0/release_manifest.json) — version identifiers to cite |
| **Scripts** | [`scripts/`](scripts/) — offline validation and table regeneration (**no model API calls**) |

Families **F2–F4** and calibration **C1** are specified but **not** part of the v1.0.0 empirical
slice.

---

## How does it relate to the paper?

The companion **ACM TOSEM** manuscript specifies **witness-aware layered evaluation**—a reporting
protocol with separate endpoints, failure stages, and typed tool access. **FSMReasonBench v1.0.0**
is the **calibration instrument**: it supplies items, verifier rules, frozen model runs, and export
pipelines for the empirical study. The paper’s contribution is methodological; the artifact is the
replicable evidence base.

| Need | Where |
|------|-------|
| Manuscript source (monorepo checkout) | [`../paper/`](../paper/) |
| Authoritative run index & headline numbers | [`../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../paper/EXPERIMENTAL_FREEZE_TOSEM.md) |
| Artifact-side freeze mirror | [`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md) |
| TOSEM artifact guide | [`docs/tosem/README.md`](docs/tosem/README.md) |

In a **Zenodo-only** tree, the manuscript may not be bundled; cite the paper separately and use this
repository to audit every reported rate.

---

## Where is the frozen artifact?

| Role | Location |
|------|----------|
| **Citable archival snapshot** | **Zenodo** — [DOI 10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937), version **v1.0.0** |
| **Release manifest & notes** | [`releases/1.0.0/`](releases/1.0.0/) |
| **Citation metadata** | [`CITATION.cff`](CITATION.cff), [`codemeta.json`](codemeta.json) |
| **Tarball quickstart** | [`README-RELEASE.md`](README-RELEASE.md) |

The Zenodo deposit is the **frozen, version-pinned** bundle used to reproduce the paper’s tables and
figures. It includes cohort snapshots, frozen run trees, verifier/scoring code, and analysis exports.

---

## How do I reproduce the experiments?

**Read-only audit (recommended for reviewers):** recompute scores and regenerate exports from frozen
`scores.jsonl` / `summary.json` files. **No API keys required.**

```bash
pip install -e ".[dev,plot]"
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

**Re-executing live model campaigns** (frontier APIs, Ollama) is optional and **not** required to
verify the paper. Frozen run roots are indexed in
[`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md). Post-freeze extension
studies (replicates, additional attribution cells) are documented in
[`docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md) and require
provider credentials.

Full replication tiers: [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md).

---

## How do I reproduce the paper?

Regenerate all TOSEM manuscript LaTeX tables and export manifests from frozen runs:

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

**Outputs**

- LaTeX tables → `../paper/tables/` (when the monorepo `paper/` directory is present)
- Export manifest → [`docs/tosem_empirical_package_v1/package_manifest.json`](docs/tosem_empirical_package_v1/package_manifest.json)
- Experiment A1 tables → [`docs/a1_constructible_equivalence_v1/`](docs/a1_constructible_equivalence_v1/)

**Compile the manuscript** (monorepo layout):

```bash
make -C ../paper
```

Step-by-step workflow: [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md).

---

## Where is the documentation?

| Document | Purpose |
|----------|---------|
| [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md) | Reviewer workflow — tiers, commands, expected outputs |
| [`docs/tosem/README.md`](docs/tosem/README.md) | TOSEM companion artifact overview |
| [`docs/specification/BENCHMARK_SPEC.md`](docs/specification/BENCHMARK_SPEC.md) | Normative benchmark definition |
| [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md) | Zenodo archival policy and replication tiers |
| [`docs/dataset_card.md`](docs/dataset_card.md) | Dataset overview |
| [`docs/artifact/`](docs/artifact/) | Release, versioning, and governance policies |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Component inventory for v1.0.0 |

Repository layout reference: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md).

---

## Where should future development happen?

| Branch / surface | Use |
|------------------|-----|
| **Zenodo v1.0.0** | Cite and reproduce **published paper numbers** |
| **GitHub release [`FSMReasonBench v1.0.0`](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0)** | Tag-aligned mirror of the archival freeze |
| **GitHub `main`** | Ongoing development **after** the freeze — new cohorts, exporters, or experiments |

Changes on `main` do not retroactively alter the v1.0.0 Zenodo deposit. Fork or branch from `main` for
new work; publish a **new Zenodo version** if you need a new citable snapshot.

---

## Citation

```bibtex
@misc{fsmreasonbench2026,
  author  = {Andr{\'e}s, C{\'e}sar},
  title   = {{FSMReasonBench}: Evaluating Reasoning over Executable Finite-State Machines},
  year    = {2026},
  version = {v1.0.0},
  doi     = {10.5281/zenodo.20897937},
  url     = {https://doi.org/10.5281/zenodo.20897937}
}
```

Or use [`CITATION.cff`](CITATION.cff).

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

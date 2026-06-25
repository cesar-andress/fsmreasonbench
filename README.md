# FSMReasonBench

**Evaluating Reasoning over Executable Finite-State Machines**

FSMReasonBench measures whether language models can supply **machine-verifiable witnesses**
(certificates) for formal finite-state decision tasks—not boolean verdicts alone.
Each item pairs a typed question with an independent verifier that recomputes witnesses from
supplied automata under a fixed, auditable contract.

## Cite the published artifact

**FSMReasonBench v1.0.0** is archived on Zenodo:

**DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)

Use `CITATION.cff` or the DOI above. Git `main` is for development; **do not cite the git URL**.

Companion empirical paper (separate): [`../paper/`](../paper/)

---

## What v1.0.0 includes

| Component | Description |
|-----------|-------------|
| **Verifier + scorer** | Independent replay and hash-contract checking for C2 and F1 certificate classes |
| **Generators + oracles** | Seeded item construction with self-verification |
| **Frozen cohort** | `v0.1-expanded-n100` — C2 and F1 mixed snapshots ($n{=}100$ per family) |
| **Evaluation pipeline** | R0/R1/R2 tracks, attribution ablations, failure inspection |
| **Paper-support analyses** | Verifier audit ($16/16$), hash-mismatch decomposition, bootstrap/McNemar exports |
| **Empirical package** | [`docs/tmlr_empirical_package_v1/`](docs/tmlr_empirical_package_v1/) — Claude tables/figures |
| **TOSEM package** | [`docs/tosem_empirical_package_v1/`](docs/tosem_empirical_package_v1/) — Claude+GPT manuscript tables |
| **Documentation** | Normative spec, reproducibility policies, dataset card |

Families **F2–F4** and calibration **C1** remain specified but are **not** part of the v1.0.0
empirical slice. Historical exploratory milestone: [`docs/releases/v0.1-exploratory.md`](docs/releases/v0.1-exploratory.md).

Release manifest: [`releases/1.0.0/release_manifest.json`](releases/1.0.0/release_manifest.json)

---

## Reproduce paper results (offline)

Tarball quickstart: [`README-RELEASE.md`](README-RELEASE.md)

From a development clone:

```bash
pip install -e ".[dev,plot]"
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
PYTHONPATH=src python -m fsmreasonbench.cli.export_tmlr_empirical_package
PYTHONPATH=src python -m fsmreasonbench.cli.export_tosem_empirical_package
PYTHONPATH=src python -m fsmreasonbench.cli.artifact_health
```

Primary frozen runs and analysis paths are documented in
[`docs/tmlr_empirical_package_v1/README.md`](docs/tmlr_empirical_package_v1/README.md) and
[`docs/paper_results.md`](docs/paper_results.md). Regeneration uses frozen `scores.jsonl` files;
**no model API calls** are required for audit, decomposition, or table export.

---

## Repository layout

```
docs/specification/     Normative benchmark definition
docs/artifact/          Release and reproducibility policies
docs/tmlr_empirical_package_v1/   Paper tables, figures, uncertainty exports
cohorts/v0.1-expanded-n100/       Frozen paper cohort (manifest + JSONL)
src/fsmreasonbench/     Generator, verifier, evaluator, runners, cohort tools
releases/1.0.0/         Published release manifest
scripts/                Offline validation and scoring helpers
```

Detail: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md)

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Current released components and assets |
| [`docs/specification/BENCHMARK_SPEC.md`](docs/specification/BENCHMARK_SPEC.md) | Normative benchmark definition |
| [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md) | Replication tiers and commands |
| [`docs/dataset_card.md`](docs/dataset_card.md) | Dataset overview |
| [`docs/artifact/reproducibility_policy.md`](docs/artifact/reproducibility_policy.md) | R1–R4 reproduction tiers |

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

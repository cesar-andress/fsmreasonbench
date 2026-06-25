# FSMReasonBench

**Evaluating Reasoning over Executable Finite-State Machines**

FSMReasonBench measures whether language models can supply **machine-verifiable witnesses**
(certificates) for formal finite-state decision tasks—not boolean verdicts alone.
Each item pairs a typed question with an independent verifier that recomputes witnesses from
supplied automata under a fixed, auditable contract.

**Active companion paper:** ACM TOSEM manuscript in [`../paper/`](../paper/)  
**Experimental freeze:** [`../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../paper/EXPERIMENTAL_FREEZE_TOSEM.md)

## Cite the published artifact

**FSMReasonBench v1.0.0** is archived on Zenodo:

**DOI:** [10.5281/zenodo.20836348](https://doi.org/10.5281/zenodo.20836348)

Use `CITATION.cff` or the DOI above. Git `main` is for development; **do not cite the git URL**.

---

## What v1.0.0 includes

| Component | Description |
|-----------|-------------|
| **Verifier + scorer** | Independent replay and hash-contract checking for C2 and F1 certificate classes |
| **Generators + oracles** | Seeded item construction with self-verification |
| **Frozen cohort** | `v0.1-expanded-n100` — C2 and F1 mixed snapshots ($n{=}100$ per family) |
| **Evaluation pipeline** | R0/R1/R2 tracks, attribution ablations, failure inspection |
| **Paper-support analyses** | Verifier audit ($16/16$), hash-mismatch decomposition, bootstrap/McNemar exports |
| **TOSEM package** | [`docs/tosem_empirical_package_v1/`](docs/tosem_empirical_package_v1/) — Claude+GPT+local TOSEM tables |
| **Extension experiments (manual)** | [`docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md) — replicates + GPT ladder (post-freeze) |
| **Constructible equivalence (A1)** | [`docs/TOSEM_A1_EXPERIMENT_PLAN.md`](docs/TOSEM_A1_EXPERIMENT_PLAN.md) — bisimulation witness construct-validity study |
| **Historical TMLR package** | [`docs/tmlr_empirical_package_v1/`](docs/tmlr_empirical_package_v1/) — Claude ablations (still used by export) |
| **Documentation** | Normative spec, reproducibility policies, dataset card |

Families **F2–F4** and calibration **C1** remain specified but are **not** part of the v1.0.0
empirical slice. Historical exploratory milestone: [`docs/releases/v0.1-exploratory.md`](docs/releases/v0.1-exploratory.md).

Release manifest: [`releases/1.0.0/release_manifest.json`](releases/1.0.0/release_manifest.json)

---

## Reproduce TOSEM paper results (offline)

Tarball quickstart: [`README-RELEASE.md`](README-RELEASE.md)  
Full workflow: [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md)

From a development clone (Python ≥ 3.11):

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

Equivalent manual commands:

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.export_tosem_empirical_package
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.export_tmlr_empirical_package
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

Primary frozen runs are listed in
[`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md).
Regeneration uses frozen `scores.jsonl` / `combined_summary.json` files;
**no model API calls** are required for audit, decomposition, or table export.

**Post-freeze extension campaigns** (replicates, full GPT attribution ladder) require API keys
and are documented in [`docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md).
Launch manually via [`scripts/run_tosem_extension_campaigns.sh`](scripts/run_tosem_extension_campaigns.sh).

---

## Repository layout

```
docs/specification/     Normative benchmark definition
docs/tosem/             ACM TOSEM companion documentation
docs/artifact/          Release and reproducibility policies
docs/tosem_empirical_package_v1/   TOSEM table export manifest
docs/tmlr_empirical_package_v1/  Historical Claude ablation exports
cohorts/v0.1-expanded-n100/       Frozen paper cohort (manifest + JSONL)
src/fsmreasonbench/     Generator, verifier, evaluator, runners, cohort tools
releases/1.0.0/         Published release manifest
scripts/                Offline validation and table reproduction
```

Detail: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md)

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Current released components and assets |
| [`docs/tosem/README.md`](docs/tosem/README.md) | TOSEM companion artifact guide |
| [`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md) | Frozen campaigns (artifact mirror) |
| [`docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md) | Post-freeze extension study plan |
| [`docs/tosem_extension_experiments_v1/README.md`](docs/tosem_extension_experiments_v1/README.md) | Extension export manifest |
| [`docs/specification/BENCHMARK_SPEC.md`](docs/specification/BENCHMARK_SPEC.md) | Normative benchmark definition |
| [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md) | Replication tiers and commands |
| [`docs/dataset_card.md`](docs/dataset_card.md) | Dataset overview |
| [`docs/historical/README.md`](docs/historical/README.md) | Superseded TMLR-era docs |

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

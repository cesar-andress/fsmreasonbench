# FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20897937.svg)](https://doi.org/10.5281/zenodo.20897937)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

> **ACM TOSEM reviewer?** Start at **[`REVIEWER.md`](REVIEWER.md)** — verify v1.0.0, reproduce paper
> tables in ~5 minutes, **no API keys**. Full guide: [`docs/REVIEWER.md`](docs/REVIEWER.md).

| | |
|--|--|
| **Frozen archival release (cite this)** | [Zenodo v1.0.0 — DOI 10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |
| **Version check** | [`ARTIFACT_VERSION`](ARTIFACT_VERSION) · [`releases/1.0.0/release_manifest.json`](releases/1.0.0/release_manifest.json) |
| **Companion paper** | ACM TOSEM — witness-aware layered evaluation (this artifact calibrates the study) |
| **Future development** | [GitHub `main`](https://github.com/cesar-andress/fsmreasonbench) — **not** the v1.0.0 snapshot ([details](docs/artifact/FROZEN_VS_DEVELOPMENT.md)) |

---

## What is FSMReasonBench?

A **frozen evaluation artifact** for verifier-gated formal reasoning on finite-state tasks.
It measures **machine-verifiable witnesses** (not boolean verdicts alone) with separate endpoints for
extractability, verdict accuracy, witness validity, full correctness, pipeline-stage failures, and a
**verdict–witness gap**.

**v1.0.0** covers families **C2** (reachability) and **F1** (equivalence/separation) on cohort
**`v0.1-expanded-n100`** ($n{=}100$ per cell, $T{=}0.2$).

---

## What does this repository contain?

| Layer | Path |
|-------|------|
| **Reviewer entry** | [`REVIEWER.md`](REVIEWER.md), [`docs/REVIEWER.md`](docs/REVIEWER.md) |
| **Documentation hub** | [`docs/README.md`](docs/README.md) |
| **Normative spec** | [`docs/specification/`](docs/specification/) |
| **Frozen cohort** | [`cohorts/v0.1-expanded-n100/`](cohorts/v0.1-expanded-n100/) |
| **Engine** | [`src/fsmreasonbench/`](src/fsmreasonbench/) |
| **Frozen runs** | [`runs/`](runs/) (in Zenodo tarball) |
| **Paper exports** | [`docs/tosem_empirical_package_v1/`](docs/tosem_empirical_package_v1/), [`docs/a1_constructible_equivalence_v1/`](docs/a1_constructible_equivalence_v1/) |
| **Reproduction script** | [`scripts/reproduce_tosem_tables.sh`](scripts/reproduce_tosem_tables.sh) |

Layout reference: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md).

---

## How does it relate to the paper?

The TOSEM manuscript specifies **witness-aware layered evaluation** (reporting protocol). **FSMReasonBench
v1.0.0** is the **calibration instrument** — frozen runs and export pipelines for the empirical study.

| Need | Location |
|------|----------|
| Manuscript (monorepo checkout) | [`../paper/`](../paper/) |
| Authoritative freeze index | [`../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../paper/EXPERIMENTAL_FREEZE_TOSEM.md) |
| Artifact-side freeze mirror | [`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md) |
| TOSEM artifact overview | [`docs/tosem/README.md`](docs/tosem/README.md) |

Zenodo-only trees may omit `paper/`; export manifests under `docs/` suffice to audit reported rates.

---

## Reproduce the paper (reviewer path)

```bash
cat ARTIFACT_VERSION    # confirm v1.0.0 + DOI
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

**Outputs:** `docs/tosem_empirical_package_v1/package_manifest.json` (+ `../paper/tables/` when present).  
**Details:** [`docs/tosem/REPRODUCTION.md`](docs/tosem/REPRODUCTION.md) · **Tarball:** [`README-RELEASE.md`](README-RELEASE.md)

Re-running live model campaigns is **optional** and requires API keys — not needed to verify published
tables. See [`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](docs/EXPERIMENTAL_FREEZE_TOSEM.md).

---

## Frozen v1.0.0 vs. GitHub `main`

| Surface | Reproduce paper numbers? |
|---------|-------------------------|
| **Zenodo DOI** | **Yes** — archival deposit |
| **GitHub release `v1.0.0`** | **Yes** — tag-aligned mirror |
| **GitHub `main`** | **No** — post-freeze development |

→ [`docs/artifact/FROZEN_VS_DEVELOPMENT.md`](docs/artifact/FROZEN_VS_DEVELOPMENT.md)

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

Or [`CITATION.cff`](CITATION.cff).

---

## License

Apache License 2.0 — [`LICENSE`](LICENSE).

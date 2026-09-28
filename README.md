# FSMReasonBench: Witness-Aware Evaluation for Verifier-Gated Reasoning Systems

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20836347.svg)](https://doi.org/10.5281/zenodo.20836347)
[![Release](https://img.shields.io/badge/release-v2.0.0-blue)](https://github.com/cesar-andress/fsmreasonbench)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

Verifier-gated reasoning benchmark and evaluation framework with layered verdict,
witness, and full-correctness metrics.

| | |
|--|--|
| **Software (concept / all versions)** | [DOI 10.5281/zenodo.20836347](https://doi.org/10.5281/zenodo.20836347) |
| **v1.0.0 archival deposit** | [DOI 10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |
| **Active software version** | [`ARTIFACT_VERSION`](ARTIFACT_VERSION) · `2.0.0` (prep; version-specific Zenodo DOI after archival) |
| **Source** | [GitHub](https://github.com/cesar-andress/fsmreasonbench) |

---

## What it measures

FSMReasonBench scores verifier-gated boolean tasks at four independently reported layers:

1. **Extractability** — a schema-valid structured submission can be recovered
2. **Verdict accuracy** — the declared boolean verdict matches gold (among extractable outputs)
3. **Witness validity** — an independent deterministic verifier accepts the witness under a named contract
4. **Full correctness** — extractable + correct verdict + accepted witness

It also records a mutually exclusive **failure stage**, the named **witness contract**, and the
**tool-access condition**. Legacy machine-readable fields may still use the historical
`certificate_*` schema names; protocol prose uses *witness*.

Reported experimental cells are **frozen archived evaluations** (typically one archived generation
per item under the recorded configuration). This release supports offline regeneration of reported
analyses from archived outputs. It does **not** create repeated-generation experiments or estimate
long-run stochastic model performance.

---

## Repository contents

| Layer | Path |
|-------|------|
| Documentation hub | [`docs/README.md`](docs/README.md) |
| Normative / protocol docs | [`docs/specification/`](docs/specification/) |
| Frozen cohort | [`cohorts/v0.1-expanded-n100/`](cohorts/v0.1-expanded-n100/) |
| Engine (generator, verifier, runners, exports) | [`src/fsmreasonbench/`](src/fsmreasonbench/) |
| Frozen run trees | [`runs/`](runs/) (included in archival deposits) |
| Layered analysis exports | [`docs/tosem_empirical_package_v1/`](docs/tosem_empirical_package_v1/), [`docs/a1_constructible_equivalence_v1/`](docs/a1_constructible_equivalence_v1/) |
| Offline table regeneration | [`scripts/reproduce_archived_tables.sh`](scripts/reproduce_archived_tables.sh) |

Layout: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md).

Historical path names such as `tosem_*` / `tmlr_*` are **legacy identifiers** retained so frozen
regeneration commands stay stable; they do not name a current journal submission.

---

## Reproduce archived analyses

Offline only (no model APIs):

```bash
cat ARTIFACT_VERSION
pip install -e ".[dev,plot]"
./scripts/reproduce_archived_tables.sh
```

Optional health check:

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
```

Re-running live model campaigns is optional, requires external APIs, and is **not** required to
verify archived layered metrics.

---

## Verification contracts

Deterministic verifiers check named witness contracts (for example replay-based reachability and
equivalence/separation obligations). Contract definitions, schemas, and scoring live under
`src/fsmreasonbench/` and `schema/`. See [`docs/zenodo/REPRODUCIBILITY.md`](docs/zenodo/REPRODUCIBILITY.md).

---

## Data / archived outputs

Primary calibration cohort: **`v0.1-expanded-n100`** (families C2 and F1, \(n{=}100\) per primary cell,
temperature \(0.2\)). Archived responses, scores, and rollups under `runs/` support offline analysis
regeneration. Redistribution of third-party model outputs follows the repository license and any
provider terms noted in the documentation; contact the maintainer if a redistribution question is
unclear.

---

## Citation

Until the v2.0.0 version-specific Zenodo DOI is minted, cite the **concept DOI** (all versions):

```bibtex
@software{fsmreasonbench,
  author  = {Andr{\'e}s, C{\'e}sar},
  title   = {{FSMReasonBench}: Witness-Aware Evaluation for Verifier-Gated Reasoning Systems},
  year    = {2026},
  version = {2.0.0},
  doi     = {10.5281/zenodo.20836347},
  url     = {https://doi.org/10.5281/zenodo.20836347},
  note    = {Concept DOI. Version-specific DOI for v2.0.0 will be added after archival.}
}
```

The frozen v1.0.0 deposit remains citable at [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937).
See also [`CITATION.cff`](CITATION.cff).

---

## License

Apache License 2.0 — [`LICENSE`](LICENSE).

---

## AI-assisted development

AI-assisted coding tools were used during parts of software development. Research design decisions,
repository integration, testing, verification, reported analyses, and release approval remained under
the author's responsibility. Historical commits may include `Co-authored-by: Cursor` trailers; that
history is retained. Further notes: [`docs/clean_v2/AI_ASSISTED_PROVENANCE.md`](docs/clean_v2/AI_ASSISTED_PROVENANCE.md).

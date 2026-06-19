# FSMReasonBench

**Evaluating Reasoning over Executable Finite-State Machines**

This repository is the **canonical Zenodo artifact** for FSMReasonBench — not merely a
GitHub source tree. The citable object will be:

> **FSMReasonBench v1.0.0 (Zenodo DOI)**

Git `main` is for development. **Cite the Zenodo DOI**, not the git URL.

Companion paper (separate): `../paper/`

---

## Artifact philosophy

| Priority | Principle |
|----------|-----------|
| 1 | Normative benchmark specification |
| 2 | Reproducibility from tarball alone |
| 3 | Long-term archival value (≥ 5 years) |
| 4 | Implementation convenience |

Read [`docs/artifact/artifact_philosophy.md`](docs/artifact/artifact_philosophy.md) first.

---

## Zenodo release model

Every release pins **four version axes**:

| Axis | Example |
|------|---------|
| `benchmark_version` | `1.0.0` |
| `cohort_version` | `1.0-public` |
| `schema_version` | `1.0.0` |
| `verifier_version` | `1.0.0` |

Manifest: `releases/<benchmark_version>/release_manifest.json`

**Quickstart (tarball users):** [`README-RELEASE.md`](README-RELEASE.md)

---

## Benchmark spine (v2)

### Flagship families (≥ 85% of cohort)

| ID | Family |
|----|--------|
| F1 | Separation / Witness |
| F2 | Non-materialized Composition |
| F3 | Constructive Synthesis |
| F4 | Formalization Fidelity |

### Calibration (≤ 15%, non-headline)

C1 trace/membership · C2 basic reachability

---

## Repository layers

```
docs/specification/     ← normative benchmark spec
docs/artifact/          ← release, reproducibility, archival policies
spec/                   ← declarative generator/oracle parameters
schema/                 ← JSON Schema contracts (schema_version)
cohorts/                ← frozen manifests (data in Zenodo tarball)
src/fsmreasonbench/
  generator/            ← implementation (generator_version)
  verifier/             ← implementation (verifier_version) — required for DOI
  cohort/               ← integrity validation
  evaluator/            ← scoring harness
releases/               ← per-version manifests
scripts/                ← offline reproduction scripts
paper_reproduction/     ← archived submissions (supplement, not manuscript)
```

**Not in this repo:** paper prose (`../paper/`).

Layout detail: [`docs/artifact/repository_layout.md`](docs/artifact/repository_layout.md)

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [`docs/specification/BENCHMARK_SPEC.md`](docs/specification/BENCHMARK_SPEC.md) | Normative benchmark definition |
| [`docs/artifact/release_policy.md`](docs/artifact/release_policy.md) | Zenodo deposit structure |
| [`docs/artifact/reproducibility_policy.md`](docs/artifact/reproducibility_policy.md) | R1–R4 reproduction tiers |
| [`docs/artifact/contamination_policy.md`](docs/artifact/contamination_policy.md) | Leakage controls |
| [`docs/artifact/archival_policy.md`](docs/artifact/archival_policy.md) | 5-year usability |
| [`docs/versioning_policy.md`](docs/versioning_policy.md) | Four-axis version rules |
| [`docs/artifact/github_vs_zenodo.md`](docs/artifact/github_vs_zenodo.md) | Design review |
| [`docs/artifact/zenodo_checklist.md`](docs/artifact/zenodo_checklist.md) | Pre-upload gate |

---

## Evaluation tracks

| Track | Name |
|-------|------|
| R0 | Pure reasoning |
| R1 | Tool-augmented |
| R2 | Solver delegation |

Results = **capability surfaces**, not a single leaderboard score.

---

## Current status

| Component | Status |
|-----------|--------|
| Zenodo-first architecture docs | ✅ |
| v2 spec (F1–F4, C1–C2) | ✅ draft |
| Release manifest template | ✅ |
| Verifier | ⬜ **blocks v1.0.0 DOI** |
| Generator | ⬜ not started |
| Cohort 1.0-public | ⬜ not frozen |
| LICENSE / DOI in CITATION.cff | ⬜ placeholder |

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## Artifact health

Quick sanity check before release prep or after cloning:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health --json
```

Verifies package import, required schemas, reference example self-verification, and core CLI imports. Exits non-zero on failure.

---

## Citation

Use `CITATION.cff` after DOI minting. Until then, do not cite `-draft` specifications.

---

## License

TBD before Zenodo — see [`LICENSE`](LICENSE) and PROJECT_STATUS U10.

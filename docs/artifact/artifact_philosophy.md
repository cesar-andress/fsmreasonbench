# FSMReasonBench — Artifact Philosophy

**Status:** normative (artifact governance)  
**Applies to:** all Zenodo releases of this repository

---

## 1. What this repository is

The directory `fsmreasonbench/` is **not** a conventional application source repository.
It is the **canonical research artifact** that will be archived, versioned, cited, and
evaluated on Zenodo as:

> **FSMReasonBench vX.Y.Z** (Zenodo DOI)

The GitHub (or other VCS) mirror is a **development surface**. The **Zenodo release
tarball** is the **source of truth** for scientific reproduction.

---

## 2. Design priorities (ordered)

1. **Normative specification** — What the benchmark *is* must survive longer than any implementation.
2. **Reproducibility** — A researcher with only the Zenodo deposit can validate, verify, and reproduce declared results.
3. **Archival stability** — Releases remain usable and citable for ≥ 5 years without unpublished dependencies.
4. **Implementation** — Code serves the spec and release manifest; convenience never overrides (1–3).

---

## 3. What belongs in the artifact

| Layer | Location | Role |
|-------|----------|------|
| **Benchmark specification** | `docs/specification/` | Normative definitions (families, certificates, scoring) |
| **Artifact governance** | `docs/artifact/` | Release, versioning, reproducibility, contamination, archival policies |
| **Generator specification** | `spec/generator/`, `spec/oracle/` | Declarative parameters and oracle bindings (not code) |
| **JSON Schema** | `schema/` | Machine-readable contracts, version-pinned |
| **Generator implementation** | `src/fsmreasonbench/generator/` | Regenerates population from spec + seed |
| **Verifier implementation** | `src/fsmreasonbench/verifier/` | Independent certificate checking |
| **Cohort tooling** | `src/fsmreasonbench/cohort/` | Manifest validation, integrity checks |
| **Evaluation harness** | `src/fsmreasonbench/evaluator/` | Submission scoring, capability surfaces |
| **Frozen cohort data** | `cohorts/` (manifests); item JSON in release bundle | Immutable evaluation sets |
| **Release manifests** | `releases/` | Per-version pins linking all layers |

---

## 4. What does NOT belong in the artifact

| Excluded | Where it lives |
|----------|----------------|
| Paper manuscript prose | `../paper/` |
| Paper-specific figures and tables (source) | `../paper/` |
| Experimental results and leaderboard snapshots | Zenodo **results supplement** or paper supplement only |
| Author-internal notes | Outside public artifact |
| Unpinned “latest main” dependencies | Forbidden in release |

Paper tables MUST be reproducible from **published release pins**, not from unpublished branches.

---

## 5. Independence requirements

1. **Verifier ⊥ generator ⊥ oracle** — Verifier MUST NOT import generator or oracle modules.
2. **Spec ⊥ implementation** — Normative text in `docs/specification/` is authoritative; code is conforming or non-conforming.
3. **Evaluatee ⊥ evaluator bundles** — Public cohort excludes answer keys and F4 hidden probes.
4. **Release ⊥ development** — Zenodo tarball content is defined by `releases/<version>/release_manifest.json`, not by git branch HEAD.

---

## 6. Citation model

Researchers MUST cite:

1. The **Zenodo record** (DOI) for the benchmark version used.
2. The **`benchmark_version`** and **`cohort_version`** from the release manifest.
3. Optionally the companion paper when available.

See root `CITATION.cff` (populated at first Zenodo release).

---

## 7. Long-term usability (5-year minimum)

Every Zenodo release MUST ship sufficient material to:

- Validate cohort integrity (manifest + checksums)
- Run the verifier on submissions without network access
- Reproduce benchmark items after embargo lift (seeds + generator spec + pinned generator version)
- Reproduce paper table **generation commands** (not necessarily re-run LLM experiments)

---

## 8. Related documents

- [`release_policy.md`](release_policy.md)
- [`versioning_policy.md`](../versioning_policy.md)
- [`reproducibility_policy.md`](reproducibility_policy.md)
- [`contamination_policy.md`](contamination_policy.md)
- [`archival_policy.md`](archival_policy.md)
- [`repository_layout.md`](repository_layout.md)

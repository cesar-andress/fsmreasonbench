# FSMReasonBench — Repository Layout

**Status:** normative  
**Principle:** Separation of specification, implementation, data, and release packaging

---

## 1. Layer diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  ZENODO RELEASE (source of truth for citation)                  │
│  releases/<benchmark_version>/release_manifest.json             │
└─────────────────────────────────────────────────────────────────┘
         ▲ bundles snapshots from layers below
         │
┌────────┴────────┬──────────────┬──────────────┬────────────────┐
│ SPECIFICATION   │ DECLARATIVE  │ DATA         │ IMPLEMENTATION │
│ docs/spec/      │ spec/        │ cohorts/     │ src/           │
│ docs/artifact/  │ schema/      │ releases/    │ scripts/       │
└─────────────────┴──────────────┴──────────────┴────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  OUT OF REPOSITORY: ../paper/ (manuscript only)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory responsibilities

### 2.1 Benchmark specification (normative)

| Path | Content | Versioned by |
|------|---------|--------------|
| `docs/specification/` | BENCHMARK_SPEC, families, certificates, difficulty, evaluation | `benchmark_version` |
| `docs/artifact/` | Release, reproducibility, contamination, archival policies | `benchmark_version` |
| `docs/versioning_policy.md` | Four-axis version rules | `benchmark_version` |

**Rule:** Changing normative semantics → bump `benchmark_version`.

### 2.2 Declarative generator specification (normative parameters)

| Path | Content | Versioned by |
|------|---------|--------------|
| `spec/generator/` | Family quotas, difficulty ladders, sampling rules | `benchmark_version` + hash in manifest |
| `spec/oracle/` | Oracle procedure registry (declarative) | `benchmark_version` |

**Rule:** This is **not** Python code. It is YAML/JSON consumed by generator implementation.

### 2.3 JSON Schema (contract)

| Path | Content | Versioned by |
|------|---------|--------------|
| `schema/` | FSM, question, answer, certificate, manifest schemas | `schema_version` |
| `schema/VERSION` | Current schema_version string | `schema_version` |

### 2.4 Frozen cohorts (data)

| Path | Content | Versioned by |
|------|---------|--------------|
| `cohorts/<cohort_version>.manifest.json` | Item inventory + SHA-256 | `cohort_version` |
| `cohorts/evaluatee/` | Public items (small fixtures in git; full set in Zenodo only) | `cohort_version` |
| `cohorts/MANIFEST_SPEC.md` | Manifest format normative doc | `benchmark_version` |

**Rule:** Full cohort JSON MUST NOT bloat git; manifests and fixtures only until Zenodo freeze.

### 2.5 Implementation (conforming code)

| Path | Role | Versioned by |
|------|------|--------------|
| `src/fsmreasonbench/generator/` | Regenerates items from `spec/` + seed | `generator_version` |
| `src/fsmreasonbench/verifier/` | Independent certificate verification | `verifier_version` |
| `src/fsmreasonbench/cohort/` | Manifest validation, integrity checks | `verifier_version` or shared |
| `src/fsmreasonbench/evaluator/` | Submission scoring, capability surfaces | `verifier_version` |
| `src/fsmreasonbench/models/` | Shared types (non-normative helpers) | implementation |

**Rule:** Implementation MUST NOT be the only place where semantics are defined.

### 2.6 Evaluation harness (orchestration)

| Path | Role |
|------|------|
| `scripts/validate_cohort_integrity.sh` | R1 integrity |
| `scripts/verify_submission.py` | R2 verification entry point |
| `scripts/reproduce_table.sh` | R4 paper tables |
| `src/cli/` | CLI wrappers |

### 2.7 Release packaging

| Path | Role |
|------|------|
| `releases/README.md` | Release index |
| `releases/<benchmark_version>/` | Per-release manifest, notes, checksum template |
| `CITATION.cff` | Zenodo DOI and preferred citation metadata |
| `LICENSE` | SPDX license (before Zenodo) |

### 2.8 Tests (development + release gate)

| Path | Role |
|------|------|
| `tests/golden/` | Verifier acceptance fixtures (shipped in Zenodo) |
| `tests/unit/`, `tests/property/` | Development tests |

### 2.9 Explicitly excluded from artifact

| Path | Reason |
|------|--------|
| `../paper/` | Manuscript; separate citation |
| `baselines/results/` | Paper outputs; archive in supplement |
| Author notebooks | Not archival |

---

## 3. Dependency direction (normative)

```
docs/specification  →  spec/  →  generator (impl)
docs/specification  →  schema/  →  verifier, evaluator
docs/specification  →  cohorts/  →  cohort tools
verifier  ⊥  generator  ⊥  oracle (impl)
```

---

## 4. Related documents

- [`artifact_philosophy.md`](artifact_philosophy.md)
- [`release_policy.md`](release_policy.md)

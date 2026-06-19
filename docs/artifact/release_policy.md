# FSMReasonBench — Release Policy

**Status:** normative  
**Target platform:** [Zenodo](https://zenodo.org) (first-class)

---

## 1. Release identity

Each public benchmark release is identified by:

```
FSMReasonBench v<benchmark_version>
```

Example: **FSMReasonBench v1.0.0 (Zenodo DOI: 10.5281/zenodo.XXXXXXX)**

The Zenodo record is the **citable object**. Git tags MUST mirror `benchmark_version`
(e.g., `v1.0.0`).

---

## 2. Four independent version axes

Every Zenodo release MUST pin all four axes in `releases/<benchmark_version>/release_manifest.json`:

| Axis | Field | Meaning | Example |
|------|-------|---------|---------|
| **Benchmark** | `benchmark_version` | Normative spec + governance docs | `1.0.0` |
| **Cohort** | `cohort_version` | Frozen item set identifier | `1.0-public` |
| **Schema** | `schema_version` | JSON Schema contract set | `1.0.0` |
| **Verifier** | `verifier_version` | Independent verifier implementation | `1.0.0` |

**Rule:** A paper MUST declare all four pins. Mixing axes across releases invalidates comparison.

Optional fifth pin (when items are regenerated):

| Axis | Field | Meaning |
|------|-------|---------|
| **Generator** | `generator_version` | Item regeneration implementation | `1.0.0` |

---

## 3. Zenodo deposit structure

Each release produces **one primary Zenodo record** with the following files:

```
FSMReasonBench-v1.0.0/
├── SHA256SUMS                          # checksums for all files below
├── release_manifest.json               # version pins + file inventory
├── BENCHMARK_SPEC-v1.0.0.pdf           # rendered normative spec (optional but recommended)
├── spec/                               # snapshot of normative generator/oracle specs
├── schema/                             # version-pinned schemas
├── cohorts/
│   ├── 1.0-public.manifest.json
│   └── evaluatee/                      # public items (no answer keys)
├── evaluator/                          # separate access OR encrypted supplement
│   ├── 1.0-public.answer_keys.jsonl
│   ├── 1.0-public.hidden_probes/       # F4 only
│   └── oracle_metadata.json
├── src/                                # verifier + evaluator + cohort tools (minimal runnable set)
├── scripts/
│   ├── validate_cohort_integrity.sh
│   ├── verify_submission.py
│   └── reproduce_table.sh              # paper table commands (no LLM reruns required)
├── environment/
│   ├── requirements-lock.txt           # pinned Python deps for verifier/evaluator
│   └── CONTAINER.md                    # optional container digest pin
├── CITATION.cff
├── LICENSE
└── README-RELEASE.md                   # quickstart from tarball only
```

### 3.1 Split deposits (recommended for v1.0.0)

| Record | Contents | Access |
|--------|----------|--------|
| **Primary** | evaluatee cohort, spec, schema, verifier, manifest | Public |
| **Evaluator supplement** | answer keys, hidden probes, seeds (post-embargo) | Public after review, or restricted until embargo lift |

Both records cross-reference each other's DOI in metadata.

---

## 4. Release lifecycle

```
draft (main branch)
  → release candidate (git tag v1.0.0-rc.1)
  → frozen manifest + cohort integrity check
  → Zenodo upload + DOI minted
  → immutable (never overwrite Zenodo file for same version)
  → patch only via new version (1.0.1) or new cohort (1.1-public)
```

### 4.1 Pre-release checklist

See [`zenodo_checklist.md`](zenodo_checklist.md).

### 4.2 Immutability

- Published Zenodo files MUST NOT be replaced in place.
- Errata require a new `benchmark_version` patch or documentation supplement with new DOI.
- Cohort manifests are append-only across versions.

---

## 5. Relationship to GitHub

| Concern | GitHub | Zenodo |
|---------|--------|--------|
| Purpose | Development, issues, PRs | Citation, reproduction |
| Source of truth | No | **Yes** |
| “Latest main” | Unstable | **Must not be cited** |
| CI badges | Informational | Not sufficient for AE |

Researchers downloading from GitHub MUST be directed (via README) to cite the Zenodo DOI.

---

## 6. Paper table reproduction

Each release that supports a paper MUST include:

```bash
scripts/reproduce_table.sh --table all
```

The script MUST:

1. Read pinned `release_manifest.json`
2. Validate cohort integrity
3. Regenerate **deterministic** summary tables from bundled evaluator outputs or bundled baseline submission files
4. NOT require unpublished code or live API keys

LLM re-runs are **out of scope** for mandatory reproduction; submission files archived alongside the paper supplement satisfy AE for non-deterministic systems.

---

## 7. Version skew warnings

Implementations MUST emit warnings when:

- `submission.spec_version` ≠ manifest `benchmark_version`
- `submission.cohort_id` ≠ manifest `cohort_version`
- Verifier self-report ≠ manifest `verifier_version`

---

## 8. Related documents

- [`versioning_policy.md`](../versioning_policy.md)
- [`reproducibility_policy.md`](reproducibility_policy.md)
- [`archival_policy.md`](archival_policy.md)
- [`../specification/BENCHMARK_SPEC.md`](../specification/BENCHMARK_SPEC.md)

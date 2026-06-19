# FSMReasonBench — Reproducibility Policy

**Status:** normative  
**Audience:** artifact evaluators, future researchers, paper reviewers

---

## 1. Reproducibility claims

FSMReasonBench supports three reproducibility tiers:

| Tier | Claim | Required material |
|------|-------|-------------------|
| **R1 — Integrity** | Downloaded cohort matches published manifest | `SHA256SUMS`, manifest, validation script |
| **R2 — Verification** | Submissions scored identically to paper | Pinned verifier, submission JSON, evaluator bundle |
| **R3 — Regeneration** | Items reproduced from seed after embargo | Generator spec snapshot, seed, pinned generator |
| **R4 — Tables** | Paper summary tables reproduced | `scripts/reproduce_table.sh`, archived baseline submissions |

**Mandatory for Zenodo v1.0.0:** R1, R2, R4.  
**R3** required after seed embargo lift (documented date in release manifest).

---

## 2. Researcher workflow (Zenodo-only, no GitHub)

A researcher with **only** the Zenodo tarball MUST be able to:

```bash
# 1. Verify tarball integrity
sha256sum -c SHA256SUMS

# 2. Validate cohort integrity
./scripts/validate_cohort_integrity.sh \
  --manifest cohorts/1.0-public.manifest.json \
  --items cohorts/evaluatee/

# 3. Verify a submission (example)
python scripts/verify_submission.py \
  --submission my_submission.json \
  --release release_manifest.json

# 4. Reproduce paper tables (deterministic aggregates)
./scripts/reproduce_table.sh --table all
```

No unpublished code, no `git clone`, no network (after offline install of pinned deps).

---

## 3. Pinned environment

Every release MUST include:

| File | Purpose |
|------|---------|
| `environment/requirements-lock.txt` | Exact Python packages for verifier/evaluator |
| `environment/CONTAINER.md` | Optional OCI image digest |
| `release_manifest.json` | Python version used at release (e.g., `3.12.3`) |

**Rule:** Verifier MUST run on declared Python version ± one minor.

---

## 4. Determinism guarantees

| Process | Deterministic? | Notes |
|---------|----------------|-------|
| Cohort manifest hashes | Yes | Content-addressed |
| Verifier on fixed submission | Yes | Pure functions |
| Evaluator aggregates | Yes | Given fixed submission + keys |
| Generator from spec + seed | Yes | Required after embargo |
| LLM evaluatee responses | No | Archive submission files for AE |

---

## 5. Paper-specific reproduction package

Paper results that depend on LLM outputs MUST ship:

- `paper_reproduction/submissions/` — frozen model outputs used in paper
- `paper_reproduction/manifest.json` — links submission files to cohort items
- `paper_reproduction/table_provenance.json` — maps each table row to script + input files

This material MAY be a **separate Zenodo supplement** linked from primary record.

**Must NOT:** rely on author's local paths or unreleased scripts.

---

## 6. Oracle vs verifier reproduction

| Component | Role in reproduction |
|-----------|---------------------|
| **Verifier** | MUST be in primary tarball; sufficient for scoring |
| **Oracle** | Used at generation time; not required for scoring existing cohort |
| **Generator** | Required only for R3 regeneration claims |

Researchers reproducing **paper scores** need verifier + evaluator bundle, not generator.

---

## 7. Independent reimplementation

The specification in `docs/specification/` MUST be sufficient to reimplement a compatible verifier without reading Python source. Source code is a **reference implementation**, not the spec.

---

## 8. Failure and errata

If a reproducibility defect is found post-release:

1. Document in `releases/<version>/ERRATA.md`
2. Publish patch release (`1.0.1`) with fixed verifier if needed
3. Never silently replace Zenodo files

---

## 9. Related documents

- [`release_policy.md`](release_policy.md)
- [`archival_policy.md`](archival_policy.md)
- [`../specification/evaluation_protocol.md`](../specification/evaluation_protocol.md)

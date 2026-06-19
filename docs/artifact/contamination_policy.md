# FSMReasonBench — Contamination Policy

**Status:** normative  
**Goal:** Keep frozen cohorts scientifically valid for ≥ 5 years

---

## 1. Threat model

| Threat | Mitigation |
|--------|------------|
| Training data memorization | Public fingerprints; holdout option; embargoed seeds |
| Pre-release item leakage | No public dumps before Zenodo DOI |
| Benchmark scraping | Evaluatee bundle separate from keys; ToS in README-RELEASE |
| Version confusion | Four-axis version pins in every submission |
| Hidden probe leakage (F4) | Evaluator-only bundle; never in evaluatee tarball |

---

## 2. Public fingerprint

Every item carries:

```
public_fingerprint = SHA-256(canonical_fsm ‖ canonical_question)
```

Published in:
- Cohort manifest (evaluatee)
- `contamination/fingerprints/<cohort_version>.txt` in Zenodo release

Researchers MAY check corpora for fingerprint intersection (best-effort).

---

## 3. Seed embargo

| Phase | Seed visibility |
|-------|-----------------|
| Pre-Zenodo development | Private |
| Primary Zenodo release | **Embargoed** (evaluator supplement or timed second deposit) |
| Post-embargo date | Public in `embargo/seeds/<cohort_version>/` |

Embargo duration declared in `release_manifest.json`:

```json
{
  "seed_embargo_until": "2027-06-01",
  "seed_embargo_rationale": "Reduce memorization risk during initial evaluation window"
}
```

---

## 4. Holdout cohort (optional)

| Cohort | Purpose | Zenodo |
|--------|---------|--------|
| `1.0-public` | Paper + primary leaderboard | Primary record |
| `1.0-holdout` | Post-publication monitoring | Separate DOI, delayed |

Holdout MUST NOT appear in development repos or CI logs before release.

---

## 5. Development hygiene

Forbidden before cohort freeze:
- Committing full evaluatee JSON at scale to public GitHub
- Publishing item prompts in issue trackers
- Indexing benchmark items in searchable gists

Permitted:
- Hashed fingerprints
- Hand-authored golden fixtures (≤ 20 items, clearly marked `tests/golden/`)

---

## 6. Submission provenance

Evaluation harness SHOULD record:

```json
{
  "model_training_cutoff": "optional",
  "tools_used": [],
  "track": "R0 | R1 | R2"
}
```

Misreported track → invalid for comparative ranking (not offline research ban).

---

## 7. Leakage response

If leakage detected post-release:

1. Document in ERRATA
2. Activate holdout cohort for new comparisons
3. Do NOT mutate frozen `1.0-public` manifest

---

## 8. Related documents

- [`release_policy.md`](release_policy.md)
- [`../specification/evaluation_protocol.md`](../specification/evaluation_protocol.md)

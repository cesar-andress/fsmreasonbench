# Zenodo Release Checklist

**Status:** normative gate checklist  
**Published reference release:** v1.0.0 — DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)

Use this checklist for **future** benchmark versions. v1.0.0 completed publication on 2026-06-20.

---

## A. Version pins

- [ ] `benchmark_version` finalized (SemVer, no `-draft`)
- [ ] `cohort_version` finalized and frozen
- [ ] `schema_version` matches `schema/VERSION`
- [ ] `verifier_version` matches verifier package
- [ ] `generator_version` recorded (if regeneration claimed)
- [ ] `releases/<benchmark_version>/release_manifest.json` complete

---

## B. Normative documentation

- [ ] `docs/specification/BENCHMARK_SPEC.md` matches release (no `-draft`)
- [ ] PDF snapshot generated (recommended)
- [ ] All `docs/artifact/*` policies included in tarball
- [ ] `README-RELEASE.md` written for tarball-only users

---

## C. Data integrity

- [ ] Cohort manifest SHA-256 for every item
- [ ] `SHA256SUMS` covers entire tarball
- [ ] `./scripts/validate_cohort_integrity.sh` passes
- [ ] Flagship ≥ 85%, calibration ≤ 15% verified in manifest
- [ ] `contamination/fingerprints/<cohort>.txt` generated

---

## D. Verifier and evaluator

- [ ] `tests/golden/` passes on pinned Python version
- [ ] Verifier does not import generator/oracle
- [ ] `./scripts/verify_submission.py` works offline
- [ ] Evaluator bundle separated from evaluatee bundle
- [ ] F4 hidden probes only in evaluator bundle

---

## E. Reproducibility

- [ ] `environment/requirements-lock.txt` pinned
- [ ] Python version recorded in manifest
- [ ] `./scripts/reproduce_table.sh` reproduces paper tables from archived submissions
- [ ] `paper_reproduction/` supplement uploaded (if paper exists)

---

## F. Legal and citation

- [ ] `LICENSE` file with SPDX identifier
- [x] `CITATION.cff` with DOI (v1.0.0: `10.5281/zenodo.20897937`)
- [ ] Zenodo metadata: creators, ORCID, keywords, related paper DOI
- [ ] Embargo date for seeds documented in manifest

---

## G. Immutability

- [ ] Git tag `v<benchmark_version>` created
- [ ] Zenodo upload reviewed (no secrets, no dev cohorts)
- [ ] Post-upload: DOI backfilled into CITATION.cff and release_manifest

---

## H. Post-release

- [ ] README on GitHub points to Zenodo DOI as citation target
- [ ] ERRATA.md process documented if needed
- [ ] Holdout cohort DOI planned (if applicable)

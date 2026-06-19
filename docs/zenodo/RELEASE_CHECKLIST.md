# Release checklist

**Status:** pre-release draft  
**Purpose:** gate checklist for a **future** FSMReasonBench Zenodo release

This is a working checklist for maintainers. It does not assign version numbers, create
Zenodo metadata, or freeze any dataset. Complete every section before minting a DOI.

Extended normative gate: [`docs/artifact/zenodo_checklist.md`](../artifact/zenodo_checklist.md).

---

## 1. Freeze cohort

- [ ] Select flagship vs calibration mix (target: flagship ≥ 85%, calibration ≤ 15%)
- [ ] Generate final item set from pinned generator spec + seeds
- [ ] Run `self_verify_item()` on every item (or equivalent batch gate)
- [ ] Split into **evaluatee bundle** (no answer keys) and **evaluator bundle** (keys + hidden material)
- [ ] Record cohort identifier (e.g. `1.0-public`) — assign only at freeze time
- [ ] Confirm no exploratory / pilot items from `runs/` are included
- [ ] Document seed embargo policy if seeds are withheld initially

**Current state:** no frozen cohort exists; development uses on-demand generation.

---

## 2. Generate manifests

- [ ] Create `cohorts/<cohort-id>.manifest.json` with:
  - [ ] Cohort identifier
  - [ ] Item count by family and difficulty stratum
  - [ ] Ordered list of `item_id` values
  - [ ] Per-item file path within bundle
  - [ ] Per-item SHA-256 content hash
- [ ] Create `releases/<benchmark-version>/release_manifest.json` with:
  - [ ] Four version pins (benchmark, cohort, schema, verifier) — assign at release time
  - [ ] File inventory for tarball
  - [ ] Python version and environment reference
  - [ ] Cross-links to evaluator supplement (if split deposit)
- [ ] Generate `contamination/fingerprints/<cohort-id>.txt` from item fingerprints
- [ ] Validate manifest against actual bundle contents

**Current state:** manifest templates described in [`docs/artifact/release_policy.md`](../artifact/release_policy.md); no manifest files committed.

---

## 3. Compute hashes

- [ ] SHA-256 every file in evaluatee bundle; store in cohort manifest
- [ ] SHA-256 every file in evaluator bundle; store in evaluator manifest
- [ ] Generate top-level `SHA256SUMS` for entire release tarball
- [ ] Run integrity validation script (planned: `scripts/validate_cohort_integrity.sh`)
- [ ] Verify `./SHA256SUMS` passes with `sha256sum -c`
- [ ] Record tarball hash in release manifest

**Current state:** per-item `public_fingerprint` exists at generation time; release-level checksums not yet produced.

---

## 4. Export datasheet

- [ ] Write machine-readable dataset description (Datasheet for Datasets format or equivalent)
- [ ] Document:
  - [ ] Motivation and intended use
  - [ ] Composition (families, item counts, difficulty strata)
  - [ ] Collection process (generator spec, seeds, self-verification)
  - [ ] Preprocessing / exclusion criteria
  - [ ] Distribution format and file layout (see [`DATASET_STRUCTURE.md`](DATASET_STRUCTURE.md))
  - [ ] Maintenance and errata process
- [ ] Include datasheet in release tarball
- [ ] Cross-reference datasheet from `README-RELEASE.md`

**Current state:** no datasheet exported; schema and structure documented in this folder and `docs/specification/`.

**Note:** do **not** create Zenodo platform metadata (`.zenodo.json`) until upload time.

---

## 5. Archive release artifacts

- [ ] Assemble tarball per [`docs/artifact/release_policy.md`](../artifact/release_policy.md):
  - [ ] Normative spec snapshot (`docs/specification/`)
  - [ ] Pinned JSON schemas (`schema/`)
  - [ ] Verifier + evaluator source (minimal runnable set)
  - [ ] Cohort evaluatee bundle
  - [ ] Scripts: validate integrity, verify submission, reproduce tables
  - [ ] Pinned environment (`environment/requirements-lock.txt`)
  - [ ] `LICENSE`, `CITATION.cff`, `README-RELEASE.md`
- [ ] Render spec PDF (recommended)
- [ ] Run full test suite on pinned Python version
- [ ] Confirm verifier does not import generator/oracle
- [ ] Review tarball for secrets, local paths, and dev-only files
- [ ] Create git tag mirroring benchmark version (at release time)
- [ ] Upload evaluator supplement if using split deposit

**Current state:** development tree on GitHub; `runs/` and exploratory summaries are not release artifacts.

---

## 6. Create DOI release

- [ ] Upload primary tarball to Zenodo (new record — do not overwrite)
- [ ] Fill Zenodo metadata at upload time (creators, ORCID, keywords, license, related paper)
- [ ] Mint DOI
- [ ] Backfill DOI into `CITATION.cff` and `release_manifest.json`
- [ ] Upload evaluator supplement record if applicable; cross-link DOIs
- [ ] Update GitHub `README.md` to cite Zenodo DOI as canonical source
- [ ] Publish `ERRATA.md` process for post-release defects
- [ ] Verify offline reproduction workflow from tarball alone (see [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md))

**Current state:** no Zenodo record, no DOI, no assigned benchmark version.

---

## Pre-upload sanity checks

- [ ] Implemented families documented: **C2**, **F1**
- [ ] Four scoring layers reported separately in evaluator outputs
- [ ] No final model results or paper claims embedded in release docs
- [ ] Exploratory pilot summaries (`docs/pilot_v0_*`, `docs/pilot_v1_*`) excluded from tarball or clearly marked non-normative
- [ ] All items pass self-verification
- [ ] Re-scoring transcripts is deterministic for bundled examples

---

## Explicit non-goals (until release gate passes)

| Item | Status |
|------|--------|
| Zenodo `.zenodo.json` / platform metadata file | Not created |
| Assigned `benchmark_version` / `cohort_version` | Not assigned |
| Frozen dataset on Zenodo | Not frozen |
| Paper table reproduction from archived cohort | Not available |

---

## Related documents

| Document | Path |
|----------|------|
| Release policy | [`docs/artifact/release_policy.md`](../artifact/release_policy.md) |
| Reproducibility policy | [`docs/artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md) |
| Archival policy | [`docs/artifact/archival_policy.md`](../artifact/archival_policy.md) |
| Dataset structure | [`DATASET_STRUCTURE.md`](DATASET_STRUCTURE.md) |
| Reproducibility (implementation) | [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) |

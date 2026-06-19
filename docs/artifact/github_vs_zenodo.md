# GitHub-Convenient vs Zenodo-Appropriate — Design Review

**Status:** advisory (artifact governance)  
**Purpose:** Identify choices acceptable for development but **inappropriate** for a citable 5-year artifact

---

## 1. Currently acceptable for GitHub, inappropriate for Zenodo

| # | GitHub pattern | Zenodo problem | Required fix before DOI |
|---|----------------|----------------|-------------------------|
| G1 | Spec labeled `2.0.0-draft` | Non-citable, unstable | Normalize to `1.0.0` at release; PDF snapshot |
| G2 | Full cohort in git or LFS | Bit rot, clone size, no checksum discipline | Cohort in tarball + SHA256SUMS only |
| G3 | README as sole entry point | Insufficient for AE | `README-RELEASE.md` + release_manifest |
| G4 | "Clone and pip install -e ." | Unpinned deps | `requirements-lock.txt` in release |
| G5 | CI green badge as reproducibility | CI not archived | Golden tests + scripts in tarball |
| G6 | Schemas without `schema_version` pin | Contract drift | `schema/VERSION` + manifest pin |
| G7 | Verifier not yet implemented | Cannot score | Verifier required for v1.0.0 DOI |
| G8 | T1–T7 references in JSON schemas | Spec/code skew | Align schemas to F1–F4 (M1) |
| G9 | Paper tables from local scripts | Unpublished dependency | `reproduce_table.sh` + archived submissions |
| G10 | Single bundle with answer keys | Contamination, misuse | Split evaluatee / evaluator deposits |
| G11 | `-draft` in `__init__.py` version | Ambiguous citation | Match release_manifest semver |
| G12 | External wiki/docs site (if planned) | Link rot | Normative docs in tarball |
| G13 | Oracle and verifier same module | Independence violation | Enforced directory split |
| G14 | Implicit "latest main" in docs | Version ambiguity | All docs reference release pins |
| G15 | No CITATION.cff / LICENSE | Cannot cite properly | Both required pre-upload |

---

## 2. Design choices already Zenodo-appropriate

| Choice | Rationale |
|--------|-----------|
| F1–F4 certificate-first flagship | Witnesses survive tool progress |
| Four-axis version model | Precise citation |
| Independent verifier requirement | Reimplementation possible |
| Manifest + content hashes | Integrity without trust |
| Seed embargo policy | Contamination control |
| Capability surfaces not scalar leaderboard | Scientific longevity |
| Paper in separate repo | Clean artifact boundary |

---

## 3. Risk: over-reliance on Python reference implementation

**Problem:** If semantics live only in Python, the artifact dies when dependencies break.

**Mitigation (required):**
- Normative spec in `docs/specification/` sufficient for reimplementation
- JSON Schema for all exchanged objects
- Golden fixtures with expected verifier outputs

---

## 4. Risk: F4 hidden probes as sole scoring path

**Problem:** Probes in evaluator bundle only → correct, but reproduction requires evaluator supplement DOI.

**Mitigation:** Dual DOI linking in Zenodo metadata; `reproduce_table.sh` documents both downloads.

---

## 5. Risk: LLM non-determinism blocks AE

**Problem:** Cannot rerun GPT-4 identically in 5 years.

**Mitigation:** Archive submission JSON used in paper (`paper_reproduction/` supplement); scripts reproduce **aggregates**, not model calls.

---

## 6. Action items before `FSMReasonBench v1.0.0 (Zenodo DOI)`

1. Implement verifier + golden tests (G7)
2. Align schemas to F1–F4 (G8)
3. Create release manifest template + SHA256SUMS workflow (G2, G3)
4. Pin environment (G4)
5. Choose license + CITATION.cff (G15)
6. Split evaluatee/evaluator bundles (G10)
7. Normalize benchmark_version to 1.0.0 at freeze (G1)

---

## 7. Related documents

- [`archival_policy.md`](archival_policy.md)
- [`release_policy.md`](release_policy.md)
- [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md)

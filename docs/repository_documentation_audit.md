# Repository Documentation Synchronization Audit

**Generated:** 2026-06-20  
**Repository:** `fsmreasonbench/`  
**Published artifact:** FSMReasonBench v1.0.0 — DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937)  
**Author identity:** César Andrés (ORCID `0009-0001-8968-3404`) per `~/papers/promts/author_identity_standardization.md`

---

## Summary

Documentation was synchronized to reflect the **published Zenodo v1.0.0 release**, the paper cohort
`v0.1-expanded-n100`, and offline reproducibility assets. Obsolete pre-release status tables,
placeholder license/DOI language, and roadmap-style `PROJECT_STATUS.md` content were replaced with
current-state descriptions.

**Canonical DOI location:** [`README.md`](../README.md) (single primary citation block). Other
files link to the DOI where context requires (release manifest, cohort READMEs, Zenodo docs) without
repeating full availability prose.

---

## Files modified

| File | Change |
|------|--------|
| `README.md` | Full rewrite: what / problem / v1.0.0 contents / DOI / reproduction |
| `PROJECT_STATUS.md` | Converted to current-state document (released components, assets, future work) |
| `CITATION.cff` | Added `date-released`; verified author, DOI, URL, version, license |
| `LICENSE` | Replaced TBD placeholder with Apache-2.0 notice |
| `pyproject.toml` | `license = Apache-2.0` |
| `README-RELEASE.md` | Published DOI, cohort paths, offline export commands |
| `releases/README.md` | v1.0.0 published index with DOI |
| `releases/1.0.0/release_manifest.json` | **Created** — version pins + DOI |
| `releases/1.0.0/RELEASE_NOTES.md` | **Created** — release summary |
| `cohorts/README.md` | Paper cohort + DOI; future `1.0-public` as design target |
| `cohorts/v0.1-expanded-n100/README.md` | v1.0.0 paper cohort context |
| `docs/zenodo/README.md` | Published status (was pre-release draft) |
| `docs/zenodo/REPRODUCIBILITY.md` | Header + citable scope updated |
| `docs/zenodo/RELEASE_CHECKLIST.md` | Marked v1.0.0 completed reference |
| `docs/zenodo/DATASET_STRUCTURE.md` | Published header |
| `docs/dataset_card.md` | Version, cohort tiers, citation section |
| `docs/specification/BENCHMARK_SPEC.md` | Published status header |
| `docs/specification/evaluation_protocol.md` | Published status header |
| `docs/specification/certificate_formats.md` | Published status header |
| `docs/specification/task_families.md` | Published status header |
| `docs/specification/difficulty_model.md` | Published status header |
| `docs/tmlr_empirical_package_v1/README.md` | Published context; impersonal non-claims |
| `docs/releases/v0.1-exploratory.md` | Historical milestone banner (superseded for citation) |
| `docs/release_v1_0_0_zenodo_audit.md` | Supersession notice at top |
| `docs/artifact/repository_layout.md` | CITATION.cff description |
| `docs/artifact/zenodo_checklist.md` | v1.0.0 reference; DOI item checked |
| `docs/artifact/github_vs_zenodo.md` | G7 verifier row updated |
| `paper_reproduction/README.md` | v1.0.0 + export commands (was empty placeholder) |

**Not present:** `CONTRIBUTING.md` (no file in repository).

---

## Obsolete statements removed (representative)

| Former wording | Location | Replacement |
|----------------|----------|-------------|
| “not published” / ⬜ Zenodo status | `README.md` status table | Published v1.0.0 + DOI |
| “TBD before Zenodo” license | `README.md`, `LICENSE` | Apache-2.0 |
| “Use CITATION.cff after DOI minting” | `README.md` | Direct DOI + `CITATION.cff` |
| “Not a Zenodo release” (project-wide) | `PROJECT_STATUS.md` opener | Published release header |
| Roadmap phases as primary narrative | `PROJECT_STATUS.md` | Released components + future work |
| “No release yet” | `releases/README.md` | v1.0.0 row with DOI |
| “Zenodo DOI not yet deposited” | `cohorts/README.md` | DOI + paper cohort |
| “pre-release draft” (Zenodo folder) | `docs/zenodo/README.md` | Published release status |
| “not yet released as citable dataset” | `docs/dataset_card.md` | Cite Zenodo DOI |
| “Not populated during specification phase” | `paper_reproduction/README.md` | v1.0.0 reproduction pointers |

**Retained intentionally:** `docs/releases/v0.1-exploratory.md` still states “This is not a Zenodo release” for the **historical exploratory tier** (accurate; banner adds v1.0.0 supersession).

---

## DOI updates

| Check | Result |
|-------|--------|
| Canonical citation block | `README.md` (1 primary block) |
| `CITATION.cff` | `doi`, `url`, `date-released: 2026-06-20` |
| Release manifest | `releases/1.0.0/release_manifest.json` |
| DOI occurrences in `.md`/`.cff` (excluding historical audit body) | 20 files — each contextual (release/cohort/doc pointer), not duplicated availability paragraphs |
| Removed “planned DOI / minting / TBD” from active docs | ✅ |

---

## Status corrections

| Area | Before | After |
|------|--------|-------|
| Public release | “not published” | v1.0.0 on Zenodo |
| Paper cohort | “internal / not public” (in places) | `v0.1-expanded-n100` in v1.0.0 release |
| License | TBD placeholder | Apache-2.0 |
| Empirical package | “submission prep” tone | Published paper-support artifact |
| `PROJECT_STATUS.md` | Implementation roadmap | Released components inventory |
| Release manifest | Missing | `releases/1.0.0/` added |

---

## Author identity consistency

| Field | Value used |
|-------|------------|
| Display / CFF | César Andrés |
| ORCID | `0009-0001-8968-3404` |
| LICENSE copyright | César Andrés |
| No `Sánchez` variants introduced | ✅ |

---

## Remaining manual-review items

| Item | Notes |
|------|-------|
| `pyproject.toml` `version = "0.2.0-dev"` | Package dev version ≠ release label `1.0.0`; align at next packaging pass if desired |
| `docs/release_v1_0_0_zenodo_audit.md` body | Historical pre-release findings retained below supersession banner |
| `scripts/reproduce_table.sh` | Still a stub; README-RELEASE points to `export_tmlr_empirical_package` instead |
| Root `SHA256SUMS` | Not in git; may exist only on Zenodo tarball |
| `runs/` gitignored | Frozen runs documented; tarball must include them for full offline replay |
| `CONTRIBUTING.md` | Absent — add if venue requires contribution guidelines |
| Spec family tables (`task_families.md`) | “not yet” rows for F1.b/F2+ remain accurate for unimplemented subtypes |
| `tests/golden/README.md` | “not yet populated” — fixture backlog, not release status |
| `schema/README.md` | JSON schema files “not yet created” for some manifest types |
| Hash decomposition docs | `C1_EMPTY_OR_PLACEHOLDER` category name — analysis taxonomy, not doc placeholder |

---

## Final validation search (repository-wide)

Search patterns: `placeholder`, `TODO`, `not published`, `release candidate`, `RC`, `draft artifact`, `future release`, `coming soon` (excluding `.json` data).

### Intentional / non-actionable remaining hits

| Pattern | Files | Reason |
|---------|-------|--------|
| `placeholder` | `docs/equivalence_hash_mismatch_decomposition.md`, `docs/tmlr_empirical_package_v1/addendum_*` | Failure category `C1_EMPTY_OR_PLACEHOLDER` and hash analysis prose |
| `placeholder` | `docs/frontier_provider_backends.md` (per pre-release audit) | Ellipsis env-var examples |
| `release candidate` / `RC` | `docs/versioning_policy.md`, `docs/artifact/release_policy.md` | Versioning policy for **future** releases |
| `not a Zenodo release` | `docs/releases/v0.1-exploratory.md` | Accurate for exploratory tier only |
| `not yet` | `docs/specification/task_families.md`, `schema/README.md`, `tests/golden/README.md` | Unimplemented subtypes / schemas / fixtures |
| `future release` | `docs/zenodo/DATASET_STRUCTURE.md` (section heading) | Future cohort packaging tier |
| `minting` | `docs/zenodo/REPRODUCIBILITY.md` (exploratory freeze section) | Describes exploratory freeze without DOI — still valid |
| Pre-release audit text | `docs/release_v1_0_0_zenodo_audit.md` | Historical record (banner added) |

### No remaining hits in

`README.md`, `PROJECT_STATUS.md`, `CITATION.cff`, `LICENSE`, `releases/1.0.0/`, `cohorts/v0.1-expanded-n100/README.md`, `docs/zenodo/README.md`, `docs/tmlr_empirical_package_v1/README.md`, `paper_reproduction/README.md` (active status sections).

### `TODO` in tracked files

No `TODO` markers in synchronized markdown front-matter files. (`LICENSE` no longer contains TODO.)

---

## Goal assessment

The repository front matter (`README`, `PROJECT_STATUS`, release manifest, cohort docs, Zenodo
folder, citation metadata) now presents FSMReasonBench as a **finished, citable, published research
artifact**. Deep historical and analysis documents retain domain-specific vocabulary (e.g. hash
placeholder categories) without implying the release is unpublished.

---

## Suggested commit message

```
docs: synchronize repository documentation with Zenodo v1.0.0 release
```

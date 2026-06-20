# Publication Readiness Report

Repository root: `fsmreasonbench`

## Repository status

* **Implemented task families:** C2, F1
* **Frozen cohorts:** 0
* **Exploratory cohorts:** 2
* **Dataset card (`docs/dataset_card.md`):** present
* **Release notes (`docs/releases/`):** present
* **Zenodo preparation docs:** present

## Frozen cohorts

| cohort_id | item_count | cohort_fingerprint | validation_status |
|-----------|------------|--------------------|-------------------|
| `c2-reachability-level3-v0.1-exploratory` | 20 | `77d3bfa104266396d016415527c2cc74eea545bec2bf1295bf0d2ee1c1086230` | PASS |
| `f1-mixed-level3-v0.1-exploratory` | 20 | `4e1e662307456c871ed8c424a4ba493ab041b3d32530feecdef7c19ffe634a67` | PASS |

## Experimental evidence inventory

| path | type | last modified |
|------|------|---------------|
| `../paper/tables/benchmark_families.tex` | paper_table | 2026-06-19T22:39:28Z |
| `../paper/tables/capability_surface_summary.tex` | paper_table | 2026-06-19T22:53:24Z |
| `../paper/tables/f1_mixed_capability_surface_summary.tex` | paper_table | 2026-06-20T07:25:25Z |
| `../paper/tables/f1_mixed_failure_taxonomy.tex` | paper_table | 2026-06-20T07:28:00Z |
| `../paper/tables/pilot_metrics.tex` | paper_table | 2026-06-19T22:39:29Z |
| `../paper/tables/scoring_dimensions.tex` | paper_table | 2026-06-19T22:39:28Z |
| `docs/capability_surface_report.md` | capability_surface_report | 2026-06-19T22:53:24Z |
| `docs/capability_surface_summary.csv` | capability_surface_summary_csv | 2026-06-19T22:53:24Z |
| `docs/f1_mixed_capability_surface_report.md` | f1_mixed_report | 2026-06-20T06:56:53Z |
| `docs/f1_mixed_capability_surface_summary.csv` | f1_mixed_summary_csv | 2026-06-20T06:56:53Z |
| `docs/f1_mixed_failure_taxonomy_report.md` | f1_mixed_report | 2026-06-20T07:08:59Z |
| `docs/pilot_v0_report.md` | pilot_report | 2026-06-19T16:16:25Z |
| `docs/pilot_v0_summary.json` | pilot_summary_json | 2026-06-19T16:16:25Z |
| `docs/pilot_v1_report.md` | pilot_report | 2026-06-19T16:25:35Z |
| `docs/pilot_v1_summary.csv` | pilot_summary_csv | 2026-06-19T16:25:35Z |
| `docs/pilot_v1_summary.json` | pilot_summary_json | 2026-06-19T16:25:35Z |

## Reproducibility checklist

* **manifest.json present:** PASS — manifest.json present in all 2 cohort snapshot directories
* **sha256sums.txt present:** PASS — sha256sums.txt present in all 2 cohort snapshot directories
* **README.md present:** PASS — README.md present in all 2 cohort snapshot directories
* **dataset card present:** PASS — docs/dataset_card.md
* **release notes present:** PASS — docs/releases/*.md
* **reproducibility docs present:** PASS — docs/zenodo/REPRODUCIBILITY.md, docs/zenodo/RELEASE_CHECKLIST.md, docs/zenodo/DATASET_STRUCTURE.md
* **frozen cohort validation passes:** PASS — all discovered cohort manifests pass validate_cohort

## Paper readiness checklist

* **benchmark specification documented:** PASS — docs/specification/BENCHMARK_SPEC.md
* **certificate formats documented:** PASS — docs/specification/certificate_formats.md
* **reproducibility documented:** PASS — docs/zenodo/REPRODUCIBILITY.md
* **exploratory results documented:** PASS — pilot, capability surface, or F1 mixed report present in docs/
* **frozen cohorts available:** PASS — at least one cohort manifest under cohorts/
* **capability surface available:** PASS — docs/capability_surface_report.md
* **failure taxonomy available:** PASS — docs/*failure_taxonomy*report.md
* **dataset card available:** PASS — docs/dataset_card.md

## Open issues

* None detected.

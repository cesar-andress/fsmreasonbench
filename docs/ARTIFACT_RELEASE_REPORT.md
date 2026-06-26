# TOSEM Artifact Release Report

**Artifact:** FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0  
**Zenodo DOI:** 10.5281/zenodo.20897937  
**GitHub release:** FSMReasonBench v1.0.0  
**Release tag:** `FSMReasonBench v1.0.0`  
**Release date:** 2026-06-25 (UTC)  
**Repository:** `fsmreasonbench` (artifact root)  
**Manuscript:** ACM TOSEM companion in [`../paper/`](../paper/) — feature complete, experiments frozen  
**Authoritative freeze:** [`../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../paper/EXPERIMENTAL_FREEZE_TOSEM.md)

---

## 1. Repository status

| Check | Result |
|-------|--------|
| Git branch | `main` |
| Remote | `origin` → `git@github.com-ucjc:cesar-andress/fsmreasonbench.git` |
| Python package | `fsmreasonbench 0.2.0-dev` |
| Cohort snapshots | `v0.1-expanded-n100` (C2 + F1 mixed, n=100, T=0.2) — validated |
| Frozen run trees | Present under `runs/` (gitignored; ship via Zenodo tarball) |
| Zenodo DOI | [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937) |
| `./scripts/reproduce_tosem_tables.sh` | **PASS** (read-only; no API calls) |
| `artifact_health` | **PASS** |
| Full pytest suite | **569 passed** (~9.5 min, Python 3.12) |
| Publication readiness CLI | **PASS** (no open issues) |

**Policy:** No scientific changes during this release pass — only documentation, manifests, reproducibility paths, and cleanup.

---

## 2. Experiment inventory

All campaigns referenced by the TOSEM manuscript export path are present with complete `combined_summary.json` (or cell `summary.json`) rollups.

| Campaign | Run root | Status |
|----------|----------|--------|
| Claude Sonnet 4.5 frontier tools (C2/F1 R1/R2) | `runs/frontier_claude_sonnet_tools_n100_v2/` | **complete** (4/4 cells) |
| GPT-4.1 frontier tools (C2/F1 R1/R2) | `runs/frontier_gpt_tools_n100_v1/` | **complete** (4/4 cells) |
| Local Ollama matrix (4 models × C2/F1 × R0/R1/R2) | `runs/local_matrix_n100_t02_v2/` | **complete** (24/24 cells) |
| Claude F1 attribution ablations (Oracle, R2A/R2B/R2C) | `runs/ablations_f1_r2_attribution_claude_n100_v1/` + Oracle control | **complete** |
| Claude C2 existential/universal ablations | `runs/ablations_c2_existential_universal_claude_n100_v1/` | **complete** (5/5) |
| GPT F1 R2C attribution ablation | `runs/ablations_f1_r2c_gpt_n100_v1/` | **complete** (1/1) |
| Constructible equivalence (A1) — Claude | `runs/f1_constructible_equivalence_claude_n100_v1/` | **complete** |
| Constructible equivalence (A1) — GPT | `runs/f1_constructible_equivalence_gpt_n100_v1/` | **complete** |

**Statistical exports (frozen JSON):**

| Analysis | Path |
|----------|------|
| Bootstrap / McNemar | `docs/tmlr_empirical_package_v1/uncertainty/bootstrap_mcnemar_summary.json` |
| Certificate complexity | `docs/certificate_class_complexity_analysis.json` |
| Constructible equivalence (A1) | `docs/a1_constructible_equivalence_v1/constructible_equivalence_analysis.json` |
| GPT frontier summary | `docs/frontier_gpt_tools_n100_v1_summary.json` |
| Local matrix bootstrap | `docs/local_matrix_n100_t02_bootstrap_summary.json` |

**Excluded (audit only — not cited):** `runs/frontier_claude_sonnet_full_n100_v1/`, `runs/frontier_gemini_*`, superseded n=20 pilots.

**Post-freeze extension campaigns (not run — do not cite):** `*_replicates/`, full GPT attribution ladder, Gemini/DeepSeek pilots. See [`docs/TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](TOSEM_EXPERIMENT_EXTENSION_PLAN.md).

---

## 3. Paper alignment

Manuscript inputs are under `../paper/` (sibling of artifact root). Export CLIs write LaTeX tables and main-text figures there during `./scripts/reproduce_tosem_tables.sh`.

### Main-text tables (22 `\input{tables/...}` in manuscript `.tex`)

| Table | LaTeX | Export / source |
|-------|-------|-----------------|
| Scoring dimensions | `scoring_dimensions.tex` | Hand-maintained protocol table |
| Benchmark families | `benchmark_families.tex` | Hand-maintained |
| Local matrix design | `design_local_matrix_cells.tex` | Hand-maintained |
| Frontier comparison | `frontier_tools_comparison_n100.tex` | `export_tosem_empirical_package` |
| Knowing vs showing gap | `knowing_showing_gap_n100.tex` | `export_tosem_empirical_package` |
| F1 Claude ablations | `f1_claude_ablations.tex` | `export_tmlr_empirical_package` |
| F1 GPT ablations | `f1_gpt_ablations.tex` | `export_tosem_empirical_package` |
| A1 witness table | `extension_constructible_equivalence_witness.tex` | `export_constructible_equivalence_analysis` |
| A1 statistics | `extension_constructible_equivalence_statistics.tex` | `export_constructible_equivalence_analysis` |
| Local matrix summary | `local_matrix_n100_summary.tex` | `export_tosem_empirical_package` |
| Failure stage | `failure_stage_n100.tex` | `export_tosem_empirical_package` |
| Certificate complexity | `certificate_complexity.tex` | `export_tmlr_empirical_package` |
| Resource access | `resource_access_conditions.tex` | Hand-maintained appendix |
| Confound by subtype | `confound_by_subtype.tex` | `export_tmlr_empirical_package` |
| Bootstrap subtypes | `results_bootstrap_subtypes.tex` | `export_tmlr_empirical_package` |
| Paired McNemar | `results_paired_mcnemar.tex` | `export_tosem_empirical_package` |
| Extended McNemar | `appendix_mcnemar_extended.tex` | `export_tmlr_empirical_package` |
| Failure taxonomy | `appendix_failure_taxonomy.tex` | Frozen export / prior campaign reports |
| Oracle ceiling | `oracle_ceiling_summary.tex` | Hand-maintained appendix |
| C2 Claude ablations | `c2_claude_ablations.tex` | `export_tmlr_empirical_package` |
| Verifier audit | `appendix_verifier_audit_full.tex` | Frozen verifier audit export |
| Hash decomposition | `appendix_hash_decomposition.tex` | Frozen hash decomposition export |

**Alignment:** All 22 manuscript `\input{tables/...}` files exist under `../paper/tables/` (27 `.tex` files total; five are extension-only and not cited in the frozen TOSEM main text).

### Main-text figures (4 `\includegraphics{figures/...}`)

| Figure | PDF | Generator |
|--------|-----|-----------|
| Verdict–witness gap | `figure_verdict_witness_gap_comparison.pdf` | `export_tosem_empirical_package` |
| Certificate complexity (frontier) | `figure_certificate_complexity_frontier_comparison.pdf` | `export_tmlr_empirical_package` |
| Attribution fingerprint | `figure_attribution_fingerprint_comparison.pdf` | `export_tosem_empirical_package` |
| Constructible equivalence (A1) | `extension_constructible_equivalence_comparison.pdf` | `export_constructible_equivalence_analysis` |

**Cleanup:** Legacy `figure1_complexity_vs_success.*` removed from `../paper/figures/` (superseded by `figure_certificate_complexity_frontier_comparison.pdf`; retained under `docs/tmlr_empirical_package_v1/figures/` for historical reproduction).

### Package manifest

`docs/tosem_empirical_package_v1/package_manifest.json` records portable relative paths (`../paper/tables/...`, `../paper/figures/...`) for all TOSEM export artifacts.

---

## 4. Reproducibility status

| Tier | Command | Result |
|------|---------|--------|
| 0 | `artifact_health` + export unit tests | **PASS** |
| 1 | `validate_cohort` on frozen snapshots | **PASS** (via CI / manual) |
| 2 | `./scripts/reproduce_tosem_tables.sh` | **PASS** — regenerates tables, figures, manifests from frozen runs |
| 3 | Full pytest (`569` tests) | **PASS** |

**Determinism:** Export CLIs read frozen JSON/JSONL only; matplotlib figures are regenerated from the same source summaries. Item generation seeds are fixed in cohort manifests.

**Runtime (Tier 2):** 2–5 minutes on a typical Linux workstation; **$0 API cost**.

**Hardware:** Any machine with Python ≥ 3.11; no GPU required for reproduction.

---

## 5. Documentation status

| Document | Purpose | Status |
|----------|---------|--------|
| [`README.md`](../README.md) | Installation, quick start, TOSEM reproduction | **Updated** (TOSEM primary) |
| [`README-RELEASE.md`](../README-RELEASE.md) | Zenodo tarball quickstart | **Current** |
| [`docs/tosem/REPRODUCTION.md`](tosem/REPRODUCTION.md) | Full offline workflow, runtime/cost/seeds | **Updated** |
| [`docs/EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) | Artifact mirror of manuscript freeze | **Current** |
| [`docs/tosem_empirical_package_v1/README.md`](tosem_empirical_package_v1/README.md) | TOSEM export manifest | **Current** |
| [`docs/zenodo/REPRODUCIBILITY.md`](zenodo/REPRODUCIBILITY.md) | Zenodo archival policy | **Current** |
| [`docs/historical/README.md`](historical/README.md) | Legacy TMLR / exploratory docs | **Archived** |

Historical TMLR package paths (`docs/tmlr_empirical_package_v1/`) remain for Claude ablation and bootstrap exports; they are **not** the primary venue narrative.

---

## 6. Remaining known limitations

1. **Partial GPT attribution ladder** — only F1 R2C frozen; no GPT Oracle/R2A/R2B.
2. **Open-weight models** — local matrix R0/R1/R2 only; no attribution ablations.
3. **Gemini / DeepSeek excluded** — quota-contaminated or not in scope.
4. **Single temperature** — T=0.2 only in frozen cells.
5. **Post-freeze extensions not run** — replicates and full GPT ladder documented but absent.
6. **Run trees gitignored** — `runs/` must ship in the Zenodo tarball alongside this repository snapshot.

These match the limitations section in [`../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../paper/EXPERIMENTAL_FREEZE_TOSEM.md).

---

## 7. Git commit hashes (release series)

Commits on `main` forming this release (newest first):

| Commit | Summary |
|--------|---------|
| `2c7a4c4` | docs: TOSEM artifact release report, reproduction guide, frozen export refresh |
| `5889c0e` | artifact: portable TOSEM manifest paths; restore `runs/` gitignore |
| `d709107` | evaluator: export paired verdict-witness gap figures for TOSEM |
| `4478ca2` | figures: add frontier certificate complexity comparison |
| `9fc5746` | Add A1 statistical export with bootstrap, McNemar, and artifact docs |
| `93e6732` | docs: document construct-validity experiment |
| `33c60b8` | analysis: export constructible equivalence witness comparisons |

**Release tag:** `FSMReasonBench v1.0.0` (annotated) — frozen TOSEM experiments, manuscript v1.0 artifact bundle, read-only reproduction verified.

---

## 8. Zenodo contents checklist

Include in the archival tarball:

- [ ] Full git snapshot at tag `FSMReasonBench v1.0.0`
- [ ] Frozen `runs/` trees listed in §2
- [ ] `cohorts/v0.1-expanded-n100/`
- [ ] `docs/tosem_empirical_package_v1/` + `docs/tmlr_empirical_package_v1/`
- [ ] `docs/a1_constructible_equivalence_v1/`
- [ ] Companion `paper/` directory (`tables/`, `figures/`, manuscript sources)
- [ ] `SHA256SUMS` / checksum manifest
- [ ] This report: `docs/ARTIFACT_RELEASE_REPORT.md`

---

*Generated as part of the ACM TOSEM artifact freeze pass. Re-run `./scripts/reproduce_tosem_tables.sh` and `artifact_health` after any tarball assembly to confirm bit-exact table regeneration.*

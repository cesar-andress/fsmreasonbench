# Zenodo release preparation — TOSEM companion update

**Status:** preparation notes only — **no DOI minted**, **no upload performed**  
**Base artifact:** **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines** v1.0.0 ([10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937))  
**Companion paper:** ACM TOSEM manuscript in [`../../paper/`](../../paper/)

This document describes what a **follow-on Zenodo deposit** (or v1.0.1 tarball refresh) should
contain to support TOSEM reviewers. It does not supersede the published v1.0.0 record until a
new version is explicitly released.

---

## Release package description (draft)

**Title (working):** FSMReasonBench v1.0.x — artifact supporting witness-aware layered evaluation (ACM TOSEM companion)

**Contents:**

| Layer | Included |
|-------|----------|
| Source code | `src/fsmreasonbench/` — generator, verifier, evaluator, offline exporters |
| Schemas & spec | `schema/`, `docs/specification/`, `spec/` |
| Frozen cohort | `cohorts/v0.1-expanded-n100/` (C2 + F1, n=100 each) |
| Frozen runs | All run roots listed in [`../EXPERIMENTAL_FREEZE_TOSEM.md`](../EXPERIMENTAL_FREEZE_TOSEM.md) |
| Analysis exports | `docs/tosem_empirical_package_v1/`, supporting JSON under `docs/` |
| Reproduction scripts | `scripts/reproduce_tosem_tables.sh`, `scripts/validate_cohort_integrity.sh` |
| Manuscript tables | Optional bundle: `paper/tables/` snapshot or regenerate via scripts |
| Policies | `docs/artifact/`, `docs/zenodo/`, `CITATION.cff`, `LICENSE` |

---

## Environment

| Requirement | Value |
|-------------|-------|
| Python | ≥ 3.11 (3.12 recommended) |
| Install | `pip install -e ".[dev,plot]"` |
| OS tested | Linux x86_64 |
| API keys | **Not required** for table reproduction |

Optional for **new** inference (out of scope for TOSEM freeze):

- `OPENAI_API_KEY` — GPT frontier reruns only
- Anthropic credentials — Claude reruns only
- Ollama — local matrix reruns only

---

## Frozen datasets / cohorts

| Cohort ID | Path | Role |
|-----------|------|------|
| `c2-reachability-level3-v0.1-expanded-n100` | `cohorts/v0.1-expanded-n100/c2-reachability-level3/` | C2 items |
| `f1-mixed-level3-v0.1-expanded-n100` | `cohorts/v0.1-expanded-n100/f1-mixed-level3/` | F1 items |

Manifests include per-item SHA-256 (`manifest.json`, `sha256sums.txt`).

---

## Frozen run paths (TOSEM evidence)

See authoritative list in [`../../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../../paper/EXPERIMENTAL_FREEZE_TOSEM.md).

Summary:

- `runs/frontier_claude_sonnet_tools_n100_v2/` — 4 cells
- `runs/ablations_f1_r2_attribution_claude_n100_v1/` — R2A/B/C
- `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/`
- `runs/ablations_c2_existential_universal_claude_n100_v1/`
- `runs/frontier_gpt_tools_n100_v1/` — 4 cells
- `runs/ablations_f1_r2c_gpt_n100_v1/` — R2C
- `runs/local_matrix_n100_t02_v2/` — 24 cells

---

## Excluded runs (ship for audit, mark DO NOT CITE)

| Path | Reason |
|------|--------|
| `runs/frontier_claude_sonnet_full_n100_v1/` | Provider misclassification |
| `runs/frontier_gemini_*` | Quota contamination |
| Superseded n=20 pilots | Replaced by n=100 freeze |

Include an `EXCLUDED_RUNS.md` pointer in the tarball (this freeze doc satisfies that role).

---

## Checksums / manifest

Existing mechanisms:

- Per-cohort `sha256sums.txt`
- `releases/1.0.0/release_manifest.json` — version pins

**Before next Zenodo upload:**

- [ ] Regenerate tarball-level `SHA256SUMS`
- [ ] Bump `releases/<version>/release_manifest.json` with TOSEM campaign list
- [ ] Record export CLI git commit hash in manifest
- [ ] Verify `./scripts/reproduce_tosem_tables.sh` on clean extract

---

## Limitations (disclose in deposit description)

1. Exploratory-expanded cohort — not a public competition release
2. Single temperature T=0.2
3. GPT attribution partial (R2C only)
4. Open-weight cells: low extractability on some F1 tool tracks
5. TMLR-era export path still required for Claude ablation LaTeX until merged into TOSEM exporter

---

## Citation guidance

- **Benchmark artifact:** Zenodo DOI `10.5281/zenodo.20897937` (v1.0.0) until a new version ships
- **TOSEM paper:** cite the ACM publication when available; until then reference the manuscript preprint path documented by the authors
- **Do not cite** git `main` URLs as the artifact source of truth

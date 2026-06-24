# Paper freeze audit

**Audit date:** 2026-06-20  
**Mode:** PAPER FREEZE — no benchmark logic changes, no experiment reruns.

---

## Checklist

| Item | Status | Evidence |
|------|--------|----------|
| Local matrix frozen | **PASS** | `runs/local_matrix_n100_t02_v2` — 24/24 `completed` in `combined_summary.json` |
| Claude tools frozen | **PASS** | `runs/frontier_claude_sonnet_tools_n100_v2` — 4/4 `completed`, `provider_error_count=0` all cells |
| Canonical doc | **PASS** | `docs/paper_results.md` |
| LaTeX source | **PASS** | `docs/paper_results_latex.md`, `paper/results_frozen.tex`, `paper/tables/*_n100*.tex` |
| Excluded runs documented | **PASS** | `docs/paper_results.md` § Excluded runs |
| Full local metrics in doc | **PASS** | `docs/paper_results.md` § Appendix A (24-cell table) |
| Audit notes | **PASS** | `docs/paper_results.md` § Audit notes |

---

## Frozen artifacts (cite in paper)

| Artifact | Path |
|----------|------|
| Local combined summary | `runs/local_matrix_n100_t02_v2/combined_summary.json` |
| Local report | `runs/local_matrix_n100_t02_v2/report.md` |
| Local plots | `runs/local_matrix_n100_t02_v2/plots/*.png` |
| Claude combined summary | `runs/frontier_claude_sonnet_tools_n100_v2/combined_summary.json` |
| Claude report | `runs/frontier_claude_sonnet_tools_n100_v2/report.md` |
| Committed prose | `docs/paper_results.md`, `docs/paper_local_results.md`, `docs/local_matrix_n100_t02_analysis.md` |
| LaTeX tables | `paper/tables/local_matrix_n100_summary.tex`, `claude_sonnet_tools_n100_summary.tex`, `knowing_showing_gap_n100.tex`, `failure_stage_n100.tex` |
| LaTeX section draft | `paper/results_frozen.tex` |

Run directories are **gitignored**; freeze is defined by on-disk `combined_summary.json` + committed documentation.

---

## Excluded artifacts (audit only)

| Run root | Reason | On disk |
|----------|--------|---------|
| `runs/frontier_claude_sonnet_full_n100_v1` | Anthropic credit exhaustion + rate limits misclassified as benchmark failures | Yes |
| `runs/frontier_gemini_flash_r0_smoke_v1` | Quota contamination | Yes |
| `runs/frontier_gemini_flash_r0_smoke_v2` | Quota contamination | Yes |
| `runs/frontier_gemini_flash_r0_smoke_v3` | Quota contamination | Yes |
| `runs/frontier_gemini_flash_r0_smoke_v4` | Quota contamination | Yes |
| Other `frontier_claude_sonnet_*` n=20 pilots | Superseded by clean n=100 tools run | Yes |

**Do not** cite excluded runs as model performance.

---

## Remaining gaps before manuscript integration

1. **Integrate into `paper/sections/06_results.tex`** — `\input{results_frozen}` or merge prose; replace exploratory-only framing where n=100 frozen evidence is cited.
2. **Bootstrap CIs** — not computed for n=100 frozen cells (`docs/rate_ci_report.md` covers older pilots only).
3. **Zenodo / public cohort** — frozen runs use `v0.1-expanded-n100` cohorts, not `v1.0-public`.
4. **Claude R0 baseline** — tools run covers R1/R2 only; no frozen Claude R0 n=100 cell.
5. **Paper repo git** — `paper/` lives outside `fsmreasonbench/` artifact git; commit LaTeX files in parent repo separately if needed.

---

## Suggested commit message

```
paper freeze: audit n100 results and add LaTeX tables
```

# Experimental freeze — ACM TOSEM (artifact mirror)

**Authoritative copy:** [`../../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../../paper/EXPERIMENTAL_FREEZE_TOSEM.md)

The manuscript freeze document in `paper/` is the single source of truth for campaign lists,
headline numbers, excluded runs, and export paths. This mirror exists so artifact reviewers can
find the freeze without leaving the repository.

**Frozen:** 2026-06-25 · **Venue:** ACM TOSEM · **Cohort:** `v0.1-expanded-n100` (n=100, T=0.2)

---

## Quick reference — frozen campaigns

| Campaign | Run root | Cells |
|----------|----------|------:|
| Claude Sonnet 4.5 tools | `runs/frontier_claude_sonnet_tools_n100_v2/` | 4 |
| Claude F1 attribution | `runs/ablations_f1_r2_attribution_claude_n100_v1/` + Oracle control | 4+1 |
| Claude C2 ablations | `runs/ablations_c2_existential_universal_claude_n100_v1/` | 5 |
| GPT-4.1 tools | `runs/frontier_gpt_tools_n100_v1/` | 4 |
| GPT F1 R2C | `runs/ablations_f1_r2c_gpt_n100_v1/` | 1 |
| Local Ollama matrix | `runs/local_matrix_n100_t02_v2/` | 24 |

**Regenerate tables (read-only):** `./scripts/reproduce_tosem_tables.sh`

**Excluded (audit only):** `runs/frontier_claude_sonnet_full_n100_v1/`, `runs/frontier_gemini_*`,
superseded n=20 pilots — full table in the authoritative freeze doc.

---

## Policy

No new experiments without explicitly reopening the freeze in `paper/EXPERIMENTAL_FREEZE_TOSEM.md`.
Scoring, verifier, cohorts, and frozen run outputs must not be edited for release preparation.

---

## Extension campaigns (post-freeze v1)

Additive studies for external TOSEM review — **see authoritative section** in
[`../../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../../paper/EXPERIMENTAL_FREEZE_TOSEM.md#extension-campaigns-post-freeze-v1).

Plan: [`TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](TOSEM_EXPERIMENT_EXTENSION_PLAN.md)

# Frozen n=100 results — LaTeX preparation source

**PAPER FREEZE · 2026-06-20**

Canonical prose: [`paper_results.md`](paper_results.md)  
LaTeX manuscript: [`../../paper/main.tex`](../../paper/main.tex) (§6–§7 and appendix)  
Tables: [`../../paper/tables/`](../../paper/tables/) (`*_n100*.tex`)

Integrate into the manuscript with:

```latex
\input{results_frozen}
```

---

## Publication prose (English)

### Benchmark design

FSMReasonBench evaluates models on typed finite-state-machine tasks with **layered metrics**: extractability (parseable submission), verdict accuracy (boolean answer among extractable outputs), certificate validity (verifier-accepted witness among extractable outputs), and fully correct (verdict and certificate both pass, $n$ denominator). Tracks R0 (direct), R1 (tool plan without execution), and R2 (tool execution) isolate whether delegation changes verdicts, certificates, or both.

### Evaluation protocol

Each of $n=100$ items per cell is scored independently. Failures decompose into **not extractable**, **verdict wrong**, **certificate invalid**, and **correct** (fully correct). Provider/infrastructure failures (`provider_error`) are excluded from model-quality interpretation. Verdict and certificate rates share the extractable denominator; fully correct uses the full cohort size.

### Frozen campaigns

1. **Local Ollama matrix** — `runs/local_matrix_n100_t02_v2`: four models × C2/F1 × R0/R1/R2 × T=0.2, **24/24 completed**.
2. **Claude Sonnet tools** — `runs/frontier_claude_sonnet_tools_n100_v2`: `claude-sonnet-4-5-20250929`, C2/F1, R1/R2 only, **4/4 completed**, zero provider errors.

Cohorts: `c2-reachability-level3-v0.1-expanded-n100`, `f1-mixed-level3-v0.1-expanded-n100` (exploratory expanded; not `v1.0-public`).

### Local results (summary)

Local open-weight models under R2 often achieve **near-perfect verdict accuracy** while **certificate validity and fully correct remain low** (especially C2 R2: full 5–17%). On F1 R2, many models reach verdict = 1.0 among extractable items but fail certification; **Qwen** is strongest (full = 0.300, cert = 0.455, verdict = 1.000). R1 seldom improves fully correct. Several F1 tool-track cells have extractability <50% (Llama, Mistral) and are unsafe for cross-track comparison.

### Claude Sonnet results (summary)

| Family | Track | Verdict | Cert | Full |
|--------|-------|--------:|-----:|-----:|
| C2 | R1 | 0.970 | 0.950 | 0.950 |
| C2 | R2 | 1.000 | 1.000 | 1.000 |
| F1 | R1 | 1.000 | 0.460 | 0.460 |
| F1 | R2 | 1.000 | 1.000 | 0.990 |

Claude F1 R1 already has perfect verdict but only 46% certification — **planning alone is insufficient**. F1 R2 closes the gap (99% fully correct): **execution converts correct verdicts into verifiable certificates**. This contrasts with local models that stall at high verdict / low cert.

### Knowing–Showing gap

Define **Gap = Verdict − Full** (reported rates). Large gaps under local R2 indicate models *know* the boolean answer without *showing* a valid certificate. Claude F1 R1: Gap = 0.54; Claude F1 R2: Gap = 0.01.

### Exclusions

**Do not cite:**

- `runs/frontier_claude_sonnet_full_n100_v1` — Anthropic credit/rate-limit failures misclassified as benchmark failures.
- Any `runs/frontier_gemini_*` — quota contamination.

**Cite:** `runs/frontier_claude_sonnet_tools_n100_v2` only for frontier tools.

### Limitations

Exploratory cohorts; single frontier model configuration; no bootstrap CIs for n=100 cells; local stack fixed (single GPU Ollama); Claude run excludes R0 baseline at n=100.

---

## Table 1 — Local matrix summary

See [`../../paper/tables/local_matrix_n100_summary.tex`](../../paper/tables/local_matrix_n100_summary.tex) (`\label{tab:local-matrix-n100-summary}`).

24 rows: all models × C2/F1 × R0/R1/R2. Columns: Model, Family, Track, n, Extract., Verdict, Cert., Full.

---

## Table 2 — Claude Sonnet summary

See [`../../paper/tables/claude_sonnet_tools_n100_summary.tex`](../../paper/tables/claude_sonnet_tools_n100_summary.tex) (`\label{tab:claude-sonnet-tools-n100-summary}`).

| Fam | Track | Extract | Verdict | Cert | Full |
|-----|-------|--------:|--------:|-----:|-----:|
| C2 | R1 | 1.000 | 0.970 | 0.950 | 0.950 |
| C2 | R2 | 1.000 | 1.000 | 1.000 | 1.000 |
| F1 | R1 | 1.000 | 1.000 | 0.460 | 0.460 |
| F1 | R2 | 0.990 | 1.000 | 1.000 | 0.990 |

---

## Table 3 — Knowing–Showing gap

See [`../../paper/tables/knowing_showing_gap_n100.tex`](../../paper/tables/knowing_showing_gap_n100.tex) (`\label{tab:knowing-showing-gap-n100}`).

28 rows (24 local + 4 Claude). Columns: Model, Family, Track, Verdict, Certificate, Full, **Gap = Verdict − Full**.

**Selected highlights:**

| Model | Fam | Track | Verdict | Full | Gap |
|-------|-----|-------|--------:|-----:|----:|
| gemma2:9b | C2 | R2 | 1.000 | 0.170 | 0.830 |
| qwen2.5-coder:7b | F1 | R2 | 1.000 | 0.300 | 0.700 |
| Claude Sonnet | F1 | R1 | 1.000 | 0.460 | 0.540 |
| Claude Sonnet | F1 | R2 | 1.000 | 0.990 | 0.010 |

---

## Table 4 — Failure-stage decomposition

See [`../../paper/tables/failure_stage_n100.tex`](../../paper/tables/failure_stage_n100.tex) (`\label{tab:failure-stage-n100}`).

Columns: Model, Family, Track, Not Extractable, Verdict Wrong, Certificate Invalid, Correct (counts summing to 100).

**Claude failure movement:**

| Fam | Track | Not Ext | Verdict Wrong | Cert Invalid | Correct |
|-----|-------|--------:|--------------:|-------------:|--------:|
| C2 | R1 | 0 | 3 | 2 | 95 |
| C2 | R2 | 0 | 0 | 0 | 100 |
| F1 | R1 | 0 | 0 | 54 | 46 |
| F1 | R2 | 1 | 0 | 0 | 99 |

**Local F1 R2 pattern (certificate invalid dominates when extractable):**

| Model | Not Ext | Verdict Wrong | Cert Invalid | Correct |
|-------|--------:|--------------:|-------------:|--------:|
| qwen2.5-coder:7b | 34 | 0 | 36 | 30 |
| gemma2:9b | 46 | 0 | 51 | 3 |
| llama3.1:8b | 85 | 0 | 6 | 1 |
| mistral-nemo:12b | 94 | 0 | 6 | 0 |

---

## Regeneration

Numbers are frozen from on-disk `combined_summary.json`. To re-verify reports without rerunning inference:

```bash
cd fsmreasonbench
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --report-only --out-dir runs/local_matrix_n100_t02_v2 \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 --tracks R0,R1,R2 --temperatures 0.2 --max-items 100

PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --report-only --provider anthropic \
  --out-dir runs/frontier_claude_sonnet_tools_n100_v2 \
  --models claude-sonnet-4-5-20250929 \
  --families C2,F1 --tracks R1,R2 --temperatures 0.2 --max-items 100
```

LaTeX tables are hand-aligned to those summaries at freeze time; re-diff if summaries change.

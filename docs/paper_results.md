# Frozen experimental results (paper-facing)

**Frozen:** 2026-06-20 · **PAPER FREEZE mode**  
**Status:** Experimental state locked for manuscript drafting. Scoring, verifier, cohorts, prompts, and answer keys are **unchanged** unless a critical bug is found.

**LaTeX sources:** [`docs/paper_results_latex.md`](paper_results_latex.md) · `paper/results_frozen.tex` · `paper/tables/*_n100*.tex`  
**Audit checklist:** [`PAPER_FREEZE_AUDIT.md`](PAPER_FREEZE_AUDIT.md)

This document is the **canonical entry point** for n=100 empirical results cited in the paper. Run artifacts live under `runs/` (gitignored); numbers below match auto-generated `report.md` / `combined_summary.json` at freeze time.

---

## Frozen runs (use these)

| Campaign | Run root | Cells | Provider | Models | Families | Tracks | T | n |
|----------|----------|------:|----------|--------|----------|--------|---|--:|
| **Local Ollama matrix** | `runs/local_matrix_n100_t02_v2` | **24/24** | Ollama | gemma2:9b, llama3.1:8b, mistral-nemo:12b, qwen2.5-coder:7b | C2, F1 | R0, R1, R2 | 0.2 | 100 |
| **Claude Sonnet tools (frontier)** | `runs/frontier_claude_sonnet_tools_n100_v2` | **4/4** | Anthropic | claude-sonnet-4-5-20250929 | C2, F1 | R1, R2 | 0.2 | 100 |

**Cohorts (both campaigns):**

- C2: `c2-reachability-level3-v0.1-expanded-n100`
- F1: `f1-mixed-level3-v0.1-expanded-n100`

These are **v0.1-exploratory expanded** snapshots — reproducible and frozen for this study, but **not** `v1.0-public` benchmark releases.

**Supporting docs:**

- Local detail: [`paper_local_results.md`](paper_local_results.md), [`local_matrix_n100_t02_analysis.md`](local_matrix_n100_t02_analysis.md)
- Local plots: `runs/local_matrix_n100_t02_v2/plots/`

---

## Excluded runs (audit only — do not cite as results)

| Run root | Reason |
|----------|--------|
| `runs/frontier_claude_sonnet_full_n100_v1` | **Provider-contaminated.** Anthropic HTTP 400 (insufficient credit) and HTTP 429 (rate limit) were misclassified as `not_extractable`, inflating apparent model extraction failure. Repaired post-hoc for diagnostics only; **not** a citable score. |
| `runs/frontier_gemini_*` (any) | **Quota-contaminated.** Gemini 429 quota failures dominated several cells. **Do not include Gemini as a model result** in the paper. |
| `runs/frontier_gemini_flash_r0_smoke_v1` … `v4` | Confirmed on disk; all excluded from scientific conclusions. |
| Earlier Claude pilots (`frontier_claude_sonnet_f1_r2_n20_v2`, etc.) | Superseded by clean n=100 tools run where noted; retain only for development audit. |

**Clean frontier tools result:** `runs/frontier_claude_sonnet_tools_n100_v2` only (4/4 cells, zero provider_error, zero failed/missing/running/stale).

---

## Metric channels (read separately)

| Channel | Meaning | Denominator |
|---------|---------|-------------|
| **Extractability** | Parseable model submission | total **n** |
| **Verdict accuracy** | Boolean verdict matches key | **extractable** items |
| **Certificate validity** | Verifier accepts certificate | **extractable** items |
| **Fully correct** | Verdict and certificate both pass | total **n** |
| **Provider error** | Infra/API failure (`failure_stage=provider_error`) | excluded from model-quality reads |

**Core claim supported by these results:** tool execution can improve **verdict accuracy** and, on capable models, convert correct verdicts into **machine-verifiable certificates**. On weaker models, verdict and certificate **decouple** — high verdict does not imply certification success.

---

## 1. Local Ollama n=100 matrix (`local_matrix_n100_t02_v2`)

**Design:** 4 models × 2 families × 3 tracks × T=0.2, n=100, **24/24 complete**.

### Headline (local)

**Tools often repair the verdict channel, but verified certification remains the bottleneck.**

On **C2 R2**, local models reach **verdict ≈ 1.0** on extractable items while **certificate validity** stays **5–17%** and **fully correct** matches cert.

On **F1 R2**, many models also reach **verdict = 1.0** among extractable outputs but **fail to produce valid certificates**. **Qwen** is the strongest local model; others are extractability-limited or cert-limited.

### C2 — R2 (local)

| Model | Extract | Verdict | Cert | Full |
|-------|---------|---------|------|------|
| gemma2:9b | 100/100 | 1.000 | 0.170 | 0.170 |
| llama3.1:8b | 96/100 | 0.990 | 0.073 | 0.070 |
| mistral-nemo:12b | 100/100 | 1.000 | 0.060 | 0.060 |
| qwen2.5-coder:7b | 100/100 | 0.970 | 0.050 | 0.050 |

**R1** does not close the certification gap; **fully correct** stays near zero for several models.

### F1 — strongest local (Qwen R2)

| Metric | Value |
|--------|------:|
| Extractable | 66/100 |
| Verdict | 1.000 (66/66 ext) |
| Certificate | 0.455 (30/66 ext) |
| Fully correct | **0.300** (30/100) |

Other local F1 R2 models: high verdict on tiny extractable sets (Gemma, Llama, Mistral) but **cert ≈ 0** and **full ≤ 0.03** — see [`paper_local_results.md`](paper_local_results.md) for unsafe cells.

---

## 2. Claude Sonnet tools n=100 (`frontier_claude_sonnet_tools_n100_v2`)

**Design:** Anthropic `claude-sonnet-4-5-20250929`, C2+F1, **R1+R2 only**, T=0.2, n=100, **4/4 complete**, **0** provider_error / failed / missing / running / stale.

### Per-cell metrics (counts)

| Family | Track | Extract | Verdict | Cert | Full |
|--------|-------|---------|---------|------|------|
| C2 | R1 | 100/100 | 97/100 | 95/100 | 95/100 |
| C2 | R2 | 100/100 | 100/100 | 100/100 | 100/100 |
| F1 | R1 | 100/100 | 100/100 | 46/100 | 46/100 |
| F1 | R2 | 99/100 | 99/99 | 99/99 | 99/100 |

### Failure movement (`failure_stage_counts`)

| Family | Track | not_extractable | provider_error | verdict_wrong | certificate_invalid | correct |
|--------|-------|------------------:|---------------:|--------------:|--------------------:|--------:|
| C2 | R1 | 0 | 0 | 3 | 2 | 95 |
| C2 | R2 | 0 | 0 | 0 | 0 | 100 |
| F1 | R1 | 0 | 0 | 0 | 54 | 46 |
| F1 | R2 | 1 | 0 | 0 | 0 | 99 |

### Claude interpretation

1. **F1 R1 — verdict without certification:** Claude already reaches **100% verdict accuracy** (100/100 extractable), but only **46% certificate validity** and **46% fully correct**. Planning / tool-access alone is **insufficient** for F1 certification.

2. **F1 R2 — execution closes the gap:** **99% fully correct** (99/100), **100% certificate validity** on extractable items (99/99), **100% verdict** on extractable items. Tool **execution** converts correct verdicts into **machine-verifiable certificates**.

3. **C2:** R1 is strong (95/100 full); R2 is perfect (100/100). Reachability certification is easier under delegation for this frontier model than F1 mixed equivalence.

4. **Supports core benchmark claim:** tool execution does **not merely** improve verdict accuracy; on F1 it **bridges verdict → certificate**, which local models largely fail to do.

---

## 3. Verdict vs certificate analysis

### Pattern A — Verdict overstatement (local, especially C2 R2)

| Observation | Evidence |
|-------------|----------|
| Verdict → 1.0 under R2 | All four local models on C2 R2 |
| Cert stays low | 5–17% among extractable |
| Full tracks cert | Same low band |

Solver delegation helps models state the **right boolean answer** while **witness/trace certificates** still fail verification.

### Pattern B — Verdict–cert gap under R1, closed by R2 (Claude F1)

| Track | F1 verdict | F1 cert | F1 full |
|-------|----------:|--------:|--------:|
| R1 | 1.000 | 0.460 | 0.460 |
| R2 | 1.000 (on ext) | 1.000 (on ext) | 0.990 |

**Δ(R2−R1) on F1 full:** +0.53 (46% → 99%). The gap is **certification**, not verdict: R1 already has perfect verdict among extractable items.

### Pattern C — Local F1 R2: verdict without certification (contrast)

| Model | F1 R2 verdict (ext) | F1 R2 cert (ext) | F1 R2 full |
|-------|--------------------:|-----------------:|-----------:|
| qwen2.5-coder:7b | 1.000 | 0.455 | 0.300 |
| gemma2:9b | 1.000 | 0.056 | 0.030 |
| llama3.1:8b | 1.000 | 0.143 | 0.010 |
| mistral-nemo:12b | 1.000 | 0.000 | 0.000 |
| **claude-sonnet (frontier)** | **1.000** | **1.000** | **0.990** |

Same track (F1 R2), same cohort — **frontier model closes the verdict→certificate gap** that local open-weight models largely cannot.

---

## 4. Frontier / local contrast (manuscript framing)

| Setting | Best F1 R2 fully correct | Best F1 R2 cert (extractable) | Verdict (extractable) |
|---------|-------------------------:|------------------------------:|----------------------:|
| Local (Qwen) | 0.300 | 0.455 | 1.000 |
| Claude Sonnet tools | 0.990 | 1.000 | 1.000 |

**Safe claim:** FSMReasonBench separates **sounding right** (verdict) from **proving right** (certificate). Local R2 often maximizes verdict; frontier R2 additionally achieves certification on F1 mixed items.

**Unsafe claim:** General “tools improve reasoning” without naming track, family, and metric channel.

---

## 5. Paper-safe and unsafe claims

### Safe (with frozen-run caveats)

- Layered metrics **diverge by design**; report verdict, cert, and full separately.
- **R1 ≠ R2:** planning without execution does not substitute for execution-mediated certification (Claude F1; local models broadly).
- **Local R2** often yields high verdict, low cert (C2; F1 for non-Qwen models).
- **Claude F1 R2** demonstrates execution converting verdict into valid certificates at n=100.
- Report **extractability** and exclude **provider-contaminated** runs from model comparisons.

### Unsafe

- Citing `frontier_claude_sonnet_full_n100_v1` or any Gemini run as model performance.
- Leaderboard / SOTA from four local Ollama models + one frontier point.
- Treating v0.1-expanded cohorts as `v1.0-public` benchmark scores.
- Verdict accuracy alone as benchmark success.

---

## 6. Regeneration (reproduce reports from frozen run dirs)

```bash
cd fsmreasonbench

# Local matrix report
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --report-only --out-dir runs/local_matrix_n100_t02_v2 \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 --tracks R0,R1,R2 --temperatures 0.2 --max-items 100

# Claude tools report
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --report-only --provider anthropic \
  --out-dir runs/frontier_claude_sonnet_tools_n100_v2 \
  --models claude-sonnet-4-5-20250929 \
  --families C2,F1 --tracks R1,R2 --temperatures 0.2 --max-items 100

# Local plots
PYTHONPATH=src python -m fsmreasonbench.cli.plot_local_matrix \
  --summary runs/local_matrix_n100_t02_v2/combined_summary.json \
  --out-dir runs/local_matrix_n100_t02_v2/plots
```

---

---

## Audit notes

**Verification (2026-06-20):**

| Check | Result |
|-------|--------|
| `local_matrix_n100_t02_v2` cell count | 24/24 `completed` in `combined_summary.json` |
| `frontier_claude_sonnet_tools_n100_v2` cell count | 4/4 `completed`; all `provider_error_count=0` |
| Metrics match `report.md` | Yes (regenerated with `--report-only` at freeze) |
| Scoring / verifier / cohorts modified for freeze | **No** |
| Gemini included as model result | **No** |
| Contaminated Claude full n=100 cited | **No** (audit reference only) |

**Denominator reminder:** Verdict and certificate rates condition on **extractable** items; fully correct and extractability use **n=100**. The Knowing–Showing gap (Verdict − Full) therefore mixes denominators by design—it flags cells where boolean accuracy overstates end-to-end certification.

**Unsafe cells (local):** Llama F1 R1/R2 and Mistral F1 R1/R2 have extractability <50%; verdict/certificate rates are not comparable across tracks without qualification (see [`paper_local_results.md`](paper_local_results.md)).

---

## Appendix A — Full local matrix (24 cells)

| Model | Fam | Track | Extract | Verdict | Cert | Full |
|-------|-----|-------|--------:|--------:|-----:|-----:|
| gemma2:9b | C2 | R0 | 0.980 | 0.388 | 0.071 | 0.070 |
| gemma2:9b | C2 | R1 | 1.000 | 0.290 | 0.000 | 0.000 |
| gemma2:9b | C2 | R2 | 1.000 | 1.000 | 0.170 | 0.170 |
| gemma2:9b | F1 | R0 | 1.000 | 0.530 | 0.240 | 0.240 |
| gemma2:9b | F1 | R1 | 1.000 | 0.850 | 0.000 | 0.000 |
| gemma2:9b | F1 | R2 | 0.540 | 1.000 | 0.056 | 0.030 |
| llama3.1:8b | C2 | R0 | 1.000 | 0.650 | 0.100 | 0.100 |
| llama3.1:8b | C2 | R1 | 0.180 | 0.333 | 0.056 | 0.010 |
| llama3.1:8b | C2 | R2 | 0.960 | 0.990 | 0.073 | 0.070 |
| llama3.1:8b | F1 | R0 | 1.000 | 0.490 | 0.200 | 0.200 |
| llama3.1:8b | F1 | R1 | 0.090 | 0.444 | 0.000 | 0.000 |
| llama3.1:8b | F1 | R2 | 0.070 | 1.000 | 0.143 | 0.010 |
| mistral-nemo:12b | C2 | R0 | 1.000 | 0.490 | 0.150 | 0.150 |
| mistral-nemo:12b | C2 | R1 | 0.950 | 0.758 | 0.084 | 0.080 |
| mistral-nemo:12b | C2 | R2 | 1.000 | 1.000 | 0.060 | 0.060 |
| mistral-nemo:12b | F1 | R0 | 1.000 | 0.490 | 0.100 | 0.100 |
| mistral-nemo:12b | F1 | R1 | 0.040 | 1.000 | 0.000 | 0.000 |
| mistral-nemo:12b | F1 | R2 | 0.060 | 1.000 | 0.000 | 0.000 |
| qwen2.5-coder:7b | C2 | R0 | 0.980 | 0.561 | 0.020 | 0.020 |
| qwen2.5-coder:7b | C2 | R1 | 1.000 | 0.710 | 0.040 | 0.040 |
| qwen2.5-coder:7b | C2 | R2 | 1.000 | 0.970 | 0.050 | 0.050 |
| qwen2.5-coder:7b | F1 | R0 | 1.000 | 0.490 | 0.030 | 0.030 |
| qwen2.5-coder:7b | F1 | R1 | 0.650 | 0.985 | 0.000 | 0.000 |
| qwen2.5-coder:7b | F1 | R2 | 0.660 | 1.000 | 0.455 | 0.300 |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-20 | Freeze local n=100 matrix (`local_matrix_n100_t02_v2`, 24/24) and clean Claude tools n=100 (`frontier_claude_sonnet_tools_n100_v2`, 4/4). Exclude contaminated full-matrix Claude n=100 and all Gemini quota runs from paper results. |
| 2026-06-20 | PAPER FREEZE audit: full 24-cell table, audit notes, LaTeX tables (`paper/tables/*_n100*.tex`), `paper/results_frozen.tex`, `docs/paper_results_latex.md`, `docs/PAPER_FREEZE_AUDIT.md`. |

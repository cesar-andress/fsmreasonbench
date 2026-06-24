# Local Matrix n=100 (T=0.2) Analysis

> **Frozen (2026-06-20):** Local baseline is `runs/local_matrix_n100_t02_v2` (24/24). Paper-facing summary: [`paper_results.md`](paper_results.md). Do **not** use provider-contaminated frontier runs for citations.

**Follow-up run:** `runs/local_matrix_n100_t02_v2`
**Baseline pilot:** `runs/local_matrix_v1` at T=0.2 (n=20)
**Configured items/cell:** 100
**Temperature:** 0.2 only (no cross-temperature replication in this campaign)

> **Not final benchmark scores.** Exploratory local-Ollama matrix on v0.1-exploratory cohorts. Do not cite as `v1.0-public` evidence or frontier-model rankings.

## Campaign status

- **Expected cells:** 24 (4 models × 2 families × 3 tracks × 1 temperature)
- **Completed:** 24
- **Missing / partial / failed:** 0 missing, 0 partial, 0 failed

- **Auto report:** `runs/local_matrix_n100_t02_v2/report.md`
- **Extractability audit:** `docs/extractability_audit_n100_t02.md`
- **Plots:** `runs/local_matrix_n100_t02_v2/plots/` (`fully_correct_by_track.png`, `certificate_valid_by_track.png`, `verdict_accuracy_by_track.png`, `delegation_gap_R2_minus_R0.png`)

## 1. Which n=20 findings replicate at n=100?

Replication is assessed at **T=0.2** by comparing metric **direction** and delegation-gap sign between the n=20 pilot (`local_matrix_v1`) and this follow-up. All 24 cells are **complete**; replication verdicts below are final for this campaign.

| Finding (n=20 @ T=0.2) | Pilot evidence | n=100 status | Replication |
|--------------------------|----------------|--------------|-------------|
| Qwen F1 R2 delegation win | Δfull=+0.400, R2 v=1.000, c=0.533, f=0.400, n_ext=15/20 | Δfull=+0.270, R2 v=1.000, c=0.455, f=0.300, n_ext=66/100 | **replicated with smaller effect** |
| C2 verdict > certificate on R2 | qwen Δ(v−c)=+0.85; gemma Δ(v−c)=+0.90; mistral Δ(v−c)=+0.85 | qwen Δ(v−c)=+0.92; gemma Δ(v−c)=+0.83; mistral Δ(v−c)=+0.94; llama Δ(v−c)=+0.92 | **replicated for qwen, mistral, gemma, llama** |
| Llama tool-track collapse | R1 v=1.000, c=0.000, f=0.000, n_ext=2/20; F1 R1 v=0.000, c=0.000, f=0.000, n_ext=0/20 | R1 v=0.333, c=0.056, f=0.010, n_ext=18/100; F1 R1 v=0.444, c=0.000, f=0.000, n_ext=34/100 | **persistent operational/tool-track failure; not interpretable as reasoning** |
| Layered metrics diverge (verdict vs cert) | Multiple models show v≫c on extractable items (see §6) | Multiple models show v≫c on extractable items (see §6) | **replicated** |

## 2. Delegation gaps Δ(R2−R0) by model and family

Δ(R2−R0) = metric(R2) − metric(R0) on the same items. Requires **completed** R0 and R2 cells with adequate extractability.

### n=100 follow-up (T=0.2)

| Model | Family | Status | n_ext (R0/R2) | Δ verdict | Δ cert | Δ full |
|-------|--------|--------|---------------:|----------:|-------:|-------:|
| `gemma2:9b` | C2 | ok | 98/100 | +0.612 | +0.099 | +0.100 |
| `llama3.1:8b` | C2 | ok | 100/96 | +0.340 | -0.027 | -0.030 |
| `mistral-nemo:12b` | C2 | ok | 100/100 | +0.510 | -0.090 | -0.090 |
| `qwen2.5-coder:7b` | C2 | ok | 98/100 | +0.409 | +0.030 | +0.030 |
| `gemma2:9b` | F1 | ok | 100/54 | +0.470 | -0.184 | -0.210 |
| `llama3.1:8b` | F1 | unsafe | 100/15 | — | — | — |
| `mistral-nemo:12b` | F1 | unsafe | 100/6 | — | — | — |
| `qwen2.5-coder:7b` | F1 | ok | 100/66 | +0.510 | +0.425 | +0.270 |

### n=20 pilot reference (T=0.2)

| Model | Family | Status | n_ext (R0/R2) | Δ verdict | Δ cert | Δ full |
|-------|--------|--------|---------------:|----------:|-------:|-------:|
| `gemma2:9b` | C2 | ok | 20/20 | +0.800 | +0.100 | +0.100 |
| `llama3.1:8b` | C2 | unsafe | 20/0 | — | — | — |
| `mistral-nemo:12b` | C2 | ok | 20/20 | +0.800 | +0.100 | +0.100 |
| `qwen2.5-coder:7b` | C2 | ok | 20/20 | +0.700 | +0.100 | +0.100 |
| `gemma2:9b` | F1 | unsafe | 20/9 | — | — | — |
| `llama3.1:8b` | F1 | unsafe | 20/0 | — | — | — |
| `mistral-nemo:12b` | F1 | unsafe | 20/2 | — | — | — |
| `qwen2.5-coder:7b` | F1 | ok | 20/15 | +0.550 | +0.533 | +0.400 |

## 3. Cells unsafe due to low extractability

Safety tiers (scaled to observed n): **safe** ≥75% extractable, **marginal** 50–74%, **unsafe** <50%. Rates in unsafe cells are not comparable across tracks.

| Model | Family | Track | Status | n | Extractable | Tier | verdict | cert | full |
|-------|--------|-------|--------|--:|------------:|------|--------:|-----:|-----:|
| `gemma2:9b` | C2 | R0 | completed | 100 | 98 | **safe** | 0.388 | 0.071 | 0.070 |
| `gemma2:9b` | C2 | R1 | completed | 100 | 100 | **safe** | 0.290 | 0.000 | 0.000 |
| `gemma2:9b` | C2 | R2 | completed | 100 | 100 | **safe** | 1.000 | 0.170 | 0.170 |
| `llama3.1:8b` | C2 | R0 | completed | 100 | 100 | **safe** | 0.650 | 0.100 | 0.100 |
| `llama3.1:8b` | C2 | R1 | completed | 100 | 18 | **unsafe** | 0.333 | 0.056 | 0.010 |
| `llama3.1:8b` | C2 | R2 | completed | 100 | 96 | **safe** | 0.990 | 0.073 | 0.070 |
| `mistral-nemo:12b` | C2 | R0 | completed | 100 | 100 | **safe** | 0.490 | 0.150 | 0.150 |
| `mistral-nemo:12b` | C2 | R1 | completed | 100 | 95 | **safe** | 0.758 | 0.084 | 0.080 |
| `mistral-nemo:12b` | C2 | R2 | completed | 100 | 100 | **safe** | 1.000 | 0.060 | 0.060 |
| `qwen2.5-coder:7b` | C2 | R0 | completed | 100 | 98 | **safe** | 0.561 | 0.020 | 0.020 |
| `qwen2.5-coder:7b` | C2 | R1 | completed | 100 | 100 | **safe** | 0.710 | 0.040 | 0.040 |
| `qwen2.5-coder:7b` | C2 | R2 | completed | 100 | 100 | **safe** | 0.970 | 0.050 | 0.050 |
| `gemma2:9b` | F1 | R0 | completed | 100 | 100 | **safe** | 0.530 | 0.240 | 0.240 |
| `gemma2:9b` | F1 | R1 | completed | 100 | 100 | **safe** | 0.850 | 0.000 | 0.000 |
| `gemma2:9b` | F1 | R2 | completed | 100 | 54 | **marginal** | 1.000 | 0.056 | 0.030 |
| `llama3.1:8b` | F1 | R0 | completed | 100 | 100 | **safe** | 0.490 | 0.200 | 0.200 |
| `llama3.1:8b` | F1 | R1 | completed | 100 | 34 | **unsafe** | 0.444 | 0.000 | 0.000 |
| `llama3.1:8b` | F1 | R2 | completed | 100 | 15 | **unsafe** | 1.000 | 0.143 | 0.010 |
| `mistral-nemo:12b` | F1 | R0 | completed | 100 | 100 | **safe** | 0.490 | 0.100 | 0.100 |
| `mistral-nemo:12b` | F1 | R1 | completed | 100 | 4 | **unsafe** | 1.000 | 0.000 | 0.000 |
| `mistral-nemo:12b` | F1 | R2 | completed | 100 | 6 | **unsafe** | 1.000 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | F1 | R0 | completed | 100 | 100 | **safe** | 0.490 | 0.030 | 0.030 |
| `qwen2.5-coder:7b` | F1 | R1 | completed | 100 | 65 | **marginal** | 0.985 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | F1 | R2 | completed | 100 | 66 | **marginal** | 1.000 | 0.455 | 0.300 |

## 4. Is Qwen F1 R2 still the strongest positive delegation result?

**Pilot (n=20, T=0.2):** Qwen F1 showed the largest positive Δ(R2−R0) on `fully_correct_rate` (+0.400) and `certificate_valid_rate` (+0.533), with R2 `fully_correct_rate` ≈ 0.40 on balanced F1 mixed items.

**Follow-up:** Δfull=+0.270, Δcert=+0.425. Compare against other models in §2.

## 5. Does Llama still collapse under tool tracks?

**Pilot pattern (T=0.2):** Llama R1/R2 often had near-zero extractability (C2 R1: 2/20; C2 R2: 0/20) or zero metrics on F1 tool tracks — tool-protocol / infra collapse rather than measured reasoning.

- **Pilot:** C2/R1: ext=2/20, v=1.000, f=0.000 (unsafe); C2/R2: ext=0/20, v=0.000, f=0.000 (unsafe); F1/R1: ext=0/20, v=0.000, f=0.000 (unsafe); F1/R2: ext=0/20, v=0.000, f=0.000 (unsafe)
- **Follow-up:** C2/R1: ext=18/100, v=0.333, f=0.010 (unsafe); C2/R2: ext=96/100, v=0.990, f=0.070 (safe); F1/R1: ext=34/100, v=0.444, f=0.000 (unsafe); F1/R2: ext=15/100, v=1.000, f=0.010 (unsafe)

**Assessment:** Llama tool-track cells remain **operationally fragile** on F1 (R1/R2 extractability <50%; not safe for verdict/certificate comparisons). C2 R2 recovers extractability (96/100) and shows the same verdict–certificate decoupling as other models, but F1 tool tracks still collapse for Llama and Mistral — treat as **protocol/extractability failure**, not measured reasoning improvement.

## 6. Does C2 still show verdict improvement without certificate improvement?

On C2 R2, n=20 pilot at T=0.2 showed **high verdict_accuracy with low certificate_valid_rate** (e.g. Qwen v=0.95, c=0.10; Gemma/Mistral v=1.0, c≈0.10–0.15) — verdict improvement without matching certificate improvement.

| Model | Pilot v | Pilot c | Pilot v−c | Follow-up v | Follow-up c | Follow-up v−c |
|-------|--------:|--------:|----------:|------------:|------------:|--------------:|
| `qwen2.5-coder:7b` | 0.950 | 0.100 | +0.850 | 0.970 | 0.050 | +0.920 |
| `llama3.1:8b` | — | — | — | 0.990 | 0.073 | +0.917 |
| `mistral-nemo:12b` | 1.000 | 0.150 | +0.850 | 1.000 | 0.060 | +0.940 |
| `gemma2:9b` | 1.000 | 0.100 | +0.900 | 1.000 | 0.170 | +0.830 |

**Assessment:**
C2 verdict–certificate decoupling is **replicated on all four local models** at n=100.

- **gemma:** v=1.000, c=0.170, v−c=+0.830
- **llama:** v=0.990, c=0.073, v−c=+0.917
- **mistral:** v=1.000, c=0.060, v−c=+0.940
- **qwen:** v=0.970, c=0.050, v−c=+0.920

## 7. Temperature conclusions from n=20 at T=0.2 only?

The n=100 campaign fixes T=0.2 only. It **cannot replicate or refute** n=20 conclusions about T=0 vs T=0.7 effects (e.g. mistral C2 R1 infra failures at T=0.2, gemma extractability swings at T=0.7).

**Plausible carry-over at T=0.2:** Pilot already showed **small temperature sensitivity at T=0.2 vs T=0.0** for several C2 R2 cells (Δfull often 0.0 between T=0 and T=0.2 in `local_matrix_v1_final_report.md`). Workshop-safe wording: *preliminary n=20 suggested limited benefit from mild stochasticity at T=0.2; powered follow-up at T=0.2 alone cannot validate broader temperature claims.*

To test RQ-L2 properly, a future campaign needs multi-temperature replication at n≥100 **after** item pool expansion.

## 8. Claims safe for a workshop paper

- FSMReasonBench layered metrics **can diverge** on local open-weight models: boolean verdict accuracy may exceed contract-verified certificate validity on the same extractable items.
- **Tool tracks change failure modes** (extractability, protocol errors) — report cell health before delegation gaps.
- At n=20/T=0.2, **Qwen F1 R2** showed the clearest positive Δ(R2−R0) on full correctness among four local models (exploratory; single cohort; not public benchmark scores).
- **C2 R2** often improved verdict accuracy under solver delegation without comparable certificate gains — illustrates verdict-overstatement risk under the benchmark contract.
- Campaign-incomplete matrices must show missing cells explicitly; do not interpolate delegation gaps.

## 9. Claims unsafe for journal submission

- Any claim of **n=100 per cell** until item pools exceed 20 items (C2=c2-reachability-level3-v0.1-expanded-n100, F1=f1-mixed-level3-v0.1-expanded-n100 cohorts cap at 20).
- **Model ranking** or state-of-the-art claims from four local Ollama models.
- **General LLM reasoning competence** over FSMs from this matrix alone.
- **Temperature effects** derived only from the n=20 multi-T pilot while citing n=100 T=0.2 results as confirmation.
- **Delegation superiority** without complete R0/R2 pairs, extractability ≥75%, and bootstrap CIs.
- Treating v0.1-exploratory cohort scores as **v1.0-public** or citable benchmark numbers.
- Ignoring **Llama/mistral tool-track extractability collapse** when comparing R2 to R0.

## Regeneration

```bash
cd fsmreasonbench
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --report-only --out-dir runs/local_matrix_n100_t02_v2 \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 --tracks R0,R1,R2 --temperatures 0.2 --max-items 100
PYTHONPATH=src python -m fsmreasonbench.cli.export_extractability_audit \
  --root runs/local_matrix_n100_t02_v2 \
  --out docs/extractability_audit_n100_t02.md --expected-items 100
PYTHONPATH=src python -m fsmreasonbench.cli.export_local_matrix_analysis \
  --follow-root runs/local_matrix_n100_t02_v2 \
  --pilot-root runs/local_matrix_v1 \
  --temperature 0.2 --expected-n 100 \
  --out docs/local_matrix_n100_t02_analysis.md
```

# Local Matrix n=100 (T=0.2) Analysis

**Follow-up run:** `runs/local_matrix_n100_t02_v1`
**Baseline pilot:** `runs/local_matrix_v1` at T=0.2 (n=20)
**Configured items/cell:** 100
**Temperature:** 0.2 only (no cross-temperature replication in this campaign)

> **Not final benchmark scores.** Exploratory local-Ollama matrix on v0.1-exploratory cohorts. Do not cite as `v1.0-public` evidence or frontier-model rankings.

## Campaign status

- **Expected cells:** 24 (4 models × 2 families × 3 tracks × 1 temperature)
- **Completed:** 2
- **Missing / partial / failed:** 22 missing, 0 partial, 0 failed

**Cohort cap:** completed cells report n=20, below configured `--max-items 100`. The frozen v0.1-exploratory cohorts contain 20 items each; powered sampling requires an expanded item pool or on-demand generation.

- **Auto report:** `runs/local_matrix_n100_t02_v1/report.md`
- **Extractability audit:** `docs/extractability_audit_n100_t02.md`
- **Plots:** `runs/local_matrix_n100_t02_v1/plots/` (regenerate after campaign completes)

## 1. Which n=20 findings replicate at n=100?

Replication is assessed at **T=0.2** by comparing metric **direction** and delegation-gap sign between the n=20 pilot (`local_matrix_v1`) and this follow-up. Until all 24 cells complete, replication verdicts are **provisional**.

| Finding (n=20 @ T=0.2) | Pilot evidence | n=100 status | Replication |
|--------------------------|----------------|--------------|-------------|
| Qwen F1 R2 delegation win | Δfull=+0.400, R2 v=1.000, c=0.533, f=0.400, n_ext=15/20 | Δfull=—, R2 cell incomplete | **pending** until F1 R2 completes |
| C2 verdict > certificate on R2 | qwen2.5-coder Δ(v−c)=+0.85; gemma2 Δ(v−c)=+0.90; mistral-nemo Δ(v−c)=+0.85 | pending | **pending** (campaign incomplete) |
| Llama tool-track collapse | R1 v=1.000, c=0.000, f=0.000, n_ext=2/20; F1 R1 v=0.000, c=0.000, f=0.000, n_ext=0/20 | R1 —; F1 R1 — | see §2–§6 after campaign completes |
| Layered metrics diverge (verdict vs cert) | Multiple models show v≫c on extractable items (see §6) | Multiple models show v≫c on extractable items (see §6) | see §2–§6 after campaign completes |

## 2. Delegation gaps Δ(R2−R0) by model and family

Δ(R2−R0) = metric(R2) − metric(R0) on the same items. Requires **completed** R0 and R2 cells with adequate extractability.

### n=100 follow-up (T=0.2)

| Model | Family | Status | n_ext (R0/R2) | Δ verdict | Δ cert | Δ full |
|-------|--------|--------|---------------:|----------:|-------:|-------:|
| `gemma2:9b` | C2 | incomplete | — | — | — | — |
| `llama3.1:8b` | C2 | incomplete | — | — | — | — |
| `mistral-nemo:12b` | C2 | incomplete | — | — | — | — |
| `qwen2.5-coder:7b` | C2 | incomplete | 20/None | — | — | — |
| `gemma2:9b` | F1 | incomplete | — | — | — | — |
| `llama3.1:8b` | F1 | incomplete | — | — | — | — |
| `mistral-nemo:12b` | F1 | incomplete | — | — | — | — |
| `qwen2.5-coder:7b` | F1 | incomplete | — | — | — | — |

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
| `gemma2:9b` | C2 | R0 | missing | — | — | **missing** | — | — | — |
| `gemma2:9b` | C2 | R1 | missing | — | — | **missing** | — | — | — |
| `gemma2:9b` | C2 | R2 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | C2 | R0 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | C2 | R1 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | C2 | R2 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | C2 | R0 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | C2 | R1 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | C2 | R2 | missing | — | — | **missing** | — | — | — |
| `qwen2.5-coder:7b` | C2 | R0 | completed | 20 | 20 | **partial** | 0.200 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | C2 | R1 | completed | 20 | 20 | **partial** | 0.800 | 0.150 | 0.150 |
| `qwen2.5-coder:7b` | C2 | R2 | missing | — | — | **missing** | — | — | — |
| `gemma2:9b` | F1 | R0 | missing | — | — | **missing** | — | — | — |
| `gemma2:9b` | F1 | R1 | missing | — | — | **missing** | — | — | — |
| `gemma2:9b` | F1 | R2 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | F1 | R0 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | F1 | R1 | missing | — | — | **missing** | — | — | — |
| `llama3.1:8b` | F1 | R2 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | F1 | R0 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | F1 | R1 | missing | — | — | **missing** | — | — | — |
| `mistral-nemo:12b` | F1 | R2 | missing | — | — | **missing** | — | — | — |
| `qwen2.5-coder:7b` | F1 | R0 | missing | — | — | **missing** | — | — | — |
| `qwen2.5-coder:7b` | F1 | R1 | missing | — | — | **missing** | — | — | — |
| `qwen2.5-coder:7b` | F1 | R2 | missing | — | — | **missing** | — | — | — |

## 4. Is Qwen F1 R2 still the strongest positive delegation result?

**Pilot (n=20, T=0.2):** Qwen F1 showed the largest positive Δ(R2−R0) on `fully_correct_rate` (+0.400) and `certificate_valid_rate` (+0.533), with R2 `fully_correct_rate` ≈ 0.40 on balanced F1 mixed items.

**Follow-up:** F1 R2 cell not yet complete — **cannot confirm or deny** strongest-delegation status. Re-check after campaign finishes and extractability audit passes.

## 5. Does Llama still collapse under tool tracks?

**Pilot pattern (T=0.2):** Llama R1/R2 often had near-zero extractability (C2 R1: 2/20; C2 R2: 0/20) or zero metrics on F1 tool tracks — tool-protocol / infra collapse rather than measured reasoning.

- **Pilot:** C2/R1: ext=2/20, v=1.000, f=0.000 (unsafe); C2/R2: ext=0/20, v=0.000, f=0.000 (unsafe); F1/R1: ext=0/20, v=0.000, f=0.000 (unsafe); F1/R2: ext=0/20, v=0.000, f=0.000 (unsafe)
- **Follow-up:** C2/R1: missing; C2/R2: missing; F1/R1: missing; F1/R2: missing

**Assessment:** Replication **pending** until Llama R1/R2 cells complete. If extractability remains <50%, report as **tooling failure**, not delegation gap.

## 6. Does C2 still show verdict improvement without certificate improvement?

On C2 R2, n=20 pilot at T=0.2 showed **high verdict_accuracy with low certificate_valid_rate** (e.g. Qwen v=0.95, c=0.10; Gemma/Mistral v=1.0, c≈0.10–0.15) — verdict improvement without matching certificate improvement.

| Model | Pilot v | Pilot c | Pilot v−c | Follow-up v | Follow-up c | Follow-up v−c |
|-------|--------:|--------:|----------:|------------:|------------:|--------------:|
| `qwen2.5-coder:7b` | 0.950 | 0.100 | +0.850 | — | — | — |
| `llama3.1:8b` | — | — | — | — | — | — |
| `mistral-nemo:12b` | 1.000 | 0.150 | +0.850 | — | — | — |
| `gemma2:9b` | 1.000 | 0.100 | +0.900 | — | — | — |

**Assessment:** Follow-up **pending** for most R2 cells. Single completed Qwen C2 R0 cell (not R2) is insufficient to test this finding.

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

- Any claim of **n=100 per cell** until item pools exceed 20 items (C2=c2-reachability-level3-v0.1-exploratory, F1=f1-mixed-level3-v0.1-exploratory cohorts cap at 20).
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
  --report-only --out-dir runs/local_matrix_n100_t02_v1 \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 --tracks R0,R1,R2 --temperatures 0.2 --max-items 100
PYTHONPATH=src python -m fsmreasonbench.cli.export_extractability_audit \
  --root runs/local_matrix_n100_t02_v1 \
  --out docs/extractability_audit_n100_t02.md --expected-items 100
PYTHONPATH=src python -m fsmreasonbench.cli.export_local_matrix_analysis \
  --follow-root runs/local_matrix_n100_t02_v1 \
  --pilot-root runs/local_matrix_v1 \
  --temperature 0.2 --expected-n 100 \
  --out docs/local_matrix_n100_t02_analysis.md
```

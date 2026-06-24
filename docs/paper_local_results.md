# Local open-weight results (paper-facing)

**Campaign:** `runs/local_matrix_n100_t02_v2` — **24/24 cells complete**  
**Design:** 4 Ollama models × 2 families (C2, F1) × 3 tracks (R0, R1, R2) × T=0.2, **n=100** per cell  
**Cohorts:** `c2-reachability-level3-v0.1-expanded-n100`, `f1-mixed-level3-v0.1-expanded-n100` (v0.1-exploratory; not `v1.0-public`)  
**Artifacts:** `report.md`, `combined_summary.json`, plots under `plots/`, internal replication notes in `local_matrix_n100_t02_analysis.md`

> **Scope.** These are exploratory local-matrix results on a single GPU stack. They illustrate benchmark behavior and failure modes; they are **not** frontier-model rankings or final public benchmark scores.

---

## Metric channels (read separately)

| Channel | Definition | Denominator |
|---------|------------|-------------|
| **Extractability** | Model produced a parseable submission | total **n** |
| **Verdict accuracy** | Boolean verdict matches key | **extractable** items only |
| **Certificate validity** | Verifier accepts the certificate object | **extractable** items only |
| **Fully correct** | Verdict and certificate both pass | total **n** |
| **Provider / infra error** | Runner/Ollama timeout or API failure (`failure_stage=provider_error`) | excluded from model-extractability interpretation |

**Headline narrative:** tools and solver delegation often **repair the verdict channel** without producing **verifier-accepted certificates**. Fully correct stays low because certification remains the bottleneck.

Do not equate high verdict accuracy among extractable outputs with reasoning success on the benchmark contract.

---

## Main finding

**Tools often repair the verdict channel, but verified certification remains the bottleneck.**

Across families and models, R2 (tool execution) frequently pushes **verdict accuracy** toward 1.0 on extractable items while **certificate validity** stays far lower. **Fully correct** — the strict end-to-end metric — therefore remains low even when models “sound right.”

This pattern is stronger than “tools help reasoning.” It shows that **layered FSMReasonBench metrics diverge by design**: boolean verdicts and contract-verified certificates measure different capabilities.

---

## C2 (reachability)

On **R2**, local models with adequate extractability show **near-perfect verdict accuracy** but **low certificate validity** and matching low **fully correct**:

| Model | R2 verdict | R2 cert | R2 full | Extractable |
|-------|----------:|--------:|--------:|------------:|
| `gemma2:9b` | 1.000 | 0.170 | 0.170 | 100/100 |
| `llama3.1:8b` | 0.990 | 0.073 | 0.070 | 96/100 |
| `mistral-nemo:12b` | 1.000 | 0.060 | 0.060 | 100/100 |
| `qwen2.5-coder:7b` | 0.970 | 0.050 | 0.050 | 100/100 |

**Delegation Δ(R2−R0)** improves verdict substantially for every model (+0.34 to +0.61) while **certificate** and **full** gains are small or negative (e.g. Mistral Δcert=−0.09, Δfull=−0.09).

**R1** does not reliably close the gap: planning without dependable execution leaves **fully correct** near zero for Gemma (0.000) and only marginally above R0 for others. R1 is a weak intervention compared with R2 on verdict — but R2 still fails to lift certification.

**Interpretation for the paper:** C2 R2 demonstrates **verdict overstatement under delegation**: solvers help models state the right boolean answer while **witness/trace certificates** still fail verification.

---

## F1 (mixed)

**Qwen** is the strongest local model under **R2**:

| Metric | Qwen F1 R2 |
|--------|------------|
| Fully correct | **0.300** (30/100) |
| Certificate validity | **0.455** (30/66 extractable) |
| Verdict accuracy | **1.000** (66/66 extractable) |
| Extractability | 0.660 (66/100) |

**Δ(R2−R0):** Δfull=+0.270, Δcert=+0.425, Δverdict=+0.510 — the clearest positive delegation story in the matrix, though effect size is smaller than the n=20 pilot.

**Other models** largely **fail to convert tool access into valid certificates** on F1:

| Model | R2 verdict | R2 cert | R2 full | Extractable | Safety |
|-------|----------:|--------:|--------:|------------:|--------|
| `gemma2:9b` | 1.000 | 0.056 | 0.030 | 54/100 | marginal extractability |
| `llama3.1:8b` | 1.000 | 0.143 | 0.010 | 7/100 | **unsafe** |
| `mistral-nemo:12b` | 1.000 | 0.000 | 0.000 | 6/100 | **unsafe** |

On extractable F1 R2 items, Gemma/Llama/Mistral often reach **verdict=1.0** but **cert≈0** (or cert undefined on tiny denominators). Only Qwen translates tool execution into a meaningful share of **fully correct** items.

**R1 on F1** is generally weak for end-to-end success: e.g. Qwen R1 verdict=0.985 but cert=0.000 and full=0.000; Gemma R1 verdict=0.850 with cert=0.000. Tool **planning** without robust execution does not substitute for R2.

---

## R1 vs R2

| Track | Role | Pattern |
|-------|------|---------|
| **R0** | Direct submission | Baseline verdict/cert/full |
| **R1** | Tool plan, no execution | Often improves verdict modestly or not at all; **rarely** improves certificates or fully correct |
| **R2** | Tool execution | Strong **verdict** gains; **certificate** gains weak or absent except Qwen F1 |

**Paper-safe wording:** R1 is not a dependable proxy for “giving models tools.” Execution (R2) changes the verdict distribution, but **certification** requires additional model competence that local open-weight models mostly lack.

---

## Cells unsafe for reasoning comparisons

Report **cell health** before citing delegation gaps:

| Model | Family | Track | Extractable | Issue |
|-------|--------|-------|------------:|-------|
| `llama3.1:8b` | C2 | R1 | 18/100 | low extractability |
| `llama3.1:8b` | F1 | R1 | 9/100 | **unsafe**; includes provider errors |
| `llama3.1:8b` | F1 | R2 | 7/100 | **unsafe** |
| `mistral-nemo:12b` | F1 | R1 | 4/100 | **unsafe** |
| `mistral-nemo:12b` | F1 | R2 | 6/100 | **unsafe** |

Verdict and certificate rates in these cells are **not** comparable across tracks. Some Llama F1 failures are **`provider_error`** (infra), not model `not_extractable` — both are excluded from fair model-quality reads but should be labeled separately in tables.

---

## Suggested paper claims

**Safe (with caveats above):**

1. FSMReasonBench’s layered metrics **separate** verdict correctness, certificate validity, and fully correct outcomes — they **need not move together**.
2. On local open-weight models at n=100/T=0.2, **solver delegation (R2) often maximizes verdict accuracy** while **certificate validity stays low**, especially on C2.
3. **Qwen F1 R2** is the standout positive case for **fully correct** (+0.27 vs R0), but still only 30% end-to-end success.
4. **R1** seldom improves fully correct; the benchmark rewards **executable** tool use, not plans alone.
5. Tool-track **extractability collapse** (Llama/Mistral F1) is an operational confound — report it before interpreting delegation.

**Unsafe:**

- General “tools improve FSM reasoning” claims.
- Model leaderboard or SOTA statements from four local models.
- Treating exploratory v0.1 cohort scores as `v1.0-public` benchmark numbers.
- Citing verdict accuracy alone as benchmark success.

---

## Figures (local disk)

Paths relative to `runs/local_matrix_n100_t02_v2/plots/`:

- `fully_correct_by_track.png`
- `certificate_valid_by_track.png`
- `verdict_accuracy_by_track.png`
- `delegation_gap_R2_minus_R0.png`

Regenerate:

```bash
cd fsmreasonbench
PYTHONPATH=src python -m fsmreasonbench.cli.plot_local_matrix \
  --summary runs/local_matrix_n100_t02_v2/combined_summary.json \
  --out-dir runs/local_matrix_n100_t02_v2/plots
```

---

## Related internal docs

- `docs/local_matrix_n100_t02_analysis.md` — pilot replication tables, safety tiers, claim guardrails
- `docs/local_model_matrix_experiment.md` — runner design and matrix layout
- `docs/frontier_provider_backends.md` — provider_error vs not_extractable (frontier runs; same reporting columns)

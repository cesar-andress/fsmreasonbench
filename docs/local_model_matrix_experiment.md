# Local Model Track-Temperature Matrix Experiment

**Status:** living design document (2026-06-20)  
**Artifact:** `fsmreasonbench` — exploratory empirical study on local Ollama models  
**Hardware target:** single NVIDIA RTX 4090, reproducible local inference  
**No paid APIs.**

---

## 1. Purpose

Extend the R0/R1/R2 track pilot into a reproducible experimental matrix that tests whether **local** models show systematic differences across:

- model family / size
- evaluation track (R0 direct, R1 step tools, R2 solver delegation)
- sampling temperature
- task family (C2 reachability, F1 separation)

This experiment is **not** a final benchmark claim. It identifies whether larger-n runs and public-cohort studies are worth executing.

---

## 2. Experimental factors

### Models (primary panel)

| Model | Role |
|-------|------|
| `qwen2.5-coder:7b` | Primary local coder baseline |
| `llama3.1:8b` | General instruct baseline |
| `mistral-nemo:12b` | Mid-size instruct |
| `gemma2:9b` | Google open-weight baseline |

### Optional model slots

| Slot | Candidate | Notes |
|------|-----------|-------|
| Larger coder | `qwen2.5-coder:14b` or `qwen2.5:14b` | Tests RQ-L3 size effect |
| Alt coder | `deepseek-coder:6.7b` or equivalent | Second coder family |
| Small baseline | `phi3:mini` or similar | Lower bound / speed anchor |

### Task families

| Family | Cohort | n (initial) | Scale-up |
|--------|--------|-------------|----------|
| **C2** | `cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl` | 20 | 100–200 |
| **F1** | `cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl` | 20 | 100–200 |

Cohort IDs:

- `c2-reachability-level3-v0.1-exploratory`
- `f1-mixed-level3-v0.1-exploratory`

### Tracks

| Track | Protocol |
|-------|----------|
| **R0** | Single-shot submission, no tools |
| **R1** | Two-phase: `step` tool plan → final submission |
| **R2** | Two-phase: solver tools → final submission |

### Temperatures

| Value | Rationale |
|-------|-----------|
| **0.0** | Deterministic baseline; certificate compliance probe |
| **0.2** | Mild stochasticity; may help tool-plan diversity |
| **0.7** | High exploration; expected to hurt schema compliance |

---

## 3. Cell definition

One **cell** = one `(model, family, track, temperature)` combination evaluated on `n` items.

Initial matrix size (primary panel):

```
4 models × 2 families × 3 tracks × 3 temperatures = 72 cells
× n=20 items/cell
```

Each cell produces:

```
runs/local_matrix_v1/{model_dir}/{family}/temp_{temperature}/{track}/
  results.jsonl
  scores.jsonl
  transcripts/
  summary.json
```

Global aggregates:

```
runs/local_matrix_v1/combined_summary.json
runs/local_matrix_v1/combined_summary.csv
runs/local_matrix_v1/report.md
runs/local_matrix_v1/plots/   # optional, via plot_local_matrix
```

---

## 4. Research questions

| ID | Question |
|----|----------|
| **RQ-L1** | Does tool access improve verdict accuracy, certificate validity, or both? |
| **RQ-L2** | Does temperature improve exploration or degrade certificate compliance? |
| **RQ-L3** | Do larger/local-coder models improve contract-verified success more than verdict accuracy? |
| **RQ-L4** | Are delegation gaps (Δ_R2−R0, Δ_R1−R0) family-specific (C2 vs F1)? |

### Derived metrics

**Per model × family × temperature:**

- Δ_R1−R0 for `verdict_accuracy`, `certificate_valid_rate`, `fully_correct_rate`
- Δ_R2−R0 for same metrics
- Δ_R2−R1 for same metrics

**Per model × family × track:**

- Δ_temp_0.2−0.0 for same metrics
- Δ_temp_0.7−0.0 for same metrics

---

## 5. Execution

```bash
# Full primary panel (slow — hours on RTX 4090)
python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0,0.2,0.7 \
  --max-items 20 \
  --timeout 300 \
  --out-dir runs/local_matrix_v1

# Smoke subset (2 models)
python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0,0.2,0.7 \
  --max-items 20 \
  --timeout 300 \
  --out-dir runs/local_matrix_v1

# Plots (optional)
python -m fsmreasonbench.cli.plot_local_matrix \
  --summary runs/local_matrix_v1/combined_summary.json \
  --out-dir runs/local_matrix_v1/plots
```

Resume: re-run without `--force` to skip completed cells. Re-run with `--force` to overwrite.

---

## 6. Runtime estimates (RTX 4090, n=20)

Rough order-of-magnitude per cell:

| Track | LLM calls/item | Typical cell time |
|-------|----------------|-------------------|
| R0 | 1 | 2–5 min |
| R1/R2 | 2 | 5–15 min |

**Full 72-cell matrix:** ~12–36 GPU-hours depending on model size and timeouts.  
**2-model smoke (36 cells):** ~6–18 GPU-hours.

Recommend `--timeout 300` (or 600 for 12B+ models) and run overnight.

---

## 7. Scale-up plan

1. **Smoke validate** (n=20, 2–4 models, all temperatures) — confirm infrastructure, failure taxonomy, delegation signal.
2. **Primary panel** (n=20, 4 models) — full matrix for exploratory paper figures.
3. **Powered local study** (n=100 or 200/cell) — only if smoke shows non-trivial Δ_R2−R0 or temperature effects.
4. **Optional slots** — add 14B coder / phi3 mini for RQ-L3 without expanding the core matrix.
5. **Public cohort gate** — do **not** migrate claims to `v1.0-public` until M4 freeze + powered quotas.

---

## 8. Constraints (unchanged)

- No change to scoring semantics or verifier rules
- No schema relaxation or post-processing of invalid submissions
- No paid API models in this experiment
- F2 not in scope for this pass

---

## 9. Interpretation checklist

Before claiming any empirical result:

- [ ] Is the effect consistent across ≥2 models?
- [ ] Does Δ_R2−R0 improve certificate, verdict, or both?
- [ ] Does higher temperature increase `final_submission_not_extractable`?
- [ ] Is the signal family-specific (C2 vs F1)?
- [ ] Would the effect survive n=100+ with bootstrap CIs?

If any answer is "no" or "unclear", treat as pilot diagnostic only.

# Local Model Track-Temperature Matrix Report

## Matrix overview

- **Models:** `qwen2.5-coder:7b`, `llama3.1:8b`, `mistral-nemo:12b`, `gemma2:9b`
- **Families:** C2, F1
- **Tracks:** R0, R1, R2
- **Temperatures:** 0.0, 0.2, 0.7
- **Items per cell:** n=20
- **Timeout (s):** 900.0

### Cohort IDs

- **C2:** `c2-reachability-level3-v0.1-exploratory`
- **F1:** `f1-mixed-level3-v0.1-exploratory`

### Cell status

- **Completed:** 72
- **Failed:** 0
- **Missing:** 0
- **Partial:** 0
- **Running:** 0
- **Stale-running:** 0

## C2 — per-track metrics

| Model | Temp | Track | n | extract | verdict | cert | full | tool_rate | avg_tools |
|-------|-----:|-------|--:|------:|------:|------:|------:|------:|------:|

## C2 — per-temperature summary (R2 fully correct)

| Model | Temp | full (R2) | cert (R2) | verdict (R2) |
|-------|-----:|----------:|----------:|-------------:|
| `qwen2.5-coder:7b` | 0 | 0.100 | 0.100 | 0.950 |
| `qwen2.5-coder:7b` | 0.2 | 0.100 | 0.100 | 0.950 |
| `qwen2.5-coder:7b` | 0.7 | 0.100 | 0.100 | 0.950 |
| `llama3.1:8b` | 0 | 0.050 | 0.053 | 1.000 |
| `llama3.1:8b` | 0.2 | 0.000 | 0.000 | 0.000 |
| `llama3.1:8b` | 0.7 | 0.000 | 0.000 | 0.000 |
| `mistral-nemo:12b` | 0 | 0.150 | 0.150 | 1.000 |
| `mistral-nemo:12b` | 0.2 | 0.150 | 0.150 | 1.000 |
| `mistral-nemo:12b` | 0.7 | 0.150 | 0.150 | 1.000 |
| `gemma2:9b` | 0 | 0.100 | 0.100 | 1.000 |
| `gemma2:9b` | 0.2 | 0.100 | 0.100 | 1.000 |
| `gemma2:9b` | 0.7 | 0.100 | 0.100 | 1.000 |

## C2 — delegation gaps by temperature

| Model | Temp | Δ_R1−R0 full | Δ_R2−R0 full | Δ_R2−R1 full | Δ_R2−R0 cert | Δ_R2−R0 verdict |
|-------|-----:|-------------:|-------------:|-------------:|-------------:|----------------:|
| `gemma2:9b` | 0 | +0.000 | +0.100 | +0.100 | +0.100 | +0.800 |
| `gemma2:9b` | 0.2 | +0.000 | +0.100 | +0.100 | +0.100 | +0.800 |
| `gemma2:9b` | 0.7 | +0.000 | +0.100 | +0.100 | +0.100 | +0.789 |
| `llama3.1:8b` | 0 | -0.100 | -0.050 | +0.050 | -0.047 | +0.350 |
| `llama3.1:8b` | 0.2 | -0.100 | -0.100 | +0.000 | -0.100 | -0.650 |
| `llama3.1:8b` | 0.7 | -0.050 | -0.050 | +0.000 | -0.053 | -0.526 |
| `mistral-nemo:12b` | 0 | -0.050 | +0.100 | +0.150 | +0.100 | +0.800 |
| `mistral-nemo:12b` | 0.2 | -0.050 | +0.100 | +0.150 | +0.100 | +0.800 |
| `mistral-nemo:12b` | 0.7 | +0.100 | +0.150 | +0.050 | +0.150 | +0.700 |
| `qwen2.5-coder:7b` | 0 | +0.150 | +0.100 | -0.050 | +0.100 | +0.687 |
| `qwen2.5-coder:7b` | 0.2 | +0.150 | +0.100 | -0.050 | +0.100 | +0.700 |
| `qwen2.5-coder:7b` | 0.7 | +0.100 | +0.050 | -0.050 | +0.050 | +0.600 |

## C2 — temperature sensitivity by track

| Model | Track | Δ_T0.2−T0.0 full | Δ_T0.7−T0.0 full | Δ_T0.2−T0.0 cert | Δ_T0.7−T0.0 cert |
|-------|-------|-----------------:|-----------------:|-----------------:|-----------------:|
| `gemma2:9b` | R0 | +0.000 | +0.000 | +0.000 | +0.000 |
| `gemma2:9b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `gemma2:9b` | R2 | +0.000 | +0.000 | +0.000 | +0.000 |
| `llama3.1:8b` | R0 | +0.000 | -0.050 | +0.000 | -0.047 |
| `llama3.1:8b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `llama3.1:8b` | R2 | -0.050 | -0.050 | -0.053 | -0.053 |
| `mistral-nemo:12b` | R0 | +0.000 | -0.050 | +0.000 | -0.050 |
| `mistral-nemo:12b` | R1 | +0.000 | +0.100 | +0.000 | +0.100 |
| `mistral-nemo:12b` | R2 | +0.000 | +0.000 | +0.000 | +0.000 |
| `qwen2.5-coder:7b` | R0 | +0.000 | +0.050 | +0.000 | +0.050 |
| `qwen2.5-coder:7b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `qwen2.5-coder:7b` | R2 | +0.000 | +0.000 | +0.000 | +0.000 |

## C2 — failure movement

| Model | Temp | Track | final_submission_not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|-----:|-------|---:|---:|---:|---:|
| `qwen2.5-coder:7b` | 0 | R0 | 1 | 14 | 5 | 0 |
| `qwen2.5-coder:7b` | 0 | R1 | 0 | 4 | 13 | 3 |
| `qwen2.5-coder:7b` | 0 | R2 | 0 | 1 | 17 | 2 |
| `qwen2.5-coder:7b` | 0.2 | R0 | 0 | 15 | 5 | 0 |
| `qwen2.5-coder:7b` | 0.2 | R1 | 0 | 3 | 14 | 3 |
| `qwen2.5-coder:7b` | 0.2 | R2 | 0 | 1 | 17 | 2 |
| `qwen2.5-coder:7b` | 0.7 | R0 | 0 | 13 | 6 | 1 |
| `qwen2.5-coder:7b` | 0.7 | R1 | 0 | 5 | 12 | 3 |
| `qwen2.5-coder:7b` | 0.7 | R2 | 0 | 1 | 17 | 2 |
| `llama3.1:8b` | 0 | R0 | 0 | 7 | 11 | 2 |
| `llama3.1:8b` | 0 | R1 | 0 | 2 | 0 | 0 |
| `llama3.1:8b` | 0 | R2 | 0 | 0 | 18 | 1 |
| `llama3.1:8b` | 0.2 | R0 | 0 | 7 | 11 | 2 |
| `llama3.1:8b` | 0.2 | R1 | 0 | 0 | 2 | 0 |
| `llama3.1:8b` | 0.2 | R2 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.7 | R0 | 1 | 9 | 9 | 1 |
| `llama3.1:8b` | 0.7 | R1 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.7 | R2 | 0 | 0 | 0 | 0 |
| `mistral-nemo:12b` | 0 | R0 | 0 | 16 | 3 | 1 |
| `mistral-nemo:12b` | 0 | R1 | 0 | 0 | 0 | 0 |
| `mistral-nemo:12b` | 0 | R2 | 0 | 0 | 17 | 3 |
| `mistral-nemo:12b` | 0.2 | R0 | 0 | 16 | 3 | 1 |
| `mistral-nemo:12b` | 0.2 | R1 | 0 | 0 | 0 | 0 |
| `mistral-nemo:12b` | 0.2 | R2 | 0 | 0 | 17 | 3 |
| `mistral-nemo:12b` | 0.7 | R0 | 0 | 14 | 6 | 0 |
| `mistral-nemo:12b` | 0.7 | R1 | 0 | 1 | 1 | 2 |
| `mistral-nemo:12b` | 0.7 | R2 | 0 | 0 | 17 | 3 |
| `gemma2:9b` | 0 | R0 | 0 | 16 | 4 | 0 |
| `gemma2:9b` | 0 | R1 | 0 | 16 | 4 | 0 |
| `gemma2:9b` | 0 | R2 | 0 | 0 | 18 | 2 |
| `gemma2:9b` | 0.2 | R0 | 0 | 16 | 4 | 0 |
| `gemma2:9b` | 0.2 | R1 | 0 | 15 | 5 | 0 |
| `gemma2:9b` | 0.2 | R2 | 0 | 0 | 18 | 2 |
| `gemma2:9b` | 0.7 | R0 | 1 | 15 | 4 | 0 |
| `gemma2:9b` | 0.7 | R1 | 0 | 15 | 5 | 0 |
| `gemma2:9b` | 0.7 | R2 | 0 | 0 | 18 | 2 |

## F1 — per-track metrics

| Model | Temp | Track | n | extract | verdict | cert | full | tool_rate | avg_tools |
|-------|-----:|-------|--:|------:|------:|------:|------:|------:|------:|

## F1 — per-temperature summary (R2 fully correct)

| Model | Temp | full (R2) | cert (R2) | verdict (R2) |
|-------|-----:|----------:|----------:|-------------:|
| `qwen2.5-coder:7b` | 0 | 0.400 | 0.500 | 1.000 |
| `qwen2.5-coder:7b` | 0.2 | 0.400 | 0.533 | 1.000 |
| `qwen2.5-coder:7b` | 0.7 | 0.450 | 0.643 | 1.000 |
| `llama3.1:8b` | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1:8b` | 0.2 | 0.000 | 0.000 | 0.000 |
| `llama3.1:8b` | 0.7 | 0.000 | 0.000 | 0.000 |
| `mistral-nemo:12b` | 0 | 0.000 | 0.000 | 1.000 |
| `mistral-nemo:12b` | 0.2 | 0.000 | 0.000 | 1.000 |
| `mistral-nemo:12b` | 0.7 | 0.000 | 0.000 | 0.000 |
| `gemma2:9b` | 0 | 0.100 | 0.222 | 1.000 |
| `gemma2:9b` | 0.2 | 0.100 | 0.222 | 1.000 |
| `gemma2:9b` | 0.7 | 0.150 | 0.300 | 1.000 |

## F1 — delegation gaps by temperature

| Model | Temp | Δ_R1−R0 full | Δ_R2−R0 full | Δ_R2−R1 full | Δ_R2−R0 cert | Δ_R2−R0 verdict |
|-------|-----:|-------------:|-------------:|-------------:|-------------:|----------------:|
| `gemma2:9b` | 0 | -0.250 | -0.150 | +0.100 | -0.028 | +0.450 |
| `gemma2:9b` | 0.2 | -0.250 | -0.150 | +0.100 | -0.028 | +0.450 |
| `gemma2:9b` | 0.7 | -0.200 | -0.050 | +0.150 | +0.100 | +0.450 |
| `llama3.1:8b` | 0 | -0.400 | -0.400 | +0.000 | -0.400 | -0.450 |
| `llama3.1:8b` | 0.2 | -0.250 | -0.250 | +0.000 | -0.250 | -0.450 |
| `llama3.1:8b` | 0.7 | -0.200 | -0.200 | +0.000 | -0.200 | -0.500 |
| `mistral-nemo:12b` | 0 | +0.000 | +0.000 | +0.000 | +0.000 | +0.550 |
| `mistral-nemo:12b` | 0.2 | +0.000 | +0.000 | +0.000 | +0.000 | +0.550 |
| `mistral-nemo:12b` | 0.7 | -0.050 | -0.050 | +0.000 | -0.050 | -0.500 |
| `qwen2.5-coder:7b` | 0 | +0.000 | +0.400 | +0.400 | +0.500 | +0.550 |
| `qwen2.5-coder:7b` | 0.2 | +0.000 | +0.400 | +0.400 | +0.533 | +0.550 |
| `qwen2.5-coder:7b` | 0.7 | +0.000 | +0.450 | +0.450 | +0.643 | +0.474 |

## F1 — temperature sensitivity by track

| Model | Track | Δ_T0.2−T0.0 full | Δ_T0.7−T0.0 full | Δ_T0.2−T0.0 cert | Δ_T0.7−T0.0 cert |
|-------|-------|-----------------:|-----------------:|-----------------:|-----------------:|
| `gemma2:9b` | R0 | +0.000 | -0.050 | +0.000 | -0.050 |
| `gemma2:9b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `gemma2:9b` | R2 | +0.000 | +0.050 | +0.000 | +0.078 |
| `llama3.1:8b` | R0 | -0.150 | -0.200 | -0.150 | -0.200 |
| `llama3.1:8b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `llama3.1:8b` | R2 | +0.000 | +0.000 | +0.000 | +0.000 |
| `mistral-nemo:12b` | R0 | +0.000 | +0.050 | +0.000 | +0.050 |
| `mistral-nemo:12b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `mistral-nemo:12b` | R2 | +0.000 | +0.000 | +0.000 | +0.000 |
| `qwen2.5-coder:7b` | R0 | +0.000 | +0.000 | +0.000 | +0.000 |
| `qwen2.5-coder:7b` | R1 | +0.000 | +0.000 | +0.000 | +0.000 |
| `qwen2.5-coder:7b` | R2 | +0.000 | +0.050 | +0.033 | +0.143 |

## F1 — failure movement

| Model | Temp | Track | final_submission_not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|-----:|-------|---:|---:|---:|---:|
| `qwen2.5-coder:7b` | 0 | R0 | 0 | 11 | 9 | 0 |
| `qwen2.5-coder:7b` | 0 | R1 | 4 | 0 | 16 | 0 |
| `qwen2.5-coder:7b` | 0 | R2 | 4 | 0 | 8 | 8 |
| `qwen2.5-coder:7b` | 0.2 | R0 | 0 | 11 | 9 | 0 |
| `qwen2.5-coder:7b` | 0.2 | R1 | 4 | 0 | 16 | 0 |
| `qwen2.5-coder:7b` | 0.2 | R2 | 5 | 0 | 7 | 8 |
| `qwen2.5-coder:7b` | 0.7 | R0 | 1 | 9 | 10 | 0 |
| `qwen2.5-coder:7b` | 0.7 | R1 | 9 | 0 | 11 | 0 |
| `qwen2.5-coder:7b` | 0.7 | R2 | 6 | 0 | 5 | 9 |
| `llama3.1:8b` | 0 | R0 | 0 | 11 | 1 | 8 |
| `llama3.1:8b` | 0 | R1 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0 | R2 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.2 | R0 | 0 | 11 | 4 | 5 |
| `llama3.1:8b` | 0.2 | R1 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.2 | R2 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.7 | R0 | 0 | 10 | 6 | 4 |
| `llama3.1:8b` | 0.7 | R1 | 0 | 0 | 0 | 0 |
| `llama3.1:8b` | 0.7 | R2 | 0 | 0 | 0 | 0 |
| `mistral-nemo:12b` | 0 | R0 | 0 | 11 | 9 | 0 |
| `mistral-nemo:12b` | 0 | R1 | 9 | 1 | 0 | 0 |
| `mistral-nemo:12b` | 0 | R2 | 19 | 0 | 1 | 0 |
| `mistral-nemo:12b` | 0.2 | R0 | 0 | 11 | 9 | 0 |
| `mistral-nemo:12b` | 0.2 | R1 | 6 | 1 | 0 | 0 |
| `mistral-nemo:12b` | 0.2 | R2 | 18 | 0 | 2 | 0 |
| `mistral-nemo:12b` | 0.7 | R0 | 0 | 10 | 9 | 1 |
| `mistral-nemo:12b` | 0.7 | R1 | 8 | 1 | 1 | 0 |
| `mistral-nemo:12b` | 0.7 | R2 | 18 | 0 | 0 | 0 |
| `gemma2:9b` | 0 | R0 | 0 | 9 | 6 | 5 |
| `gemma2:9b` | 0 | R1 | 0 | 0 | 19 | 0 |
| `gemma2:9b` | 0 | R2 | 11 | 0 | 7 | 2 |
| `gemma2:9b` | 0.2 | R0 | 0 | 9 | 6 | 5 |
| `gemma2:9b` | 0.2 | R1 | 0 | 0 | 20 | 0 |
| `gemma2:9b` | 0.2 | R2 | 11 | 0 | 7 | 2 |
| `gemma2:9b` | 0.7 | R0 | 0 | 9 | 7 | 4 |
| `gemma2:9b` | 0.7 | R1 | 0 | 0 | 18 | 0 |
| `gemma2:9b` | 0.7 | R2 | 10 | 0 | 7 | 3 |

## Research questions

- **RQ-L1:** Does tool access improve verdict accuracy, certificate validity, or both?
- **RQ-L2:** Does temperature improve exploration or degrade certificate compliance?
- **RQ-L3:** Do larger/local-coder models improve contract-verified success more than verdict accuracy?
- **RQ-L4:** Are delegation gaps family-specific?

## Interpretation

This report is **exploratory** only:

- Local Ollama models only — reproducible on a single RTX 4090; **no paid APIs**.
- n=20 items per model × family × track × temperature cell (initial pilot).
- Frozen **v0.1-exploratory** cohorts — not `v1.0-public`.
- **Not a final benchmark score.**
- Use results to decide whether a larger-n run (100–200 items/cell) is worth executing.

When reading delegation gaps, ask whether tools improve **verdict accuracy only**, **certificate validity**, or **both** (fully correct). Compare temperature rows to see whether higher temperature helps exploration or hurts certificate compliance.

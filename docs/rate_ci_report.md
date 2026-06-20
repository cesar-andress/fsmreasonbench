# Rate Confidence Interval Report

**Bootstrap resamples:** 1000
**Bootstrap seed:** 4242

Percentile bootstrap confidence intervals (95%) for exploratory model runs.
Computed from existing `scores.jsonl` files only; no LLM re-runs.

**Score roots:** 3
- `/home/cesar/papers/fsmreasonbench/fsmreasonbench/runs/capability_surface_models`
- `/home/cesar/papers/fsmreasonbench/fsmreasonbench/runs/capability_surface_models_f1_mixed`
- `/home/cesar/papers/fsmreasonbench/fsmreasonbench/runs/pilot_v1`

**Rows:** 8

## Sample-size note

Most capability-surface cells use `n=20` items per model per level.
Bootstrap intervals are therefore wide; per-level rate movements should be
read as descriptive capability profiles, not ranked performance claims.

## Example rows (first five)

| source | family | model | level | n | verdict [CI] | cert [CI] | full [CI] |
|--------|--------|-------|------:|--:|--------------|-----------|-----------|
| `pilot_v1/gemma2_9b/C2/scores.jsonl` | C2 | gemma2:9b | — | 20 | 0.55 [0.35, 0.75] | 0.05 [0.00, 0.15] | 0.05 [0.00, 0.15] |
| `pilot_v1/gemma2_9b/F1/scores.jsonl` | F1 | gemma2:9b | — | 20 | 1.00 [1.00, 1.00] | 0.20 [0.05, 0.40] | 0.20 [0.05, 0.40] |
| `pilot_v1/llama3.1_8b/C2/scores.jsonl` | C2 | llama3.1:8b | — | 20 | 0.45 [0.25, 0.65] | 0.20 [0.05, 0.40] | 0.20 [0.05, 0.40] |
| `pilot_v1/llama3.1_8b/F1/scores.jsonl` | F1 | llama3.1:8b | — | 20 | 1.00 [1.00, 1.00] | 0.10 [0.00, 0.25] | 0.10 [0.00, 0.25] |
| `pilot_v1/mistral-nemo_12b/C2/scores.jsonl` | C2 | mistral-nemo:12b | — | 20 | 0.60 [0.40, 0.80] | 0.05 [0.00, 0.15] | 0.05 [0.00, 0.15] |

## Interval width (fully correct rate)

Mean CI width across rows with `n>=20`: **0.244**.

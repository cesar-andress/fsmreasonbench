# Capability Surface Report (exploratory)

Source: `runs/capability_surface_models_f1_mixed/combined_summary.json`
Rows recorded: 20
Grid completeness: 20/20 cells

## Family averages

| Family | Rows | Extractability | Verdict | Certificate | Fully correct |
|--------|-----:|---------------:|--------:|------------:|--------------:|
| F1 | 20 | 1.000 | 0.480 | 0.135 | 0.135 |

## F1 — model comparison

| Model | Levels | Missing levels | Extractability | Verdict | Certificate | Fully correct |
|-------|-------:|---------------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 5 | 0 | 1.000 | 0.510 | 0.170 | 0.170 |
| `llama3.1:8b` | 5 | 0 | 1.000 | 0.470 | 0.200 | 0.200 |
| `mistral-nemo:12b` | 5 | 0 | 1.000 | 0.470 | 0.140 | 0.140 |
| `qwen2.5-coder:7b` | 5 | 0 | 1.000 | 0.470 | 0.030 | 0.030 |

### F1 — by difficulty level

| Model | Level | Extractability | Verdict | Certificate | Fully correct |
|-------|------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 1 | 1.000 | 0.500 | 0.050 | 0.050 |
| `gemma2:9b` | 2 | 1.000 | 0.400 | 0.100 | 0.100 |
| `gemma2:9b` | 3 | 1.000 | 0.550 | 0.250 | 0.250 |
| `gemma2:9b` | 4 | 1.000 | 0.600 | 0.100 | 0.100 |
| `gemma2:9b` | 5 | 1.000 | 0.500 | 0.350 | 0.350 |
| `llama3.1:8b` | 1 | 1.000 | 0.450 | 0.000 | 0.000 |
| `llama3.1:8b` | 2 | 1.000 | 0.400 | 0.000 | 0.000 |
| `llama3.1:8b` | 3 | 1.000 | 0.450 | 0.400 | 0.400 |
| `llama3.1:8b` | 4 | 1.000 | 0.600 | 0.300 | 0.300 |
| `llama3.1:8b` | 5 | 1.000 | 0.450 | 0.300 | 0.300 |
| `mistral-nemo:12b` | 1 | 1.000 | 0.450 | 0.250 | 0.250 |
| `mistral-nemo:12b` | 2 | 1.000 | 0.400 | 0.000 | 0.000 |
| `mistral-nemo:12b` | 3 | 1.000 | 0.450 | 0.000 | 0.000 |
| `mistral-nemo:12b` | 4 | 1.000 | 0.600 | 0.350 | 0.350 |
| `mistral-nemo:12b` | 5 | 1.000 | 0.450 | 0.100 | 0.100 |
| `qwen2.5-coder:7b` | 1 | 1.000 | 0.450 | 0.150 | 0.150 |
| `qwen2.5-coder:7b` | 2 | 1.000 | 0.400 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | 3 | 1.000 | 0.450 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | 4 | 1.000 | 0.600 | 0.000 | 0.000 |
| `qwen2.5-coder:7b` | 5 | 1.000 | 0.450 | 0.000 | 0.000 |

## Interpretation (template)

This report summarizes an **exploratory** capability-surface run. Metrics are averaged across recorded difficulty levels per family and model. Where verdict accuracy exceeds certificate validity, the pattern is consistent with the benchmark's verdict-overstatement hypothesis — but no final claims should be drawn from non-frozen, in-progress cohorts. Treat all values as diagnostic only until a frozen public cohort is evaluated.

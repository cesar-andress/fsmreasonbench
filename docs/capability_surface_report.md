# Capability Surface Report (exploratory)

Source: `runs/capability_surface_models/combined_summary.json`
Rows recorded: 40
Grid completeness: 40/40 cells

## Family averages

| Family | Rows | Extractability | Verdict | Certificate | Fully correct |
|--------|-----:|---------------:|--------:|------------:|--------------:|
| C2 | 20 | 0.998 | 0.556 | 0.110 | 0.110 |
| F1 | 20 | 1.000 | 1.000 | 0.568 | 0.568 |

## C2 — model comparison

| Model | Levels | Missing levels | Extractability | Verdict | Certificate | Fully correct |
|-------|-------:|---------------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 5 | 0 | 0.990 | 0.433 | 0.091 | 0.090 |
| `llama3.1:8b` | 5 | 0 | 1.000 | 0.650 | 0.160 | 0.160 |
| `mistral-nemo:12b` | 5 | 0 | 1.000 | 0.530 | 0.120 | 0.120 |
| `qwen2.5-coder:7b` | 5 | 0 | 1.000 | 0.610 | 0.070 | 0.070 |

### C2 — by difficulty level

| Model | Level | Extractability | Verdict | Certificate | Fully correct |
|-------|------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 1 | 1.000 | 0.850 | 0.100 | 0.100 |
| `gemma2:9b` | 2 | 1.000 | 0.550 | 0.050 | 0.050 |
| `gemma2:9b` | 3 | 1.000 | 0.350 | 0.100 | 0.100 |
| `gemma2:9b` | 4 | 1.000 | 0.150 | 0.100 | 0.100 |
| `gemma2:9b` | 5 | 0.950 | 0.263 | 0.105 | 0.100 |
| `llama3.1:8b` | 1 | 1.000 | 0.900 | 0.100 | 0.100 |
| `llama3.1:8b` | 2 | 1.000 | 0.450 | 0.200 | 0.200 |
| `llama3.1:8b` | 3 | 1.000 | 0.500 | 0.150 | 0.150 |
| `llama3.1:8b` | 4 | 1.000 | 0.700 | 0.150 | 0.150 |
| `llama3.1:8b` | 5 | 1.000 | 0.700 | 0.200 | 0.200 |
| `mistral-nemo:12b` | 1 | 1.000 | 0.900 | 0.250 | 0.250 |
| `mistral-nemo:12b` | 2 | 1.000 | 0.600 | 0.050 | 0.050 |
| `mistral-nemo:12b` | 3 | 1.000 | 0.450 | 0.050 | 0.050 |
| `mistral-nemo:12b` | 4 | 1.000 | 0.300 | 0.050 | 0.050 |
| `mistral-nemo:12b` | 5 | 1.000 | 0.400 | 0.200 | 0.200 |
| `qwen2.5-coder:7b` | 1 | 1.000 | 0.900 | 0.050 | 0.050 |
| `qwen2.5-coder:7b` | 2 | 1.000 | 0.750 | 0.100 | 0.100 |
| `qwen2.5-coder:7b` | 3 | 1.000 | 0.500 | 0.100 | 0.100 |
| `qwen2.5-coder:7b` | 4 | 1.000 | 0.450 | 0.050 | 0.050 |
| `qwen2.5-coder:7b` | 5 | 1.000 | 0.450 | 0.050 | 0.050 |

## F1 — model comparison

| Model | Levels | Missing levels | Extractability | Verdict | Certificate | Fully correct |
|-------|-------:|---------------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 5 | 0 | 1.000 | 1.000 | 0.580 | 0.580 |
| `llama3.1:8b` | 5 | 0 | 1.000 | 1.000 | 0.500 | 0.500 |
| `mistral-nemo:12b` | 5 | 0 | 1.000 | 1.000 | 0.680 | 0.680 |
| `qwen2.5-coder:7b` | 5 | 0 | 1.000 | 1.000 | 0.510 | 0.510 |

### F1 — by difficulty level

| Model | Level | Extractability | Verdict | Certificate | Fully correct |
|-------|------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 1 | 1.000 | 1.000 | 0.150 | 0.150 |
| `gemma2:9b` | 2 | 1.000 | 1.000 | 0.200 | 0.200 |
| `gemma2:9b` | 3 | 1.000 | 1.000 | 0.850 | 0.850 |
| `gemma2:9b` | 4 | 1.000 | 1.000 | 0.850 | 0.850 |
| `gemma2:9b` | 5 | 1.000 | 1.000 | 0.850 | 0.850 |
| `llama3.1:8b` | 1 | 1.000 | 1.000 | 0.050 | 0.050 |
| `llama3.1:8b` | 2 | 1.000 | 1.000 | 0.100 | 0.100 |
| `llama3.1:8b` | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| `llama3.1:8b` | 4 | 1.000 | 1.000 | 0.700 | 0.700 |
| `llama3.1:8b` | 5 | 1.000 | 1.000 | 0.650 | 0.650 |
| `mistral-nemo:12b` | 1 | 1.000 | 1.000 | 0.350 | 0.350 |
| `mistral-nemo:12b` | 2 | 1.000 | 1.000 | 0.200 | 0.200 |
| `mistral-nemo:12b` | 3 | 1.000 | 1.000 | 0.950 | 0.950 |
| `mistral-nemo:12b` | 4 | 1.000 | 1.000 | 0.900 | 0.900 |
| `mistral-nemo:12b` | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| `qwen2.5-coder:7b` | 1 | 1.000 | 1.000 | 0.250 | 0.250 |
| `qwen2.5-coder:7b` | 2 | 1.000 | 1.000 | 0.050 | 0.050 |
| `qwen2.5-coder:7b` | 3 | 1.000 | 1.000 | 0.700 | 0.700 |
| `qwen2.5-coder:7b` | 4 | 1.000 | 1.000 | 0.750 | 0.750 |
| `qwen2.5-coder:7b` | 5 | 1.000 | 1.000 | 0.800 | 0.800 |

## Interpretation (template)

This report summarizes an **exploratory** capability-surface run. Metrics are averaged across recorded difficulty levels per family and model. Where verdict accuracy exceeds certificate validity, the pattern is consistent with the benchmark's verdict-overstatement hypothesis — but no final claims should be drawn from non-frozen, in-progress cohorts. Treat all values as diagnostic only until a frozen public cohort is evaluated.

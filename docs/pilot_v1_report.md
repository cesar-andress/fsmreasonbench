# Multi-Model Pilot Report

Models: 4
Families: C2, F1

## C2 comparison

| Model | extractability_rate | verdict_accuracy | certificate_valid_rate | fully_correct_rate |
|-------|------:|------:|------:|------:|
| `qwen2.5-coder:7b` | 1.000 | 0.750 | 0.100 | 0.100 |
| `llama3.1:8b` | 1.000 | 0.450 | 0.200 | 0.200 |
| `mistral-nemo:12b` | 1.000 | 0.600 | 0.050 | 0.050 |
| `gemma2:9b` | 1.000 | 0.550 | 0.050 | 0.050 |

### C2 failure stage counts

| Model | not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|------:|------:|------:|------:|
| `qwen2.5-coder:7b` | 0 | 5 | 13 | 2 |
| `llama3.1:8b` | 0 | 11 | 5 | 4 |
| `mistral-nemo:12b` | 0 | 8 | 11 | 1 |
| `gemma2:9b` | 0 | 9 | 10 | 1 |

## F1 comparison

| Model | extractability_rate | verdict_accuracy | certificate_valid_rate | fully_correct_rate |
|-------|------:|------:|------:|------:|
| `qwen2.5-coder:7b` | 1.000 | 1.000 | 0.050 | 0.050 |
| `llama3.1:8b` | 1.000 | 1.000 | 0.100 | 0.100 |
| `mistral-nemo:12b` | 1.000 | 1.000 | 0.200 | 0.200 |
| `gemma2:9b` | 1.000 | 1.000 | 0.200 | 0.200 |

### F1 failure stage counts

| Model | not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|------:|------:|------:|------:|
| `qwen2.5-coder:7b` | 0 | 0 | 19 | 1 |
| `llama3.1:8b` | 0 | 0 | 18 | 2 |
| `mistral-nemo:12b` | 0 | 0 | 16 | 4 |
| `gemma2:9b` | 0 | 0 | 16 | 4 |

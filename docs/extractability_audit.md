# Extractability Audit

**Source:** `runs/local_matrix_v1`
**Cells audited:** 72

## Denominator policy (code)

From `summarize_scoring_records()` in `evaluator/summary.py`:

| Metric | Numerator | Denominator |
|--------|-----------|-------------|
| `extractability_rate` | extractable items | **total items** (`n`) |
| `verdict_accuracy` | items with `verdict_correct is True` | **extractable items** |
| `certificate_valid_rate` | items with `certificate_valid is True` | **extractable items** |
| `fully_correct_rate` | items with `fully_correct is True` | **total items** (`n`) |

**Conclusion:** `verdict_accuracy` and `certificate_valid_rate` share the same denominator: the count of extractable items, not total items.

## Audit summary

- **Verdict/certificate denominators identical in all cells:** True
- **`summary.json` matches recomputation from `scores.jsonl`:** True
- **Partial cells (< 20 scored items):** 0

## C2

| Model | Track | Temp | Total | Extractable | Non-extractable | Verdict denom. | Cert denom. | Verdict acc. | Cert valid | Fully correct |
|-------|-------|-----:|------:|------------:|----------------:|--------------:|------------:|-------------:|-----------:|--------------:|
| `gemma2_9b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.000 | 0.000 |
| `gemma2_9b` | R1 | 0 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.100 | 0.100 |
| `gemma2_9b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.000 | 0.000 |
| `gemma2_9b` | R1 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.250 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0.2 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.100 | 0.100 |
| `gemma2_9b` | R0 | 0.7 | 20 | 19 | 1 | 19 | 19 | 0.211 | 0.000 | 0.000 |
| `gemma2_9b` | R1 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.250 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0.7 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.100 | 0.100 |
| `llama3.1_8b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.650 | 0.100 | 0.100 |
| `llama3.1_8b` | R1 | 0 | 20 | 2 | 18 | 2 | 2 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0 | 20 | 19 | 1 | 19 | 19 | 1.000 | 0.053 | 0.050 |
| `llama3.1_8b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.650 | 0.100 | 0.100 |
| `llama3.1_8b` | R1 | 0.2 | 20 | 2 | 18 | 2 | 2 | 1.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0.2 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R0 | 0.7 | 20 | 19 | 1 | 19 | 19 | 0.526 | 0.053 | 0.050 |
| `llama3.1_8b` | R1 | 0.7 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0.7 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.050 | 0.050 |
| `mistral-nemo_12b` | R1 | 0 | 20 | 3 | 17 | 3 | 3 | 0.667 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R2 | 0 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.150 | 0.150 |
| `mistral-nemo_12b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.050 | 0.050 |
| `mistral-nemo_12b` | R1 | 0.2 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R2 | 0.2 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.150 | 0.150 |
| `mistral-nemo_12b` | R0 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.300 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R1 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.650 | 0.100 | 0.100 |
| `mistral-nemo_12b` | R2 | 0.7 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.150 | 0.150 |
| `qwen2.5-coder_7b` | R0 | 0 | 20 | 19 | 1 | 19 | 19 | 0.263 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0 | 20 | 20 | 0 | 20 | 20 | 0.800 | 0.150 | 0.150 |
| `qwen2.5-coder_7b` | R2 | 0 | 20 | 20 | 0 | 20 | 20 | 0.950 | 0.100 | 0.100 |
| `qwen2.5-coder_7b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.250 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.850 | 0.150 | 0.150 |
| `qwen2.5-coder_7b` | R2 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.950 | 0.100 | 0.100 |
| `qwen2.5-coder_7b` | R0 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.350 | 0.050 | 0.050 |
| `qwen2.5-coder_7b` | R1 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.750 | 0.150 | 0.150 |
| `qwen2.5-coder_7b` | R2 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.950 | 0.100 | 0.100 |

## F1

| Model | Track | Temp | Total | Extractable | Non-extractable | Verdict denom. | Cert denom. | Verdict acc. | Cert valid | Fully correct |
|-------|-------|-----:|------:|------------:|----------------:|--------------:|------------:|-------------:|-----------:|--------------:|
| `gemma2_9b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.550 | 0.250 | 0.250 |
| `gemma2_9b` | R1 | 0 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0 | 20 | 9 | 11 | 9 | 9 | 1.000 | 0.222 | 0.100 |
| `gemma2_9b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.550 | 0.250 | 0.250 |
| `gemma2_9b` | R1 | 0.2 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0.2 | 20 | 9 | 11 | 9 | 9 | 1.000 | 0.222 | 0.100 |
| `gemma2_9b` | R0 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.550 | 0.200 | 0.200 |
| `gemma2_9b` | R1 | 0.7 | 20 | 20 | 0 | 20 | 20 | 1.000 | 0.000 | 0.000 |
| `gemma2_9b` | R2 | 0.7 | 20 | 10 | 10 | 10 | 10 | 1.000 | 0.300 | 0.150 |
| `llama3.1_8b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.400 | 0.400 |
| `llama3.1_8b` | R1 | 0 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.250 | 0.250 |
| `llama3.1_8b` | R1 | 0.2 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0.2 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R0 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.500 | 0.200 | 0.200 |
| `llama3.1_8b` | R1 | 0.7 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `llama3.1_8b` | R2 | 0.7 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R1 | 0 | 20 | 2 | 18 | 2 | 2 | 0.500 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R2 | 0 | 20 | 1 | 19 | 1 | 1 | 1.000 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R1 | 0.2 | 20 | 2 | 18 | 2 | 2 | 0.500 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R2 | 0.2 | 20 | 2 | 18 | 2 | 2 | 1.000 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R0 | 0.7 | 20 | 20 | 0 | 20 | 20 | 0.500 | 0.050 | 0.050 |
| `mistral-nemo_12b` | R1 | 0.7 | 20 | 5 | 15 | 5 | 5 | 0.800 | 0.000 | 0.000 |
| `mistral-nemo_12b` | R2 | 0.7 | 20 | 0 | 20 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R0 | 0 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0 | 20 | 16 | 4 | 16 | 16 | 1.000 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R2 | 0 | 20 | 16 | 4 | 16 | 16 | 1.000 | 0.500 | 0.400 |
| `qwen2.5-coder_7b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.450 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0.2 | 20 | 16 | 4 | 16 | 16 | 1.000 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R2 | 0.2 | 20 | 15 | 5 | 15 | 15 | 1.000 | 0.533 | 0.400 |
| `qwen2.5-coder_7b` | R0 | 0.7 | 20 | 19 | 1 | 19 | 19 | 0.526 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0.7 | 20 | 11 | 9 | 11 | 11 | 1.000 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R2 | 0.7 | 20 | 14 | 6 | 14 | 14 | 1.000 | 0.643 | 0.450 |

## Interpretation notes

- Non-extractable items (`extractable=false`) are excluded from both `verdict_accuracy` and `certificate_valid_rate`; they still count toward `extractability_rate` and `fully_correct_rate` denominators differently.
- On extractable items with wrong verdict, the certificate is still validated; both metrics remain conditioned on extractability only.
- Compare delegation gaps using cells with the same extractable denominator, especially when extractability drops sharply (e.g. R2 tool-protocol failures).

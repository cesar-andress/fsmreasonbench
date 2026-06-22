# Extractability Audit

**Source:** `runs/local_matrix_n100_t02_v1`
**Cells audited:** 2

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
- **Partial cells (< 100 scored items):** 2

### Partial cells

- `qwen2.5-coder_7b` / C2 / R0 / T=0.2: 20/100 items
- `qwen2.5-coder_7b` / C2 / R1 / T=0.2: 20/100 items

## C2

| Model | Track | Temp | Total | Extractable | Non-extractable | Verdict denom. | Cert denom. | Verdict acc. | Cert valid | Fully correct |
|-------|-------|-----:|------:|------------:|----------------:|--------------:|------------:|-------------:|-----------:|--------------:|
| `qwen2.5-coder_7b` | R0 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.200 | 0.000 | 0.000 |
| `qwen2.5-coder_7b` | R1 | 0.2 | 20 | 20 | 0 | 20 | 20 | 0.800 | 0.150 | 0.150 |

## Interpretation notes

- Non-extractable items (`extractable=false`) are excluded from both `verdict_accuracy` and `certificate_valid_rate`; they still count toward `extractability_rate` and `fully_correct_rate` denominators differently.
- On extractable items with wrong verdict, the certificate is still validated; both metrics remain conditioned on extractability only.
- Compare delegation gaps using cells with the same extractable denominator, especially when extractability drops sharply (e.g. R2 tool-protocol failures).

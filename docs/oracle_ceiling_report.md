# Oracle Ceiling Report

**Baseline:** symbolic oracle (not a human or model ceiling).

This report evaluates the oracle baseline on the exact item batches used in the
current exploratory paper runs and on the two sealed exploratory cohort snapshots.

## Interpretation

- This is an **oracle/symbolic ceiling**, not a human or model ceiling.
- It demonstrates that **certificate contracts are satisfiable** on the evaluated items.
- It does **not** prove that certificate failures by LLMs are reasoning failures;
  they may reflect certificate-expression or orchestration errors instead.

## Batch results

| source | family | level | cohort | n | extract | verdict | cert | full |
|--------|--------|------:|--------|--:|--------:|--------:|-----:|-----:|
| `capability_surface_models/C2/min_witness_length_1/items.jsonl` | C2 | 1 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models/C2/min_witness_length_2/items.jsonl` | C2 | 2 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models/C2/min_witness_length_3/items.jsonl` | C2 | 3 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models/C2/min_witness_length_4/items.jsonl` | C2 | 4 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models/C2/min_witness_length_5/items.jsonl` | C2 | 5 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_1/items.jsonl` | F1 | 1 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_2/items.jsonl` | F1 | 2 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_3/items.jsonl` | F1 | 3 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_4/items.jsonl` | F1 | 4 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_5/items.jsonl` | F1 | 5 | — | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl` | C2 | — | c2-reachability-level3-v0.1-exploratory | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl` | F1 | — | f1-mixed-level3-v0.1-exploratory | 20 | 1.000 | 1.000 | 1.000 | 1.000 |

## Family-level ceiling

- **C2:** `fully_correct_rate = 1.0` on all 5 evaluated batches.
- **F1:** `fully_correct_rate = 1.0` on all 5 evaluated batches.
- **C2 (frozen cohort):** `fully_correct_rate = 1.0` on all 1 evaluated batches.
- **F1 (frozen cohort):** `fully_correct_rate = 1.0` on all 1 evaluated batches.

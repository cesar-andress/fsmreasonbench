# F1 Local Matrix — Subtype-Stratified Analysis

Offline analysis of `runs/local_matrix_n100_t02_v2` (no new model calls).

- **Matrix root:** `/home/cesar/papers/fsmreasonbench/fsmreasonbench/runs/local_matrix_n100_t02_v2`
- **Cohort metadata:** `/home/cesar/papers/fsmreasonbench/fsmreasonbench/cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl`
- **Models:** gemma2_9b, llama3.1_8b, mistral-nemo_12b, qwen2.5-coder_7b
- **Tracks:** R0, R1, R2
- **F1 cells analyzed:** 12

## Item ID alignment

- **gemma2_9b R0:** n=100, shared_with_cohort=100 (aligned)
- **gemma2_9b R1:** n=100, shared_with_cohort=100 (aligned)
- **gemma2_9b R2:** n=100, shared_with_cohort=100 (aligned)
- **llama3.1_8b R0:** n=100, shared_with_cohort=100 (aligned)
- **llama3.1_8b R1:** n=100, shared_with_cohort=100 (aligned)
- **llama3.1_8b R2:** n=100, shared_with_cohort=100 (aligned)
- **mistral-nemo_12b R0:** n=100, shared_with_cohort=100 (aligned)
- **mistral-nemo_12b R1:** n=100, shared_with_cohort=100 (aligned)
- **mistral-nemo_12b R2:** n=100, shared_with_cohort=100 (aligned)
- **qwen2.5-coder_7b R0:** n=100, shared_with_cohort=100 (aligned)
- **qwen2.5-coder_7b R1:** n=100, shared_with_cohort=100 (aligned)
- **qwen2.5-coder_7b R2:** n=100, shared_with_cohort=100 (aligned)

## Metadata availability

- **gold_verdict:** `answer_key.verdict`
- **gold_certificate_type:** `answer_key.certificate.certificate_type`
- **gold_equivalent:** `difficulty.core.equivalent`
- **distinguishing_trace_length:** `difficulty.core.distinguishing_trace_length`
- **failure_category:** `derived from scores.certificate_errors via classify_certificate_errors`
- **non-equivalent trace lengths:** [3]
- All local F1 cells in this matrix share the expanded n=100 cohort item IDs.
- All 49 non-equivalent cohort items use distinguishing_trace_length=3.
- Analysis uses within-run stratification only (no cross-run pairing).

## Table 1 — Overall F1 by model and track

| model | track | n | extract | verdict | cert | full | not_extractable | verdict_wrong | certificate_invalid | correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemma2_9b | R0 | 100 | 1.000 | 0.530 | 0.240 | 0.240 | 0 | 47 | 29 | 24 |
| gemma2_9b | R1 | 100 | 1.000 | 0.850 | 0.000 | 0.000 | 0 | 15 | 85 | 0 |
| gemma2_9b | R2 | 100 | 0.540 | 1.000 | 0.030 | 0.030 | 46 | 0 | 51 | 3 |
| llama3.1_8b | R0 | 100 | 1.000 | 0.490 | 0.200 | 0.200 | 0 | 51 | 29 | 20 |
| llama3.1_8b | R1 | 100 | 0.090 | 0.444 | 0.000 | 0.000 | 66 | 5 | 4 | 0 |
| llama3.1_8b | R2 | 100 | 0.070 | 1.000 | 0.010 | 0.010 | 85 | 0 | 6 | 1 |
| mistral-nemo_12b | R0 | 100 | 1.000 | 0.490 | 0.100 | 0.100 | 0 | 51 | 39 | 10 |
| mistral-nemo_12b | R1 | 100 | 0.040 | 1.000 | 0.000 | 0.000 | 96 | 0 | 4 | 0 |
| mistral-nemo_12b | R2 | 100 | 0.060 | 1.000 | 0.000 | 0.000 | 94 | 0 | 6 | 0 |
| qwen2.5-coder_7b | R0 | 100 | 1.000 | 0.490 | 0.030 | 0.030 | 0 | 51 | 46 | 3 |
| qwen2.5-coder_7b | R1 | 100 | 0.650 | 0.985 | 0.000 | 0.000 | 35 | 1 | 64 | 0 |
| qwen2.5-coder_7b | R2 | 100 | 0.660 | 1.000 | 0.300 | 0.300 | 34 | 0 | 36 | 30 |

## Table 2 — F1 by certificate subtype

| model | track | certificate_type | n | extract | verdict | cert | full | certificate_invalid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemma2_9b | R0 | equivalence_witness | 51 | 1.000 | 0.078 | 0.000 | 0.000 | 4 |
| gemma2_9b | R0 | distinguishing_trace | 49 | 1.000 | 1.000 | 0.490 | 0.490 | 25 |
| gemma2_9b | R1 | equivalence_witness | 51 | 1.000 | 1.000 | 0.000 | 0.000 | 51 |
| gemma2_9b | R1 | distinguishing_trace | 49 | 1.000 | 0.694 | 0.000 | 0.000 | 34 |
| gemma2_9b | R2 | equivalence_witness | 51 | 0.275 | 1.000 | 0.000 | 0.000 | 14 |
| gemma2_9b | R2 | distinguishing_trace | 49 | 0.816 | 1.000 | 0.061 | 0.061 | 37 |
| llama3.1_8b | R0 | equivalence_witness | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| llama3.1_8b | R0 | distinguishing_trace | 49 | 1.000 | 1.000 | 0.408 | 0.408 | 29 |
| llama3.1_8b | R1 | equivalence_witness | 51 | 0.098 | 0.800 | 0.000 | 0.000 | 4 |
| llama3.1_8b | R1 | distinguishing_trace | 49 | 0.082 | 0.000 | 0.000 | 0.000 | 0 |
| llama3.1_8b | R2 | equivalence_witness | 51 | 0.137 | 1.000 | 0.020 | 0.020 | 6 |
| llama3.1_8b | R2 | distinguishing_trace | 49 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| mistral-nemo_12b | R0 | equivalence_witness | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| mistral-nemo_12b | R0 | distinguishing_trace | 49 | 1.000 | 1.000 | 0.204 | 0.204 | 39 |
| mistral-nemo_12b | R1 | equivalence_witness | 51 | 0.020 | 1.000 | 0.000 | 0.000 | 1 |
| mistral-nemo_12b | R1 | distinguishing_trace | 49 | 0.061 | 1.000 | 0.000 | 0.000 | 3 |
| mistral-nemo_12b | R2 | equivalence_witness | 51 | 0.118 | 1.000 | 0.000 | 0.000 | 6 |
| mistral-nemo_12b | R2 | distinguishing_trace | 49 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| qwen2.5-coder_7b | R0 | equivalence_witness | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| qwen2.5-coder_7b | R0 | distinguishing_trace | 49 | 1.000 | 1.000 | 0.061 | 0.061 | 46 |
| qwen2.5-coder_7b | R1 | equivalence_witness | 51 | 0.314 | 0.938 | 0.000 | 0.000 | 15 |
| qwen2.5-coder_7b | R1 | distinguishing_trace | 49 | 1.000 | 1.000 | 0.000 | 0.000 | 49 |
| qwen2.5-coder_7b | R2 | equivalence_witness | 51 | 0.373 | 1.000 | 0.000 | 0.000 | 19 |
| qwen2.5-coder_7b | R2 | distinguishing_trace | 49 | 0.959 | 1.000 | 0.612 | 0.612 | 17 |

## Table 3 — F1 by gold verdict

| model | track | gold_verdict | n | extract | verdict | cert | full | certificate_invalid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemma2_9b | R0 | equivalent | 51 | 1.000 | 0.078 | 0.000 | 0.000 | 4 |
| gemma2_9b | R0 | non_equivalent | 49 | 1.000 | 1.000 | 0.490 | 0.490 | 25 |
| gemma2_9b | R1 | equivalent | 51 | 1.000 | 1.000 | 0.000 | 0.000 | 51 |
| gemma2_9b | R1 | non_equivalent | 49 | 1.000 | 0.694 | 0.000 | 0.000 | 34 |
| gemma2_9b | R2 | equivalent | 51 | 0.275 | 1.000 | 0.000 | 0.000 | 14 |
| gemma2_9b | R2 | non_equivalent | 49 | 0.816 | 1.000 | 0.061 | 0.061 | 37 |
| llama3.1_8b | R0 | equivalent | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| llama3.1_8b | R0 | non_equivalent | 49 | 1.000 | 1.000 | 0.408 | 0.408 | 29 |
| llama3.1_8b | R1 | equivalent | 51 | 0.098 | 0.800 | 0.000 | 0.000 | 4 |
| llama3.1_8b | R1 | non_equivalent | 49 | 0.082 | 0.000 | 0.000 | 0.000 | 0 |
| llama3.1_8b | R2 | equivalent | 51 | 0.137 | 1.000 | 0.020 | 0.020 | 6 |
| llama3.1_8b | R2 | non_equivalent | 49 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| mistral-nemo_12b | R0 | equivalent | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| mistral-nemo_12b | R0 | non_equivalent | 49 | 1.000 | 1.000 | 0.204 | 0.204 | 39 |
| mistral-nemo_12b | R1 | equivalent | 51 | 0.020 | 1.000 | 0.000 | 0.000 | 1 |
| mistral-nemo_12b | R1 | non_equivalent | 49 | 0.061 | 1.000 | 0.000 | 0.000 | 3 |
| mistral-nemo_12b | R2 | equivalent | 51 | 0.118 | 1.000 | 0.000 | 0.000 | 6 |
| mistral-nemo_12b | R2 | non_equivalent | 49 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| qwen2.5-coder_7b | R0 | equivalent | 51 | 1.000 | 0.000 | 0.000 | 0.000 | 0 |
| qwen2.5-coder_7b | R0 | non_equivalent | 49 | 1.000 | 1.000 | 0.061 | 0.061 | 46 |
| qwen2.5-coder_7b | R1 | equivalent | 51 | 0.314 | 0.938 | 0.000 | 0.000 | 15 |
| qwen2.5-coder_7b | R1 | non_equivalent | 49 | 1.000 | 1.000 | 0.000 | 0.000 | 49 |
| qwen2.5-coder_7b | R2 | equivalent | 51 | 0.373 | 1.000 | 0.000 | 0.000 | 19 |
| qwen2.5-coder_7b | R2 | non_equivalent | 49 | 0.959 | 1.000 | 0.612 | 0.612 | 17 |

## Table 4 — Failure taxonomy

| model | track | certificate_type | failure_category | count | percentage |
| --- | --- | --- | --- | --- | --- |
| gemma2_9b | R0 | equivalence_witness | acceptance_mismatch | 4 | 1.000 |
| gemma2_9b | R0 | distinguishing_trace | acceptance_mismatch | 25 | 1.000 |
| gemma2_9b | R1 | equivalence_witness | equivalence_hash_mismatch | 51 | 1.000 |
| gemma2_9b | R1 | distinguishing_trace | acceptance_mismatch | 34 | 1.000 |
| gemma2_9b | R2 | equivalence_witness | equivalence_hash_mismatch | 14 | 1.000 |
| gemma2_9b | R2 | distinguishing_trace | acceptance_mismatch | 37 | 1.000 |
| llama3.1_8b | R0 | distinguishing_trace | acceptance_mismatch | 25 | 0.862 |
| llama3.1_8b | R0 | distinguishing_trace | replay_failure | 4 | 0.138 |
| llama3.1_8b | R1 | equivalence_witness | equivalence_hash_mismatch | 4 | 1.000 |
| llama3.1_8b | R2 | equivalence_witness | equivalence_hash_mismatch | 6 | 1.000 |
| mistral-nemo_12b | R0 | distinguishing_trace | acceptance_mismatch | 39 | 1.000 |
| mistral-nemo_12b | R1 | equivalence_witness | equivalence_hash_mismatch | 1 | 1.000 |
| mistral-nemo_12b | R1 | distinguishing_trace | acceptance_mismatch | 3 | 1.000 |
| mistral-nemo_12b | R2 | equivalence_witness | equivalence_hash_mismatch | 6 | 1.000 |
| qwen2.5-coder_7b | R0 | distinguishing_trace | acceptance_mismatch | 45 | 0.978 |
| qwen2.5-coder_7b | R0 | distinguishing_trace | replay_failure | 1 | 0.022 |
| qwen2.5-coder_7b | R1 | equivalence_witness | equivalence_hash_mismatch | 15 | 1.000 |
| qwen2.5-coder_7b | R1 | distinguishing_trace | acceptance_mismatch | 49 | 1.000 |
| qwen2.5-coder_7b | R2 | equivalence_witness | equivalence_hash_mismatch | 19 | 1.000 |
| qwen2.5-coder_7b | R2 | distinguishing_trace | acceptance_mismatch | 17 | 1.000 |

## Table 5 — Gap decomposition

| model | track | dist_trace_full | eq_witness_full | dist_trace_cert | eq_witness_cert | subtype_gap |
| --- | --- | --- | --- | --- | --- | --- |
| gemma2_9b | R0 | 0.490 | 0.000 | 0.490 | 0.000 | 0.490 |
| gemma2_9b | R1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gemma2_9b | R2 | 0.061 | 0.000 | 0.061 | 0.000 | 0.061 |
| llama3.1_8b | R0 | 0.408 | 0.000 | 0.408 | 0.000 | 0.408 |
| llama3.1_8b | R1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| llama3.1_8b | R2 | 0.000 | 0.020 | 0.000 | 0.020 | -0.020 |
| mistral-nemo_12b | R0 | 0.204 | 0.000 | 0.204 | 0.000 | 0.204 |
| mistral-nemo_12b | R1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| mistral-nemo_12b | R2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| qwen2.5-coder_7b | R0 | 0.061 | 0.000 | 0.061 | 0.000 | 0.061 |
| qwen2.5-coder_7b | R1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| qwen2.5-coder_7b | R2 | 0.612 | 0.000 | 0.612 | 0.000 | 0.612 |

## Research questions

### 1. Do local models also show high distinguishing_trace success and low equivalence_witness success?

**Partially, but not on R1 tools the way Claude does.** On local **R1**, all four models have `subtype_gap≈0` (average 0.000): both subtypes are near **full=0.000** because of low extractability and/or certificate failure on both. Eq-witness cert is 0.000 for every model on R1.
Dist-trace cert on R1 averages 0.000 vs Claude R1 dist-trace full=0.939.
On **R0** (no tools), dist-trace exceeds eq-witness for 3/4 models (average subtype_gap 0.291; e.g. gemma2 R0 dist full=0.490 vs eq full=0.000). So the dist>eq pattern appears when locals can answer, but Claude's strong R1 dist-trace success is **not** reproduced locally.

### 2. Is the aggregate F1 gap mostly explained by equivalence_witness failures?

**Among semantic certificate errors, eq-witness hash failures are central; aggregate shortfall is broader.** When extractable submissions fail, eq-witness errors are **100% `equivalence_hash_mismatch`** (Table 4). Dist-trace errors are **`acceptance_mismatch` / `replay_failure`** (e.g. qwen R1: 49/49 dist invalid). On R1, gemma2 records 51 eq-witness vs 34 dist-trace cert invalid; qwen inverts that (15 eq vs 49 dist). Low overall F1 also reflects **not_extractable** and **verdict_wrong**, not only subtype choice.

### 3. Does R2 help locals on equivalence_witness, or only on distinguishing_trace?

**Mostly distinguishing_trace, and only materially for qwen2.5-coder; eq-witness stays near zero.**

- gemma2_9b: eq-witness full 0.000→0.000, dist-trace 0.000→0.061
- llama3.1_8b: eq-witness full 0.000→0.020, dist-trace 0.000→0.000
- mistral-nemo_12b: eq-witness full 0.000→0.000, dist-trace 0.000→0.000
- qwen2.5-coder_7b: eq-witness full 0.000→0.000, dist-trace 0.000→0.612

R2 average eq-witness full=0.005, dist-trace full=0.168; subtype_gap R1→R2: 0.000→0.163. Unlike Claude (eq full 0.000→0.980 on R2), locals do **not** get a large eq-witness lift from solver tools.

### 4. Are failures semantic rather than formatting-related?

**Yes.** No `wrong_trace_format` or formatting taxa appear in Table 4. Eq-witness: `equivalence_hash_mismatch` only. Dist-trace: `acceptance_mismatch` and `replay_failure`.

### 5. Is the Claude pattern model-general or Claude-specific?

**Mixed.** The *hardness* of eq-witness hash synthesis is model-general (locals also show 0% eq-witness cert on R1; Claude eq-witness R1 full=0.000). Claude's *success* pattern is largely Claude-specific: R1 dist-trace full=0.939 vs local R1 dist average 0.000; R2 eq-witness lift to 0.980 is not matched by open-weight models (max local R2 eq-witness full=0.020). Subtype mechanism (hash vs trace semantics) is shared; magnitude of tool-assisted certificate completion is Claude-specific on this matrix.

## Notes

- Frozen runs were read only; nothing was re-executed.
- Stratification uses cohort `answer_key.certificate.certificate_type` (51 eq-witness / 49 dist-trace).
- R0 included for completeness; tool-free track still shows eq-witness hash failures when models attempt certificates.

# F1 Claude Ablation — Item-Level Stratified Analysis

Offline analysis of frozen Claude Sonnet F1 runs and ablations (no new model calls).

## Data sources

- **R1:** `runs/frontier_claude_sonnet_tools_n100_v2/claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl`
- **Oracle+Format:** `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/scores.jsonl`
- **R2A:** `runs/ablations_f1_r2_attribution_claude_n100_v1/R2A/scores.jsonl`
- **R2B:** `runs/ablations_f1_r2_attribution_claude_n100_v1/R2B/scores.jsonl`
- **R2C:** `runs/ablations_f1_r2_attribution_claude_n100_v1/R2C/scores.jsonl`
- **Frozen R2:** `runs/frontier_claude_sonnet_tools_n100_v2/claude-sonnet-4-5-20250929/F1/temp_0.2/R2/scores.jsonl`
- **Cohort metadata:** `/home/cesar/papers/fsmreasonbench/fsmreasonbench/cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl`

## Item ID alignment

- Reference (**R1**) n=100
- **R1:** n=100, shared_with_R1=100 (aligned)
- **Frozen R2:** n=100, shared_with_R1=100 (aligned)
- **Oracle+Format:** n=100, shared_with_R1=100 (aligned)
- **R2A:** n=100, shared_with_R1=100 (aligned)
- **R2B:** n=100, shared_with_R1=100 (aligned)
- **R2C:** n=100, shared_with_R1=100 (aligned)

## Metadata availability

- **gold_verdict:** `answer_key.verdict`
- **gold_certificate_type:** `answer_key.certificate.certificate_type`
- **gold_equivalent:** `difficulty.core.equivalent`
- **distinguishing_trace_length:** `difficulty.core.distinguishing_trace_length`
- **question_task:** `question.task`
- **prompt_id:** `question.prompt_id`
- **failure_category:** `derived from scores.certificate_errors via classify_certificate_errors`
- **difficulty.core fields observed:** alphabet_size, distinguishing_trace_length, equivalent, transition_count_A, transition_count_B, |Q_A|, |Q_B|
- **non-equivalent trace lengths in cohort:** [3]
- All 49 non-equivalent cohort items share distinguishing_trace_length=3 in this cohort.
- Equivalent items store distinguishing_trace_length=0 in difficulty.core.

## Table 1 — Overall comparison

| Condition | n | extract | verdict | cert | full | not_extractable | verdict_wrong | certificate_invalid | correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 100 | 1.000 | 1.000 | 0.460 | 0.460 | 0 | 0 | 54 | 46 |
| Oracle+Format | 100 | 1.000 | 1.000 | 0.340 | 0.340 | 0 | 0 | 66 | 34 |
| R2A | 100 | 1.000 | 1.000 | 0.490 | 0.490 | 0 | 0 | 51 | 49 |
| R2B | 100 | 1.000 | 1.000 | 0.480 | 0.480 | 0 | 0 | 52 | 48 |
| R2C | 100 | 0.990 | 1.000 | 0.990 | 0.990 | 1 | 0 | 0 | 99 |
| Frozen R2 | 100 | 0.990 | 1.000 | 0.990 | 0.990 | 1 | 0 | 0 | 99 |

## Table 2 — By gold verdict

| Condition | gold_verdict | n | cert | full | certificate_invalid |
| --- | --- | --- | --- | --- | --- |
| R1 | equivalent | 51 | 0.000 | 0.000 | 51 |
| R1 | non_equivalent | 49 | 0.939 | 0.939 | 3 |
| Oracle+Format | equivalent | 51 | 0.000 | 0.000 | 51 |
| Oracle+Format | non_equivalent | 49 | 0.694 | 0.694 | 15 |
| R2A | equivalent | 51 | 0.000 | 0.000 | 51 |
| R2A | non_equivalent | 49 | 1.000 | 1.000 | 0 |
| R2B | equivalent | 51 | 0.000 | 0.000 | 51 |
| R2B | non_equivalent | 49 | 0.980 | 0.980 | 1 |
| R2C | equivalent | 51 | 0.980 | 0.980 | 0 |
| R2C | non_equivalent | 49 | 1.000 | 1.000 | 0 |
| Frozen R2 | equivalent | 51 | 0.980 | 0.980 | 0 |
| Frozen R2 | non_equivalent | 49 | 1.000 | 1.000 | 0 |

## Table 3 — By certificate type

| Condition | certificate_type | n | cert | full | certificate_invalid |
| --- | --- | --- | --- | --- | --- |
| R1 | equivalence_witness | 51 | 0.000 | 0.000 | 51 |
| R1 | distinguishing_trace | 49 | 0.939 | 0.939 | 3 |
| Oracle+Format | equivalence_witness | 51 | 0.000 | 0.000 | 51 |
| Oracle+Format | distinguishing_trace | 49 | 0.694 | 0.694 | 15 |
| R2A | equivalence_witness | 51 | 0.000 | 0.000 | 51 |
| R2A | distinguishing_trace | 49 | 1.000 | 1.000 | 0 |
| R2B | equivalence_witness | 51 | 0.000 | 0.000 | 51 |
| R2B | distinguishing_trace | 49 | 0.980 | 0.980 | 1 |
| R2C | equivalence_witness | 51 | 0.980 | 0.980 | 0 |
| R2C | distinguishing_trace | 49 | 1.000 | 1.000 | 0 |
| Frozen R2 | equivalence_witness | 51 | 0.980 | 0.980 | 0 |
| Frozen R2 | distinguishing_trace | 49 | 1.000 | 1.000 | 0 |

## Table 4 — Failure taxonomy (certificate_invalid only)

| Condition | failure_category | count | percentage |
| --- | --- | --- | --- |
| R1 | equivalence_hash_mismatch | 51 | 0.944 |
| R1 | acceptance_mismatch | 2 | 0.037 |
| R1 | replay_failure | 1 | 0.019 |
| Oracle+Format | equivalence_hash_mismatch | 51 | 0.773 |
| Oracle+Format | acceptance_mismatch | 14 | 0.212 |
| Oracle+Format | replay_failure | 1 | 0.015 |
| R2A | equivalence_hash_mismatch | 51 | 1.000 |
| R2B | equivalence_hash_mismatch | 51 | 0.981 |
| R2B | acceptance_mismatch | 1 | 0.019 |

## Table 5 — Paired item-level comparisons

### R1 vs Oracle+Format

- Shared items: 100 (perfect)
- Both correct: 32
- R1 only correct: 14
- Oracle+Format only correct: 2
- Both incorrect: 52
- McNemar exact p-value: 0.004180908203125
- Full rate diff (first − second): +0.120 [+0.050, +0.190]
- Cert rate diff (first − second): +0.120 [+0.040, +0.200]

### R1 vs R2A

- Shared items: 100 (perfect)
- Both correct: 46
- R1 only correct: 0
- R2A only correct: 3
- Both incorrect: 51
- McNemar exact p-value: 0.25
- Full rate diff (first − second): -0.030 [-0.070, +0.000]
- Cert rate diff (first − second): -0.030 [-0.060, +0.000]

### R1 vs R2B

- Shared items: 100 (perfect)
- Both correct: 45
- R1 only correct: 1
- R2B only correct: 3
- Both incorrect: 51
- McNemar exact p-value: 0.625
- Full rate diff (first − second): -0.020 [-0.060, +0.020]
- Cert rate diff (first − second): -0.020 [-0.060, +0.020]

### R2A vs R2C

- Shared items: 100 (perfect)
- Both correct: 49
- R2A only correct: 0
- R2C only correct: 50
- Both incorrect: 1
- McNemar exact p-value: 1.7763568394002505e-15
- Full rate diff (first − second): -0.500 [-0.600, -0.400]
- Cert rate diff (first − second): -0.500 [-0.600, -0.390]

### R2B vs R2C

- Shared items: 100 (perfect)
- Both correct: 48
- R2B only correct: 0
- R2C only correct: 51
- Both incorrect: 1
- McNemar exact p-value: 8.881784197001252e-16
- Full rate diff (first − second): -0.510 [-0.620, -0.410]
- Cert rate diff (first − second): -0.510 [-0.610, -0.410]

## Research questions

### 1. Are failures dominated by equivalent items requiring equivalence_witness?

**Yes for R1 and model-construction ablations.** On **R1**, all 51 equivalence_witness items fail cert validation (cert=0.000) while distinguishing_trace items succeed on 46/49 (cert=0.939; only 3 invalid). Of 54 R1 certificate failures, **51 (94.4%)** are equivalence_witness items. The same eq-witness collapse appears under Oracle+Format (51/51 invalid) and R2A/R2B (51/51 eq-witness invalid each).

### 2. Are distinguishing_trace certificates easier than equivalence_witness?

**Yes, markedly on R1.** dist-trace cert=0.939 (n=49) vs eq-witness cert=0.000 (n=51), Δ=+0.939. Oracle+Format does not close the eq gap (still 0.000) and **hurts** dist-trace (0.694 vs 0.939).

### 3. Does oracle-verdict help either subtype?

**No for equivalence_witness; no for distinguishing_trace overall.** Eq-witness stays at cert=0.000 (51/51 invalid). Dist-trace drops to cert=0.694 (15/49 invalid) vs R1 0.939. Oracle verdict + format control does not fix hash synthesis and adds dist-trace semantic errors (acceptance_mismatch).

### 4. Does verify-only or repair-only help either subtype?

**Only distinguishing_trace, marginally.** R2A: eq-witness cert=0.000 (51/51 invalid), dist-trace cert=1.000. R2B: eq=0.000, dist=0.980. Verify/repair can surface/fix trace submissions but **cannot** produce valid minimized hashes for equivalence_witness.

### 5. Does R2C solve both subtypes or only one?

**Both; equivalence_witness is the harder lift.** R2C: eq-witness full=0.980 (n=51), dist-trace full=1.000 (n=49). Frozen R2 matches. Solver generators lift eq-witness from 0% (R1) to ~98% and dist-trace from ~94% to 100%.

### 6. Is the R1-to-R2 gap mainly an equivalence-witness synthesis gap?

**Primarily yes.** R1→Frozen R2 full gain: eq-witness **+0.980** (0.000→0.980), dist-trace **+0.061** (0.939→1.000). Because R1 already reaches 0.939 on dist-trace, **~94% of the aggregate R1→R2 full lift** is explained by fixing equivalence_witness items. The decisive mechanism remains **tool-side certificate synthesis** (solver generators), not model-side validation or formatting.

## Notes

- Failure taxonomy categories are inferred from `certificate_errors` in existing scores.
- Bootstrap CIs use paired item resampling (1000 resamples, seed 4242, 95% percentile).
- McNemar exact test uses discordant pairs on `fully_correct`.
- Frozen runs were not modified or re-executed.

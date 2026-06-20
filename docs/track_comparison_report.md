# Track Comparison Report — c2-reachability-level3-v0.1-exploratory

Comparison of LLM evaluation runs under R0, R1, and R2.

## Per-track metrics

| track | model | family | n | extract | verdict | cert | full | tool_rate | avg_tools |
|-------|-------|--------|--:|--------:|--------:|-----:|-----:|----------:|----------:|
| R0 | qwen2.5-coder:7b | C2 | 20 | 0.950 | 0.263 | 0.000 | 0.000 | 0.000 | 0.0 |
| R1 | qwen2.5-coder:7b | C2 | 20 | 1.000 | 0.800 | 0.150 | 0.150 | 1.000 | 1.0 |
| R2 | qwen2.5-coder:7b | C2 | 20 | 1.000 | 0.950 | 0.100 | 0.100 | 1.000 | 1.0 |

## Track failure taxonomy

| track | no_tool_plan | invalid_tool_plan | disallowed_tool | tool_execution_error | final_submission_not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 0 | 0 | 0 | 0 | 1 | 14 | 5 | 0 |
| R1 | 0 | 0 | 0 | 0 | 0 | 4 | 13 | 3 |
| R2 | 0 | 0 | 0 | 0 | 0 | 1 | 17 | 2 |

## Delegation gaps

### R1_minus_R0
- `verdict_accuracy`: +0.537
- `certificate_valid_rate`: +0.150
- `fully_correct_rate`: +0.150

### R2_minus_R0
- `verdict_accuracy`: +0.687
- `certificate_valid_rate`: +0.100
- `fully_correct_rate`: +0.100


---

# Track Comparison Report — f1-mixed-level3-v0.1-exploratory

Comparison of LLM evaluation runs under R0, R1, and R2.

## Per-track metrics

| track | model | family | n | extract | verdict | cert | full | tool_rate | avg_tools |
|-------|-------|--------|--:|--------:|--------:|-----:|-----:|----------:|----------:|
| R0 | qwen2.5-coder:7b | F1 | 20 | 1.000 | 0.450 | 0.000 | 0.000 | 0.000 | 0.0 |
| R1 | qwen2.5-coder:7b | F1 | 20 | 0.800 | 1.000 | 0.000 | 0.000 | 1.000 | 1.0 |
| R2 | qwen2.5-coder:7b | F1 | 20 | 0.800 | 1.000 | 0.500 | 0.400 | 1.000 | 1.0 |

## Track failure taxonomy

| track | no_tool_plan | invalid_tool_plan | disallowed_tool | tool_execution_error | final_submission_not_extractable | verdict_wrong | certificate_invalid | correct |
|-------|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 0 | 0 | 0 | 0 | 0 | 11 | 9 | 0 |
| R1 | 0 | 0 | 0 | 0 | 4 | 0 | 16 | 0 |
| R2 | 0 | 0 | 0 | 0 | 4 | 0 | 8 | 8 |

## Delegation gaps

### R1_minus_R0
- `verdict_accuracy`: +0.550
- `certificate_valid_rate`: +0.000
- `fully_correct_rate`: +0.000

### R2_minus_R0
- `verdict_accuracy`: +0.550
- `certificate_valid_rate`: +0.500
- `fully_correct_rate`: +0.400

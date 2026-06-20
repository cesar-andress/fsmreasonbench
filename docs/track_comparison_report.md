# Track Comparison Report

Comparison of LLM evaluation runs under R0, R1, and R2.

## Per-track metrics

| track | model | family | n | extract | verdict | cert | full | tool_rate | avg_tools |
|-------|-------|--------|--:|--------:|--------:|-----:|-----:|----------:|----------:|
| R0 | qwen2.5-coder:7b | C2 | 5 | 1.000 | 0.400 | 0.000 | 0.000 | 0.000 | 0.0 |
| R1 | qwen2.5-coder:7b | C2 | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.0 |
| R2 | qwen2.5-coder:7b | C2 | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.0 |

## Delegation gaps

### R1_minus_R0
- `verdict_accuracy`: -0.400
- `certificate_valid_rate`: +0.000
- `fully_correct_rate`: +0.000

### R2_minus_R0
- `verdict_accuracy`: -0.400
- `certificate_valid_rate`: +0.000
- `fully_correct_rate`: +0.000

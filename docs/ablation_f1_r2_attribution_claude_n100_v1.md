# F1 R2 Attribution Ablation (Claude Sonnet n=100)

Decisive ablation decomposing frozen F1 R2 into model vs tool contributions.

## Conditions

| Mode | ID | Model | Tool |
|------|-----|-------|------|
| **R2A** | `f1_r2a_verify_only` | Constructs full certificate | `verifier.validate_f1_certificate` only |
| **R2B** | `f1_r2b_repair_only` | Constructs initial certificate | `format.repair_f1_submission` (formatting only) |
| **R2C** | `f1_r2c_generator_assisted` | Standard two-phase R2 protocol | `solver.check_separation`, `solver.equivalence_certificate`, `solver.distinguishing_certificate` |

## Run configuration

- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.2
- n: 100 (F1 expanded cohort)
- Provider retries: 3, backoff 5s, max delay 120s
- Timeout: 86400s per item

## CLI

```bash
# Smoke (n=5, all modes)
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation --smoke --all --force

# Full study
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation --all --force --max-items 100

# Single mode
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation --mode R2A --max-items 100
```

## Outputs

- Study root: `runs/ablations_f1_r2_attribution_claude_n100_v1/`
- Per mode: `{R2A,R2B,R2C}/summary.json`, `scores.jsonl`, `certificate_failure_taxonomy.json`, `report.md`
- Aggregate: `combined_summary.json`, `report.md`

## Frozen baselines (read-only comparison)

- R1 / R2: `runs/frontier_claude_sonnet_tools_n100_v2/combined_summary.json`
- Oracle+format: `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/summary.json`

## Division of labor (R2)

1. **Model**: `tool_plan` + `final_submission` (verdict and, in R2A/R2B, certificate content).
2. **Tool**: R2C solver generators synthesize witnesses; R2A validates; R2B repairs JSON/format wrappers only.
3. **Verifier**: Independent `verify_f1_certificate` at scoring (unchanged).
4. **Certificate generator**: Oracle builders inside solver tools (R2C only).

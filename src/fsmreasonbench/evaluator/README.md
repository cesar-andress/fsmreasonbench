# Evaluation harness

**Layer:** implementation  
**Version axis:** `verifier_version` (scoring depends on verifier)

Scores submissions, produces capability surface reports.

## Status

Not implemented.

## Rules

- Requires evaluator bundle (answer keys, F4 probes) — separate Zenodo deposit or supplement
- Output: capability surface JSON + summary tables
- Paper table reproduction via `scripts/reproduce_table.sh`

## Not included

- LLM inference (evaluatee responsibility)
- Paper prose

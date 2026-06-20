# Baseline scripts

Reference baselines for capability surface comparison.

## Baselines

| Name | Role |
|------|------|
| `oracle` | Symbolic ceiling: builds verifier-valid certificates via oracle procedures |
| `random` | Seeded lower reference with parseable but usually incorrect submissions |
| `invalid` | Extractability floor (non-JSON output) |
| `reference_submitter` | Independent reasoning workflow that emits model-shaped submissions without reading `answer_key.certificate` |
| `competent_submitter` | R1-style step-simulator ceiling with auditable reasoning logs; runtime-only (no `oracle` imports) |

## Reference submitter

The reference submitter:

1. Reads evaluatee-visible FSM fields and questions only.
2. Computes verdicts with the same decision procedures used in item generation (`is_reachable`, `are_equivalent`).
3. Builds certificates through the public certificate builders (`build_reachability_certificate`, `build_*_separation_certificate`).
4. Serializes `{item_id, verdict, certificate}` JSON and scores it through `parse_submission` / `score_item`.

It does **not** copy `answer_key.certificate` and does **not** use oracle baseline helpers that read gold verdicts.

Export frozen-cohort comparison (oracle vs reference submitter):

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_reference_submitter_report
```

Outputs: `docs/reference_submitter_summary.json`, `.csv`, and `docs/reference_submitter_report.md`.

## Competent submitter

The competent submitter simulates a **competent R1-style agent**:

1. Reads evaluatee-visible FSM fields only.
2. Decides using **runtime** simulation (`simulate`, `reachable_states`, `accepts_trace`, `minimized_dfa_hash`) — not `fsmreasonbench.oracle`.
3. Assembles certificates through the public submission schema.
4. Records a structured `reasoning_log` per item.
5. Scores through `parse_submission` / `score_item`.

On current C2/F1 exploratory cohorts it matches `reference_submitter` at `fully_correct_rate = 1.0`. The incremental value is **process coverage** (auditable step-simulator path), not a higher metric ceiling. See `docs/q1_readiness_roadmap.md` (M2).

Export three-way ceiling comparison (oracle / reference / competent):

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_competent_ceiling_report
```

Outputs: `docs/competent_ceiling_summary.json`, `.csv`, and `docs/competent_ceiling_report.md`.

**Results not stored here** — archive in `paper_reproduction/` at publication.

See `docs/specification/evaluation_protocol.md` §9.

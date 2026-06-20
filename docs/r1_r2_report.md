# R1/R2 Track Report

First operational evaluation tracks on frozen exploratory cohorts.

## Track definitions

| Track | Permitted | Forbidden | Artifact agent |
|-------|-----------|-----------|----------------|
| **R0** | Scratchpad / inline reasoning | Tools, oracle, answer keys | `run_r0_agent` |
| **R1** | `step(fsm_id, state, symbol)` + scratchpad | Oracle, global solvers | `run_r1_agent` |
| **R2** | Registered solver tools + certificate assembly | Gold certificate copy | `run_r2_agent` |

See `docs/r1_r2_design_review.md` for normative semantics and trust boundaries.

## Reproducibility guarantees

- Every R1/R2 tool call is logged in `audit_log.tool_invocations` with inputs, outputs, and provenance.
- `replay_audit_log()` re-executes invocations and verifies output equality.
- Track transcripts store `tracks_version`, `track`, and full audit logs under `{out_dir}/transcripts/`.
- Scoring uses unchanged `parse_submission` / `score_item` (backward compatible `ScoringRecord`).

## Track results

| cohort | family | track | n | extract | verdict | cert | full | tools/item |
|--------|--------|-------|--:|--------:|--------:|-----:|-----:|-----------:|
| `c2-reachability-level3-v0.1-exploratory` | C2 | R0 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | R1 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 7.8 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | R2 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 2.0 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | R0 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | R1 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 30.3 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | R2 | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 2.0 |

## Delegation gap Δ_R2_R0

| cohort | family | metric | R0 | R2 | Δ |
|--------|--------|--------|---:|---:|--:|
| `c2-reachability-level3-v0.1-exploratory` | C2 | verdict_accuracy | 1.000 | 1.000 | +0.000 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | certificate_valid_rate | 1.000 | 1.000 | +0.000 |
| `c2-reachability-level3-v0.1-exploratory` | C2 | fully_correct_rate | 1.000 | 1.000 | +0.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | verdict_accuracy | 1.000 | 1.000 | +0.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | certificate_valid_rate | 1.000 | 1.000 | +0.000 |
| `f1-mixed-level3-v0.1-exploratory` | F1 | fully_correct_rate | 1.000 | 1.000 | +0.000 |

Reference agents on exploratory cohorts achieve identical rates; Δ = 0 is expected. Non-zero delegation gaps appear when R0 systems (e.g. LLMs without tools) underperform R2 solver-delegation pipelines on the same items.

## Example transcripts

Item `d4450489-5803-5cce-a43a-3c46d3609607` (R0, cohort `c2-reachability-level3-v0.1-exploratory`):

```json
{
  "certificate_assembly": [],
  "scratchpad": [
    {
      "details": {
        "family": "C2",
        "item_id": "d4450489-5803-5cce-a43a-3c46d3609607"
      },
      "message": "loaded evaluatee-visible item fields",
      "phase": "read_question"
    },
    {
      "details": {
        "fsm_id": "463bc7f6-4553-50c4-a417-305fbf4daf62",
        "initial_state": "q0",
        "target_state": "q4"
      },
      "message": "read_question",
      "phase": "read_question"
    },
    {
      "details": {
        "reachable_states": [
          "q0",
          "q1"
        ]
      },
      "message": "enumerate_reachable_states",
      "phase": "enumerate_reachable_states"
    },
    {
      "details": {
        "reason": "target not in reachable set",
        "target_state": "q4"
      },
      "message": "conclude_unreachable",
      "phase": "conclude_unreachable"
    },
    {
      "details": {},
      "message": "assembled public submission envelope without tool invocations",
      "phase": "construct_submission"
    }
  ],
  "tool_invocations": [],
  "track": "R0",
  "track_version": "1.0"
}
```

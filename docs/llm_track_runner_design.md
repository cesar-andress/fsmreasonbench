# LLM Track Runner Design

**Date:** 2026-06-20  
**Parent:** `docs/r1_r2_design_review.md`  
**Scope:** C2/F1 via Ollama local models; two-phase JSON protocol

---

## 1. Model interfaces

### R0 — single-shot submission

| Field | Value |
|-------|-------|
| **Calls** | 1 × `generate(prompt)` |
| **Prompt** | Existing `render_prompt()` (unchanged) |
| **Output** | Direct submission JSON `{item_id, verdict, certificate}` |
| **Tools** | None |
| **Audit log** | Empty tool list (legacy `record_transcript`) |

### R1 — step simulator (two-phase)

| Phase | Model output | Runner action |
|-------|--------------|---------------|
| 1 | `{ "phase": "tool_plan", "tool_calls": [...] }` | Execute `step` via `StepSimulator`; reject other tools |
| 2 | `{ "phase": "final_submission", "submission": {...} }` | Parse, score via `score_item` |

Allowed tool: **`step`** with inputs `{fsm_id, state, symbol}`.

### R2 — solver delegation (two-phase)

| Phase | Model output | Runner action |
|-------|--------------|---------------|
| 1 | `{ "phase": "tool_plan", "tool_calls": [...] }` | Execute registered `solver.*` tools only |
| 2 | `{ "phase": "final_submission", "submission": {...} }` | Parse, score |

Registered tools: `solver.is_reachable`, `solver.reachability_certificate`, `solver.check_separation`, `solver.equivalence_certificate`, `solver.distinguishing_certificate`.

---

## 2. Prompt differences

| Track | Phase-1 focus | Phase-2 focus |
|-------|---------------|---------------|
| R0 | Full task + submission schema | — |
| R1 | Item JSON + `step` tool docs + `tool_plan` schema | Tool results JSON + submission schema |
| R2 | Item JSON + solver tool docs + `tool_plan` schema | Tool results JSON + submission schema |

Prompts: `runners/track_prompts.py`. R0 reuses `runners/prompts.py` verbatim.

**Phase-2 hardening (v2):** `runners/track_prompt_schemas.py` supplies exact
`final_submission` envelope, family-specific certificate examples (C2
trace/unreachability; F1 distinguishing/equivalence), invalid payload negatives,
and a 10-point pre-submit checklist. The runner never repairs invalid certificates.

---

## 3. Tool exposure model

- **Closed-world execution:** runner validates tool name before dispatch (`runners/tool_executor.py`).
- **Rejected calls** return `{status: "rejected", error: ...}` in phase-2 context; still logged if executed path attempted.
- **Executed calls** append to `audit_log.tool_invocations` via `AuditLogBuilder`.
- **Cap:** max 64 tool calls per plan round.
- **No nested rounds in v1:** exactly one plan round, one submission round.

---

## 4. Audit log format

Same as reference tracks (`tracks/models.py`):

```json
{
  "track": "R1",
  "track_version": "1.0",
  "scratchpad": [{"phase": "...", "message": "...", "details": {}}],
  "tool_invocations": [{
    "sequence": 1,
    "tool_name": "step",
    "tool_version": "1.0",
    "inputs": {"fsm_id": "...", "state": "q0", "symbol": "a"},
    "outputs": {"success": false, "error": "..."},
    "provenance": "r1_step_simulator"
  }],
  "certificate_assembly": []
}
```

R1/R2 LLM runs populate `tool_invocations` from runner execution, not from model claims alone.

---

## 5. Transcript format (R1/R2)

`LLMTrackTranscript` in `runners/ollama_track_batch.py`:

| Field | Content |
|-------|---------|
| `messages` | Full user/assistant prompts and responses (both phases) |
| `tool_calls_requested` | Parsed plan from phase 1 |
| `tool_calls_executed` | Subset with `status=executed` |
| `tool_outputs` | Full result list (executed + rejected) |
| `audit_log` | Replayable invocation log |
| `scoring_record` | Standard four-layer record |
| `protocol_errors` | Parse/fallback warnings |

R0 transcripts remain the legacy envelope (`evaluator/transcript.py`).

---

## 6. Security / trust boundaries

| Rule | Enforcement |
|------|-------------|
| No answer key in prompts | `item.to_evaluatee_dict()` only in track prompts |
| No oracle in R1 | `track_guards` + executor allowlist |
| R2 oracle only via registry | Closed tool list + provenance string |
| Tool replay integrity | `replay_audit_log()` after each item |
| Model cannot forge tool outputs | Phase-2 prompt contains runner-produced results only |

---

## 7. Failure modes

| Failure | Handling |
|---------|----------|
| Invalid phase-1 JSON | Empty tool results; `protocol_errors` logged; phase 2 proceeds |
| Disallowed tool | Rejected entry in `tool_outputs`; no audit invocation |
| Invalid phase-2 protocol | Best-effort `extract_submission_payload`; may fail extractability |
| Ollama timeout / HTTP error | Propagates; no partial transcript for that item |
| Replay mismatch | Raises during item evaluation (programmer error if log corrupt) |

---

## 8. Ollama / local model limitations

- **No native function-calling assumed.** Two-phase JSON protocol avoids fragile tool-call APIs.
- **Small models may ignore phase discipline.** Fallback extraction on phase 2 reduces hard failures but may inflate extractability without valid certificates.
- **Tool planning quality varies.** A model may request zero tools on R1/R2; run still completes.
- **Latency:** R1/R2 = 2× generate calls per item vs R0.
- **Temperature 0 recommended** for reproducibility (same as existing Ollama runner).

---

## 9. Output layout

```
{out_dir}/
  results.jsonl          # run records
  scores.jsonl           # scoring + track, model, tool_invocation_count
  summary.json           # backward compatible aggregate
  track_summary.json     # same + tool_invocation_rate, average_tool_calls_per_item
  transcripts/{item_id}.json
```

`summarize_scores --scores scores.jsonl` ignores extra fields via `ScoringRecord.from_dict`.

---

## 10. Track failure taxonomy

Primary class per item (`evaluator/track_failure_taxonomy.py`):

| Class | Meaning |
|-------|---------|
| `no_tool_plan` | R1/R2: valid phase-1 parse but empty `tool_calls` |
| `invalid_tool_plan` | Phase-1 JSON/protocol parse failed |
| `disallowed_tool` | Tools requested but all rejected |
| `tool_execution_error` | Runner error executing plan |
| `final_submission_not_extractable` | Submission schema/extractability failure |
| `verdict_wrong` | Extractable but wrong verdict |
| `certificate_invalid` | Extractable but verifier rejects certificate |
| `correct` | Fully correct |

Aggregated in `track_summary.json` as `track_failure_counts` / `track_failure_rates`.

---

## 10. CLIs

```bash
# Dedicated track batch
python -m fsmreasonbench.cli.run_ollama_track_batch \
  --model qwen2.5-coder:7b --items cohorts/.../items.jsonl \
  --out runs/.../results.jsonl --out-dir runs/.../R1 --track R1

# Legacy CLI with --track (R0 default)
python -m fsmreasonbench.cli.run_ollama_batch ... --track R0

# Compare runs
python -m fsmreasonbench.cli.compare_tracks \
  --r0-dir runs/.../R0 --r1-dir runs/.../R1 --r2-dir runs/.../R2

# Multi-model track pilot (R0/R1/R2 × models × families)
python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --max-items 20 \
  --temperature 0 \
  --out-dir runs/track_pilot_v1
```

`track_pilot_v1` is the first experiment layout capable of measuring **Δ_R1−R0** and **Δ_R2−R0** on actual LLM outputs across a model panel. Each cell writes `results.jsonl`, `scores.jsonl`, `transcripts/`, and `summary.json` under `{out_dir}/{model_dir}/{family}/{track}/`. Root outputs: `combined_summary.json`, `combined_summary.csv`, `report.md` (with per-family metrics, delegation gaps, and failure-movement tables). Use `--force` to re-run completed cells; failures are recorded per cell without aborting the sweep.

### Local model track-temperature matrix

```bash
python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0,0.2,0.7 \
  --max-items 20 \
  --out-dir runs/local_matrix_v1

python -m fsmreasonbench.cli.plot_local_matrix \
  --summary runs/local_matrix_v1/combined_summary.json \
  --out-dir runs/local_matrix_v1/plots
```

When `--temperatures` lists more than one value, cells are written under `{out_dir}/{model_dir}/{family}/temp_{temperature}/{track}/`. The combined report adds per-temperature delegation gaps, temperature sensitivity (Δ_T0.2−T0.0, Δ_T0.7−T0.0), and RQ-L1–RQ-L4 framing. See [`docs/local_model_matrix_experiment.md`](local_model_matrix_experiment.md). Intended to test track and temperature effects on reproducible local models (RTX 4090, no paid APIs) before any frontier or public-cohort study.

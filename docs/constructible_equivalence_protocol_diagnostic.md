# Constructible-equivalence protocol diagnostic (A1)

**Date:** 2026-06-20  
**Scope:** F1 constructible bisimulation witness study (`F1-constructible-equivalence-v1`)  
**Providers reviewed:** OpenAI GPT-4.1, Anthropic Claude Sonnet 4.5  
**Tracks reviewed:** R1, R2C  

This note records why prior runs were **invalid as scientific measurements**, what was fixed, and whether GPT and Claude are now evaluated under a **protocol-comparable** contract.

---

## Executive summary

| Cell | Prior status | Root cause | Post-fix comparability |
|------|--------------|------------|------------------------|
| GPT R1 (n=51) | **Invalid** — extractability 0/51 | Prompt template used static placeholders; GPT copied them literally | Same parser + prompts + smoke gate as Claude |
| Claude R1 (n=39 partial) | **Invalid** — extractability 0/39 | Markdown-fenced JSON, omitted `fsm_ids`, hallucinated `item_id` strings | Same study-local extraction/normalization path |
| GPT R2C (partial) | **Invalid** — tool/replay failure | Audit replay lacked `solver.bisimulation_certificate` | Replay fixed; same R2C runner for both providers |
| Claude R2C | Not run | — | Ready after smoke gate |

**Verdict:** Prior GPT and Claude constructible-equivalence numbers are **not comparable** and must not be interpreted as model capability. After the protocol fix, both providers share one canonical final-answer schema, one batch runner, one parser/normalizer, and identical smoke gates.

---

## GPT R1 — transcript diagnosis

**On-disk run:** `runs/f1_constructible_equivalence_gpt_n100_v1/R1/` (51 items)

| Metric | Value |
|--------|------:|
| extractability_rate | 0.0 |
| final_submission_not_extractable | 51/51 |
| provider_error_count | 0 |
| tool_invocation_rate | 1.0 |
| average_tool_calls_per_item | ~13.5 |
| certificate_assembly | `[]` (expected for R1) |

**What actually happened**

- Phase 1: valid `tool_plan` with many `step` calls (~13.5/item).
- Phase 2: **valid JSON** with `"phase": "final_submission"` and `"certificate_type": "bisimulation_witness"`.
- Failure mode: copied **prompt placeholders** instead of real IDs:
  - `"item_id": "<must match item>"`
  - `"fsm_ids": ["<fsm_a.fsm_id>", "<fsm_b.fsm_id>"]`
- Scorer error: `item_id mismatch` → `not_extractable`.

This is a **protocol/prompt issue**, not evidence that GPT cannot emit a bisimulation witness.

---

## Claude R1 — transcript diagnosis

**On-disk run:** `runs/f1_constructible_equivalence_claude_n100_v1/R1/` (39 items, incomplete)

| Metric | Value |
|--------|------:|
| extractability_rate | 0.0 (39/39 scored) |
| final_submission_not_extractable | 39/39 |
| certificate_type in final JSON | `bisimulation_witness` (39/39 when fence stripped) |
| markdown JSON fences | 39/39 |
| missing `fsm_ids` | 39/39 |
| hallucinated `item_id` | 39/39 (e.g. `F1_bisim_pair_00`, `f1_bisim_3`) |
| certificate_assembly | `[]` (expected for R1) |

**What actually happened**

- Claude **did** emit structurally plausible bisimulation witnesses.
- Parse failure was **`fsm_ids must be an array of length 2`** (checked before item_id in the F1 parser).
- Wrong `item_id` values would have failed next; they were masked by the earlier `fsm_ids` error.
- No Claude-specific runner branch existed; failure was **not** due to a privileged Claude code path.

---

## Claude R2C

No Claude R2C cell exists on disk yet. GPT R2C partial runs (when present) failed with:

`unsupported replay tool: 'solver.bisimulation_certificate'`

That blocked audit replay after tool execution — an infrastructure gap, not a verifier rule change. Replay support for `solver.bisimulation_certificate` is now added.

---

## Protocol comparability checklist

| Question | Answer |
|----------|--------|
| Same batch runner? | **Yes** — `constructible_equivalence_batch.py` for all cells |
| Same prompts per track? | **Yes** — `constructible_equivalence_prompts.py`; no provider branches |
| Same final-answer schema? | **Yes** — `constructible_final_answer_contract.py` |
| Same parser? | **Yes** — `extract_constructible_final_submission()` → `parse_f1_response()` |
| Provider-specific parser? | **No** |
| Provider-specific prompt text? | **No** (only provider/model API backend differs) |
| Same scorer / verifier? | **Yes** — frozen `score_item` / `verify_f1_certificate` |
| Claude-specific success path? | **No** |

---

## R1 `step` call policy

| Layer | Limit | Notes |
|-------|------:|-------|
| Prompt guidance | 16 (`R1_MAX_STEP_CALLS`) | Soft target in phase-1 prompt |
| Executor hard cap | 64 (`MAX_TOOL_CALLS_PER_ROUND`) | Shared with main R1 track |
| Observed GPT R1 | ~13.5 calls/item | Within guidance; **not** the extractability failure |

R1 is **designed to allow many `step` calls** during exploration. The invalid GPT R1 run is **not** explained by excessive stepping.

---

## Fixes applied (study-local; frozen hash protocol untouched)

1. **Canonical contract** — `constructible_final_answer_contract.py` embeds real `item_id` / `fsm_ids` in the example envelope.
2. **Provider-independent prompts** — phase-2 block identical for GPT and Claude.
3. **Study-local normalization** — `constructible_submission_normalize.py` repairs:
   - placeholder literals (GPT pattern),
   - missing / placeholder `fsm_ids` (Claude pattern),
   - wrong model `item_id` when it differs from the benchmark item (logged as `item_id_repaired_from_model_value`).
4. **Diagnostics** — per-item `final_submission_diagnostics` includes raw final text, parse path/errors, JSON keys, `certificate_type`, `final_json_found`, verifier outcome.
5. **Smoke gates** — `--smoke` enforces extractability=1.0, provider errors=0, final JSON found, `bisimulation_witness`, verifier invoked (`certificate_valid` is bool). R2C also requires non-empty `certificate_assembly`.
6. **Replay** — `solver.bisimulation_certificate` added to `tracks/replay.py` for R2C audit integrity.

**Explicitly unchanged:** hash-witness experiments, original F1 hash protocol, item IDs, cohort, task content, scoring metrics, verifier rules.

---

## Smoke tests (manual; require API keys)

All smokes use the same CLI and must exit 0 before any full rerun:

```bash
cd fsmreasonbench
export PYTHONPATH=src
```

| Smoke | Command |
|-------|---------|
| Claude R1 | `python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider anthropic --track R1 --smoke --force` |
| Claude R2C | `python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider anthropic --track R2C --smoke --force` |
| GPT R1 | `python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider openai --model gpt-4.1 --track R1 --smoke --force` |
| GPT R2C | `python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider openai --model gpt-4.1 --track R2C --smoke --force` |

Shell shortcuts: `./scripts/run_a1_constructible_equivalence.sh {claude,gpt}-{r1,r2c}-smoke`

Offline unit gate:

```bash
PYTHONPATH=src python3.12 -m pytest tests/unit/test_constructible_equivalence_protocol.py -q
```

---

## Full rerun commands (manual only after smokes pass)

```bash
# Claude
python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider anthropic --track R1 --force
python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider anthropic --track R2C --force

# GPT
python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider openai --model gpt-4.1 --track R1 --force
python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --provider openai --model gpt-4.1 --track R2C --force
```

---

## Interpretation guidance

- **Invalidate** all pre-fix constructible-equivalence extractability rates for both providers.
- After smokes pass, new runs measure model behavior under a **shared, parseable** bisimulation contract.
- Study-local normalization logs repairs in `final_submission_diagnostics.repairs_applied`; analyze repair rates separately when comparing providers.
- R1 `certificate_assembly` remains empty by design; use R2C assembly logs for synthesis attribution.

---

## Related files

- Contract: `src/fsmreasonbench/runners/constructible_final_answer_contract.py`
- Prompts: `src/fsmreasonbench/runners/constructible_equivalence_prompts.py`
- Parser/normalizer: `src/fsmreasonbench/runners/constructible_submission_normalize.py`
- Batch + smoke gate: `src/fsmreasonbench/runners/constructible_equivalence_batch.py`
- Tests: `tests/unit/test_constructible_equivalence_protocol.py`

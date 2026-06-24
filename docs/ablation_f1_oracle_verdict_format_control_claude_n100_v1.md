# Ablation: F1 Oracle-Verdict + Format-Control (Claude Sonnet n=100)

**Condition ID:** `f1_oracle_verdict_format_control`  
**Run root:** `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1`  
**Smoke run:** `runs/ablations_f1_oracle_verdict_format_control_claude_smoke_v1` (n=5)  
**Model:** `claude-sonnet-4-5-20250929` (Anthropic)  
**Cohort:** `f1-mixed-level3-v0.1-expanded-n100`, n=100, T=0.2  
**Frozen baseline:** `runs/frontier_claude_sonnet_tools_n100_v2` (F1 R1/R2 only)

> **Purpose.** Isolate whether F1 R1 certificate failures are driven by **verdict uncertainty** or **serialization/formatting** vs **semantic certificate construction**. The model receives the **oracle (gold) verdict**, must not re-derive it, and submits **certificate only** (no tools, no solver delegation). Parser and verifier are unchanged.

---

## Design

| Aspect | Ablation | Claude F1 R1 (frozen) | Claude F1 R2 (frozen) |
|--------|----------|----------------------|----------------------|
| Verdict source | Oracle-fixed in prompt | Model + tool plan | Model + tool execution |
| Tools | **Forbidden** | Plan only (no execution) | Execution |
| Track label | `AB1-oracle-verdict` | R1 | R2 |
| Prompt | Schema + 2 worked examples + fixed verdict | Standard R1 two-phase protocol | Standard R2 two-phase protocol |

**JSON repair (secondary):** smart-quote normalization before standard extraction; reported in `summary_json_repair.json`. Does not alter semantic certificate fields.

---

## Results (n=100)

### Primary metrics

| Metric | Ablation | Claude F1 R1 | Claude F1 R2 |
|--------|----------:|-------------:|-------------:|
| extractability_rate | 1.000 | 1.000 | 0.990 |
| verdict_accuracy | 1.000 | 1.000 | 1.000 |
| certificate_valid_rate | **0.340** | **0.460** | **1.000** |
| fully_correct_rate | **0.340** | **0.460** | **0.990** |

### Failure-stage counts (ablation)

| not_extractable | provider_error | verdict_wrong | certificate_invalid | correct |
|----------------:|---------------:|--------------:|--------------------:|--------:|
| 0 | 0 | 0 | 66 | 34 |

- **100% extractability** — failures are not formatting/extraction at the submission envelope level.
- **0 verdict_wrong** — models obey the fixed oracle verdict in JSON.
- **66 certificate_invalid** — remaining gap is **verifier rejection of certificate content**.

### JSON repair delta

Repair changed **0** items (Δcert = 0, Δfull = 0). Failures are **not** fixable by harmless quote trimming.

### Certificate failure taxonomy (n=100, cert_invalid=66)

| Category | Count | Share |
|----------|------:|------:|
| equivalence_hash_mismatch | 51 | 77.3% |
| acceptance_mismatch | 14 | 21.2% |
| replay_failure | 1 | 1.5% |

---

## Answers to research questions

### 1. Does providing the correct verdict improve certificate_valid_rate?

**Partially isolates verdict uncertainty — but does not match R1 cert.**

With oracle verdict, **verdict_accuracy = 1.0** and **verdict_wrong = 0**, yet **cert = 0.34** (34/100 fully correct). Verdict uncertainty is eliminated; certification remains the bottleneck.

Compared to frozen **Claude F1 R1 (cert = 0.46)**, ablation cert is **lower** (0.34 < 0.46). Removing tools while fixing the verdict does **not** outperform R1; tool-assisted planning in R1 appears to help certification modestly relative to certificate-only generation without execution.

### 2. Does strict schema + examples improve certificate_valid_rate?

**Not versus R1 tools; extractability is perfect.**

Schema + examples achieve **100% extractability** (vs R1 also 100%). Certificate validity **does not exceed R1** (0.34 vs 0.46). Format-control improves parseability but **does not close** the certification gap.

### 3. Does the gap to R2 remain?

**Yes — decisively.**

Ablation **full = 0.34** vs Claude F1 R2 **full = 0.99**. Execution-mediated certification (R2) remains necessary for near-complete fully-correct performance on F1 mixed items.

### 4. Are remaining failures semantic or formatting-related?

**Predominantly semantic.**

- JSON repair: **no change** in outcomes.
- Taxonomy: **77% equivalence_hash_mismatch**, **21% acceptance_mismatch** among certificate_invalid items.
- Failures reflect **incorrect witness construction** (hashes, traces, acceptance), not wrapper JSON formatting.

---

## Interpretation (decisive ablation)

1. **Knowing ≠ showing even with oracle verdict:** fixing the boolean answer leaves **66%** of items without valid certificates.
2. **R1 certificate gap is not primarily verdict guessing:** R1 already reaches verdict = 1.0; ablation confirms certification fails without correct witness/trace/hash construction.
3. **R2 effect is not replicated by prompt/format control:** the jump from ~0.46 (R1) to ~0.99 (R2) requires **tool execution**, not oracle verdict + schema examples alone.
4. **Primary failure mode:** `equivalence_hash_mismatch` on equivalent items — models struggle to compute minimized DFA hashes without solver assistance.

---

## Artifacts

| File | Description |
|------|-------------|
| `summary.json` | Primary cell summary |
| `summary_json_repair.json` | JSON-repair scoring summary |
| `scores.jsonl` / `scores_json_repair.jsonl` | Per-item scores |
| `results.jsonl` | Full run records |
| `combined_summary.json` | Matrix-style single-row summary |
| `report.md` | Auto-generated report |
| `certificate_failure_taxonomy.json` | Taxonomy export |
| `ablation_metadata.json` | Condition metadata |

---

## Reproduce

```bash
cd fsmreasonbench

# Smoke (n=5)
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
  --smoke --force \
  --out-dir runs/ablations_f1_oracle_verdict_format_control_claude_smoke_v1

# Full n=100
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
  --max-items 100 --force \
  --out-dir runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1

# Regenerate report only
PYTHONPATH=src python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
  --report-only \
  --out-dir runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1
```

**Code:** `src/fsmreasonbench/runners/ablation_prompts.py`, `ablation_batch.py`, `cli/run_f1_oracle_verdict_ablation.py`

---

## Exclusions

- Do **not** compare to `runs/frontier_claude_sonnet_full_n100_v1` (provider-contaminated).
- Do **not** overwrite frozen runs under `local_matrix_n100_t02_v2` or `frontier_claude_sonnet_tools_n100_v2`.

---

## Changelog

| Date | Event |
|------|-------|
| 2026-06-20 | Smoke n=5 passed; full n=100 completed (cert=0.34, 0 provider errors) |

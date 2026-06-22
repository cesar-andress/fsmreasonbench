# Local Matrix v1 Integrity Audit

**Date:** 2026-06-21  
**Source:** `runs/local_matrix_v1` (inspection only — no experiments rerun)  
**Expected matrix:** 4 models × 2 families × 3 tracks × 3 temperatures = **72 cells**  
**On disk:** **63** `scores.jsonl` files (62 complete n=20, 1 partial n=4, 9 cells absent)

---

## Executive summary

| Question | Verdict |
|----------|---------|
| 1. Same denominator for verdict & certificate? | **Yes** — both use extractable-item count; verified in all 63 scored cells |
| 2. Statistically meaningless cells? | **Yes — 15 cells** (11 low/zero extractability, 1 partial, 3 marginal) plus **2 cells dominated by Ollama infra errors** |
| 3. Temperature propagated? | **Yes** — `results.jsonl` stores correct T per cell; 77.5% of item responses differ across T=0/0.2/0.7 |
| 4. Aggregation bugs JSON ↔ report? | **Yes — two bugs:** stale `combined_summary.json` (18/63 cells); empty per-track table in `report.md` (renderer bug) |
| 5. Safe for science? | **48 cells** (extractable ≥ 15/20, complete) |
| 6. Must rerun? | **10 cells** (9 missing + 1 partial) **plus 13 unhealthy cells** (infra errors or extractable < 10) |

**Bottom line:** Per-cell metrics in `summary.json` / `scores.jsonl` are **internally consistent and arithmetically valid**. The **aggregate artifacts** (`combined_summary.json`, `report.md`) are **stale and incomplete**. Several cells — especially `llama3.1:8b` R1/R2 and `mistral-nemo:12b` R1 — must not be used for model comparison without rerun or explicit caveats.

---

## Methodology

Inspected without rerunning:

- `runs/local_matrix_v1/combined_summary.json`, `report.md`, `combined_summary.csv`
- All 63 cell directories: `scores.jsonl`, `results.jsonl`, `summary.json`, `transcripts/`
- Recomputation via `summarize_scoring_records()` (`evaluator/summary.py`) and `audit_matrix_scores()` (`evaluator/extractability_audit.py`)

Checks performed:

1. Denominator identity (verdict vs certificate vs extractable count)
2. `summary.json` vs recomputation from `scores.jsonl`
3. `scores.jsonl` vs `results.jsonl` row counts and item-id order
4. Transcript file presence for every results row
5. Stored `temperature` field vs directory path
6. Cross-temperature response diffs (MD5 of `raw_response_text` prefix)
7. `combined_summary.json` / `report.md` vs on-disk cell metrics

---

## 1. Are verdict and certificate computed on the same denominator?

**Yes.** In all 63 cells:

| Metric | Numerator | Denominator |
|--------|-----------|-------------|
| `extractability_rate` | extractable items | **total n** |
| `verdict_accuracy` | `verdict_correct is True` | **extractable items** |
| `certificate_valid_rate` | `certificate_valid is True` | **extractable items** |
| `fully_correct_rate` | `fully_correct is True` | **total n** |

Implementation (`evaluator/summary.py` lines 40–46):

```python
verdict_accuracy = verdict_correct_count / extractable_count if extractable_count else 0.0
certificate_valid_rate = certificate_valid_count / extractable_count if extractable_count else 0.0
fully_correct_rate = fully_correct_count / n
```

**Audit result:** `verdict_scored == certificate_scored == extractable_items` in **63/63** cells. All per-cell `summary.json` files match recomputation from `scores.jsonl`.

**Caveat (not a bug):** `fully_correct_rate` uses a **different** denominator (total n). A cell can show high `verdict_accuracy` and zero `fully_correct_rate` when certificates fail — that is expected, not an aggregation error.

**Misleading but valid:** When extractable count is tiny (e.g. 2/20), `verdict_accuracy = 0.667` or `1.000` reflects only those 2 items. The rate is arithmetically correct but **not statistically meaningful** (see §2).

---

## 2. Are any cells statistically meaningless due to low extractability?

**Yes.** Classification thresholds:

| Tier | Criterion | Count | Use |
|------|-----------|------:|-----|
| **Safe** | n=20 and extractable ≥ 15 | 48 | Primary analysis |
| **Marginal** | n=20 and extractable 10–14 | 3 | Secondary; report n_extractable |
| **Unsafe** | n=20 and extractable < 10 (incl. 0) | 11 | Do not compare rates |
| **Partial** | 0 < n < 20 | 1 | Invalid — rerun |
| **Missing** | no scores on disk | 9 | Invalid — rerun |

### Unsafe cells (verdict/cert rates unreliable)

| Model | Family | Track | Temp | n | Extractable | Reported verdict | Notes |
|-------|--------|-------|-----:|--:|------------:|-----------------:|-------|
| `mistral-nemo:12b` | C2 | R1 | 0.2 | 20 | **0** | 0.000 | **All 20 items:** `Connection refused` (Ollama down) |
| `mistral-nemo:12b` | F1 | R2 | 0.7 | 20 | **0** | 0.000 | Protocol/extractability collapse |
| `mistral-nemo:12b` | C2 | R1 | 0 | 20 | 3 | 0.667 | 17/20 infra errors (`Connection refused` / connection drop) |
| `mistral-nemo:12b` | F1 | R1 | 0 | 20 | 2 | 0.500 | Tool/extractability failure |
| `mistral-nemo:12b` | F1 | R1 | 0.2 | 20 | 2 | 0.500 | Tool/extractability failure |
| `mistral-nemo:12b` | F1 | R2 | 0 | 20 | 1 | 1.000 | **n=1** — meaningless 100% |
| `mistral-nemo:12b` | F1 | R2 | 0.2 | 20 | 2 | 1.000 | **n=2** — meaningless 100% |
| `mistral-nemo:12b` | F1 | R1 | 0.7 | 20 | 5 | 0.800 | High variance |
| `llama3.1:8b` | C2 | R1 | 0 | 20 | 2 | 0.000 | Tool timeouts / protocol errors |
| `gemma2:9b` | F1 | R2 | 0 | 20 | 9 | 1.000 | Low extractability on R2 |
| `gemma2:9b` | F1 | R2 | 0.2 | 20 | 9 | 1.000 | Low extractability on R2 |

### Partial cell

| Model | Family | Track | Temp | Progress | Extractable |
|-------|--------|-------|-----:|----------|------------:|
| `llama3.1:8b` | C2 | R1 | 0.2 | **4/20** | 1 |

### Marginal cells (usable with explicit denominator)

| Model | Family | Track | Temp | Extractable |
|-------|--------|-------|-----:|------------:|
| `gemma2:9b` | F1 | R2 | 0.7 | 10/20 |
| `qwen2.5-coder:7b` | F1 | R1 | 0.7 | 11/20 |
| `qwen2.5-coder:7b` | F1 | R2 | 0.7 | 14/20 |

### Parser / protocol failure modes (aggregate, 1244 item scores)

Non-extractable items (235 total) break down as:

| failure_stage / track_failure_class | Count |
|-------------------------------------|------:|
| `not_extractable` / `final_submission_not_extractable` | 146 |
| `not_extractable` / `tool_execution_error` | 57 |
| `not_extractable` / `disallowed_tool` | 28 |
| `not_extractable` / `invalid_tool_plan` | 4 |

Top `parse_errors` (not all imply parser bugs — many are runner/infra):

| Error | Count |
|-------|------:|
| `fsm_ids must be an array of length 2` | 167 |
| `Connection refused` (Ollama) | 36 |
| `equivalence_witness.payload.minimized_hash_*` | 50 |
| `timed out` | 20 |

These are **legitimate scoring outcomes** (model failed to produce extractable JSON), not post-hoc repairs. They deflate extractability and can make verdict/cert rates unstable when the extractable subset is small.

---

## 3. Is temperature correctly propagated?

**Yes — at the runner level.**

Evidence:

1. **`results.jsonl`** stores `"temperature": <float>` on every row; **0/63** cells have a mismatch between directory (`temp_0`, `temp_0.2`, `temp_0.7`) and stored value.
2. **Cross-temperature response diff:** For item IDs present in all three complete temperature dirs, **310/400 (77.5%)** have differing `raw_response_text` (first 500 chars) across T=0, 0.2, 0.7.
3. Example (`qwen2.5-coder:7b` C2): identical T=0 vs T=0.7 responses on only 1/20 (R0), 7/20 (R1), 10/20 (R2). Identical responses at T>0 often occur when the model hits the same protocol failure or deterministic tool path — not evidence of a stuck temperature parameter.

Separate diagnostic run (`runs/ollama_temperature_diagnostic/`) confirmed Ollama HTTP payloads carry distinct `options.temperature` values.

**Caveat:** Temperature sensitivity tables in `report.md` cover **only mistral** (stale aggregate) and should not be read until `combined_summary.json` is regenerated over all models.

---

## 4. Are there aggregation bugs between JSON and report.md?

**Yes — three distinct issues.**

### 4a. Stale `combined_summary.json` (critical)

| Artifact | Content | Reality on disk |
|----------|---------|-----------------|
| `combined_summary.json` → `models` | `[mistral-nemo:12b]` only | 4 model dirs |
| `cell_inventory` / `track_rows` | **18 cells** | **63 scored cells** |
| `cell_status_counts.completed` | 18 | 62 complete + 1 partial |

The 45 cells for `gemma2:9b`, `llama3.1:8b`, and `qwen2.5-coder:7b` exist on disk with valid `summary.json` but are **absent from the combined aggregate**. Per-cell metrics for those models are valid; the **matrix-level JSON/CSV is wrong**.

**Fix (no rerun):** Regenerate combined summary from all on-disk cells (e.g. re-run report-only mode once implemented, or manual merge).

### 4b. Empty per-track metrics table in `report.md` (renderer bug)

`report.md` sections **"C2 — per-track metrics"** and **"F1 — per-track metrics"** contain headers only — **0 data rows**.

Root cause in `runners/track_pilot_models.py` `render_track_pilot_report()` (~lines 1070–1087): `lines.append(...)` is **unreachable** after `continue` when `row is not None`:

```python
if row is None:
    continue
    lines.append(...)  # dead code — never runs when row exists
```

Delegation-gap, temperature-sensitivity, and failure-movement tables **do render** (18 mistral rows each). R2 summary table is populated. Only the main per-track metrics grid is blank.

### 4c. `report.md` consistent with stale JSON (not a second bug)

Regenerating `report.md` from current `combined_summary.json` yields **byte-identical** output. The markdown faithfully reflects the stale 18-cell JSON; the bug is **stale input + dead-code renderer**, not numeric drift within the mistral subset.

**Mistral subset check:** All 18 mistral cells in `combined_summary.json` match recomputation from `scores.jsonl` (metrics agree to 1e-9).

### 4d. Per-cell artifacts are healthy

| Check | Result |
|-------|--------|
| `summary.json` vs `scores.jsonl` | **63/63 match** |
| `scores.jsonl` vs `results.jsonl` length | **63/63 match** |
| item_id order scores ↔ results | **0 mismatches** |
| Missing transcript files | **0** |

---

## 5. Which cells are safe to use scientifically?

**48 cells** with n=20 and extractable ≥ 15/20. These support exploratory comparison of R0/R1/R2 and temperature **within model**, provided you always report extractable count alongside rates.

### Safe cells by model

**`gemma2:9b` (17/18 on disk):** All C2 (9 cells); F1 R0/R1 all temps (6 cells); F1 R2 T=0.7 only (1 cell).  
*Exclude:* F1 R2 T=0, T=0.2 (9 extractable).

**`llama3.1:8b` (14/27 expected — incomplete matrix):** C2 R0 all temps (3); C2 R2 T=0 (1); F1 R0 all temps (3).  
*Exclude:* C2 R1 T=0 (2 extractable); all missing R1/R2 F1 and most llama C2 R1/R2 temps.

**`mistral-nemo:12b` (12/18):** C2 R0/R2 all temps (6); C2 R1 T=0.7 (1); F1 R0 all temps (3); F1 R1 T=0.7 excluded (5 extractable).  
*Exclude:* all mistral F1 R1/R2 except none safe; C2 R1 T=0, T=0.2.

**`qwen2.5-coder:7b` (18/18 on disk):** All C2 (9 cells); F1 R0 all temps (3); F1 R1/R2 T=0, T=0.2 (4); F1 R2 T=0.7 marginal (14 extractable — use with caveat).  
*Strongest panel overall* for tool-track and temperature analysis.

### Recommended primary panel for papers

Use **`qwen2.5-coder:7b`** and **`gemma2:9b` C2 + F1 R0/R1** as the cleanest complete submatrix. Treat **`mistral-nemo:12b` R1** and **`llama3.1:8b` tool tracks** as case studies in protocol failure, not capability measurement, until rerun.

---

## 6. Which cells must be rerun?

### Mandatory (no valid n=20)

| Priority | Model | Family | Track | Temp | Reason |
|----------|-------|--------|-------|-----:|--------|
| P0 | `llama3.1:8b` | C2 | R1 | 0.2 | **Partial 4/20** (interrupted) |
| P0 | `llama3.1:8b` | C2 | R2 | 0.2 | Missing |
| P0 | `llama3.1:8b` | C2 | R1 | 0.7 | Missing |
| P0 | `llama3.1:8b` | C2 | R2 | 0.7 | Missing |
| P0 | `llama3.1:8b` | F1 | R1 | 0, 0.2, 0.7 | Missing (3 cells) |
| P0 | `llama3.1:8b` | F1 | R2 | 0, 0.2, 0.7 | Missing (3 cells) |

### Strongly recommended (complete but invalid / infra-contaminated)

| Model | Family | Track | Temp | Reason |
|-------|--------|-------|-----:|--------|
| `mistral-nemo:12b` | C2 | R1 | 0.2 | 100% Ollama `Connection refused` |
| `mistral-nemo:12b` | C2 | R1 | 0 | 85% infra errors |
| `mistral-nemo:12b` | F1 | R2 | 0.7 | 0 extractable |
| `llama3.1:8b` | C2 | R1 | 0 | 2/20 extractable (timeouts) |
| All mistral | F1 | R1/R2 | various | extractable ≤ 5 on most cells |

### Regenerate aggregates (no model rerun)

After any cell reruns, rebuild:

```bash
# Regenerate combined_summary.json + report.md from all on-disk cells
# (requires report-only path or full matrix completion command)
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 --tracks R0,R1,R2 --temperatures 0,0.2,0.7 \
  --out-dir runs/local_matrix_v1 --report-only
```

Also fix `render_track_pilot_report()` dead code so per-track tables populate.

---

## Appendix A — Full cell inventory

Legend: **OK** = safe (≥15 extractable); **M** = marginal (10–14); **U** = unsafe (<10); **P** = partial; **—** = missing

| Model | Fam | Track | T=0 | T=0.2 | T=0.7 |
|-------|-----|-------|-----|-------|-------|
| `gemma2:9b` | C2 | R0 | OK | OK | OK |
| | | R1 | OK | OK | OK |
| | | R2 | OK | OK | OK |
| | F1 | R0 | OK | OK | OK |
| | | R1 | OK | OK | OK |
| | | R2 | U | U | M |
| `llama3.1:8b` | C2 | R0 | OK | OK | OK |
| | | R1 | U | P | — |
| | | R2 | OK | — | — |
| | F1 | R0 | OK | OK | OK |
| | | R1 | — | — | — |
| | | R2 | — | — | — |
| `mistral-nemo:12b` | C2 | R0 | OK | OK | OK |
| | | R1 | U | U | OK |
| | | R2 | OK | OK | OK |
| | F1 | R0 | OK | OK | OK |
| | | R1 | U | U | U |
| | | R2 | U | U | U |
| `qwen2.5-coder:7b` | C2 | R0 | OK | OK | OK |
| | | R1 | OK | OK | OK |
| | | R2 | OK | OK | OK |
| | F1 | R0 | OK | OK | OK |
| | | R1 | OK | OK | M |
| | | R2 | OK | OK | M |

---

## Appendix B — Answers at a glance

1. **Same denominator for verdict & certificate?** Yes (extractable items); `fully_correct_rate` differs (uses n).
2. **Statistically meaningless cells?** Yes — 11 unsafe + 1 partial + 3 marginal; mistral C2 R1 T=0.2 is infra garbage.
3. **Temperature propagated?** Yes in runner/Ollama; stored correctly; 77.5% cross-T response diffs.
4. **Aggregation bugs?** Yes — stale combined summary (45/63 cells missing); empty per-track table in report (code bug); per-cell JSONL is fine.
5. **Safe cells?** 48 (see §5).
6. **Must rerun?** 10 missing/partial + 13 unhealthy (see §6).

---

## Related docs

- `docs/extractability_audit.md` — per-cell denominator table (63 cells)
- `docs/local_matrix_v1_failure_audit.md` — runner timeout / tool-routing failures (pre-repair)
- `runs/ollama_temperature_diagnostic/` — Ollama payload temperature probe

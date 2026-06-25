# TOSEM experiment extension plan

**Status:** Infrastructure implemented; campaigns **not** executed automatically.  
**Scope:** Post-freeze extension studies addressing external TOSEM methodological review.  
**Constraint:** Benchmark, verifier, scoring, cohorts, task generation, and **all frozen runs** remain unchanged.

---

## Implemented experiments

| ID | Name | Module / CLI | Output roots |
|----|------|--------------|--------------|
| **A** | Run-to-run stability | `fsmreasonbench.experiments.replicate_studies`, `cli.run_frontier_replicate_study` | `runs/*_replicates/replicate_XX/`, `aggregate_replicates.json` |
| **B** | GPT attribution ladder | `cli.run_f1_oracle_verdict_ablation`, `cli.run_f1_r2_attribution_ablation` (`--provider openai`) | `runs/ablations_f1_oracle_verdict_format_control_gpt_n100_v1/`, `runs/ablations_f1_r2_attribution_gpt_n100_v1/{R2A,R2B,R2C}/` |
| **C** | Cross-model attribution | `evaluator.cross_model_attribution_export` | `docs/tosem_extension_experiments_v1/cross_model_attribution_comparison.json`, `extension_cross_model_attribution.tex` |
| **D** | Run stability analysis | `evaluator.replicate_stability_export` | `replicate_stability_*.json`, `extension_stability_vs_cross_model.tex`, stability plots |
| **E** | Paper integration | `evaluator.tosem_extension_exports`, `cli.export_tosem_extension_experiments` | `paper/tables/extension_*.tex`, `paper/figures/extension_*.pdf` |

Frozen historical GPT R2C (`runs/ablations_f1_r2c_gpt_n100_v1/`) is preserved; the new ladder writes to **`ablations_f1_r2_attribution_gpt_n100_v1/`** (parallel to Claude).

---

## Recommended execution order

Execute manually in this order. Each step assumes the previous completed successfully.

| Step | Command | Experiment | Depends on |
|------|---------|------------|------------|
| 1 | `./scripts/run_tosem_extension_campaigns.sh gpt-oracle-smoke` | B | `OPENAI_API_KEY` |
| 2 | `./scripts/run_tosem_extension_campaigns.sh gpt-oracle` | B | step 1 |
| 3 | `./scripts/run_tosem_extension_campaigns.sh gpt-r2-smoke` | B | step 2 (oracle dir exists) |
| 4 | `./scripts/run_tosem_extension_campaigns.sh gpt-r2-all` | B | step 3 |
| 5 | `./scripts/run_tosem_extension_campaigns.sh replicate-claude-smoke` | A | `ANTHROPIC_API_KEY` |
| 6 | `./scripts/run_tosem_extension_campaigns.sh replicate-claude` | A | step 5 |
| 7 | `./scripts/run_tosem_extension_campaigns.sh replicate-gpt-smoke` | A | `OPENAI_API_KEY`, `--model gpt-4.1` via campaign config |
| 8 | `./scripts/run_tosem_extension_campaigns.sh replicate-gpt` | A | step 7 |
| 9 | `./scripts/run_tosem_extension_campaigns.sh replicate-aggregate` | A, D | steps 6 & 8 (≥1 replicate each) |
| 10 | `./scripts/run_tosem_extension_campaigns.sh export-extensions` | C, D, E | steps 4 & 9 for full tables; partial export OK before |

**Alternative:** Run steps 5–8 before B if replicate stability is higher priority than GPT ladder completion.

---

## Execution commands (reference)

### Experiment A — replicates

```bash
cd fsmreasonbench
export PYTHONPATH=src

# Claude (default 3 replicates in study config)
python -m fsmreasonbench.cli.run_frontier_replicate_study \
  --study-config configs/studies/claude_frontier_replicates_n100_v1.json

# Single replicate
python -m fsmreasonbench.cli.run_frontier_replicate_study \
  --study-config configs/studies/claude_frontier_replicates_n100_v1.json \
  --replicate-id 2

# GPT (match frozen model id)
python -m fsmreasonbench.cli.run_frontier_replicate_study \
  --study-config configs/studies/gpt_frontier_replicates_n100_v1.json

# Aggregate + stability exports only
python -m fsmreasonbench.cli.run_frontier_replicate_study \
  --study-config configs/studies/claude_frontier_replicates_n100_v1.json \
  --aggregate-only
```

Study configs set `--replicates N` (default **3** in JSON). Override at CLI:

```bash
python -m fsmreasonbench.cli.run_frontier_replicate_study \
  --config configs/frontier/frontier_claude_sonnet_tools_n100_v2.json \
  --replicates 5
```

### Experiment B — GPT ladder

```bash
python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
  --provider openai --model gpt-4.1

python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation \
  --provider openai --model gpt-4.1 --all
```

### Experiments C–E — exports (no API)

```bash
python -m fsmreasonbench.cli.export_tosem_extension_experiments
```

---

## Estimated runtime

Assumptions: n=100 per cell, T=0.2, same timeouts as frozen campaigns (~1 h/cell cap), typical provider latency.

| Campaign | Cells / items | Replicates (default) | Wall time (order of magnitude) |
|----------|---------------|----------------------|----------------------------------|
| GPT Oracle+Format | 100 items | 1 | 2–6 h |
| GPT R2A + R2B + R2C | 3 × 100 items | 1 | 6–18 h |
| Claude frontier replicate | 4 cells × 100 | 3 | 12–36 h |
| GPT frontier replicate | 4 cells × 100 | 3 | 12–36 h |

Smokes (n=1 or n=5) complete in minutes and should be run first.

---

## Expected API cost (order of magnitude)

Costs depend on token usage per track (R1 < R2). Use provider dashboards for ground truth.

| Campaign | Approx. paid API calls | Notes |
|----------|------------------------|-------|
| GPT Oracle+Format n=100 | ~100 | No tools; lower tokens than R2 |
| GPT R2 ladder n=100 × 3 | ~300 | Tool phases + certificates |
| Claude frontier replicate | 4 × 100 × replicates | Anthropic Sonnet pricing |
| GPT frontier replicate | 4 × 100 × replicates | Match `gpt-4.1` list pricing |

**Rough total (3 replicates each frontier + full GPT ladder):** on the order of **$200–$800 USD** depending on R2 tool trace length and retry rate. Run smokes and one replicate before committing to full matrix.

---

## Expected outputs

### Per-run artifact layout (unchanged convention)

Each executed cell / mode produces:

- `scores.jsonl`, `results.jsonl`, `summary.json`
- `report.md`, transcripts
- Study-level: `combined_summary.json`

### Extension-specific artifacts

| Path | Description |
|------|-------------|
| `runs/frontier_claude_sonnet_tools_n100_v2_replicates/replicate_01/…` | Claude replicate runs |
| `runs/frontier_gpt_tools_n100_v1_replicates/replicate_01/…` | GPT replicate runs |
| `runs/*_replicates/aggregate_replicates.json` | mean, std, min, max, bootstrap CI, CV per metric |
| `docs/tosem_extension_experiments_v1/replicate_stability_*.json` | Within-model variance (Experiment D) |
| `docs/tosem_extension_experiments_v1/cross_model_attribution_comparison.json` | Paired Claude vs GPT (Experiment C) |
| `docs/tosem_extension_experiments_v1/run_stability_vs_cross_model.json` | Gaps vs replicate noise ceiling |
| `docs/tosem_extension_experiments_v1/extension_manifest.json` | Export manifest |
| `paper/tables/extension_*.tex` | New LaTeX tables only |
| `paper/figures/extension_*.pdf` | Stability + cross-model plots |

Metrics aggregated in `aggregate_replicates.json`:

- `extractability_rate`, `verdict_accuracy`, `certificate_valid_rate`, `fully_correct_rate`

---

## Manuscript sections affected

| Section | Extension evidence |
|---------|-------------------|
| **Experimental design** | Run-to-run stability protocol (`--replicates`), GPT ladder parity with Claude |
| **Results — GPT / cross-model** | Full attribution ladder; paired Claude vs GPT table |
| **Threats to validity** | Single-run limitation addressed by replicate CV and bootstrap CIs |
| **Discussion** | Whether attribution gaps exceed replicate variability (Experiment D) |

Suggested `\input{}` targets (after campaigns complete):

- `paper/tables/extension_cross_model_attribution.tex`
- `paper/tables/extension_replicate_variability_<campaign_id>.tex`
- `paper/tables/extension_stability_vs_cross_model.tex`
- `paper/figures/extension_replicate_stability_<campaign_id>.pdf`
- `paper/figures/extension_cross_model_attribution.pdf`

Do **not** replace frozen `\input{}` paths for existing TOSEM tables.

---

## Reviewer concerns addressed

| Concern | Response |
|---------|----------|
| Single-run frontier results | Experiment A: N independent replicates, aggregate stats + bootstrap CI |
| Incomplete GPT attribution ladder | Experiment B: Oracle+Format, R2A, R2B, R2C with identical protocol |
| Cross-model comparisons asymmetric | Experiment C: paired summaries, effect sizes, bootstrap CIs |
| Effect size vs noise | Experiment D: compare \|Δ\| to F1 R2 replicate std ceiling |
| Reproducibility | Configs under `configs/studies/`, shell launcher, this plan, updated freeze extension § |

---

## Verification (no API)

```bash
cd fsmreasonbench
pip install -e ".[dev,plot]"
pytest tests/unit/test_replicate_studies.py \
       tests/unit/test_cross_model_attribution_export.py \
       tests/unit/test_f1_r2_attribution_ablation_cli.py -q
PYTHONPATH=src python3 -m fsmreasonbench.cli.export_tosem_extension_experiments
```

Partial exports are expected before campaigns run (`pending_studies` in manifest).

---

## Freeze policy

Extension campaigns are **additive**. See **Extension campaigns (post-freeze v1)** in:

- `paper/EXPERIMENTAL_FREEZE_TOSEM.md`
- `fsmreasonbench/docs/EXPERIMENTAL_FREEZE_TOSEM.md`

Frozen tables and run roots listed in the original freeze sections must not be edited or overwritten.

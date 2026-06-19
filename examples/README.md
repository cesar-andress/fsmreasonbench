# Examples

Hand-generated and tool-generated **illustrative items** (not full cohorts).

## Benchmark items

| File | Description |
|------|-------------|
| `item_C2_reachability_seed42.json` | Positive C2 reachability item (`seed=42`, `\|Q\|=5`) |
| `item_C2_reachability_seed43_negative.json` | Negative C2 reachability item (`seed=43`, unreachable target) |
| `item_F1_separation_seed42.json` | F1 smoke item (`seed=42`, `min_distinguishing_trace_length=1`) |
| `item_F1_separation_seed6_hard.json` | F1 hard item (`seed=6`, `ℓ_dist=4`, `min=3`) |

Regenerate:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42 \
  --output examples/item_C2_reachability_seed42.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 42 \
  --min-distinguishing-trace-length 1 \
  --output examples/item_F1_separation_seed42.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 6 \
  --min-distinguishing-trace-length 3 \
  --output examples/item_F1_separation_seed6_hard.json
```

Each item passes `self_verify_item`: generator → oracle → certificate → verifier.

## C2 submissions

| File | Expected outcome |
|------|------------------|
| `submission_C2_correct.json` | `failure_stage=correct` (positive) |
| `submission_C2_negative_correct.json` | `failure_stage=correct` (negative) |
| `submission_C2_wrong_verdict.json` | `failure_stage=verdict_wrong` |
| `submission_C2_invalid_certificate.json` | `failure_stage=certificate_invalid` |
| `submission_C2_malformed.json` | `failure_stage=not_extractable` |

Score a submission:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.score_submission \
  --item examples/item_C2_reachability_seed42.json \
  --submission examples/submission_C2_correct.json
```

## Transcripts

| File | Description |
|------|-------------|
| `transcript_C2_correct.json` | Full evaluation transcript for correct positive submission |

Rescore:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.rescore_transcript \
  --transcript examples/transcript_C2_correct.json
```

## C2 baselines

Reference systems (no LLM required):

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_C2_reachability_seed42.json --score
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline random --item examples/item_C2_reachability_seed42.json --seed 123
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline invalid --item examples/item_C2_reachability_seed42.json
```

| Baseline | Expected scoring |
|----------|------------------|
| `oracle` | `failure_stage=correct` |
| `random` | Usually `verdict_wrong` or `certificate_invalid` |
| `invalid` | `failure_stage=not_extractable` |

## F1 separation (flagship)

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_F1_separation_seed42.json --score
```

**Verdict:** `false` = DFAs are **not equivalent**. Certificate: `distinguishing_trace`.

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_batch \
  --family F1 --n 100 --seed 1 --out runs/f1_items.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_f1_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/f1_smoke
```

Default benchmark generation uses `min_distinguishing_trace_length=2`.

> **Constructive F1 warning (levels ≥ 3):** Capability-surface F1 batches use chain+sink constructive generation. Scores may rise with `ℓ_dist` because gold traces follow regular patterns, not necessarily because models reason more deeply. Audit items before interpreting curves:

```bash
python -m fsmreasonbench.cli.audit_f1_items \
  --items runs/capability_surface_models/F1/min_distinguishing_trace_length_5/items.jsonl \
  --out runs/f1_audit_level5.json
```

Summary fields: `repeated_trace_rate`, `final_acceptance_only_rate`, `average_branching_along_witness`, `sink_transition_ratio`, `unique_gold_traces`.

## Capability surface (exploratory, non-frozen)

Sweep difficulty levels and summarize oracle/random/invalid baselines:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_capability_surface \
  --families C2,F1 --n-per-level 50 --seed 1 --out-dir runs/capability_surface
```

| Family | Difficulty axis | Levels swept |
|--------|-----------------|--------------|
| C2 | `min_witness_length` | 1–5 |
| F1 | `min_distinguishing_trace_length` | 1–5 |

Writes per family/level items, baseline scores, summaries, plus `combined_summary.json` and `combined_summary.csv`. Generation failures abort by default; pass `--skip-failed-levels` to record skipped levels instead.

Not a frozen cohort and not for paper claims.

## Ollama exploratory evaluation

Requires a running [Ollama](https://ollama.com) server. Use the venv Python (`python`, not system `python3.11`) or `PYTHONPATH=src`:

```bash
python -m fsmreasonbench.cli.run_ollama_batch \
  --model qwen2.5-coder:7b \
  --items runs/capability_surface/C2/min_witness_length_2/items.jsonl \
  --out runs/ollama_c2_qwen7b.jsonl \
  --out-dir runs/ollama_c2_qwen7b \
  --temperature 0 \
  --max-items 10

python -m fsmreasonbench.cli.summarize_scores \
  --scores runs/ollama_c2_qwen7b/scores.jsonl

python -m fsmreasonbench.cli.inspect_failures \
  --scores runs/ollama_c2_qwen7b/scores.jsonl \
  --results runs/ollama_c2_qwen7b.jsonl \
  --limit 5
```

Inspect failure stages (`not_extractable`, `verdict_wrong`, `certificate_invalid`) with aggregate rates, sample `item_id`s per stage, raw-response excerpts, and parsed submissions when extractable. Pass `--json` for machine-readable output.

```bash
python -m fsmreasonbench.cli.inspect_failures \
  --scores runs/ollama_c2_qwen7b/scores.jsonl \
  --results runs/ollama_c2_qwen7b.jsonl \
  --limit 5 \
  --json
```

Writes per-item transcripts under `{out-dir}/transcripts/`, scoring JSONL at `{out-dir}/scores.jsonl`, and `summary.json`. Exploratory only — not for paper claims.

## Multi-model pilot runner

Run the same C2/F1 item batches across multiple Ollama models and write a comparative report:

```bash
python -m fsmreasonbench.cli.run_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --c2-items runs/capability_surface_smoke2/C2/min_witness_length_2/items.jsonl \
  --f1-items runs/capability_surface_smoke2/F1/min_distinguishing_trace_length_2/items.jsonl \
  --max-items 20 \
  --temperature 0 \
  --out-dir runs/pilot_v1
```

Layout per model/family: `{out-dir}/{model_dir}/{family}/scores.jsonl`, `results.jsonl`, `transcripts/`. Root outputs: `combined_summary.json`, `combined_summary.csv`, `report.md`. Exploratory only — not for paper claims.

## Model capability-surface evaluation

Sweep difficulty levels 1–5 with multiple Ollama models:

```bash
python -m fsmreasonbench.cli.run_capability_surface_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --levels 1,2,3,4,5 \
  --n-per-level 20 \
  --out-dir runs/capability_surface_models

python -m fsmreasonbench.cli.plot_capability_surface \
  --summary runs/capability_surface_models/combined_summary.json

python -m fsmreasonbench.cli.export_capability_surface_report \
  --summary runs/capability_surface_models/combined_summary.json \
  --out-md docs/capability_surface_report.md \
  --out-tex ../paper/tables/capability_surface_summary.tex \
  --out-csv docs/capability_surface_summary.csv
```

Requires `pip install 'fsmreasonbench[plot]'` (matplotlib) for plotting. Default output: `runs/capability_surface_models/` with per-level/per-model scores, `combined_summary.*`, `report.md`, and PNG curves.

The export CLI accepts incomplete summaries (reports missing family/level/model cells). Pass `--strict` to fail on gaps. Synthetic example input: [`capability_surface_summary_synthetic.json`](capability_surface_summary_synthetic.json).

## Exploratory batch evaluation (non-frozen)

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_batch \
  --n 100 --seed 1 --out runs/c2_items.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.evaluate_baseline_batch \
  --baseline oracle --items runs/c2_items.jsonl --out runs/oracle_scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.summarize_scores \
  --scores runs/oracle_scores.jsonl
```

Output under `runs/` is gitignored; not a frozen cohort.

## C2 smoke baseline check

One command runs all three baselines on the same generated batch and writes per-baseline plus combined summaries:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_c2_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/c2_smoke
```

Expected separation:

| Baseline | Typical `fully_correct_rate` | Typical `extractability_rate` |
|----------|---------------------------|------------------------------|
| `oracle` | 1.0 | 1.0 |
| `random` | ≪ 1.0 (deterministic under seed) | 1.0 |
| `invalid` | 0.0 | 0.0 |

Artifacts in `runs/c2_smoke/`: `c2_items.jsonl`, `{oracle,random,invalid}_scores.jsonl`, `{oracle,random,invalid}_summary.json`, `combined_summary.json`.

# Examples

Hand-generated and tool-generated **illustrative items** (not full cohorts).

## Benchmark items

| File | Description |
|------|-------------|
| `item_C2_reachability_seed42.json` | Positive C2 reachability item (`seed=42`, `\|Q\|=5`) |
| `item_C2_reachability_seed43_negative.json` | Negative C2 reachability item (`seed=43`, unreachable target) |

Regenerate:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42 \
  --output examples/item_C2_reachability_seed42.json
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

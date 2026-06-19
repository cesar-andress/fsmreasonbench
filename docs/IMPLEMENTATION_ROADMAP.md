# Implementation roadmap

**Principle:** Build the verifier before the generator. Prove one task end-to-end before widening.

## Phase 1 — Core infrastructure ✅

| Milestone | Status |
|-----------|--------|
| P1.1 FSM model (DFA, NFA) + canonical serialization + hashing | ✅ |
| P1.2 JSON schemas (fsm, reachability certificate, C2 question) | ✅ |
| P1.3 Oracle: simulation, reachability, shortest path | ✅ |
| P1.4 Verifier: reachability certificates (independent) | ✅ |
| P1.5 Tests: roundtrip, oracle, verifier, invalid rejection | ✅ |

## Phase 2 — First benchmark vertical ✅

| Milestone | Status |
|-----------|--------|
| P2.1 Seeded C2 reachability generator (`|Q|` difficulty) | ✅ |
| P2.2 Benchmark item assembly (FSM, question, gold, cert, difficulty) | ✅ |
| P2.3 Self-verification (generator → oracle → verifier) | ✅ |
| P2.4 Golden example item in `examples/` | ✅ |
| P2.5 CLI `generate_one.py` | ✅ |
| P2.6 Generator difficulty controls + negative items | ✅ |

**Success criterion met:** first self-verifying benchmark item.

## Phase 3 — Evaluation infrastructure ✅

| Milestone | Status |
|-----------|--------|
| P3.1 C2 answer parser + extractability gate | ✅ |
| P3.2 C2 scoring (extractability vs correctness) | ✅ |
| P3.3 Transcript recording + deterministic rescore | ✅ |
| P3.4 CLI `score_submission` / `rescore_transcript` | ✅ |
| P3.5 Baselines: random, oracle ceiling, invalid | ✅ |
| P3.6 C2 batch generation + baseline batch evaluation + summaries | ✅ |
| P3.7 C2 smoke baseline batch runner (oracle / random / invalid) | ✅ |

**Success criterion met:** C2 evaluation path with interpretable reference baselines and exploratory batch runs.

## Phase 4+ — Not started

- F1 separation / witness
- F2 non-materialized composition
- F3 constructive synthesis
- F4 formalization fidelity
- Multi-track infrastructure
- Contamination / frozen cohorts / Zenodo release

## Module map

```
src/fsmreasonbench/
  models/          # canonical FSM
  oracle/          # reference decision procedures
  certificates/    # oracle-side certificate builders
  verifier/        # independent verification (no oracle import)
  generator/       # seeded instance generation
  items/           # benchmark item assembly + self_verify
  evaluator/       # C2 parser, scorer, transcripts, batch, summary
  baselines/       # C2 reference systems (oracle, random, invalid)
  cli/             # generate_one, score_submission, rescore_transcript, run_baseline,
                   # generate_batch, evaluate_baseline_batch, summarize_scores,
                   # run_c2_smoke_baselines
```

## Run

```bash
pip install -e ".[dev]"
pytest
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.score_submission \
  --item examples/item_C2_reachability_seed42.json \
  --submission examples/submission_C2_correct.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.rescore_transcript \
  --transcript examples/transcript_C2_correct.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_C2_reachability_seed42.json --score
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_batch \
  --n 100 --seed 1 --out runs/c2_items.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.evaluate_baseline_batch \
  --baseline oracle --items runs/c2_items.jsonl --out runs/oracle_scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.summarize_scores \
  --scores runs/oracle_scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_c2_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/c2_smoke
```

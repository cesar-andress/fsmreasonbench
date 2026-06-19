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
| P3.8 Exploratory capability-surface runner (C2 + F1) | ✅ |
| P3.9 Minimal Ollama batch runner (C2 + F1) | ✅ |
| P3.10 Failure inspection CLI for scored model runs | ✅ |
| P3.11 Multi-model pilot runner (C2 + F1) | ✅ |
| P3.12 Model capability-surface evaluation + plotting | ✅ |

**Success criterion met:** C2 evaluation path with interpretable reference baselines and exploratory batch runs.

## Empirical evaluation framing (documentation)

The artifact reports capability as **layered rates**, not a single accuracy number:

1. **Extractability** — can the evaluator parse a schema-valid submission?
2. **Verdict accuracy** — does the declared verdict match gold (conditional on extractability)?
3. **Certificate validity** — does the independent verifier accept the certificate?
4. **Full correctness** — verdict and certificate both correct.

**Design hypothesis (under empirical test):** models may score well on verdict accuracy while failing certificate validation; headline reporting must not collapse these layers.

**Current implemented scope:**

| Family | Tier | Status |
|--------|------|--------|
| C2 Reachability | Calibration | ✅ end-to-end |
| F1 DFA non-equivalence | Flagship (first) | ✅ end-to-end |
| F2–F4, C1 | Planned | ⬜ |

**Current evaluation tracks:**

| Track | CLI / module | Role |
|-------|--------------|------|
| Oracle baseline | `run_baseline --baseline oracle` | Ceiling |
| Random baseline | `run_baseline --baseline random` | Wrong-but-extractable control |
| Invalid baseline | `run_baseline --baseline invalid` | Extractability floor |
| Local Ollama (no tools) | `run_ollama_batch`, `run_pilot_models`, `run_capability_surface_models` | Exploratory model sweeps |

Committed docs (`docs/pilot_v0_*`, `docs/pilot_v1_*`) summarize exploratory pilots; multi-model capability-surface runs produce `runs/capability_surface_models/` summaries locally. None of these are frozen cohorts or final benchmark claims.

---

## Phase 4 — Flagship verticals 🔄

| Milestone | Status |
|-----------|--------|
| P4.1 F1 DFA non-equivalence + distinguishing_trace | ✅ |
| P4.2 F1 difficulty controls + batch/smoke evaluation | ✅ |
| P4.2b F1 constructive generator for controlled ℓ_dist | ✅ |
| P4.3 F1 equivalent-pair certificates | ⬜ |
| P4.4 F1 NFA / containment subtypes | ⬜ |
| P4.5 F2 non-materialized composition | ⬜ |
| P4.6 F3 constructive synthesis | ⬜ |
| P4.7 F4 formalization fidelity | ⬜ |
| Multi-track infrastructure | ⬜ |
| Contamination / frozen cohorts / Zenodo release | ⬜ |

**Success criterion (partial):** first flagship F1 item self-verifies end-to-end.

## Phase 4+ — Remaining flagship work

- F1 equivalent-pair proofs, NFA, containment
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
  generator/       # C2 reachability + F1 separation generation
  items/           # benchmark item assembly + self_verify
  evaluator/       # family-aware parser, scorer, transcripts, batch, summary,
                   # capability_surface
  baselines/       # C2/F1 reference systems (oracle, random, invalid)
  runners/         # prompt rendering, Ollama batch evaluation
  cli/             # generate_one, score_submission, rescore_transcript, run_baseline,
                   # generate_batch, evaluate_baseline_batch, summarize_scores,
                   # run_c2_smoke_baselines, run_f1_smoke_baselines,
                   # run_capability_surface, run_ollama_batch
```

## Run

```bash
pip install -e ".[dev]"
pytest
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 42
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
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_f1_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/f1_smoke
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_capability_surface \
  --families C2,F1 --n-per-level 50 --seed 1 --out-dir runs/capability_surface
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_ollama_batch \
  --model qwen2.5-coder:7b \
  --items runs/c2_items.jsonl \
  --out runs/ollama_c2_qwen7b.jsonl \
  --temperature 0
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.summarize_scores \
  --scores runs/ollama_c2_qwen7b/scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.inspect_failures \
  --scores runs/ollama_c2_qwen7b/scores.jsonl \
  --results runs/ollama_c2_qwen7b.jsonl \
  --limit 5
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --c2-items runs/capability_surface_smoke2/C2/min_witness_length_2/items.jsonl \
  --f1-items runs/capability_surface_smoke2/F1/min_distinguishing_trace_length_2/items.jsonl \
  --max-items 20 \
  --out-dir runs/pilot_v1
```

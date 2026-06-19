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

## Phase 2 — First benchmark vertical 🔄

| Milestone | Status |
|-----------|--------|
| P2.1 Seeded C2 reachability generator (`|Q|` difficulty) | ✅ |
| P2.2 Benchmark item assembly (FSM, question, gold, cert, difficulty) | ✅ |
| P2.3 Self-verification (generator → oracle → verifier) | ✅ |
| P2.4 Golden example item in `examples/` | ✅ |
| P2.5 CLI `generate_one.py` | ✅ |

**Success criterion met:** first self-verifying benchmark item.

## Phase 3 — Evaluation infrastructure ⬜

| Milestone | Status |
|-----------|--------|
| P3.1 Answer parser + extractability checks | ⬜ |
| P3.2 Scoring (extractability vs correctness) | ⬜ |
| P3.3 Transcript recording | ⬜ |
| P3.4 Baselines: random, symbolic oracle ceiling | ⬜ |

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
  cli/             # generate_one.py
```

## Run

```bash
pip install -e ".[dev]"
pytest
python -m fsmreasonbench.cli.generate_one --seed 42
```

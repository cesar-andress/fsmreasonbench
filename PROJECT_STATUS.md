# FSMReasonBench — Project Status

**Repository:** artifact (`fsmreasonbench`)  
**Last updated:** 2025-06-19  
**Package version:** `0.2.0-dev`  
**Branch:** `main`

---

## Implementation status

**Principle:** Build the verifier before the generator. Prove one task end-to-end before widening.

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 1** — Core infrastructure | ✅ **Complete** | FSM, oracle, verifier, tests |
| **Phase 2** — First vertical (C2 reachability) | ✅ **Complete** | Difficulty controls + negative items |
| **Phase 3** — Evaluation infrastructure | ✅ **Complete** | C2 parser, scoring, transcripts, baselines |
| **Phase 4** — Flagship verticals | 🔄 **In progress** | F1 DFA non-equivalence vertical |

Roadmap detail: [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)

---

## Milestone achieved: first self-verifying item

```
generator → oracle → certificate → verifier  ✅
```

- **Family:** C2 (basic reachability, calibration)
- **Difficulty dimension:** `|Q|` (state count) only
- **Example:** `examples/item_C2_reachability_seed42.json`
- **CLI:** `python3 -m fsmreasonbench.cli.generate_one --seed 42`
- **Difficulty controls:** `min_witness_length=1`, `max_witness_length=12`, `allow_initial_target=false`
- **Negative items:** unreachable targets with `unreachability_witness`
- **Tests:** 66+ passing (`pytest`)

---

## Phase 4 deliverables (F1 separation / witness)

| Component | Path |
|-----------|------|
| Separation oracle (shortest distinguishing trace) | `oracle/separation.py` |
| Certificate builder | `certificates/separation.py` |
| Independent verifier | `verifier/separation.py` |
| Seeded F1 generator (non-equivalent DFA pairs) | `generator/separation.py` |
| F1 item assembly + self-verify | `items/assembly.py` |
| F1 parser / scorer | `evaluator/parser.py`, `scorer_f1.py` |
| F1 baselines | `baselines/f1.py`, `baselines/runner.py` |
| Schema | `schema/certificate/separation.schema.json` |
| Example item | `examples/item_F1_separation_seed42.json` |

**Verdict convention:** question asks whether A and B are **equivalent**; `verdict=false` means **not equivalent** (separable). Gold certificate type: `distinguishing_trace`.

**CLI:** `python3 -m fsmreasonbench.cli.generate_one --family F1 --seed 42`

---

## Phase 3 deliverables (C2 evaluation)

| Component | Path |
|-----------|------|
| C2 submission schema | `schema/c2_submission.schema.json` |
| Answer parser + extractability gate | `src/fsmreasonbench/evaluator/parser.py` |
| Scoring | `src/fsmreasonbench/evaluator/scorer.py` |
| Transcript + rescore | `src/fsmreasonbench/evaluator/transcript.py` |
| CLI score / rescore | `cli/score_submission.py`, `cli/rescore_transcript.py` |
| Example submissions + transcript | `examples/submission_C2_*.json`, `transcript_C2_correct.json` |
| C2 baselines | `src/fsmreasonbench/baselines/` |
| CLI run baseline | `cli/run_baseline.py` |
| C2 batch generation + evaluation | `evaluator/batch.py`, `evaluator/summary.py` |
| CLI batch tools | `cli/generate_batch.py`, `evaluate_baseline_batch.py`, `summarize_scores.py` |
| C2 smoke baseline runner | `cli/run_c2_smoke_baselines.py` |

**End-to-end path:** item → response → parser → extractability → verifier → scoring → transcript → rescore

**Reference baselines:** `oracle` (symbolic ceiling), `random` (seeded, usually wrong), `invalid` (extractability probe)

**Exploratory batch (non-frozen):** generate JSONL cohort → evaluate baseline → aggregate summary

---

## Phase 1 deliverables

| Component | Path |
|-----------|------|
| FSM model (DFA, NFA) | `src/fsmreasonbench/models/` |
| Canonical serialization + SHA-256 | `models/serialization.py` |
| Shared runtime semantics | `src/fsmreasonbench/runtime/` |
| Oracle (simulation, reachability, shortest path) | `src/fsmreasonbench/oracle/` |
| Certificate builders (oracle-side) | `src/fsmreasonbench/certificates/` |
| Independent verifier | `src/fsmreasonbench/verifier/` |
| JSON schemas | `schema/fsm.schema.json`, `schema/certificate/reachability.schema.json` |
| Unit + e2e tests | `tests/unit/` |

**Architectural rule enforced:** verifier does not import oracle or generator (see `test_verifier_independence.py`).

---

## Phase 2 deliverables

| Component | Path |
|-----------|------|
| Seeded reachability generator | `src/fsmreasonbench/generator/reachability.py` |
| | Controls: `min_witness_length`, `max_witness_length`, `allow_initial_target`, negative items |
| Item assembly + self-verify | `src/fsmreasonbench/items/assembly.py` |
| CLI | `src/fsmreasonbench/cli/generate_one.py` |

---

## Zenodo-first architecture (unchanged)

Development code on `main` is **not citable**. First Zenodo target remains **v1.0.0** after Phase 3+ and cohort freeze.

Current `verifier_version` (dev): `0.2.0-dev` — will pin at release.

---

## Next implementation milestone (Phase 4 remainder)

1. **F1 equivalent-pair proof certificates** (positive items)
2. **F1 NFA / containment subtypes**

**Not next:** frozen cohorts, contamination tooling, LLM runners, multi-track, F2 composition.

---

## Unresolved (unchanged from design phase)

| ID | Question |
|----|----------|
| U1 | F1 minimality policy |
| U9 | License (MIT vs Apache-2.0) |
| U10 | Container digest vs lockfile-only |

---

## Commands

```bash
pip install -e ".[dev]"
pytest -v
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_F1_separation_seed42.json --score
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

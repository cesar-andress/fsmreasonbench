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
| **Phase 2** — First vertical (C2 reachability) | ✅ **Complete** | First self-verifying item |
| **Phase 3** — Evaluation infrastructure | ⬜ Not started | Parser, scoring, baselines |
| **Phase 4+** — Full benchmark | ⬜ Not started | F1–F4, cohorts, Zenodo |

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
- **Tests:** 20 passing (`pytest`)

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
| Item assembly + self-verify | `src/fsmreasonbench/items/assembly.py` |
| CLI | `src/fsmreasonbench/cli/generate_one.py` |

---

## Zenodo-first architecture (unchanged)

Development code on `main` is **not citable**. First Zenodo target remains **v1.0.0** after Phase 3+ and cohort freeze.

Current `verifier_version` (dev): `0.2.0-dev` — will pin at release.

---

## Next implementation milestone (Phase 3)

1. **Answer parser** — JSON schema validation + extractability gate
2. **Scoring** — split extractability vs certificate correctness
3. **Transcript recording** — submission envelope
4. **Baselines** — random witness, symbolic oracle ceiling on C2 slice

**Not next:** F2 composition, F4 probes, frozen cohorts, contamination tooling.

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
python3 -m fsmreasonbench.cli.generate_one --seed 42
```

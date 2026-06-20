# F2 Design Review — Non-materialized Composition (First Vertical Slice)

**Date:** 2026-06-20  
**Sources reconciled:** `docs/specification/BENCHMARK_SPEC.md`, `docs/specification/task_families.md`, `docs/specification/certificate_formats.md`, `docs/q1_readiness_roadmap.md`  
**Artifact scope:** first production-grade F2 vertical slice only (no F3/F4; C2/F1 semantics unchanged)

---

## 1. What an F2 item contains

| Field | Role |
|-------|------|
| `family` | `"F2"` |
| `family_tier` | `"flagship"` |
| `fsm_a`, `fsm_b` | Two executable DFAs (component automata) |
| `question` | Composition spec + property query |
| `question.composition_spec` | Documented operator (`synchronous_product` v1), synchronized alphabet |
| `question.property` | Product-level property (slice v1: `safety` with `state_set` invariant) |
| `difficulty.core` | `|Q_A|`, `|Q_B|`, `alphabet_size`, `d_comp`, `product_width`, `violation_trace_length` |
| `difficulty.slice_metadata` | Slice flags (`counterexample_only`, `positive_verdict_supported`) |
| `answer_key` | Gold `verdict` + oracle-built certificate (evaluator-only) |
| `contamination.public_fingerprint` | Evaluatee-visible payload hash |

**Slice v1 question shape:** Given DFAs A and B, synchronous product `A ⊗ B`, and safety property φ (forbidden product state), does a violating projected trace exist?

---

## 2. What is visible to the evaluatee

Delivered via `item.to_evaluatee_dict()`:

- Both component FSMs (`fsm_a`, `fsm_b`) with full transition structure
- `question` (prompt, composition operator, synchronized alphabet, property specification)
- `difficulty` public axes (no generator seeds, no answer key)
- `family`, `family_tier`, `item_id`, contamination fingerprint

The evaluatee sees **enough to simulate each component locally** and to reason about synchronized symbols, but not the gold witness or internal product enumeration used at generation time.

---

## 3. What is hidden from the evaluatee

- `answer_key` (gold verdict, certificate, internal witness metadata)
- Generator seeds and retry counters beyond public difficulty metadata
- Oracle-internal shortest-violation search state
- Any hidden probes or evaluator-only checksums not in the public bundle

---

## 4. What “non-materialized composition” means operationally

**Normative:** the evaluatee must not submit the full product automaton.

**Operational checks (artifact v1):**

1. **Submission guard:** parser rejects certificates containing forbidden keys (`product_states`, `product_transitions`, `full_product`, `product_graph`, `transition_table`).
2. **Verifier path:** replays `component_trace_A/B` and `projected_states_A/B` on each component FSM independently; derives product states stepwise from projections; checks synchronization against `synchronized_trace`.
3. **No trust in evaluatee product:** verifier never reads a submitted product graph; internal product reconstruction is derived only from replayed component traces.

R2 solvers MAY compute products internally during solve; they MUST NOT emit them in the public certificate.

---

## 5. Allowed verdicts (slice v1)

| Verdict | Meaning | Slice v1 status |
|---------|---------|-----------------|
| `false` | Property violated; counterexample exists | **Implemented** (generator emits only these) |
| `true` | Property holds for all composed traces | **Not implemented** (no positive certificate path yet) |

Gold convention: `verdict=false` ⟺ safety invariant violated (forbidden product state reachable on submitted trace).

---

## 6. Allowed certificate types (slice v1)

| Type | Status | Use |
|------|--------|-----|
| `projected_trace_witness` | **Implemented** | Counterexample via synchronized + component traces |
| `compositional_witness` | Specified, not implemented | Positive / structural reasoning without product table |
| `bounded_structural_argument` | Specified, not implemented | Inductive / bounded-depth arguments |
| `product_invariant_witness` | Specified in roadmap | Positive safety proof |
| `no_counterexample_certificate` | Specified in roadmap | Negative reachability-style proof |

**Implemented payload fields (`projected_trace_witness`):**

- `component_trace_A`, `component_trace_B`
- `synchronized_trace`
- `projected_states_A`, `projected_states_B`
- `property_evaluation` (`property_kind`, `satisfied`, `violation_step_index`, `product_state_at_violation`)

Schema: `schema/certificate/composition.schema.json`.

---

## 7. What makes a certificate executable and checkable

A certificate is **executable** when:

1. It parses against the family submission schema and passes the materialization guard.
2. Component traces replay on `fsm_a` / `fsm_b` to the claimed projected state sequences.
3. Each step’s synchronized symbol is consistent with both component transitions (same length traces on shared alphabet).
4. Stepwise product states match `property_evaluation.product_state_at_violation` at the violation index.
5. `property_evaluation.satisfied=false` matches the declared safety invariant (forbidden state reached).
6. Certificate type matches item question and supports the declared verdict.

The verifier returns structured errors (replay mismatch, sync mismatch, property mismatch, materialization violation) without consulting the oracle module.

---

## 8. Solver / materialization shortcuts explicitly forbidden (R0/R1/R2)

| Track | Forbidden in **submission** | Allowed during **solve** |
|-------|----------------------------|-------------------------|
| **R0** | Full product state list, product transition table, forbidden payload keys | Mental simulation on components only |
| **R1** | Same as R0 | Repeated `step()` on each component; manual sync reasoning |
| **R2** | Same as R0/R0 guard on output | Internal product BFS / oracle solvers via tool registry |

**Universal submission prohibitions:**

- `product_states`, `product_transitions`, `full_product`, `product_graph`, `transition_table`
- Arrays sized as explicit `|Q_A| × Q_B` enumerations in the certificate payload

Misreporting track or injecting gold `answer_key` content remains forbidden on all tracks.

---

## 9. Minimal viable F2 difficulty axis (slice v1)

Primary axis: **`violation_trace_length`** (length of shortest counterexample trace), controlled by:

| Parameter | Default | Role |
|-----------|---------|------|
| `min_violation_trace_length` | `1` | Floor on witness length |
| `max_violation_trace_length` | `6` | Cap on witness length |
| `state_count_a`, `state_count_b` | `3` | Component state counts (`|Q_A|`, `|Q_B|`) |
| `alphabet_size` | `2` | Shared alphabet size |
| `transition_density` | `0.75` | Component edge density |
| `max_generation_attempts` | `64` | Rejection sampling budget |

Secondary recorded axes (not yet swept in capability surface): `d_comp=1` (synchronous product), `product_width=|Q_A|·|Q_B|`.

---

## 10. Out of scope for the first F2 slice

- F3, F4, C1 families
- Positive items (`verdict=true`) and `compositional_witness` / `bounded_structural_argument`
- `product_invariant_witness`, `no_counterexample_certificate`
- Async / interface composition operators beyond `synchronous_product`
- NFA or Mealy components
- R0/R1/R2 track pilot integration on F2 cohorts
- Public `v1.0-public` cohort quota
- Capability-surface sweeps and frontier model panels for F2
- Minimality proofs for counterexample traces (shortest witness is oracle metadata only)

---

## Artifact mapping

| Component | Path |
|-----------|------|
| Runtime (product, replay) | `src/fsmreasonbench/runtime/composition.py` |
| Oracle | `src/fsmreasonbench/oracle/composition.py` |
| Certificate builder | `src/fsmreasonbench/certificates/composition.py` |
| Verifier | `src/fsmreasonbench/verifier/composition.py` |
| Generator | `src/fsmreasonbench/generator/f2_composition.py` |
| Item assembly | `src/fsmreasonbench/items/assembly.py` |
| Parser / scorer | `src/fsmreasonbench/evaluator/f2_parser.py`, `scorer_f2.py` |
| Baselines | `src/fsmreasonbench/baselines/f2.py` |
| Tests | `tests/unit/test_f2_composition.py` |
| Example | `examples/F2/item_composition_seed4202.json` |

---

## Next step toward R0/R1/R2 track experiments

1. Freeze an exploratory F2 cohort (`f2-composition-v0.1-exploratory`, n≥20) after smoke validation.
2. Extend `run_track_pilot_models` / `run_ollama_track_batch` family routing to accept F2 items and track-specific prompts (non-materialization reminder).
3. Register R2 solver tools for composition (`shortest_violation_witness`) that log tool use but emit only `projected_trace_witness` certificates.
4. Add F2 to capability-surface / local-matrix sweeps on `min_violation_trace_length`.
5. Only after counterexample slice is stable: implement positive verdict path and rebalance generator toward mixed polarity.

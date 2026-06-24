# Certificate Class Complexity Analysis

Structural comparison explaining why F1 `equivalence_witness` behaves differently from other certificate classes. **No new model calls; no verifier changes.**

## Comparative matrix

| certificate_type | required | semantic | canonical | exact_match | multi_form | canon_req | synth_req | recomputes | complexity |
|------------------|--------:|---------:|----------:|------------:|---------:|----------:|----------:|-----------:|-----------:|
| distinguishing_trace | 8 | 3 | 0 | 1 | True | False | True | 3 | 4.5 |
| equivalence_witness | 9 | 3 | 2 | 4 | False | True | True | 4 | 9.5 |
| trace_witness | 7 | 2 | 0 | 1 | True | False | True | 2 | 3.5 |
| unreachability_witness | 7 | 2 | 1 | 2 | False | True | False | 2 | 5.0 |

## Per-class structural profile

### distinguishing_trace (F1, verdict false (non-equivalent))

- **Required fields:** 8 (envelope: certificate_type, version, fsm_ids, verdict_supported; payload: trace, acceptance)
- **Semantic fields:** 3
- **Verifier recomputes:** 3 checks — acceptance.A via accepts_trace(fsm_a, trace); acceptance.B via accepts_trace(fsm_b, trace); distinguishing property (acceptance_A != acceptance_B)
- **Exact-match fields:** fsm_ids (ordered pair)
- **Canonical fields:** —
- **Information content:** O(|trace|) alphabet symbols plus 2 acceptance bits; verifier does not require shortest trace.
- **Local reasoning sufficient:** False
- **Multiple valid certificates:** True (verifier accepts multiple forms: True)
- **Synthesis:** minimization=False, symbolic_search=True, state_closure=False, canonical_hash=False, exact_set=False, replay=True
- **Verifier notes:** Semantic replay checks only; any distinguishing trace accepted. Shortest trace is oracle metadata, not enforced.

### equivalence_witness (F1, verdict true (equivalent))

- **Required fields:** 9 (envelope: certificate_type, version, fsm_ids, verdict_supported; payload: equivalent, minimized_hash_A, minimized_hash_B)
- **Semantic fields:** 3
- **Verifier recomputes:** 4 checks — are_equivalent_dfas(fsm_a, fsm_b) [pair BFS]; minimized_dfa_hash(fsm_a); minimized_dfa_hash(fsm_b); hash equality across equivalent DFAs
- **Exact-match fields:** payload.equivalent == true, payload.minimized_hash_A, payload.minimized_hash_B, fsm_ids (ordered pair)
- **Canonical fields:** minimized_hash_A, minimized_hash_B
- **Information content:** Two fixed 64-char hex hashes encoding a bounded language bitvector (trace lengths 0..min(|Q|,12) over completed reachable DFA).
- **Local reasoning sufficient:** False
- **Multiple valid certificates:** False (verifier accepts multiple forms: False)
- **Synthesis:** minimization=True, symbolic_search=True, state_closure=True, canonical_hash=True, exact_set=False, replay=False
- **Verifier notes:** Strictest class: semantic equivalence PLUS exact hash match to verifier-recomputed minimized_dfa_hash outputs. Hash mismatch rejects witness even when verdict/equivalence is correct.

### trace_witness (C2, verdict true (reachable))

- **Required fields:** 7 (envelope: certificate_type, version, fsm_id, verdict_supported; payload: trace, state_sequence)
- **Semantic fields:** 2
- **Verifier recomputes:** 2 checks — simulate(fsm, trace) state_sequence; initial state and target_state endpoints
- **Exact-match fields:** state_sequence (must match replay exactly)
- **Canonical fields:** —
- **Information content:** O(|trace|) symbols plus O(|trace|+1) state labels; multiple traces may exist for same target.
- **Local reasoning sufficient:** True
- **Multiple valid certificates:** True (verifier accepts multiple forms: True)
- **Synthesis:** minimization=False, symbolic_search=True, state_closure=False, canonical_hash=False, exact_set=False, replay=True
- **Verifier notes:** Replay-based; any valid path ending at target accepted. Prompt example includes accepting but verifier ignores it.

### unreachability_witness (C2, verdict false (unreachable))

- **Required fields:** 7 (envelope: certificate_type, version, fsm_id, verdict_supported; payload: reachable_states, target_state)
- **Semantic fields:** 2
- **Verifier recomputes:** 2 checks — reachable_states(fsm) [BFS from initial]; target_state not in reachable set
- **Exact-match fields:** reachable_states set equality (frozenset), target_state string
- **Canonical fields:** reachable_states
- **Information content:** O(|R|) state names where R is reachable set; unique set content, list order immaterial (set equality).
- **Local reasoning sufficient:** True
- **Multiple valid certificates:** False (verifier accepts multiple forms: False)
- **Synthesis:** minimization=False, symbolic_search=False, state_closure=True, canonical_hash=False, exact_set=True, replay=False
- **Verifier notes:** Requires exact reachable set, not a valid sub/superset invariant. Set canonicalization (unique membership) but not hash-based.


## Failure taxonomy (frozen Claude runs)

### distinguishing_trace
- Pooled semantic failures: 18; formatting: 0; other: 0
- Rejection mechanism: Replay trace on both DFAs; reject if acceptance labels mismatch replay or trace does not distinguish.
- `acceptance_mismatch`: 16 (88.9% of pooled invalid)
- `replay_failure`: 2 (11.1% of pooled invalid)

### equivalence_witness
- Pooled semantic failures: 102; formatting: 0; other: 0
- Rejection mechanism: Run are_equivalent_dfas; recompute minimized_dfa_hash for each DFA; reject on semantic non-equivalence or any hash mismatch.
- `equivalence_hash_mismatch`: 102 (100.0% of pooled invalid)

### trace_witness
- Pooled semantic failures: 1; formatting: 6; other: 0
- Rejection mechanism: Simulate trace; reject if state_sequence length/endpoints/replay mismatch.
- `wrong_trace_format`: 6 (85.7% of pooled invalid)
- `replay_failure`: 1 (14.3% of pooled invalid)

### unreachability_witness
- Pooled semantic failures: 2; formatting: 0; other: 0
- Rejection mechanism: BFS reachable set; reject if witness set != computed set or target listed.
- `incomplete_reachability_set`: 2 (100.0% of pooled invalid)

## What makes equivalence_witness hard?

- Payload is not a human-readable witness; it requires two hex hashes produced by minimized_dfa_hash (complete DFA → reachable core → enumerate language bits for lengths 0..min(|Q|,12)).
- Verifier independently runs are_equivalent_dfas AND recomputes both hashes; all four checks must pass.
- No alternate certificate types or approximate hashes accepted (verifier audit: single canonical witness form).
- Parser enforces equivalent=true and non-empty hash strings before semantic verification.
- Claude R1 failures are 51/51 equivalence_hash_mismatch with verdict_accuracy=1.0 — models know equivalence but cannot emit verifier-identical hashes without solver.equivalence_certificate.
- R2C success (~0.98) uses build_equivalence_witness_certificate / solver tool — same code path as gold builder.

### Why C2 does not mirror F1

- trace_witness: replay-only, multiple valid paths, no hashing.
- unreachability_witness: exact set required but computable by single BFS without minimization or language bitvector hashing.
- Claude R1 unreachability_witness full≈1.00 vs equivalence_witness 0.00 despite both being 'negative verdict' items — negates simple existential/universal asymmetry explanation.

## Research questions


### Is equivalence_witness uniquely canonicalization-dependent?

Yes, among these four classes, equivalence_witness is the **only** one requiring minimized_dfa_hash canonical strings (requires_canonical_hashing=True). unreachability_witness requires exact set reconstruction but not hashing; trace_witness and distinguishing_trace accept multiple replay-valid witnesses.


### Is equivalence_witness uniquely synthesis-dependent?

No — all four require symbolic synthesis for gold construction. equivalence_witness uniquely pairs synthesis with **non-negotiable hash output**; distinguishing_trace and trace_witness need search but accept any valid witness, and unreachability_witness needs only BFS closure (no search).


### Does verifier strictness differ across certificate classes?

Yes. Strictness ordering by estimated_complexity_score: equivalence_witness (9.5) > unreachability_witness (5.0) > distinguishing_trace (4.5) > trace_witness (3.5). Only equivalence_witness rejects semantically correct verdicts when hashes are wrong (equivalence_hash_mismatch).


### Are there multiple valid certificates for other classes but not equivalence_witness?

Yes. distinguishing_trace and trace_witness accept multiple valid witnesses (verifier_accepts_multiple_forms=True). unreachability_witness allows permutation of list order but not set content. equivalence_witness accepts a single hash pair tied to minimized_dfa_hash.


### What structural property best predicts Claude's collapse?

Canonical hash emission under R1 self-construction. Claude R1: equivalence_witness 51/51 invalid (100%) with equivalence_hash_mismatch; distinguishing_trace 3/49 invalid (~6%); C2 trace_witness 2/50; unreachability_witness 0/50. Collapse tracks requires_canonical_hashing=True, not existential-vs-universal polarity.


### What exact hypothesis should the paper make?

Claude's F1 equivalence collapse is driven by the **canonical hash witness contract** (minimized_dfa_hash), not by universal quantification per se: C2 unreachability_witness also demands exact closure yet remains easy, while F1 distinguishing_trace (existential trace) stays easy without hashing. R2C closes equivalence_witness only via solver.equivalence_certificate, which runs the same hash builder as the verifier.


## Claude R1 certificate_valid_rate by type (frozen runs)

| certificate_type | cert_valid_rate |
|------------------|----------------:|
| distinguishing_trace | 0.939 |
| equivalence_witness | 0.000 |

## Methodology notes

Heuristic 1–10 composite: +2 canonical hashing, +2 minimization, +1.5 exact set reconstruction, +1 symbolic search, +1 state-space closure, +1 strict exact-match fields, −1 local reasoning sufficient, −0.5 multiple valid forms accepted.

Sources: verifier/parser/generator code paths cited in JSON export.

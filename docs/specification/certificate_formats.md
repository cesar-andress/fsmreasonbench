# Certificate and Artefact Formats — FSMReasonBench v2

**Status:** draft (pre-release)  
**Version:** 2.0.0-draft  
**Normative parent:** [`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md)  
**Zenodo:** Certificate types are pinned by `schema_version` in release manifest.

In v2, flagship tasks treat the **submitted certificate or artefact** as the primary
scoring object. Boolean verdicts are secondary or diagnostic.

The **verifier** MUST be independent of generator and oracle.

---

## Design principles

1. **Certificate-first (F1–F4)** — Primary score requires valid artefact, not verdict alone.
2. **Non-materialization (F2)** — Certificates MUST NOT contain full product enumeration.
3. **Constructive verification (F3)** — Submitted FSM checked by decision procedure against formal target.
4. **Probe-grounded fidelity (F4)** — Formal query scored on hidden probes and semantic equivalence.
5. **Extractability** — All submissions MUST validate against JSON Schema before semantic verification.

---

## Common envelope

```json
{
  "certificate_type": "string",
  "version": "2.0",
  "family": "F1 | F2 | F3 | F4 | C1 | C2",
  "fsm_id": "uuid",
  "payload": { }
}
```

---

## F1 — Separation / Witness

### Type: `distinguishing_trace` (implemented: F1.a DFA non-equivalence)

```json
{
  "certificate_type": "distinguishing_trace",
  "version": "1.0",
  "fsm_ids": ["uuid-A", "uuid-B"],
  "verdict_supported": false,
  "payload": {
    "trace": ["a", "b"],
    "acceptance": { "A": true, "B": false }
  }
}
```

| Check | Rule |
|-------|------|
| Replay | Trace must be simulable on both DFAs |
| Acceptance | Declared `A`/`B` values must match replay |
| Separation | `acceptance.A != acceptance.B` |
| Shortestness | Oracle metadata only in v0 slice; not enforced by verifier yet |

**Verdict convention:** boolean answers the equivalence question directly — `false` means **not equivalent**. Do not invert into a separate “separable?” field.

Schema: `schema/certificate/separation.schema.json`.

### Type: `separation_witness` (planned general envelope)

```json
{
  "certificate_type": "separation_witness",
  "payload": {
    "subtype": "F1.a | F1.b | F1.c",
    "trace": ["a", "b"],
    "primary_outcome": { "accepts": true },
    "secondary_outcome": { "accepts": false },
    "state_sequence_primary": ["q0", "q1"],
    "state_sequence_secondary": ["q0", "q2"],
    "claimed_minimal": true,
    "minimality_witness_kind": "length | prefix_minimal"
  }
}
```

| Subtype | Verification |
|---------|--------------|
| F1.a | Trace accepts on `M₁`, rejects on `M₂` (or Mealy behaviour differs) |
| F1.b | Trace accepts on primary, rejects on secondary |
| F1.c | Trace reaches state where invariant `P` fails |

**Minimality:** If `claimed_minimal: true`, verifier checks no shorter trace in declared bound satisfies separation.

**Primary metric:** certificate valid. Verdict field optional.

---

## F2 — Non-materialized Composition

### Type: `projected_trace_witness`

Counterexample to composed property without product table in payload.

```json
{
  "certificate_type": "projected_trace_witness",
  "payload": {
    "composed_trace": ["a", "sync", "b"],
    "projections": {
      "component_a": { "trace": ["a", "b"], "state_sequence": ["..."] },
      "component_b": { "trace": ["sync"], "state_sequence": ["..."] }
    },
    "violation": {
      "property_kind": "safety | reachability",
      "step_index": 2
    }
  }
}
```

**Verification:** Verifier rebuilds product internally; checks projections are consistent and violation holds.

### Type: `compositional_witness`

Positive witness via interface reasoning (no product table).

```json
{
  "certificate_type": "compositional_witness",
  "payload": {
    "method": "interface_invariant | assume_guarantee_template",
    "interface_states": ["idle", "sync"],
    "invariant": { "type": "state_set", "satisfying_states": ["..."] },
    "case_splits": [
      { "region": "idle×running", "argument": "..." }
    ]
  }
}
```

**Verification:** Template-specific rules in verifier; must not require evaluatee-supplied product states.

### Type: `bounded_structural_argument`

```json
{
  "certificate_type": "bounded_structural_argument",
  "payload": {
    "bound": { "max_depth": 4, "max_states_explored": 36 },
    "argument_steps": [
      { "rule": "induction_base", "states": ["q0"] },
      { "rule": "induction_step", "from": "q0", "symbol": "a", "to": "q1" }
    ],
    "conclusion": "property_holds"
  }
}
```

**Forbidden in F2 payloads:** `product_states`, `product_transitions`, arrays sized `|Q_A|×|Q_B|`.

---

## F3 — Constructive Synthesis

### Type: `synthesized_fsm` (artefact, not witness-only)

Submission IS the certificate body:

```json
{
  "certificate_type": "synthesized_fsm",
  "payload": {
    "fsm": { },
    "target_id": "uuid",
    "claimed_properties": ["equivalent_to_target", "minimal_states"]
  }
}
```

**Verification:**

```
check_equivalence(submitted_fsm, target) OR
check_table_satisfaction(submitted_fsm, behaviour_table) OR
check_refines(submitted_fsm, specification)
```

`minimal_states` checked only if claimed and decidable within bound.

---

## F4 — Formalization Fidelity

### Type: `formal_query`

```json
{
  "certificate_type": "formal_query",
  "payload": {
    "query": {
      "kind": "safety | reachability | membership | mealy_io",
      "parameters": { }
    },
    "semi_formal_source_id": "uuid"
  }
}
```

**Verification (evaluator-side):**

1. Parse and type-check query
2. Compare to reference query for semantic equivalence on hidden probe set `Π_hidden`
3. Score: `|{p ∈ Π_hidden : eval(submitted, p) ≠ eval(reference, p)}| / |Π_hidden|`

Hidden probes never shipped to evaluatee.

---

## Calibration certificates

### C1 — `trace_witness` (optional)

Short accepting or rejecting prefix witness. Verdict primary.

### C2 — `trace_witness` or `unreachability_witness`

| Verdict | Certificate | Verification |
|---------|-------------|--------------|
| `true` (reachable) | `trace_witness` | Replay trace; ends at `target_state`; length ≥ `min_witness_length` when generator policy applies |
| `false` (unreachable) | `unreachability_witness` | `target_state ∉ reachable_states`; set equals BFS reachable set from `q₀` |

**Generator policy:** empty trace (`trace: []`) is valid only when `target_state == q₀` **and** `allow_initial_target=true`. Default generator settings forbid trivial empty-trace positive items.

Verdict primary for calibration scoring; certificate independently verifiable.

### C2 submission envelope

Structured C2 submissions wrap the certificate in a top-level object (schema: `schema/c2_submission.schema.json`):

```json
{
  "item_id": "uuid",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": { "trace": ["a"], "state_sequence": ["q0", "q1"] }
  }
}
```

Extractability requires all three fields with structurally valid certificate payloads. Verdict–certificate mismatch (e.g. `verdict=true` with `unreachability_witness`) is **extractable** but scored as `verdict_wrong` or `certificate_invalid` depending on gold answer.

Example submissions: `examples/submission_C2_*.json`.

## Extractability vs correctness

| Stage | Check | Failure code |
|-------|-------|--------------|
| 1 | JSON Schema validation | `EXTRACT_FAIL` |
| 2 | Required fields for family | `EXTRACT_INCOMPLETE` |
| 3 | F2 materialization guard | `MATERIALIZATION_VIOLATION` |
| 4 | Semantic verification | `CERT_INVALID` |
| 5 | Minimality / optimality (if claimed) | `OPTIMality_FAIL` |

Reporting MUST separate extractability rate from certificate validity rate.

---

## Scoring weights (default, flagship)

| Component | Weight |
|-----------|--------|
| Extractable submission | gate (required) |
| Certificate / artefact valid | **1.0 primary** |
| Verdict (if present) | 0.25 diagnostic |
| Minimality (F1, if claimed) | 0.25 secondary |
| Probe fidelity (F4) | 1.0 primary (probe error rate) |

Calibration: verdict 1.0 primary; certificate optional.

---

## Independent verification requirement

Verifier inputs: `(item, submitted_response)` — no oracle import.

Verifier outputs:

```json
{
  "extractable": true,
  "certificate_valid": true,
  "materialization_violation": false,
  "probe_error_rate": 0.0,
  "errors": []
}
```

Future sub-schemas: `schema/certificate/*.schema.json`.

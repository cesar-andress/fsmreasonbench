# Task Families — FSMReasonBench v2

**Status:** draft (pre-release)  
**Version:** 2.0.0-draft  
**Normative parent:** [`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md)  
**Cohort quotas** are enforced in manifest; see [`../../cohorts/MANIFEST_SPEC.md`](../../cohorts/MANIFEST_SPEC.md).

FSMReasonBench v2 organizes tasks into **four flagship families (F1–F4)** and a
**calibration layer (C1–C2)**. Flagship families are the scientific headline;
calibration tasks support sanity checking and must not dominate reporting.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| `M`, `M₁`, `M₂` | Executable FSM (DFA, NFA, or bounded Mealy) |
| `q₀` | Initial state |
| `Σ` | Input alphabet |
| `δ`, `λ` | Transition and (Mealy) output functions |
| `w` | Input trace `σ₁…σₙ ∈ Σ*` |
| `φ` | Formal property or query |
| `⊗` | Documented composition operator |

---

## Flagship families

### F1 — Separation / Witness

#### Intent

Measure ability to **produce a verifiable witness** establishing separation, violation,
or non-containment—not merely to answer boolean yes/no.

#### Covers (subtypes)

| Subtype | Claim | Witness must show |
|---------|-------|-------------------|
| F1.a Non-equivalence | `L(M₁) ≠ L(M₂)` | Distinguishing trace `w` |
| F1.b Non-containment | `w ∈ L(M₁) \ L(M₂)` | Separating trace |
| F1.c Safety violation | `M ⊭ □P` | Counterexample trace to ¬P |

#### Implementation status (artifact)

| Slice | Status | Certificate | Verdict convention |
|-------|--------|-------------|-------------------|
| F1.a DFA non-equivalence | ✅ implemented | `distinguishing_trace` | `verdict=false` ⟺ not equivalent |
| F1.a equivalent pairs | ⬜ not yet | TBD | `verdict=true` |
| F1.b containment | ⬜ not yet | TBD | — |
| F1.c safety violation | ⬜ not yet | TBD | — |

**Generator controls (artifact):** `mode` (`constructive_decoy` | `constructive` | `random`; auto-select `constructive_decoy` when `min_distinguishing_trace_length ≥ 3`), `target_distinguishing_trace_length`, `min_distinguishing_trace_length` (default 2), `max_distinguishing_trace_length`, `state_count_a`, `state_count_b`, `alphabet_size`, `max_retries`. Default constructive mode builds paired DFAs with decoy branches and controlled witness divergence; legacy `constructive` uses chain+sink topology; random mode uses rejection sampling. Smoke examples may set `min_distinguishing_trace_length=1`.

> **Exploratory warning:** Constructive F1 is intended for controlled `ℓ_dist` sweeps, not as a final difficulty axis. Legacy `constructive` items exhibit high `final_acceptance_only_rate` and elevated `sink_transition_ratio`; `constructive_decoy` reduces these signals but items may still share seeded witness structure. Use `audit_f1_items` on generated JSONL before drawing conclusions from capability-surface results.

**Batch / smoke:** `generate_batch --family F1`, `evaluate_baseline_batch`, `run_f1_smoke_baselines`.

**Normative question wording:** “Are DFA A and B equivalent?” Submit `verdict=false` with a `distinguishing_trace` certificate when they are not.

#### Submitted answer (primary)

```json
{
  "witness_type": "separation_witness",
  "trace": ["..."],
  "witness_metadata": {
    "subtype": "F1.a | F1.b | F1.c",
    "claimed_minimal": true
  }
}
```

**Normative:** Verdict alone is **insufficient** for flagship scoring. A boolean field
MAY be included for extractability but is not the primary metric.

#### Certificate requirements

- Witness MUST replay correctly on supplied FSM(s)
- For `claimed_minimal: true`, verifier checks minimality within declared bound
- Oracle provides reference shortest witness; optimality gap recorded as secondary metric

#### Track notes

| Track | Notes |
|-------|-------|
| R0/R1 | Small `\|Q\|`, short `\|w\|` strata |
| R2 | Tools allowed internally; witness still required in submission |

---

### F2 — Non-materialized Composition

#### Intent

Measure reasoning about **composed behaviour** without requiring the evaluatee to
materialize the full product automaton in the submitted answer.

#### Question shape

Given `M_A`, `M_B`, documented operator `⊗`, and property `φ` on composed behaviour:

- Does `M_A ⊗ M_B ⊭ φ`? (counterexample required)
- Does `M_A ⊗ M_B ⊨ φ`? (compositional or bounded structural witness required)

#### Submitted answer (primary)

One of:

1. **Projected trace witness** — trace over composed alphabet with projections to component traces
2. **Compositional witness** — case analysis on interface states without full product listing
3. **Bounded structural argument** — formal template filling (e.g., inductive interface invariant)

```json
{
  "certificate_type": "projected_trace_witness | compositional_witness | bounded_structural_argument",
  "payload": { }
}
```

#### Non-materialization rule (normative)

Submissions MUST NOT include:

- Full product state list (`Q_A × Q_B` enumeration)
- Complete product transition table

Violations → extractability failure or automatic certificate rejection (configurable; default: reject).

Solver-delegation (R2) MAY compute products internally; they MUST NOT appear in output.

#### Certificate verification

Verifier reconstructs product **only internally** (or checks compositional witness rules)
to validate witness. Evaluatee certificate stays compressed.

#### Implementation status (artifact)

| Slice | Status | Certificate | Verdict convention |
|-------|--------|-------------|-------------------|
| F2 safety counterexample (`synchronous_product`) | ✅ implemented | `projected_trace_witness` | `verdict=false` ⟺ safety violated |
| F2 positive proof (`verdict=true`) | ⬜ not yet | `compositional_witness` / `product_invariant_witness` | TBD |
| F2 `no_counterexample_certificate` | ⬜ not yet | TBD | — |

**Generator controls (artifact v0.2+):**

| Parameter | Default | Role |
|-----------|---------|------|
| `min_violation_trace_length` | `1` | Shortest counterexample length floor |
| `max_violation_trace_length` | `6` | Counterexample length cap |
| `state_count_a`, `state_count_b` | `3` | Component state counts |
| `alphabet_size` | `2` | Shared alphabet size |
| `transition_density` | `0.75` | Component edge density |
| `max_generation_attempts` | `64` | Rejection sampling budget |

**Slice v1:** generator emits **counterexample-only** items (`difficulty.slice_metadata.counterexample_only=true`). Property kind: `safety` with `state_set` invariant on product states.

**Batch / smoke:** `generate_batch --family F2`, `evaluate_baseline_batch --baseline oracle --family F2`.

**Normative question wording:** “Does the synchronous product of FSM A and FSM B violate the given safety property?” Submit `verdict=false` with a `projected_trace_witness` when a violating synchronized trace exists.

Design review: [`../f2_design_review.md`](../f2_design_review.md).

---

### F3 — Constructive Synthesis

#### Intent

Measure ability to **construct a small FSM** satisfying a **formal target** specified
in the item—not to generate from natural-language requirements.

#### Formal target examples

- Accept exactly language `L_target` given as explicit finite language or canonical DFA reference (hidden from presentation)
- Realize a specified input–output behaviour table on bounded domain
- Satisfy Mealy constraint `(σ, q) ↦ (q', y)` for a given partial specification

#### Submitted answer (primary)

```json
{
  "submitted_fsm": { },
  "synthesis_claim": {
    "state_count": 4,
    "target_predicate": "reference_id"
  }
}
```

#### Verification

Independent decision procedure checks:

```
Verify(S_submitted, Target) ∈ { equivalent | refines | satisfies_table }
```

Per-item target relation declared in `question.synthesis_target`.

#### Scope guardrails

| Allowed | Not allowed |
|---------|-------------|
| Constrained construction from formal target | NL requirements → FSM |
| Bounded state budget `|Q| ≤ q_max` | Open-ended “design a protocol” |
| Reference oracle on submitted artefact | Human judgment of “quality” |

#### Track notes

| Track | Notes |
|-------|-------|
| R0 | Micro targets only (`|Q| ≤ 4`, small table) |
| R1 | Bounded table fill with step simulator |
| R2 | Full synthesis tools; submitted FSM still verified independently |

---

### F4 — Formalization Fidelity

#### Intent

Measure ability to translate a **controlled semi-formal property** into a **formal
query** over a given FSM, such that behaviour on hidden probes matches the intended semantics.

#### Inputs

- FSM `M` (given)
- Semi-formal property `ψ` in controlled template (structured NL + logic fragments, timing-free)

#### Submitted answer (primary)

```json
{
  "formal_query": {
    "kind": "reachability | safety | language_membership | mealy_output",
    "parameters": { }
  }
}
```

#### Scoring (not verdict-only)

1. **Semantic equivalence check** — submitted query equivalent to reference query on probe set
2. **Hidden probe behaviour** — evaluate `formal_query(M)` vs reference on evaluator-only probes
3. **Extractability** — query parses and type-checks against schema

Hidden probes are **never** in evaluatee bundle.

#### Example

Semi-formal: “After any `reset`, the system never enters `Error` without seeing `ack`.”

Submitted: safety query with predicate on states + alphabet constraints.

Scoring: probe traces where reference and submitted query disagree → failure.

---

## Calibration layer (non-headline)

### C1 — Trace / Membership

**Question:** Does trace `w` lead to acceptance in `M`?

**Purpose:** Operational literacy, format parsing, simulator sanity.

**Scoring:** Verdict correctness primary; short witness optional.

**Reporting:** Calibration panel only; MUST NOT headline abstract or primary tables.

---

### C2 — Basic Reachability

**Question:** Is state `q_t` reachable from `q₀` in `M`?

**Purpose:** Basic graph-reachability literacy; drift detection across model versions.

**Generator controls (implementation v0.2+):**

| Parameter | Default | Role |
|-----------|---------|------|
| `min_witness_length` | `1` | Positive items require non-empty witness unless initial target explicitly allowed |
| `max_witness_length` | `12` | Cap witness length for calibration strata |
| `allow_initial_target` | `false` | If false, empty trace to `q₀` is excluded from positive items |

**Positive items:** `answer_key.verdict = true` with `trace_witness` (shortest path).

**Negative items:** `answer_key.verdict = false` with `unreachability_witness` listing the complete reachable state set from `q₀`.

**Scoring:** Verdict primary; certificate required for self-verification pipeline.

**Reporting:** Calibration panel only.

---

## Cohort quotas (v1.0-public target)

| Tier | Families | Min share | Min items (indicative) |
|------|----------|-----------|------------------------|
| Flagship | F1, F2, F3, F4 | ≥ 85% | ≥ 2,125 of 2,500 |
| Calibration | C1, C2 | ≤ 15% | ≤ 375 of 2,500 |

Within flagship, each of F1–F4 SHOULD have ≥ 15% of flagship quota.

| Family | Min flagship share |
|--------|-------------------|
| F1 | 25% |
| F2 | 25% |
| F3 | 20% |
| F4 | 20% |
| (remainder) | F1/F2 sub-strata balance |

Final counts: see `PROJECT_STATUS.md`.

---

## F1 subtypes and generator tags

Items MUST declare:

```json
{
  "family": "F1",
  "family_variant": "F1.a | F1.b | F1.c",
  "family_tier": "flagship"
}
```

---

## Explicit exclusions (all families)

- NL-to-FSM from requirements (outside F3 guardrails)
- FSM repair
- Explicit product enumeration in F2 submissions
- Subjective NL-only scoring
- Hidden FSM semantics not derivable from item artifacts

---

## Oracle summary

| Family | Oracle role |
|--------|-------------|
| F1 | Find shortest witness; verify replay |
| F2 | Internal product/compositional check; compress witness |
| F3 | Verify submitted FSM against formal target |
| F4 | Compute reference query; generate hidden probes |
| C1 | Single-pass simulation |
| C2 | Reachability BFS/DFS |

Registry: `spec/oracle/procedure_registry.yaml` (future).

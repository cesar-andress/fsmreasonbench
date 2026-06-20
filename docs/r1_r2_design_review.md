# R1/R2 Design Review

**Date:** 2026-06-20  
**Sources reconciled:** `docs/specification/BENCHMARK_SPEC.md`, `docs/specification/evaluation_protocol.md`, `docs/q1_readiness_roadmap.md`  
**Artifact scope:** C2 and F1 vertical slices only (first operational tracks)

---

## 1. Track semantics (normative intent)

### R0 — Pure reasoning

| Aspect | Semantics |
|--------|-----------|
| **Construct measured** | Internal simulation and deduction without executable tools |
| **Permitted** | In-context reasoning, mental simulation, scratchpad text |
| **Forbidden** | Code execution, REPL, external APIs, benchmark oracle, answer keys, evaluator internals |
| **Certificate path** | Agent assembles `{item_id, verdict, certificate}` through public submission schema; scored by standard parser/verifier |
| **Artifact implementation** | Reference `r0_agent` uses runtime decision procedures in a single scratchpad phase with **zero tool invocations** logged |

**Clarification:** R0 does not forbid structured intermediate reasoning in transcripts; it forbids **invoking tools** during solve. An LLM on R0 may write JSON directly; an automated reference agent may compute inline.

### R1 — Tool-augmented reasoning

| Aspect | Semantics |
|--------|-----------|
| **Construct measured** | Disciplined operational reasoning with bounded single-step aid |
| **Permitted** | Scratchpad, helper procedures, local computation, **`step(fsm_id, state, symbol)`** simulator |
| **Forbidden** | Global search libraries, model checkers, SMT, automata-lib, benchmark oracle, answer keys, evaluator internals |
| **Certificate path** | Same public submission schema; agent may call `step` repeatedly to explore |
| **Artifact implementation** | `StepSimulator` logs every call; BFS/product exploration built from steps only |

**Clarification:** R1 **allows** the agent to implement BFS manually via repeated `step` calls. It forbids importing packaged graph-search or oracle modules during the solve phase.

### R2 — Solver delegation

| Aspect | Semantics |
|--------|-----------|
| **Construct measured** | Pipeline orchestration and solver use |
| **Permitted** | Arbitrary solvers through a **controlled tool interface**; internal oracle/product computation |
| **Forbidden** | Misreporting track; reading `answer_key.certificate`; F2 full product in submission (not yet applicable) |
| **Certificate path** | Tool outputs feed a separate **certificate assembly** phase; submission still public schema |
| **Artifact implementation** | `SolverToolRegistry` wraps oracle/runtime solvers; every invocation logged with provenance |

**Clarification:** R2 solvers MAY use `fsmreasonbench.oracle` internally. The trust boundary is: tools see evaluatee-visible FSMs only; gold certificates never enter the solve path.

---

## 2. Admissible tools (artifact v1)

| Track | Tool surface | Implementation module |
|-------|--------------|----------------------|
| R0 | *(none)* | — |
| R1 | `step(fsm_id, state, symbol) → {success, next_state?, error?}` | `tracks/step_simulator.py` |
| R2 | `solver.is_reachable`, `solver.reachability_certificate`, `solver.check_separation`, `solver.equivalence_certificate`, `solver.distinguishing_certificate` | `tracks/solver_tools.py` |

R2 tools are **closed-world** in v1: only registered names are invocable and auditable.

---

## 3. Trust boundaries

```
┌─────────────────────────────────────────────────────────────┐
│ Evaluatee bundle (item.to_evaluatee_dict)                   │
│  FSM(s), question, difficulty, public_fingerprint          │
│  EXCLUDES: answer_key, hidden_probes, generator seeds        │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    R0 scratchpad      R1 StepSimulator   R2 SolverToolRegistry
    (no tools)         (logged steps)     (logged solver calls)
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
              Public submission JSON {item_id, verdict, certificate}
                            │
                            ▼
              parse_submission → score_item (evaluator; uses answer_key offline)
```

| Boundary | R0 | R1 | R2 |
|----------|----|----|-----|
| Agent reads `answer_key` | ❌ | ❌ | ❌ |
| Agent calls oracle modules | ❌ | ❌ | ✅ via registry only |
| Evaluator uses `answer_key` | ✅ (scoring) | ✅ | ✅ |
| Tool calls in audit log | 0 | ≥0 | ≥0 |

---

## 4. Evaluator-visible information

**During solve:** only `BenchmarkItem.to_evaluatee_dict()` fields.

**After solve:** evaluator receives `raw_response` (submission JSON string), `TrackRunResult` audit log, and optional scratchpad. Scoring uses full item including `answer_key` — unchanged from R0 pipeline.

**Track metadata added to outputs:** `track`, `tool_invocation_count`, `audit_log`, `scratchpad`, `certificate_assembly` (R2).

---

## 5. Certificate-generation constraints

1. Submission MUST match public schema (`item_id`, `verdict`, `certificate`).
2. Certificate MUST pass independent verifier (not oracle self-check alone).
3. R0/R1 MUST NOT read `answer_key.certificate`.
4. R2 MUST NOT copy gold certificates; may use oracle **decision procedures** to derive witness fields, then assemble certificate dict explicitly in a logged assembly phase.
5. F2 non-materialization guard applies when F2 is implemented (out of scope for this pass).

---

## 6. Delegation gap (Δ_R2_R0)

Per `evaluation_protocol.md` §6.2:

```
Δ_R2_R0(metric) = metric(R2) − metric(R0)
```

Computed for `verdict_accuracy`, `certificate_valid_rate`, `fully_correct_rate` per family/cohort. Positive gap indicates solver delegation improves that layer over pure reasoning on the same items.

---

## 7. Ambiguities identified (pre-implementation)

| ID | Ambiguity | Resolution in artifact v1 |
|----|-----------|---------------------------|
| A1 | Spec lists only `step(state, symbol)` but F1 has two FSMs | `step` takes `fsm_id` to disambiguate; product exploration uses paired steps on both FSMs |
| A2 | R1 forbids "BFS libraries" but permits manual BFS via `step` | Allowed; audit log proves step-only exploration |
| A3 | R0 automated reference agent must run code to demo pipeline | Reference agents are **evaluator instrumentation**, not competing models; LLM R0 runs remain prompt-only |
| A4 | `competent_submitter` vs R1 track overlap | `competent_submitter` is an M2 ceiling; R1 track is the operational evaluation mode with enforced step logging |
| A5 | R2 "arbitrary code" vs closed tool registry | v1 registry is intentionally closed-world for reproducibility; extensible via registered tool names |
| A6 | Reproducibility tier "R1 Integrity" vs track "R1" | Naming collision: Zenodo R1 = cohort checksum integrity; evaluation R1 = tool-augmented track. Documented separately |
| A7 | Scratchpad content in transcripts | Stored as structured entries; not scored; required for audit separation on R2 |
| A8 | Negative delegation gap | Valid if R0 reference outperforms R2 on small n; report shows signed deltas without ranking claims |

---

## 8. Backward compatibility

- Existing `ScoringRecord` unchanged.
- Track runs produce `TrackScoringRecord` wrapping `ScoringRecord` plus track fields.
- Ollama batch runners default to implicit R0 (`track` omitted = R0) until `--track` is passed (future).
- Baselines `oracle`/`random`/`invalid` remain track-agnostic reference systems.

---

## 9. Out of scope (this pass)

- LLM prompt integration for R1/R2 tool calling
- F2 materialization guard implementation
- Track misreporting detection on external submissions (manual declaration only)
- Human-expert R0/R1 panel

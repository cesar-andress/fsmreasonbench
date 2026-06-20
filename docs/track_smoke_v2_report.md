# Track Smoke v2 Report

**Model:** `qwen2.5-coder:7b` (temperature 0)  
**Cohorts:** frozen exploratory C2 level-3 (n=20), F1 mixed level-3 (n=20)  
**Change vs smoke v1:** hardened R1/R2 phase-2 prompts with exact certificate examples, invalid payload negatives, and pre-submit checklist  
**Runs:** `runs/track_smoke_v2/qwen2.5-coder_7b/` (not committed)

> **Caution:** This is qwen-only smoke evidence on exploratory cohorts. It is not a frontier model panel and not citable as benchmark results.

---

## 1. Did R1/R2 increase tool use?

**Yes.** On both cohorts, `tool_invocation_rate = 1.0` and `average_tool_calls_per_item = 1.0` for R1 and R2 (unchanged from smoke v1). Tool infrastructure is working; the v2 change targeted phase-2 certificate serialization, not tool adoption.

---

## 2. Did R1/R2 improve extractability?

| Cohort | Track | Smoke v1 extract | Smoke v2 extract | Δ |
|--------|-------|-----------------:|-----------------:|--:|
| C2 | R1 | 0.00 | **1.00** | +1.00 |
| C2 | R2 | 0.00 | **1.00** | +1.00 |
| F1 | R1 | 0.00 | 0.80 | +0.80 |
| F1 | R2 | 0.00 | 0.80 | +0.80 |

**C2:** Prompt hardening eliminated phase-2 schema failures (`final_submission_not_extractable` dropped from 5/5 to **0/20** on R1/R2).  
**F1:** Large improvement but **4/20** items still fail extractability on R1/R2 (protocol or payload shape).

R0 C2 extractability: 0.95 (1 item not extractable; unchanged prompt).

---

## 3. Did R1/R2 improve certificate_valid_rate or fully_correct_rate?

### C2 (n=20)

| Track | extract | verdict | cert | full |
|-------|--------:|--------:|-----:|-----:|
| R0 | 0.95 | 0.26 | 0.00 | 0.00 |
| R1 | 1.00 | 0.80 | 0.15 | **0.15** |
| R2 | 1.00 | 0.95 | 0.10 | **0.10** |

R1/R2 beat R0 on verdict and full correctness once submissions became extractable. Certificate validity remains low (semantic witness errors dominate).

### F1 (n=20)

| Track | extract | verdict | cert | full |
|-------|--------:|--------:|-----:|-----:|
| R0 | 1.00 | 0.45 | 0.00 | 0.00 |
| R1 | 0.80 | 1.00 | 0.00 | 0.00 |
| R2 | 0.80 | 1.00 | **0.50** | **0.40** |

**F1 R2** shows the intended delegation pattern: solver tools improve certificate construction (`fully_correct_rate = 0.40` vs R0 `0.00`).

---

## 4. Did failures shift from tool-use to schema/expression?

**Yes, clearly on C2.**

| Failure class | C2 R1 v1 (n=5) | C2 R1 v2 (n=20) | C2 R2 v2 (n=20) |
|---------------|---------------:|----------------:|----------------:|
| `final_submission_not_extractable` | 5 | **0** | **0** |
| `certificate_invalid` | 0 | 13 | 17 |
| `verdict_wrong` | 0 | 4 | 1 |
| `correct` | 0 | 3 | 2 |

Failures moved from **phase-2 schema** (`final_submission_not_extractable`) to **semantic certificate** (`certificate_invalid`) and occasional **verdict_wrong**. This is the intended diagnostic shift: infrastructure works; model witness construction is the bottleneck.

F1 R1/R2 still show 4× `final_submission_not_extractable` plus heavy `certificate_invalid` on R1.

---

## 5. Delegation gap Δ_R2−R0

| Cohort | Δ verdict | Δ cert | Δ full |
|--------|----------:|-------:|-------:|
| C2 | **+0.69** | +0.10 | **+0.10** |
| F1 | **+0.55** | **+0.50** | **+0.40** |

Both cohorts show **positive** R2−R0 delegation gaps on full correctness after v2 hardening (C2 from a near-zero R0 base; F1 with a strong R2 signal).

R1−R0 on C2 full: **+0.15** (R1 also helps once extractable).

---

## 6. Interpretation

1. **Track infrastructure is evidence-ready** for reporting layered failures (tool taxonomy + four metric layers).
2. **Prompt hardening fixed the primary v1 blocker** on C2: models now emit schema-valid submissions in phase 2.
3. **Remaining model failures are semantic**, not JSON envelope errors — especially C2 `certificate_invalid` and F1 mixed extractability + witness quality.
4. **R2 solver delegation helps on F1** (40% full correct); C2 benefits more from verdict accuracy than certificate quality at this model scale.
5. **Do not over-interpret** n=20 exploratory smoke with a single local model.

---

## 7. Remaining blockers before frontier-panel runs

1. **Increase Ollama timeout** for R0 long batches (C2 R0 timed out at 120s on first pass).
2. **F1 phase-2 extractability** — 20% still fail protocol/schema on R1/R2; may need F1-specific examples or multi-step tool plans.
3. **Certificate semantics** — even with extractability 1.0 on C2 R1/R2, cert valid rate ≤ 0.15 without solver-grade witnesses.
4. **Frontier panel + powered cohort** — smoke is diagnostic only; public cohort and multiple models required for claims.
5. **Optional:** multi-round tool protocol for models that need >1 tool call per item.

---

## Artifacts

- Aggregated comparison: `docs/track_comparison_summary.{json,csv}`, `docs/track_comparison_report.md`
- Design: `docs/llm_track_runner_design.md` (updated with schema hardening + failure taxonomy)

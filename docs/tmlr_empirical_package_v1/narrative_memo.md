# Narrative memo (TMLR empirical package)

## Final paper thesis

LLMs can answer FSM verdict questions and emit **replay-checkable witnesses** (traces, acceptance labels, reachability paths, reachable sets), but fail sharply when the benchmark requires **verifier-identical canonical hash witnesses** (`minimized_dfa_hash`) for DFA equivalence. Knowing the oracle verdict and schema is insufficient; only generator-assisted tool tracks supply the canonical synthesis.

## What we stopped claiming

- A general **existential-vs-universal** certification asymmetry (C2 balanced ablation shows both C2 subtypes ~96–100% for Claude R1).
- That the universal side of F1 (`equivalence_witness`) fails because quantification is inherently harder than producing a trace.
- That verify-only or repair-only tool ablations explain the R1→R2 jump (they add ~2–3 points; R2C adds ~50).

## Three strongest empirical results

1. **F1 subtype split under Claude R1:** distinguishing_trace cert ≈ 0.94 vs equivalence_witness cert = 0.00 (same model, same track, same cohort).
2. **R2C attribution:** eq-witness jumps from 0.00 → ~0.98 only when `solver.equivalence_certificate` is allowed — matching frozen R2.
3. **C2 negative control:** no eq-witness-style collapse; unreachability_witness ≥ trace_witness for Claude — ruling out a simple universal-quantifier story.

## Three strongest controls

1. **Oracle + format ablation:** fixed gold verdict + worked examples; eq-witness remains 0.00.
2. **R2A/R2B ablation:** verify-only / repair-only tools; eq-witness remains 0.00.
3. **Verifier hostile audit:** 16/16 checks pass; hash strictness is contractual, not accidental bug.

## Main limitation

The benchmark's eq-witness contract accepts **only** hash-based witnesses (no partition/bijection alternatives). Claude's R1 failure is partly **witness-format** failure under a strict contract, even when semantic equivalence is correct (verdict accuracy 1.0, failures labeled `equivalence_hash_mismatch`).

## Abstract (proposed one sentence)

FSMReasonBench shows that frontier LLMs construct replay-valid FSM certificates for separation and reachability, yet collapse on equivalence items requiring verifier-identical minimized DFA hashes unless given solver certificate generators—indicating a sharp gap between verdict prediction and canonical symbolic synthesis, not a generic existential/universal asymmetry.

## Main figure

**Figure 1** (complexity score vs Claude R1 certificate rate): `equivalence_witness` is the isolated low outlier at complexity 9.5 with cert 0.00.

## Most dangerous reviewer attack

"The eq-witness task is unfair: you test hash memorization, not reasoning; the model knows they're equivalent (verdict 100%) so the benchmark measures an arbitrary canonical format."

## Supported rebuttal

The audit documents an independent semantic check (`are_equivalent_dfas`) **plus** a deliberate single canonical witness contract; hash mismatch is labeled witness-construction failure, not refutation. Controls show replay-style certificates succeed under the same model and prompts, and R2C succeeds by calling the **same** hash builder the verifier uses — the gap is **synthesis of the contracted witness**, not verdict ability or JSON formatting. C2 further shows exact-set and replay witnesses are not universally hard for Claude, isolating **canonical hashing** as the distinctive barrier.

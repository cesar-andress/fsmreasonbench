# TMLR Empirical Package v1

Frozen empirical artifacts for the FSMReasonBench paper submission.

## Final thesis

Knowing the verdict is not enough: LLMs can construct replay-style FSM certificates, but fail sharply on **canonical hash-based certificates** that require verifier-identical symbolic synthesis.

## No new model calls

This package is generated entirely from frozen runs and existing analysis exports. **No API calls were made during package generation.**

## Frozen run policy

- Do **not** modify directories under `runs/` referenced below.
- Do **not** overwrite prior docs under `docs/` outside this package directory.
- Regenerate only into `docs/tmlr_empirical_package_v1/`.

## Source artifacts

| Artifact | Path |
|----------|------|
| Local matrix | `runs/local_matrix_n100_t02_v2` |
| Claude frontier tools | `runs/frontier_claude_sonnet_tools_n100_v2` |
| F1 oracle ablation | `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1` |
| F1 R2 attribution | `runs/ablations_f1_r2_attribution_claude_n100_v1` |
| C2 existential/universal ablation | `runs/ablations_c2_existential_universal_claude_n100_v1` |
| F1 verifier audit | `docs/f1_equivalence_witness_verifier_audit.json` |
| F1 Claude stratified | `docs/f1_claude_ablation_stratified_analysis.json` |
| F1 local stratified | `docs/f1_local_matrix_subtype_stratified_analysis.json` |
| C2 stratified | `docs/c2_existential_universal_stratified_analysis.json` |
| Certificate complexity | `docs/certificate_class_complexity_analysis.json` |

## Excluded from scientific conclusions

- Invalid Claude credit-exhaustion / infrastructure-failure cells (excluded from conclusions).
- Invalid Gemini quota-failure runs (excluded from conclusions).
- Contaminated legacy frontier run frontier_claude_sonnet_full_n100_v1 (never used).
- Smoke-test duplicate score rows in C2 ablation were deduplicated to n=100 unique item_ids.

## Key claims (supported)

1. Claude R1 achieves ~0.94 `distinguishing_trace` cert but **0.00** `equivalence_witness` cert on F1 (n=100).
2. Oracle verdict + format control does **not** restore eq-witness (remains 0.00); R2A/R2B add ~0.02–0.03 overall, not ~0.50.
3. R2C / frozen R2 (~0.99) closes eq-witness via `solver.equivalence_certificate` (same hash builder as verifier).
4. C2 shows **no F1-like collapse**: trace_witness ~0.96, unreachability_witness ~1.00 under Claude R1.
5. Structural analysis: only `equivalence_witness` requires canonical `minimized_dfa_hash` (complexity 9.5/10).

## Non-claims

- We do **not** claim a general existential-vs-universal certification asymmetry (C2 refutes this for Claude).
- We do **not** claim the verifier is buggy (16/16 hostile audit checks pass).
- We do **not** claim oracle verdict alone enables certificate construction.
- Hash mismatch on eq-witness does **not** prove model refuted equivalence when semantic check passes.

## Tables and figures

| Output | Source |
|--------|--------|
| Table 1 | `docs/certificate_class_complexity_analysis.json` + Claude R1 frozen scores |
| Table 2 | `docs/f1_claude_ablation_stratified_analysis.json` |
| Table 3 | `docs/c2_existential_universal_stratified_analysis.json` |
| Table 4 | `docs/f1_local_matrix_subtype_stratified_analysis.json` |
| Appendix | `docs/f1_equivalence_witness_verifier_audit.json` + complexity failure taxonomy |
| Figure 1 | Table 1 |
| Figure 2 | Table 2 |
| Figure 3 | Table 3 |
| Figure 4 | Table 4 |
| Uncertainty | Item-level scores from frozen runs (see `uncertainty/`) |

## Regenerate

```bash
cd {repo_root.name}
PYTHONPATH=src python -m fsmreasonbench.cli.export_tmlr_empirical_package
```

Requires `matplotlib` (`pip install -e '.[plot]'`).

# Appendix Table: Verifier audit and failure taxonomy

## equivalence_witness verifier audit

- Checks passed: 16/16
- Single canonical witness form: True

> An F1 equivalence_witness is valid iff the benchmark DFAs are semantically equivalent (independent BFS equivalence check) and the submitter supplies the exact minimized language-signature hashes recomputed by the verifier from those DFAs; hash mismatch rejects the witness format but is not, by itself, evidence of non-equivalence when the semantic check succeeds.

## Pooled failure taxonomy (frozen Claude runs)

### equivalence_witness
- Semantic: 102; formatting: 0
- `equivalence_hash_mismatch`: 102 (100.0%)

### distinguishing_trace
- Semantic: 18; formatting: 0
- `acceptance_mismatch`: 16 (88.9%)
- `replay_failure`: 2 (11.1%)

### unreachability_witness
- Semantic: 2; formatting: 0
- `incomplete_reachability_set`: 2 (100.0%)

### trace_witness
- Semantic: 1; formatting: 6
- `wrong_trace_format`: 6 (85.7%)
- `replay_failure`: 1 (14.3%)

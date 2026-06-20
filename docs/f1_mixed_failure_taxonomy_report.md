# F1 Mixed Failure Taxonomy Report

**Source:** `docs/f1_mixed_failure_taxonomy.json`  
**Scope:** Exploratory F1 mixed capability-surface evaluation (4 local models × 5 difficulty levels, 20 scored runs).  
**Status:** Illustrative only — not a frozen cohort or final benchmark result.

---

## Summary

| Metric | Value |
|--------|------:|
| Scored runs | 20 |
| Total `certificate_invalid` | **138** |

Only two taxonomy categories appear in this run; all other categories have zero counts.

---

## Aggregated taxonomy (all runs)

| Category | Count | Share |
|----------|------:|------:|
| `acceptance_mismatch` | 88 | 63.8% |
| `replay_failure` | 50 | 36.2% |
| `wrong_trace_format` | 0 | 0.0% |
| `incomplete_reachability_set` | 0 | 0.0% |
| `equivalence_hash_mismatch` | 0 | 0.0% |
| `wrong_certificate_type` | 0 | 0.0% |
| `wrong_fsm_ids` | 0 | 0.0% |
| `malformed_certificate_payload` | 0 | 0.0% |
| `other` | 0 | 0.0% |

---

## Per-model breakdown

Aggregated over all five difficulty levels (20 items per model × level).

| Model | `certificate_invalid` | `acceptance_mismatch` | `replay_failure` |
|-------|----------------------:|----------------------:|-----------------:|
| gemma2:9b | 34 | 25 (73.5%) | 9 (26.5%) |
| llama3.1:8b | 27 | 7 (25.9%) | 20 (74.1%) |
| mistral-nemo:12b | 33 | 25 (75.8%) | 8 (24.2%) |
| qwen2.5-coder:7b | 44 | 31 (70.5%) | 13 (29.5%) |

Percentages in parentheses are shares within each model’s `certificate_invalid` items.

---

## Per-difficulty-level breakdown

Aggregated over all four models (20 items per level).

| Level (`min_distinguishing_trace_length`) | `certificate_invalid` | `acceptance_mismatch` | `replay_failure` |
|-------------------------------------------|----------------------:|----------------------:|-----------------:|
| 1 | 28 | 9 (32.1%) | 19 (67.9%) |
| 2 | 30 | 5 (16.7%) | 25 (83.3%) |
| 3 | 25 | 24 (96.0%) | 1 (4.0%) |
| 4 | 33 | 28 (84.8%) | 5 (15.2%) |
| 5 | 22 | 22 (100.0%) | 0 (0.0%) |

Percentages in parentheses are shares within each level’s `certificate_invalid` items.

---

## Interpretation (exploratory)

In the F1 mixed exploratory run, certificate failures are dominated by `acceptance_mismatch`, suggesting that failed certificates are usually semantically inconsistent with replay rather than malformed.

At lower difficulty levels (1–2), `replay_failure` is more frequent than in the aggregate; at levels 3–5, `acceptance_mismatch` accounts for most failures. Model-level mixes vary (for example, llama3.1:8b shows a higher share of `replay_failure` than the other models in this run). These patterns describe this exploratory cohort only and should not be read as general conclusions about model capability.

---

## Category definitions (brief)

| Category | Typical verifier signal |
|----------|-------------------------|
| `acceptance_mismatch` | Declared acceptance on A/B does not match replay, or trace fails to distinguish |
| `replay_failure` | Trace cannot be replayed on the supplied DFAs |
| Other categories | Schema, format, FSM-id, or reachability-set errors (none observed here) |

See the artifact failure-taxonomy module for full classification rules.

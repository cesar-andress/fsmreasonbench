# Difficulty Model — FSMReasonBench v2

**Status:** draft (pre-release)  
**Version:** 2.0.0-draft  
**Normative parent:** [`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md)  
**Analysis:** Required stratifications feed capability surfaces in Zenodo-compatible reports.

Difficulty is a **formal parameter vector** per item. Ordinal labels (`easy`, `medium`,
`hard`) MAY appear in human reports but MUST NOT replace the vector in manifests.

---

## Core difficulty vector (all families)

```
d_core = (|Q|, |Σ|, ℓ*, ndeg, struct_amb, present_len)
```

| Parameter | Symbol | Definition |
|-----------|--------|------------|
| State count | `\|Q\|` | States in primary FSM (or sum for multi-component items) |
| Alphabet size | `\|Σ\|` | Input alphabet size |
| Witness length | `ℓ*` | Shortest valid certificate trace (oracle-computed) |
| Nondeterminism degree | `ndeg` | Average branching factor / \|Σ\| |
| Structural ambiguity | `struct_amb` | Normalized local symbol interchangeability ∈ [0,1] |
| Presentation length | `present_len` | Token count of human-readable presentation |

---

## Family-specific extensions

### F1 — Separation / Witness

```
d_F1 = (d_core, sep_kind, min_witness_gap)
```

| Parameter | Definition |
|-----------|------------|
| `sep_kind` | F1.a / F1.b / F1.c |
| `min_witness_gap` | Length difference between shortest and second-shortest witness (if defined) |

Higher `min_witness_gap` → easier to avoid wrong minimal claims.

### F2 — Non-materialized Composition

```
d_F2 = (d_core, d_comp, |Q_A|, |Q_B|, product_width)
```

| Parameter | Definition |
|-----------|------------|
| `d_comp` | Composition nesting depth |
| `\|Q_A\|`, `\|Q_B\|` | Component state counts |
| `product_width` | \|Q_A\| × \|Q_B\| (oracle metric; **not** exposed to evaluatee) |

Difficulty increases with `product_width` even when submission forbids materialization.

### F3 — Constructive Synthesis

```
d_F3 = (d_core, q_max, table_size, constraint_density)
```

| Parameter | Definition |
|-----------|------------|
| `q_max` | Maximum allowed states in submission |
| `table_size` | Rows in I/O or language specification |
| `constraint_density` | Fraction of defined transitions in partial spec |

### F4 — Formalization Fidelity

```
d_F4 = (d_core, semi_formal_depth, probe_count_hidden, template_id)
```

| Parameter | Definition |
|-----------|------------|
| `semi_formal_depth` | Nesting depth of semi-formal template |
| `probe_count_hidden` | \|Π_hidden\| (evaluator only) |
| `template_id` | Controlled semi-formal pattern class |

### Calibration (C1, C2)

```
d_C = (|Q|, |Σ|, ℓ*, present_len)
```

Reduced vector; used for drift detection, not flagship analysis.

---

## JSON storage

```json
{
  "difficulty": {
    "core": {
      "|Q|": 8,
      "|Sigma|": 4,
      "witness_length": 6,
      "nondeterminism_degree": 1.0,
      "structural_ambiguity": 0.2,
      "presentation_length": 412
    },
    "family_extension": { }
  }
}
```

---

## Track strata

### R0 — Pure reasoning

| Stratum | \|Q\| | ℓ* | d_comp (F2) | q_max (F3) |
|---------|-------|-----|-------------|------------|
| S0 | ≤ 4 | ≤ 6 | 1 | ≤ 3 |
| S1 | ≤ 6 | ≤ 12 | 1 | ≤ 4 |
| S2 | ≤ 8 | ≤ 20 | 2 | ≤ 5 |

### R1 — Tool-augmented

| Stratum | \|Q\| | ℓ* | d_comp | product_width (F2) |
|---------|-------|-----|--------|---------------------|
| S0 | ≤ 6 | ≤ 10 | 1 | ≤ 24 |
| S1 | ≤ 10 | ≤ 20 | 2 | ≤ 60 |
| S2 | ≤ 15 | ≤ 40 | 2 | ≤ 100 |
| S3 | ≤ 20 | ≤ 60 | 3 | ≤ 200 |

### R2 — Solver delegation

| Stratum | \|Q\| | ℓ* | product_width | table_size (F3) |
|---------|-------|-----|---------------|-----------------|
| S0–S4 | ≤ 200 | bounded per family | ≤ 10⁴ | ≤ 500 |

F2 R2: product may be computed internally; submission non-materialization rule unchanged.

---

## Sampling policy (v1.0-public)

1. **Quota first:** flagship ≥ 85%, calibration ≤ 15%
2. **Per flagship family:** balance F1–F4 subtypes and strata
3. Reject duplicate `contamination.public_fingerprint`
4. Record **actual** vector post-oracle (not target alone)

### Indicative flagship distribution (2,500 items)

| Family | Items | Strata (min) |
|--------|-------|--------------|
| F1 | 625 | 4 (by subtype + stratum) |
| F2 | 625 | 4 |
| F3 | 500 | 3 |
| F4 | 500 | 3 |
| C1 | 188 | 2 |
| C2 | 187 | 2 |

---

## Capability surface axes (analysis)

Published results MUST correlate errors with:

1. Each `d_core` component
2. Family extension parameters
3. Track (R0/R1/R2)
4. `present_len` as covariate

**Discouraged:** single scalar “FSMReasonBench score” without stratification.

---

## Derived ordinal labels (non-normative)

```
easy   := all core parameters ≤ S0 bounds for family and track
hard   := any parameter ≥ S2 bounds (or product_width ≥ threshold for F2)
medium := otherwise
```

---

## Generator interface (future)

```yaml
family: F2
family_tier: flagship
target_stratum: R1-S1
difficulty_targets:
  product_width: { min: 30, max: 60 }
  witness_length: { min: 8, max: 25 }
```

Actual vector recorded after oracle pass; resample if out of targets.

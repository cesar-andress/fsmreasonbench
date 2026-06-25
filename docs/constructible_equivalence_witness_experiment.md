# F1 constructible equivalence witness experiment (A1)

**Purpose:** Address the TOSEM construct-validity critique that the headline F1 equivalence collapse may reflect **hash emission** rather than inability to supply a **machine-checkable equivalence witness**.

**Design choice:** `bisimulation_witness` — an explicit **state-pair relation** closed under paired transitions, with matching acceptance. No `minimized_hash_A/B` fields.

---

## What was added (does not replace frozen protocol)

| Component | Path |
|-----------|------|
| Relation builder + verifier | `src/fsmreasonbench/runtime/bisimulation.py` |
| Oracle builder | `build_bisimulation_witness_certificate()` |
| Verifier dispatch | `verify_bisimulation_witness_certificate()` (hash path unchanged) |
| R2 tool | `solver.bisimulation_certificate` |
| Study runner | `cli/run_f1_constructible_equivalence_study.py` |
| Hostile audit | `cli/export_f1_bisimulation_witness_verifier_audit.py` |
| Analysis export | `cli/export_constructible_equivalence_analysis.py` |

**Frozen intact:** `equivalence_witness` hash contract, all existing runs, tables, and cohort items.

**Subset:** 51 / 100 F1 cohort items with gold `equivalence_witness` (same item IDs, verdicts, DFAs).

---

## Verification rules (summary)

A `bisimulation_witness` is valid when:

1. Independent `are_equivalent_dfas(A,B)` succeeds.
2. `fsm_ids` match the benchmark pair.
3. `payload.pairs` is a non-empty list of `{state_a, state_b}`.
4. The **initial state pair** is included.
5. Every listed pair has **matching acceptance** on A and B.
6. For every pair and alphabet symbol, paired successors are also in the relation.

Invalid structural certificates (missing pairs, bad transitions, wrong acceptance, wrong IDs) are rejected — see `docs/f1_bisimulation_witness_verifier_audit.md`.

---

## Manual execution

```bash
cd fsmreasonbench
./scripts/run_a1_constructible_equivalence.sh help
```

Recommended order:

1. `./scripts/run_a1_constructible_equivalence.sh audit`
2. Smokes: `claude-r1-smoke`, `claude-r2c-smoke`, `gpt-r1-smoke`, `gpt-r2c-smoke`
3. Full cells: `claude-r1`, `claude-r2c`, `gpt-r1`, `gpt-r2c`
4. `./scripts/run_a1_constructible_equivalence.sh report`
5. `./scripts/run_a1_constructible_equivalence.sh export-analysis`

---

## Expected outputs

| Artifact | Location |
|----------|----------|
| Per-cell runs | `runs/f1_constructible_equivalence_{claude,gpt}_n100_v1/{R1,R2C}/` |
| Study aggregate | `.../combined_summary.json`, `report.md` |
| Audit | `docs/f1_bisimulation_witness_verifier_audit.{json,md}` |
| Analysis | `docs/a1_constructible_equivalence_v1/constructible_equivalence_analysis.json` |
| Paper table | `paper/tables/extension_constructible_equivalence_witness.tex` |
| Paper figure | `paper/figures/extension_constructible_equivalence_comparison.pdf` |

---

## How this answers the review

| Question | Analysis |
|----------|----------|
| Hash-only failure? | Compare frozen hash `equivalence_witness` cert rate vs new `bisimulation_witness` on the **same 51 items**. |
| Structural witness without hash? | R1 constructible cell measures direct state-relation synthesis. |
| R2C benefit without hash? | Compare constructible R2C (solver.bisimulation_certificate) vs R1 and vs frozen hash R2C. |
| Contrast class | Frozen `distinguishing_trace` R1 rates on the 49 non-eq items (unchanged protocol). |

---

## Manuscript reframing (guidance only)

- **Do not withdraw** the hash-witness finding; it remains the **primary contract** for the frozen TOSEM slice.
- **Add** that equivalence collapse under hash witnesses may **overstate** reasoning failure if models succeed on `bisimulation_witness`.
- If constructible rates remain near zero on R1, the critique is partially refuted (failure is not hash-specific formatting alone).
- If constructible R1 ≫ hash R1, reframe headline equivalence results as **witness-contract sensitivity**, not pure existential/universal asymmetry.

Full plan: [`TOSEM_A1_EXPERIMENT_PLAN.md`](TOSEM_A1_EXPERIMENT_PLAN.md)

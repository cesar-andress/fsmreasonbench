# TOSEM Experiment A1 plan — constructible equivalence witness

**Status:** Infrastructure implemented; campaigns **not** executed automatically.  
**Scope:** Construct-validity experiment alongside frozen hash-witness protocol.

---

## Implemented witness design

**Certificate type:** `bisimulation_witness` (alternative contract; does not replace `equivalence_witness`).

**Payload:**

```json
{
  "equivalent": true,
  "pairs": [{"state_a": "q0", "state_b": "s0"}]
}
```

**Oracle construction:** Synchronized product BFS from `(q0_A, q0_B)` on completed DFAs — all reachable paired states form a valid relation (`runtime/bisimulation.py::compute_bisimulation_pairs`).

**Why bisimulation (vs hash):**

- Machine-checkable by **replay** (like `distinguishing_trace`).
- Constructible by step simulation (R1) or solver tool (R2C).
- No canonical hash arithmetic.
- Reuses existing semantic gate `are_equivalent_dfas`.

---

## Verification rules

See hostile audit (`docs/f1_bisimulation_witness_verifier_audit.json`) — **10/10 checks** at implementation time.

Semantic gate + structural closure:

1. `are_equivalent_dfas`
2. Initial pair present
3. Acceptance preservation per pair
4. Transition closure per pair and symbol
5. States must exist in respective DFAs

**Unchanged:** `verify_equivalence_witness_certificate` (hash contract).

---

## Experimental cells

| Provider | Model | Track | Output dir |
|----------|-------|-------|------------|
| Anthropic | claude-sonnet-4-5-20250929 | R1 | `runs/f1_constructible_equivalence_claude_n100_v1/R1/` |
| Anthropic | claude-sonnet-4-5-20250929 | R2C | `.../R2C/` |
| OpenAI | gpt-4.1 | R1 | `runs/f1_constructible_equivalence_gpt_n100_v1/R1/` |
| OpenAI | gpt-4.1 | R2C | `.../R2C/` |

**Subset:** n=51 equivalence items from `cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl`.

**Optional (not in default config):** R2 full tool track — add cell to study config if desired.

---

## Run commands

```bash
cd fsmreasonbench
export PYTHONPATH=src

# Verifier audit (no API)
python3.12 -m fsmreasonbench.cli.export_f1_bisimulation_witness_verifier_audit

# Smoke then full cells
./scripts/run_a1_constructible_equivalence.sh claude-r1-smoke
./scripts/run_a1_constructible_equivalence.sh claude-r1
./scripts/run_a1_constructible_equivalence.sh claude-r2c
./scripts/run_a1_constructible_equivalence.sh gpt-r1
./scripts/run_a1_constructible_equivalence.sh gpt-r2c

# Aggregate + analysis
./scripts/run_a1_constructible_equivalence.sh report
./scripts/run_a1_constructible_equivalence.sh export-analysis
```

Direct CLI:

```bash
python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
  --provider anthropic --track R1

python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
  --provider openai --model gpt-4.1 --track R2C
```

---

## Estimated runtime & cost

| Cell | Items | Approx. wall time | API cost (order of magnitude) |
|------|------:|------------------:|------------------------------:|
| R1 smoke | 1 | 1–3 min | <$0.50 |
| R1 full | 51 | 2–8 h | $15–60 (provider dependent) |
| R2C full | 51 | 3–10 h | $20–80 |

**Total (4 full cells):** ~12–36 h, ~$70–280.

---

## Expected outputs

Standard cell artifacts: `scores.jsonl`, `results.jsonl`, `summary.json`, `transcripts/`, `report.md`.

Study-level: `combined_summary.json`.

Analysis exports:

- `docs/a1_constructible_equivalence_v1/constructible_equivalence_analysis.json`
- `paper/tables/extension_constructible_equivalence_witness.tex`
- `paper/figures/extension_constructible_equivalence_comparison.pdf`

---

## Manuscript sections affected (later integration)

| Section | Content |
|---------|---------|
| Threats / construct validity | New subsection on hash vs bisimulation witness |
| F1 equivalence results | Side-by-side table (hash frozen vs bisimulation A1) |
| Discussion | Interpretation of witness-contract sensitivity |
| Appendix | Bisimulation verifier audit |

---

## Review criticism addressed

**Critique:** Headline equivalence failure may measure **hash construction**, not witness-aware reasoning.

**Response path:**

1. Same eq subset, same verdicts, alternative checkable witness.
2. If bisimulation cert rate ≫ hash rate → reframe as contract artifact.
3. If bisimulation also collapses on R1 → substantive reasoning gap remains (not hash-only).
4. R2C bisimulation tool isolates synthesis assistance without hash builder.

---

## Claims reframing guidance

| Outcome | Recommendation |
|---------|----------------|
| Hash ≈ 0, bisimulation R1 low | Strengthen “reasoning gap” claim; hash is not the sole confound |
| Hash ≈ 0, bisimulation R1 high | **Reframe** equivalence headline: hash contract drives collapse; distinguish from universal reasoning failure |
| Hash R2C high, bisimulation R2C high | R2C helps both contracts → tool synthesis, not hash-specific |
| Hash R2C high, bisimulation R2C only modest uplift | Hash builder was the binding constraint for equivalence |

**Do not invalidate** frozen TOSEM numbers — present A1 as **supplementary** construct-validity evidence.

---

## Verification (no API)

```bash
pip install -e ".[dev,plot]"
PYTHONPATH=src python3.12 -m pytest \
  tests/unit/test_bisimulation_witness.py \
  tests/unit/test_f1_bisimulation_witness_verifier_audit.py -q
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.export_constructible_equivalence_analysis
```

---

## Related docs

- [`constructible_equivalence_witness_experiment.md`](constructible_equivalence_witness_experiment.md)
- [`TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](TOSEM_EXPERIMENT_EXTENSION_PLAN.md) (prior extension campaigns A–E)
- Frozen hash audit: [`f1_equivalence_witness_verifier_audit.md`](f1_equivalence_witness_verifier_audit.md)

# Experiment A1 — constructible equivalence witness analysis

**Study ID:** `F1-constructible-equivalence-v1`  
**Purpose:** Construct-validity extension comparing hash-based vs.\ bisimulation witnesses on the
fixed F1 equivalence subset ($n{=}51$ items).

This is an **extension study**; it does not replace the primary frozen hash-witness benchmark.

---

## Run roots (completed campaigns)

| Provider | Track | Path |
|----------|-------|------|
| Claude | R1 | `runs/f1_constructible_equivalence_claude_n100_v1/R1/` |
| Claude | R2C | `runs/f1_constructible_equivalence_claude_n100_v1/R2C/` |
| GPT-4.1 | R1 | `runs/f1_constructible_equivalence_gpt_n100_v1/R1/` |
| GPT-4.1 | R2C | `runs/f1_constructible_equivalence_gpt_n100_v1/R2C/` |

Frozen hash baselines (same item IDs) are read from primary/ablation run roots documented in
`constructible_equivalence_analysis.py`.

---

## Read-only export (no API)

```bash
cd fsmreasonbench
export PYTHONPATH=src
python3.12 -m fsmreasonbench.cli.export_constructible_equivalence_analysis
```

Outputs:

| Artifact | Path |
|----------|------|
| Analysis JSON | `docs/a1_constructible_equivalence_v1/constructible_equivalence_analysis.json` |
| Main table (LaTeX) | `docs/a1_constructible_equivalence_v1/extension_constructible_equivalence_witness.tex` |
| Statistics table (LaTeX) | `docs/a1_constructible_equivalence_v1/extension_constructible_equivalence_statistics.tex` |
| Paper table copies | `../paper/tables/extension_constructible_equivalence_*.tex` |
| Figure | `../paper/figures/extension_constructible_equivalence_comparison.pdf` |

Statistics reuse the paper-wide bootstrap settings (seed 4242, 1000 percentile resamples) and exact
paired McNemar tests on identical item IDs.

---

## Scripts and verifier

| Component | Path |
|-----------|------|
| Study runner | `src/fsmreasonbench/cli/run_f1_constructible_equivalence_study.py` |
| Shell shortcuts | `scripts/run_a1_constructible_equivalence.sh` |
| Analysis export | `src/fsmreasonbench/cli/export_constructible_equivalence_analysis.py` |
| Bisimulation verifier | `src/fsmreasonbench/verifier/separation.py` (`verify_bisimulation_witness_certificate`) |
| Verifier audit | `python3.12 -m fsmreasonbench.cli.export_f1_bisimulation_witness_verifier_audit` |
| Protocol diagnostic | `docs/constructible_equivalence_protocol_diagnostic.md` |

Included in `./scripts/reproduce_tosem_tables.sh` after the primary TOSEM export.

---

## Unit tests

```bash
PYTHONPATH=src python3.12 -m pytest \
  tests/unit/test_constructible_equivalence_analysis.py \
  tests/unit/test_constructible_equivalence_protocol.py -q
```

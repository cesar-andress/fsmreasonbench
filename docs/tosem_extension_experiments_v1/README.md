# TOSEM extension experiments (v1)

Read-only exports and manual campaign launchers for **post-freeze extension studies**
requested by external TOSEM review. These campaigns **do not modify** the benchmark,
verifier, scorer, cohorts, or any frozen run listed in
[`../EXPERIMENTAL_FREEZE_TOSEM.md`](../EXPERIMENTAL_FREEZE_TOSEM.md).

**Planning document:** [`../TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](../TOSEM_EXPERIMENT_EXTENSION_PLAN.md)

---

## What was added

| Experiment | Purpose | Launcher / export |
|------------|---------|-------------------|
| **A** Run-to-run stability | Repeated frontier campaigns (`replicate_01/…`) | `run_frontier_replicate_study` |
| **B** GPT attribution ladder | Oracle+Format, R2A, R2B, R2C for GPT-4.1 | `run_f1_oracle_verdict_ablation`, `run_f1_r2_attribution_ablation` |
| **C** Cross-model attribution | Claude vs GPT paired summaries | `export_tosem_extension_experiments` |
| **D** Stability vs gaps | Compare cross-model gaps to replicate std | same export (uses aggregate replicates) |
| **E** Paper integration | `extension_*.tex` / `extension_*.pdf` under `paper/` | same export |

New outputs use the **`extension_` prefix** and never overwrite frozen TOSEM tables.

---

## Reproduce exports (no API)

```bash
cd fsmreasonbench
pip install -e ".[dev,plot]"
PYTHONPATH=src python3 -m fsmreasonbench.cli.export_tosem_extension_experiments
```

Manifest: `docs/tosem_extension_experiments_v1/extension_manifest.json`

Pending replicate or GPT ladder runs appear under `pending_studies` until campaigns complete.

---

## Manual campaign execution

```bash
./scripts/run_tosem_extension_campaigns.sh help
```

See the extension plan for recommended order, runtime, and API cost estimates.

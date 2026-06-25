# FSMReasonBench — ACM TOSEM companion artifact

**Target venue:** ACM Transactions on Software Engineering and Methodology (TOSEM)  
**Manuscript:** [`../../paper/`](../../paper/) (sibling directory in the monorepo)  
**Authoritative freeze:** [`../../paper/EXPERIMENTAL_FREEZE_TOSEM.md`](../../paper/EXPERIMENTAL_FREEZE_TOSEM.md)  
**Artifact mirror:** [`../EXPERIMENTAL_FREEZE_TOSEM.md`](../EXPERIMENTAL_FREEZE_TOSEM.md)

This folder documents how the **published FSMReasonBench v1.0.0 artifact** supports the
TOSEM empirical study. The study uses frozen model runs, layered scoring, and read-only export
pipelines — **not** live API inference.

---

## What the TOSEM paper uses

| Evidence class | Models / conditions | Documented in |
|----------------|---------------------|---------------|
| Frontier tool tracks | Claude Sonnet 4.5, GPT-4.1 (C2/F1 × R1/R2) | Freeze doc § Claude/GPT tools |
| Claude attribution ladder | F1 Oracle+Format, R2A, R2B, R2C; C2 control ladder | Freeze doc § ablations |
| GPT partial attribution | F1 R2C only | Freeze doc § GPT R2C |
| Open-weight matrix | Gemma2 9B, Llama 3.1 8B, Mistral Nemo 12B, Qwen2.5 Coder 7B (24 cells) | Freeze doc § local matrix |

**Excluded from TOSEM claims (audit only):** Gemini, DeepSeek, provider-misclassified Claude
`frontier_claude_sonnet_full_n100_v1`, quota-contaminated Gemini pilots, superseded n=20 pilots.
See the freeze document for the full exclusion table.

---

## Read-only reproduction (no API keys)

Requires **Python ≥ 3.11** (tested with 3.12), editable install, and frozen run trees under
`runs/` (included in the Zenodo tarball; may be gitignored in development clones).

```bash
cd fsmreasonbench
pip install -e ".[dev,plot]"
./scripts/reproduce_tosem_tables.sh
```

This regenerates:

- TOSEM manuscript LaTeX tables under `../paper/tables/` (Claude+GPT frontier, gap, failure stages, local matrix with bootstrap CIs, McNemar)
- Experiment A1 constructible-equivalence tables, statistics, and figure (`export_constructible_equivalence_analysis`)
- JSON summaries under `docs/` and `docs/tosem_empirical_package_v1/`
- Claude ablation tables and complexity figure via the historical TMLR export path (still required until merged)

Details: [`REPRODUCTION.md`](REPRODUCTION.md)

---

## What is intentionally **not** in the TOSEM manuscript

- Families **F2–F4** and calibration **C1** (specified, not empirically evaluated)
- Full GPT attribution ladder (no GPT Oracle+Format, R2A, R2B) — **extension infrastructure added; campaigns manual**
- Open-weight attribution ablations (matrix is R0/R1/R2 only)
- Cross-temperature replication (T=0.2 only)
- Gemini / DeepSeek frontier results

**Post-freeze extensions (manual):** run-to-run replicates, full GPT ladder, cross-model exports —
[`../TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](../TOSEM_EXPERIMENT_EXTENSION_PLAN.md)

---

## Legacy / historical material

The companion paper was drafted during a TMLR submission cycle. Historical exports remain at
[`../tmlr_empirical_package_v1/`](../tmlr_empirical_package_v1/) and
[`../historical/README.md`](../historical/README.md). **Cite TOSEM freeze paths** for the ACM
submission; do not treat TMLR package labels as the active venue.

---

## Related documents

| Document | Role |
|----------|------|
| [`REPRODUCTION.md`](REPRODUCTION.md) | Step-by-step read-only workflow |
| [`ZENODO_RELEASE_NOTES.md`](ZENODO_RELEASE_NOTES.md) | Next Zenodo deposit checklist (TOSEM companion) |
| [`../tosem_empirical_package_v1/README.md`](../tosem_empirical_package_v1/README.md) | Export CLI outputs |
| [`../zenodo/REPRODUCIBILITY.md`](../zenodo/REPRODUCIBILITY.md) | General R1–R4 tiers |
| [`../paper_results.md`](../paper_results.md) | Canonical run inventory |

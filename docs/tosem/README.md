# Empirical package docs (legacy path: `docs/tosem/`)

> **Note:** This directory name is a **historical identifier** retained for path stability.
> Current public software identity is venue-neutral FSMReasonBench (see repository `README.md`).
>
> **Auditors:** [`../../REVIEWER.md`](../../REVIEWER.md) · [`../REVIEWER.md`](../REVIEWER.md) ·
> `./scripts/reproduce_archived_tables.sh`

**Manuscript (optional sibling):** [`../../../paper/`](../../../paper/)  
**Freeze index:** [`../EXPERIMENTAL_FREEZE_TOSEM.md`](../EXPERIMENTAL_FREEZE_TOSEM.md) (legacy filename)

This folder documents how the **published FSMReasonBench archival outputs** support offline
regeneration of layered evaluation tables. The study uses frozen model runs, layered scoring, and
read-only export pipelines — **not** live API inference.

---

## What the calibration study uses

| Evidence class | Models / conditions | Documented in |
|----------------|---------------------|---------------|
| Frontier tool tracks | Claude Sonnet 4.5, GPT-4.1 (C2/F1 × R1/R2) | Freeze doc § Claude/GPT tools |
| Claude attribution ladder | F1 Oracle+Format, R2A, R2B, R2C; C2 control ladder | Freeze doc § ablations |
| GPT partial attribution | F1 R2C only | Freeze doc § GPT R2C |
| Open-weight matrix | Gemma2 9B, Llama 3.1 8B, Mistral Nemo 12B, Qwen2.5 Coder 7B (24 cells) | Freeze doc § local matrix |

**Excluded from headline archival claims (audit only):** Gemini, DeepSeek, provider-misclassified Claude
`frontier_claude_sonnet_full_n100_v1`, quota-contaminated Gemini pilots, superseded n=20 pilots.
See the freeze document for the full exclusion table.

---

## Read-only regeneration (no API keys)

Requires **Python ≥ 3.11** (tested with 3.12), editable install, and frozen run trees under
`runs/` (included in the Zenodo tarball; may be gitignored in development clones).

```bash
pip install -e ".[dev,plot]"
./scripts/reproduce_archived_tables.sh
```

This regenerates:

- Layered-evaluation LaTeX tables under `../paper/tables/` when present (Claude+GPT frontier, gap,
  failure stages, local matrix with bootstrap CIs, McNemar)
- Experiment A1 constructible-equivalence tables, statistics, and figure
- JSON summaries under `docs/` and `docs/tosem_empirical_package_v1/`
- Claude ablation tables and complexity figure via the historical `tmlr_*` export path (legacy name)

Details: [`REPRODUCTION.md`](REPRODUCTION.md)

---

## What is intentionally **not** in the archival headline cells

- Families **F2–F4** and calibration **C1** (specified, not empirically evaluated)
- Full GPT attribution ladder (no GPT Oracle+Format, R2A, R2B)
- Open-weight attribution ablations (matrix is R0/R1/R2 only)
- Cross-temperature replication (T=0.2 only)
- Gemini / DeepSeek frontier results

**Post-freeze extension plans (manual; may require APIs):**
[`../TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](../TOSEM_EXPERIMENT_EXTENSION_PLAN.md) (legacy filename)

---

## Legacy / historical material

Earlier draft cycles left historical exports at
[`../tmlr_empirical_package_v1/`](../tmlr_empirical_package_v1/) and
[`../historical/README.md`](../historical/README.md). Prefer current freeze paths and the concept DOI
for citation; treat older package labels as historical identifiers only.

---

## Related documents

| Document | Role |
|----------|------|
| [`REPRODUCTION.md`](REPRODUCTION.md) | Step-by-step read-only workflow |
| [`ZENODO_RELEASE_NOTES.md`](ZENODO_RELEASE_NOTES.md) | Historical v1 deposit notes |
| [`../tosem_empirical_package_v1/README.md`](../tosem_empirical_package_v1/README.md) | Export CLI outputs |
| [`../zenodo/REPRODUCIBILITY.md`](../zenodo/REPRODUCIBILITY.md) | General R1–R4 tiers |
| [`../paper_results.md`](../paper_results.md) | Canonical run inventory |

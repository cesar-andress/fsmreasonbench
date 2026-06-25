# TOSEM read-only reproduction workflow

**Policy:** Reviewers and artifact evaluators must be able to regenerate manuscript-facing
tables from **frozen run outputs** without model API keys and without re-running inference.

**Python:** ≥ 3.11 (project pin in `pyproject.toml`; CI and release checks use 3.12)  
**Install:**

```bash
cd fsmreasonbench
pip install -e ".[dev,plot]"
```

---

## Tier 0 — Sanity checks (no runs required)

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python3.12 -m pytest tests/unit/test_tosem_empirical_package_export.py \
  tests/unit/test_local_matrix_bootstrap_export.py -q
```

---

## Tier 1 — Validate frozen cohorts

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/c2-reachability-level3
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3
```

---

## Tier 2 — Regenerate all TOSEM manuscript tables (recommended)

```bash
./scripts/reproduce_tosem_tables.sh
```

Equivalent manual steps:

```bash
export PYTHONPATH=src
python3.12 -m fsmreasonbench.cli.export_tosem_empirical_package
python3.12 -m fsmreasonbench.cli.export_tmlr_empirical_package
```

### TOSEM export (`export_tosem_empirical_package`)

Reads frozen `combined_summary.json` / `scores.jsonl` under:

| Campaign | Run root |
|----------|----------|
| Claude tools | `runs/frontier_claude_sonnet_tools_n100_v2/` |
| GPT tools | `runs/frontier_gpt_tools_n100_v1/` |
| GPT F1 R2C | `runs/ablations_f1_r2c_gpt_n100_v1/` |
| Local matrix | `runs/local_matrix_n100_t02_v2/` |

Writes LaTeX to `../paper/tables/` and JSON to `docs/` (see
[`../tosem_empirical_package_v1/package_manifest.json`](../tosem_empirical_package_v1/package_manifest.json)).

### Claude ablation export (`export_tmlr_empirical_package`)

Still required for:

- `paper/tables/f1_claude_ablations.tex`
- `paper/tables/c2_claude_ablations.tex`
- `paper/figures/figure_certificate_complexity_frontier_comparison.pdf`
- Bootstrap/McNemar appendix material under `docs/tmlr_empirical_package_v1/`

Reads frozen runs:

- `runs/ablations_f1_r2_attribution_claude_n100_v1/`
- `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/`
- `runs/ablations_c2_existential_universal_claude_n100_v1/`

---

## Tier 3 — Regenerate campaign combined summaries (still no inference)

If a cell directory has `scores.jsonl` but a stale `combined_summary.json`:

```bash
# GPT frontier (report-only)
./scripts/run_frontier_gpt_campaign.sh report

# General pattern: use campaign-specific report CLIs where documented
# in docs/frontier_gpt_campaign.md
```

These commands **aggregate on-disk scores**; they do not call OpenAI unless explicitly run in
`smoke`/`full`/`r1`/`r2` modes (marked **not part of reproduction**).

---

## Tier 4 — Inspect raw outputs

Per-cell artifacts live under each run root:

```
runs/<campaign>/.../scores.jsonl      # per-item scoring records
runs/<campaign>/.../results.jsonl     # raw model outputs
runs/<campaign>/.../transcripts/      # rescore-able transcripts
runs/<campaign>/.../summary.json      # cell rollup
runs/<campaign>/combined_summary.json # campaign rollup
```

Failure taxonomy example:

```bash
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.failure_taxonomy \
  --scores runs/frontier_claude_sonnet_tools_n100_v2/.../scores.jsonl \
  --results runs/frontier_claude_sonnet_tools_n100_v2/.../results.jsonl \
  --out /tmp/taxonomy.json
```

---

## Commands that require API access (NOT reproduction)

| Command | Why excluded |
|---------|--------------|
| `./scripts/run_frontier_gpt_campaign.sh smoke\|full\|r1\|r2` | Calls OpenAI |
| Track pilot / attribution runners with live providers | Calls Anthropic/OpenAI/Ollama for new inference |
| `generate_batch` with LLM runners | New model responses |

Document any new inference under a **new campaign ID** and reopen the freeze in the manuscript
before citing results.

---

## Expected outputs after Tier 2

| Output | Path |
|--------|------|
| TOSEM package manifest | `docs/tosem_empirical_package_v1/package_manifest.json` |
| GPT summaries | `docs/frontier_gpt_tools_n100_v1_summary.json`, `docs/frontier_gpt_tools_n100_v1_uncertainty.json` |
| Local matrix bootstrap | `docs/local_matrix_n100_t02_bootstrap_summary.json` |
| Manuscript tables | `../paper/tables/*_n100*.tex`, `results_paired_mcnemar.tex`, ablation tables |
| Main-text figures | `../paper/figures/figure_verdict_witness_gap_comparison.pdf`, `figure_certificate_complexity_frontier_comparison.pdf`, `figure_attribution_fingerprint_comparison.pdf`, `extension_constructible_equivalence_comparison.pdf` |

Numerical values must match the frozen `combined_summary.json` sources. If they diverge, check
that run trees are complete and that export CLIs were run with `PYTHONPATH=src`.

---

## Runtime, hardware, and cost assumptions

| Task | Expected runtime | Hardware | API cost |
|------|------------------|----------|----------|
| Tier 0 sanity (`artifact_health` + export unit tests) | < 1 min | Any Linux/macOS with Python ≥ 3.11 | $0 |
| Tier 1 cohort validation | < 30 s | Same | $0 |
| Tier 2 `./scripts/reproduce_tosem_tables.sh` | 2–5 min | Same; matplotlib for figures | $0 |
| Tier 4 extension / re-inference campaigns | hours–days | GPU optional for Ollama; API keys for frontier | **Not frozen** — see extension plan |

**Random seeds:** item generation uses fixed seeds in cohort manifests (`cohorts/v0.1-expanded-n100/*/manifest.json`). Inference cells use temperature `T=0.2` and one pass per item (`temp_0.2` directories).

**Version pins:** `releases/1.0.0/release_manifest.json`, `CITATION.cff`, Zenodo DOI `10.5281/zenodo.20836348`.

---

## Post-freeze extension experiments (Tier 4 — manual API)

Infrastructure for run-to-run replicates and the full GPT attribution ladder lives outside the
frozen TOSEM export path. These campaigns write to **new run roots** (`*_replicates/`,
`ablations_f1_r2_attribution_gpt_n100_v1/`, etc.) and produce `extension_*` manuscript artifacts.

| Step | Command |
|------|---------|
| Plan & order | [`../TOSEM_EXPERIMENT_EXTENSION_PLAN.md`](../TOSEM_EXPERIMENT_EXTENSION_PLAN.md) |
| Launch helper | `./scripts/run_tosem_extension_campaigns.sh help` |
| Export only | `PYTHONPATH=src python3 -m fsmreasonbench.cli.export_tosem_extension_experiments` |

Extension exports do **not** overwrite frozen tables from `reproduce_tosem_tables.sh`.

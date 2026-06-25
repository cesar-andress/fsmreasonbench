# TOSEM empirical package (frozen exports)

Regenerate LaTeX tables and JSON summaries for the TOSEM manuscript from **frozen runs only**
(no model API calls).

## Command

```bash
cd fsmreasonbench
PYTHONPATH=src python3 -m fsmreasonbench.cli.export_tosem_empirical_package
```

Equivalent via the GPT campaign wrapper:

```bash
./scripts/run_frontier_gpt_campaign.sh export
```

## Outputs

| Artifact | Path |
|----------|------|
| Package manifest | `docs/tosem_empirical_package_v1/package_manifest.json` |
| GPT tools summary JSON | `docs/frontier_gpt_tools_n100_v1_summary.json` |
| GPT F1 ablation JSON | `docs/f1_gpt_ablation_stratified_analysis.json` |
| GPT uncertainty JSON | `docs/frontier_gpt_tools_n100_v1_uncertainty.json` |
| Paper LaTeX tables | `../paper/tables/*.tex` |

Generated tables include Claude and GPT frontier summaries, unified frontier comparison,
verdict--witness gap, failure stages, GPT F1 ablations, and paired McNemar comparisons.

## Frozen inputs

See `package_manifest.json` for the authoritative list of `combined_summary.json` paths and
GPT F1 `scores.jsonl` roots.

Claude ablation tables (`f1_claude_ablations.tex`, `c2_claude_ablations.tex`, complexity figure)
remain under `export_tmlr_empirical_package` until merged into this package.

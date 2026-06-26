# TOSEM artifact branch readiness report

**Generated:** 2026-06-20  
**Repository:** `fsmreasonbench/` (artifact)  
**Current branch:** `main` (2 commits ahead of `origin/main` before this release pass)

---

## Latest commits made in this pass

| Commit | Message |
|--------|---------|
| `c336366` | docs: TOSEM artifact branch readiness report |
| `7360638` | tests: validate read-only TOSEM reproduction scripts |
| `d25024a` | cleanup: mark TMLR-era docs and mark inference-only GPT modes |
| `29b9f6d` | repro: add read-only table regeneration workflow |
| `ccd5449` | docs: align artifact documentation with TOSEM submission |

Prior commits already on `main` before this pass:

| Commit | Message |
|--------|---------|
| `69e977f` | Add bootstrap CIs for frozen local matrix cells from scores.jsonl |
| `97f5b33` | Add unified TOSEM empirical export from frozen GPT and Claude runs |

---

## Remaining uncommitted files (intentional)

The following **local WIP** files were **not** committed. They are inference/provider scaffolding outside the read-only TOSEM reproduction path:

| Path | Reason left uncommitted |
|------|-------------------------|
| `src/fsmreasonbench/cli/run_frontier_campaign.py` | Untracked; API inference runner |
| `src/fsmreasonbench/cli/run_openai_provider_smoke.py` | Untracked; requires OpenAI |
| `src/fsmreasonbench/runners/providers/openai.py` | Untracked; provider backend |
| `src/fsmreasonbench/runners/r2c_certificate_synthesis.py` | Untracked; runner helper |
| `tests/unit/test_openai_provider.py` | Untracked; provider tests |
| `tests/unit/test_f1_r2_attribution_ablation_cli.py` | Untracked |
| Modified runner/attribution sources (`run_f1_r2_attribution_ablation.py`, `r2_attribution_*`, etc.) | In-progress edits; frozen runs already complete |

**Action before merging inference WIP:** run targeted tests and ensure `run_frontier_gpt_campaign.sh` smoke/full modes are documented separately from reproduction.

---

## What changed

### Documentation (TOSEM-primary)

- New [`docs/tosem/README.md`](tosem/README.md), [`REPRODUCTION.md`](tosem/REPRODUCTION.md), [`ZENODO_RELEASE_NOTES.md`](tosem/ZENODO_RELEASE_NOTES.md)
- Artifact freeze mirror [`EXPERIMENTAL_FREEZE_TOSEM.md`](EXPERIMENTAL_FREEZE_TOSEM.md) pointing to `paper/EXPERIMENTAL_FREEZE_TOSEM.md`
- Historical index [`historical/README.md`](historical/README.md)
- Updated root `README.md`, `PROJECT_STATUS.md`, `README-RELEASE.md`, `paper_reproduction/README.md`
- Expanded [`paper_results.md`](paper_results.md) frozen-run table (all TOSEM campaigns)
- TMLR package README marked historical; zenodo docs cross-link TOSEM workflow
- [`frontier_gpt_campaign.md`](frontier_gpt_campaign.md) — inference modes flagged as non-reproduction

### Reproducibility

- Implemented [`scripts/reproduce_tosem_tables.sh`](../scripts/reproduce_tosem_tables.sh) (read-only)
- [`scripts/reproduce_table.sh`](../scripts/reproduce_table.sh) delegates to TOSEM script (no longer a stub)
- Validated with Python **3.12** (`requires-python >= 3.11` in `pyproject.toml`)

### Tests

- `tests/unit/test_reproduce_tosem_script.py` — script presence and no API references

---

## What was intentionally left unchanged

- All files under `runs/` (frozen outputs)
- Numerical results in `combined_summary.json`, `scores.jsonl`, exported JSON
- Scorer, verifier, cohort item content
- Manuscript in `../paper/` (no edits in this pass)
- Published Zenodo v1.0.0 DOI record (no upload, no new DOI)
- TMLR export directory contents (historical; still used by reproduction script)

---

## Frozen campaigns included (TOSEM)

| Campaign | Run root | Cells |
|----------|----------|------:|
| Claude Sonnet 4.5 tools | `runs/frontier_claude_sonnet_tools_n100_v2/` | 4 |
| Claude F1 attribution | `runs/ablations_f1_r2_attribution_claude_n100_v1/` | 3 |
| Claude F1 Oracle control | `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/` | 1 |
| Claude C2 ablations | `runs/ablations_c2_existential_universal_claude_n100_v1/` | 5 |
| GPT-4.1 tools | `runs/frontier_gpt_tools_n100_v1/` | 4 |
| GPT F1 R2C | `runs/ablations_f1_r2c_gpt_n100_v1/` | 1 |
| Local Ollama matrix | `runs/local_matrix_n100_t02_v2/` | 24 |

**Models included:** Claude Sonnet 4.5, GPT-4.1, Gemma2 9B, Llama 3.1 8B, Mistral Nemo 12B, Qwen2.5 Coder 7B.

---

## Excluded campaigns (audit only)

| Run root | Reason |
|----------|--------|
| `runs/frontier_claude_sonnet_full_n100_v1/` | Provider misclassification |
| `runs/frontier_gemini_*` | Quota contamination |
| Superseded n=20 pilots | Replaced by n=100 freeze |

Gemini and DeepSeek do not appear in TOSEM claims.

---

## Reproducibility commands (read-only)

```bash
cd fsmreasonbench
pip install -e ".[dev,plot]"

# Recommended one-shot
./scripts/reproduce_tosem_tables.sh

# Sanity
PYTHONPATH=src python3.12 -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python3.12 -m pytest tests/unit/test_tosem_empirical_package_export.py \
  tests/unit/test_local_matrix_bootstrap_export.py \
  tests/unit/test_reproduce_tosem_script.py -q
```

**Requires:** frozen run trees under `runs/` (Zenodo tarball or local archive).  
**Does not require:** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or Ollama.

---

## Zenodo readiness status

| Item | Status |
|------|--------|
| v1.0.0 DOI published | ✅ `10.5281/zenodo.20897937` |
| TOSEM companion deposit notes | ✅ `docs/tosem/ZENODO_RELEASE_NOTES.md` |
| Read-only reproduction script | ✅ `scripts/reproduce_tosem_tables.sh` |
| Tarball SHA256SUMS refresh for TOSEM runs | ⏳ Manual step before next upload |
| Bump `releases/<version>/release_manifest.json` | ⏳ Before v1.0.1+ deposit |
| Upload / mint new DOI | ❌ Not performed (by design) |

---

## Known limitations

1. Claude ablation LaTeX still flows through `export_tmlr_empirical_package` (historical path).
2. `package_manifest.json` may record absolute paths after export on a given machine; relative paths in source constants remain authoritative in `tosem_empirical_package.py`.
3. Default `python3` on some systems is 3.6 — use **python3.12** explicitly (documented).
4. GPT campaign shell `report`/`smoke` modes depend on uncommitted inference CLIs (not needed for reproduction).
5. Open-weight F1 tool-track cells with low extractability remain interpretive constraints (documented in freeze).

---

## Recommendation: create the branch

After verifying a clean commit state for documentation and scripts:

```bash
cd fsmreasonbench
git status   # expect only documented WIP provider files, if any
git switch -c tosem-artifact-freeze
```

If you prefer to branch from a specific commit hash after this pass:

```bash
git switch -c tosem-artifact-freeze <commit-sha>
git push -u origin tosem-artifact-freeze   # when ready
```

The branch name **`tosem-artifact-freeze`** marks the artifact state aligned with the ACM TOSEM manuscript freeze (`paper/EXPERIMENTAL_FREEZE_TOSEM.md`) and read-only reproduction workflow.

---

## Validation performed

| Check | Result |
|-------|--------|
| `./scripts/reproduce_tosem_tables.sh` | ✅ Pass |
| `artifact_health` | ✅ Pass |
| `pytest` TOSEM + bootstrap + reproduce script tests | ✅ Pass |
| Frozen summaries present | ✅ Claude, GPT, local matrix |
| No inference / API calls during validation | ✅ Confirmed |

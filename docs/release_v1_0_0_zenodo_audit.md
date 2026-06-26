# FSMReasonBench v1.0.0 — Pre-Zenodo Release Audit

> **Superseded for publication status.** FSMReasonBench v1.0.0 was published on Zenodo with
> DOI [10.5281/zenodo.20897937](https://doi.org/10.5281/zenodo.20897937). This report records
> the **pre-publication** audit snapshot (2026-06-20). See [`PROJECT_STATUS.md`](../PROJECT_STATUS.md)
> and [`releases/1.0.0/`](../releases/1.0.0/) for current state.

**Audit date:** 2026-06-20  
**Auditor role:** release-quality check (not research review)  
**Repository audited:** `fsmreasonbench/` (git root: `github.com/cesar-andress/fsmreasonbench`)  
**Target release:** **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0**  
**Constraints observed:** no model API calls; frozen runs not modified; no secrets printed

---

## Release readiness verdict

### **NOT READY**

The artifact has strong offline reproducibility for TMLR empirical exports and verifier audits, and frozen run directories exist on disk with documented exclusions. However, **legal metadata, release manifests, git release hygiene, cohort packaging model, and tarball assembly** are incomplete for a public Zenodo v1.0.0 deposit.

A realistic path is **READY AFTER MINOR FIXES** only for an **internal frozen-evaluation tarball** (code + docs + pinned runs) once blockers below are cleared—not for minting DOI today.

---

## Executive summary

| Area | Status | Notes |
|------|--------|-------|
| Repository hygiene | ⚠️ Partial | Core tree present; release manifest, lockfile, release notes for 1.0.0 missing |
| Secrets / sensitive data | ✅ Pass | No live API keys found in tracked files or scanned `runs/` |
| Frozen runs (on disk) | ✅ Pass | All five required run roots exist and validate structurally |
| Invalid run documentation | ✅ Pass | Excluded runs documented; not used in TMLR package |
| Offline reproducibility | ✅ Pass | Verifier audit, decomposition, complexity, TMLR package export work without APIs |
| Cohort integrity | ⚠️ Partial | `v0.1-expanded-n100` validates; no `1.0-public`; answer keys inline in cohort JSONL |
| Tests (release-critical) | ✅ Pass | 31 targeted unit tests passed |
| Zenodo metadata | ❌ Fail | `CITATION.cff` and `LICENSE` are placeholders |
| Git release state | ❌ Fail | 65 uncommitted paths; no `v1.0.0` tag; large untracked release code |

---

## 1. Repository hygiene audit

### Present and adequate

| Item | Path | Status |
|------|------|--------|
| README | `README.md` | ✅ Clear artifact philosophy; states Zenodo-first model |
| Release quickstart | `README-RELEASE.md` | ⚠️ Present but paths partly stale (see below) |
| LICENSE | `LICENSE` | ❌ Placeholder (`TBD`) |
| Citation metadata | `CITATION.cff` | ⚠️ Present; DOI/license/repo URL placeholders |
| Package config | `pyproject.toml` | ⚠️ Present; version `0.2.0-dev`, license `TBD` |
| Source | `src/fsmreasonbench/` | ✅ Generator, verifier, evaluator, runners, cohort |
| Tests | `tests/` | ✅ Large unit suite (~543 tests in pytest cache) |
| Docs | `docs/` | ✅ Spec, artifact policies, paper results, zenodo folder |
| Cohorts | `cohorts/` | ✅ Exploratory + expanded n=100 snapshots committed |
| CLI entrypoints | `src/fsmreasonbench/cli/` | ✅ 50+ modules; most invoked via `python -m` |
| Scripts | `scripts/` | ⚠️ Partial (`verify_submission.py`, `validate_cohort_integrity.sh`; `reproduce_table.sh` is stub) |
| Release notes (dev) | `docs/releases/v0.1-exploratory.md` | ✅ Milestone doc |
| Reproducibility docs | `docs/artifact/reproducibility_policy.md`, `docs/zenodo/REPRODUCIBILITY.md` | ✅ |
| Project status | `PROJECT_STATUS.md` | ✅ Honest: not yet Zenodo release |

### Missing, stale, or inconsistent

| Issue | Severity | Detail |
|-------|----------|--------|
| No `releases/1.0.0/release_manifest.json` | **Blocking** | Only `releases/TEMPLATE/` exists |
| No root `SHA256SUMS` | **Blocking** | Required by `README-RELEASE.md` step 1 |
| No `environment/requirements-lock.txt` | **Blocking** | `environment/README.md` only; release policy expects lockfile |
| `pyproject.toml` version ≠ release | **Blocking** | Package `0.2.0-dev` vs target `1.0.0` |
| `LICENSE` / `CITATION.cff` placeholders | **Blocking** | Cannot publish with `TBD` license and DOI |
| `README-RELEASE.md` cohort paths | **Major** | References `cohorts/<cohort_version>.manifest.json` and `cohorts/evaluatee/`; actual layout is `cohorts/v0.1-expanded-n100/<family>/manifest.json` |
| `scripts/reproduce_table.sh` | **Major** | Stub exits 2; contradicts README-RELEASE step 5 |
| `pyproject.scripts` | **Minor** | Only `fsmreasonbench-generate-one` registered; export CLIs undocumented in `[project.scripts]` |
| Paper prose location | **Info** | Manuscript lives in sibling `../paper/` (parent monorepo), not this git repo |
| `.gitignore` excludes `runs/` | **Info (planned)** | Correct for GitHub dev; Zenodo tarball must **include** frozen run trees explicitly |

### Recommended files to add before release

- `releases/1.0.0/release_manifest.json` (filled from template)
- `releases/1.0.0/RELEASE_NOTES.md` — title: **FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0**
- Root `SHA256SUMS` for tarball contents
- `environment/requirements-lock.txt` (pinned from tested Python 3.11 env)
- `docs/release_v1_0_0_frozen_runs_manifest.json` — inventory of five valid run roots + checksums
- `docs/release_v1_0_0_excluded_runs.md` — pointer consolidating exclusion policy (or extend `docs/paper_results.md`)

### Recommended files to remove or exclude from Zenodo tarball

- `runs/frontier_claude_sonnet_full_n100_v1/` (contaminated; audit-only if retained locally)
- `runs/frontier_gemini_flash_r0_smoke_v1`–`v4/` (quota-contaminated)
- `.pytest_cache/`, `__pycache__/`, dev smoke runs not in frozen manifest
- Staging paths referenced only in manifests: `runs/_expanded_n100_staging/`, `runs/_c2_balanced_n100_staging/` (need not ship if cohort JSONL is self-contained)

---

## 2. Sensitive data audit

**Method:** ripgrep over `*.{py,md,json,yml,yaml,env,sh,cff,jsonl,log}` and targeted scan of `runs/` for key-like patterns.

**Result: no live secrets detected.** No matches for `sk-ant-`, `AIzaSy`, or embedded high-entropy API keys in run artifacts.

### References to sensitive patterns (documentation / code — not secret values)

| Pattern | Example locations (file:line) |
|---------|----------------------------------|
| `ANTHROPIC_API_KEY` | `docs/frontier_provider_backends.md:12,55,93`; `src/fsmreasonbench/runners/providers/anthropic.py:34–37`; tests `tests/unit/test_anthropic_provider.py:31–32` |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `docs/frontier_provider_backends.md:13,114`; `src/fsmreasonbench/runners/providers/gemini.py:29–34`; tests `tests/unit/test_gemini_provider.py:30–33` |
| `export …API_KEY=...` (placeholder) | `docs/frontier_provider_backends.md:55,93,114` — ellipsis placeholders only |
| Test fixture `"gemini-key"` | `tests/unit/test_gemini_provider.py:39` — non-production dummy |
| `token` / `secret` (redaction logic) | `src/fsmreasonbench/evaluator/equivalence_hash_mismatch_decomposition.py:183` — redaction regex, not a stored secret |
| `password` / `bearer` | No matches in artifact tree |
| `~/.bashrc` | No matches |
| Personal emails | No email addresses found outside ORCID URL in `CITATION.cff` |

### Absolute local paths (should not appear in public release artifacts)

| File | Lines |
|------|-------|
| `docs/tmlr_empirical_package_v1/package_manifest.json` | 18 |
| `docs/f1_local_matrix_subtype_stratified_analysis.json` | 3–4 |
| `docs/f1_local_matrix_subtype_stratified_analysis.md` | 5–6 |
| `docs/f1_claude_ablation_stratified_analysis.json` | 3 |
| `docs/f1_claude_ablation_stratified_analysis.md` | 13 |
| `docs/c2_existential_universal_stratified_analysis.json` | 3, 12 |
| `docs/c2_existential_universal_claude_n100_v1.md` | 3 |
| `cohorts/v0.1-expanded-n100/*/manifest.json` | `source_items_path` fields (~544–547) |
| `cohorts/v0.1-exploratory/*/manifest.json` | `source_items_path` fields |
| `docs/rate_ci_summary.json` | 5–7 |
| `docs/rate_ci_report.md` | 10–12 |

**Fix:** regenerate export JSON/MD with repo-relative paths before tarball; normalize cohort manifest `source_items_path` to relative paths.

---

## 3. Frozen run audit

### Required valid / frozen runs (on disk)

| Run root | Present | Structural check | Used in TMLR package |
|----------|---------|------------------|----------------------|
| `runs/local_matrix_n100_t02_v2` | ✅ | 24/24 cells `completed`; `failed_cells=[]` | ✅ `table4`, local analysis |
| `runs/frontier_claude_sonnet_tools_n100_v2` | ✅ | 4/4 cells `completed`; aggregate `provider_error_count=0` per cell | ✅ primary Claude surface |
| `runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1` | ✅ | `combined_summary`: 1/1 `completed` | ✅ oracle ablation |
| `runs/ablations_f1_r2_attribution_claude_n100_v1` | ✅ | `combined_summary`: 3/3 `completed` (R2A/R2B/R2C) | ✅ attribution ladder |
| `runs/ablations_c2_existential_universal_claude_n100_v1` | ✅ | On disk; C2 ablation study root | ✅ C2 control |

**Size (local disk, not in git):** ~82M + 24M + 22M + 16M + 1.9M ≈ **146 MB** for the five roots.

### Documentation gaps for frozen runs

| Gap | Severity |
|-----|----------|
| `docs/paper_results.md` **Frozen runs** table lists only local matrix + Claude tools | **Major** — ablation runs documented in `docs/tmlr_empirical_package_v1/README.md` and ablation docs but **not** in canonical `paper_results.md` table |
| `docs/PAPER_FREEZE_AUDIT.md` omits ablation run roots | **Minor** |
| All frozen runs gitignored | **Expected** — must be listed in Zenodo file inventory |

### Invalid / excluded runs (documented; must not drive conclusions)

| Run root | Documented exclusion | On disk | Used in TMLR package? |
|----------|---------------------|---------|------------------------|
| `runs/frontier_claude_sonnet_full_n100_v1` | ✅ `docs/paper_results.md`, `PAPER_FREEZE_AUDIT.md`, `tmlr_empirical_package` EXCLUDED_RUNS | ✅ | ❌ No |
| `runs/frontier_gemini_flash_r0_smoke_v1`–`v4` | ✅ Same sources | ✅ v1–v4 | ❌ No |
| Other `runs/frontier_gemini_*` | ✅ Policy: any Gemini run excluded | Various | ❌ No |

**TMLR empirical package** (`src/fsmreasonbench/evaluator/tmlr_empirical_package.py`) explicitly lists excluded runs and points only to the five valid roots.

### Note on local matrix provider errors

`combined_summary.json` aggregates `provider_error_count=55` across cells, but all 24 cells are `status=completed` with empty `failed_cells`. This reflects **historical Ollama transient errors retried within completed cells**, not an incomplete matrix. Document this in release notes to avoid misreading.

---

## 4. Reproducibility audit

Assumption: fresh user has Python ≥3.11, repo checkout (or tarball), and **frozen `runs/` directories** present locally.

### Commands tested (this audit)

| Command | Result |
|---------|--------|
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort --cohort-dir cohorts/v0.1-expanded-n100/f1-mixed-level3` | ✅ VALID, n=100 |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort --cohort-dir cohorts/v0.1-expanded-n100/c2-reachability-level3` | ✅ VALID, n=100 |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort --cohort-dir cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100` | ✅ VALID, n=100 (cohort **untracked** in git) |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health` | ✅ PASS (15/15 CLI imports) |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_f1_equivalence_witness_verifier_audit` | ✅ (default under `docs/`) |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_equivalence_hash_mismatch_decomposition` | ✅ |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_certificate_class_complexity_analysis` | ✅ |
| `PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_tmlr_empirical_package --out-dir /tmp/tmlr_pkg_test` | ✅ tables + figure |
| `pip install -e ".[dev]"` + targeted pytest (31 tests) | ✅ all passed |
| `PYTHONPATH=src python3.11 -m pytest tests/unit -q` (full suite) | ⏸️ Not completed in audit session (long-running); ~543 tests in cache from prior runs |

### Commands not tested (require external services or missing impl)

| Command / workflow | Blocker |
|--------------------|---------|
| `./scripts/reproduce_table.sh` | Stub — not implemented |
| `./scripts/validate_cohort_integrity.sh` | Not executed (shell wrapper; underlying `validate_cohort` CLI works) |
| `python scripts/verify_submission.py` | Not executed |
| Any `run_track_pilot_models` without `--report-only` | Requires Ollama / Anthropic API |
| Ablation runners (`run_f1_*_ablation`, `run_c2_*`) | Requires Anthropic API |
| `sha256sum -c SHA256SUMS` | File does not exist yet |
| Fresh install on clean VM | Not executed |

### Offline regeneration checklist (no model APIs)

| Artifact | CLI | API needed? |
|----------|-----|-------------|
| Verifier hostile audit (16/16) | `export_f1_equivalence_witness_verifier_audit` | No |
| Hash mismatch decomposition | `export_equivalence_hash_mismatch_decomposition` | No |
| Certificate class complexity | `export_certificate_class_complexity_analysis` | No |
| F1 ablation stratified tables | `export_f1_claude_ablation_stratified_analysis` | No |
| Local matrix subtype analysis | `export_f1_local_matrix_subtype_stratified_analysis` | No |
| C2 existential/universal analysis | `export_c2_existential_universal_stratified_analysis` | No |
| TMLR empirical package (tables + fig) | `export_tmlr_empirical_package` | No |
| Pilot/matrix **reports** from frozen runs | `run_track_pilot_models --report-only` | No |

**Known bug:** `export_equivalence_hash_mismatch_decomposition` rejects absolute `--json-out` outside repo root (`pathlib.relative_to`); use default paths or repo-relative outputs.

---

## 5. Cohort integrity audit

### Committed cohorts

| Bundle | `cohort_id` | Items | Fingerprint / checksums |
|--------|-------------|------:|-------------------------|
| `cohorts/v0.1-expanded-n100/f1-mixed-level3/` | `f1-mixed-level3-v0.1-expanded-n100` | 100 | ✅ `manifest.json` + `sha256sums.txt` |
| `cohorts/v0.1-expanded-n100/c2-reachability-level3/` | `c2-reachability-level3-v0.1-expanded-n100` | 100 | ✅ |
| `cohorts/v0.1-exploratory/*` | `*-v0.1-exploratory` | 20 each | ✅ |
| `cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100/` | `c2-reachability-balanced-n100-v0.1-expanded` | 100 | ✅ validates; **untracked in git** |

### Identity clarity for v1.0.0 release

- **Paper/TMLR primary cohort:** `v0.1-expanded-n100` (internally frozen, **not** `1.0-public`).
- README and `PROJECT_STATUS.md` correctly state public `1.0-public` is **not published**.
- **Release naming risk:** marketing release as `v1.0.0` while cohort remains `v0.1-expanded-n100` requires explicit prose: *benchmark artifact version 1.0.0 ships frozen evaluation cohort v0.1-expanded-n100* OR rename/freeze `1.0-public` before DOI.

### Evaluatee / evaluator split

| Expectation (release policy) | Actual state |
|------------------------------|--------------|
| `cohorts/evaluatee/` without answer keys | ❌ Directory absent |
| Evaluator bundle separate | ❌ `items.jsonl` includes full `answer_key` inline (committed) |
| `difficulty.core.equivalent` in items | ⚠️ Present — documented confound in paper; evaluatee bundle should strip or document |

**Blocking for public benchmark deposit** unless release explicitly ships an **evaluator-only research tarball** (current TMLR freeze model) rather than a contamination-safe public evaluatee bundle.

---

## 6. Verifier and scoring audit

### Code present

| Component | Path |
|-----------|------|
| Verifier | `src/fsmreasonbench/verifier/` |
| Scoring / evaluator | `src/fsmreasonbench/evaluator/` |
| Parsers | family parsers under verifier + runners |
| Failure taxonomy | `failure_taxonomy` exports, ablation `certificate_failure_taxonomy.json` in runs |

### Tests executed (31 passed)

- `tests/unit/test_equivalence_witness_verifier_audit.py`
- `tests/unit/test_certificate_class_complexity_analysis.py`
- `tests/unit/test_equivalence_hash_mismatch_decomposition.py`
- `tests/unit/test_tmlr_empirical_package.py`
- `tests/unit/test_f1_claude_ablation_stratified_analysis.py`
- `tests/unit/test_c2_existential_universal_ablation.py`

---

## 7. Documentation audit

### Strengths

- Clear layered-metrics framing in README, `PROJECT_STATUS.md`, `docs/paper_results.md`
- Valid vs invalid runs documented with reasons
- Safe vs unsafe claims section in `docs/paper_results.md`
- Overclaim guardrails in decomposition exports (`too_strong_thesis_sentence`)

### Issues

| Issue | Location | Severity |
|-------|----------|----------|
| README claims Zenodo `v1.0.0` as citable object while status table says not published | `README.md` vs `PROJECT_STATUS.md` | **Major** — reconcile wording |
| `docs/tmlr_empirical_package_v1/narrative_memo.md` abstract says **"frontier LLMs"** | line 31 | **Minor** — scope to tested model/config for public release docs |
| `docs/paper_results.md` implies tools "close the gap" on F1 R2 without mechanism stratification | § Claude interpretation | **Minor** — TMLR package is tighter (R2C mechanism control) |
| Ablation frozen runs missing from canonical frozen-run table | `docs/paper_results.md` | **Major** |
| Zenodo checklist contradicts target release | `docs/zenodo/RELEASE_CHECKLIST.md` §1 "no frozen public cohort" | **Info** — update at freeze time |

### Overclaim scan (requested phrases)

| Phrase | Found as **prohibited claim**? |
|--------|--------------------------------|
| "LLMs cannot reason" | ❌ Only listed as **too strong** / negated in decomposition docs |
| "tools solve reasoning" | ❌ Not stated; unsafe-claim sections warn against generic tool claims |
| "frontier models as a class" | ❌ Not asserted; single-model scope documented |
| "general existential/universal asymmetry" | ❌ Explicitly **rejected** in narrative memo and complexity analysis |

---

## 8. Zenodo metadata audit

### Current `CITATION.cff` (needs update before upload)

| Field | Current value | Required for v1.0.0 |
|-------|---------------|---------------------|
| `title` | FSMReasonBench: Evaluating Reasoning… | ✅ OK (or match release title below) |
| `version` | `1.0.0` | ✅ |
| `date-released` | `null` | ❌ Set on upload |
| `license` | `TBD` | ❌ Choose SPDX (recommend Apache-2.0 per archival policy) |
| `authors` | César Andrés + ORCID | ✅ |
| `affiliation` | Universidad Camilo José Cela | ✅ |
| `repository-code` | `https://github.com/TBD/fsmreasonbench` | ❌ → `https://github.com/cesar-andress/fsmreasonbench` |
| `url` / `doi` | Zenodo TBD placeholders | ❌ Fill after mint |
| `keywords` | absent | ❌ Add (see below) |
| `preferred-citation.type` | `dataset` | ✅ Appropriate for frozen evaluation artifact |

### Suggested Zenodo upload metadata

**Title:** FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0

**Description (short):** Frozen evaluation artifact for machine-verifiable finite-state machine reasoning. Includes audited verifier/scoring code, cohort snapshots (`v0.1-expanded-n100`), offline reproduction of TMLR empirical tables (certificate-class analysis, attribution ablations, hash-mismatch decomposition, hostile verifier audit), and documented valid vs excluded model runs. Layered metrics separate verdict accuracy from certificate validity. Not a leaderboard benchmark; single-model frontier evidence with mechanism controls.

**Keywords:** finite-state machines; formal verification; benchmark; reproducibility; large language models; certificate synthesis; evaluation methodology

**License:** Resolve `LICENSE` + Zenodo field together (code + data dual license if splitting evaluatee bundle later).

**Related identifiers:** Paper DOI (when available); GitHub tag `v1.0.0` after release.

---

## 9. Git audit

| Check | Result |
|-------|--------|
| Current branch | `main` (tracks `origin/main`); local `master` also exists |
| Tag `v1.0.0` | **Does not exist** |
| Uncommitted changes | **65** paths (`git status --porcelain`) |
| Modified tracked files | `src/fsmreasonbench/runners/response_extract.py`, `tracks/replay.py`, `tests/unit/test_response_extract.py` |
| Untracked release-critical code | Entire TMLR export stack (`evaluator/tmlr_empirical_package.py`, export CLIs, ablation docs, `docs/tmlr_empirical_package_v1/`, balanced C2 cohort, analysis JSON/MD) |
| `runs/` tracking | Intentionally **gitignored** (`.gitignore:25`) |
| Paper artifacts | In **parent** repo `../paper/`, not `fsmreasonbench` git |
| Large files in git | Cohort JSONL + docs; no multi-GB blobs tracked |
| Remote | `git@github.com-ucjc:cesar-andress/fsmreasonbench.git` |

**Do not tag `v1.0.0` until blockers resolved and release tree committed.**

---

## 10. Blocking issues (must fix before Zenodo)

1. **Replace `LICENSE` placeholder** with chosen SPDX license.
2. **Complete `CITATION.cff`** (repo URL, license, date, DOI after mint).
3. **Align `pyproject.toml`** to `version = "1.0.0"` and matching license.
4. **Create `releases/1.0.0/release_manifest.json`** with four version pins and file inventory including frozen runs.
5. **Commit release-critical untracked code** (TMLR exporters, docs, balanced cohort) or release will not reproduce from git tag alone.
6. **Define frozen-run shipping policy:** include five run roots in Zenodo tarball with checksums; keep excluded runs out.
7. **Resolve cohort naming** (`v0.1-expanded-n100` vs `1.0-public`) in release notes and manifest.
8. **Document answer-key exposure** or split evaluatee/evaluator bundles per release policy.
9. **Generate `SHA256SUMS`** and `environment/requirements-lock.txt`**.
10. **Extend `docs/paper_results.md`** frozen-run table to include all five valid run roots used in TMLR conclusions.

---

## Recommended fixes (non-blocking but important)

- Regenerate analysis JSON/MD with **repo-relative paths** (remove `/home/cesar/...`).
- Implement or remove `scripts/reproduce_table.sh`; align `README-RELEASE.md` with actual cohort paths.
- Add `releases/1.0.0/RELEASE_NOTES.md` emphasizing layered metrics, verifier audit, no leaderboard overclaim.
- Tighten `narrative_memo.md` abstract: "Claude Sonnet 4 under audited contract" instead of "frontier LLMs".
- Register key export CLIs in `pyproject.toml` `[project.scripts]` or document `python -m` matrix in README.
- Run full `pytest tests/unit` on clean CI before tag.
- Commit or drop in-progress changes to `response_extract.py` / `replay.py` before release cut.

---

## Reproducibility checklist (release gate)

- [ ] `pip install -e ".[dev]"` succeeds on Python 3.11
- [ ] `artifact_health` PASS
- [ ] `validate_cohort` PASS on all shipped cohort dirs
- [ ] Full unit test suite PASS
- [ ] All five frozen run roots present in tarball with checksums
- [ ] Offline export CLIs regenerate TMLR package bit-identically (or documented acceptable drift)
- [ ] Excluded runs absent from tarball **or** clearly labeled audit-only
- [ ] No absolute home paths in shipped JSON manifests
- [ ] `sha256sum -c SHA256SUMS` PASS on tarball

---

## Zenodo metadata checklist

- [ ] Title: FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0
- [ ] Description emphasizes machine-verifiable certificates, layered metrics, frozen artifacts, verifier audit
- [ ] Creators + ORCID + affiliation
- [ ] Keywords (≥3)
- [ ] License field matches `LICENSE` file
- [ ] Version = v1.0.0
- [ ] `CITATION.cff` DOI backfilled post-mint
- [ ] Related paper identifier (optional)
- [ ] Upload type: Software + Dataset (or combined) per split strategy

---

## GitHub release checklist

- [ ] All release blockers committed on `main`
- [ ] `releases/1.0.0/RELEASE_NOTES.md` published
- [ ] Create annotated tag `v1.0.0` (when explicitly approved)
- [ ] GitHub Release attaches tarball or points to Zenodo DOI as canonical
- [ ] README cites Zenodo DOI, not git URL, as primary citation
- [ ] Confirm `.gitignore` still excludes dev `runs/` on GitHub while Zenodo carries frozen subset

---

## Security / secrets checklist

- [x] Scan for API keys in source, docs, runs — none found
- [x] No secrets printed in this audit
- [ ] Re-scan tarball before upload (include `runs/` transcripts)
- [ ] Confirm provider error logs in excluded runs contain no user tokens
- [ ] Remove or redact absolute home paths from shipped manifests

---

## Appendix: suggested release title and one-line scope

**FSMReasonBench: Evaluating Reasoning over Executable Finite-State Machines v1.0.0**

*Frozen, auditable evaluation artifact for certificate-based FSM reasoning research—code, cohorts, valid model-run snapshots, and offline table reproduction without new API calls.*

---

*End of audit. No model inference was run. No frozen runs were modified. No GitHub/Zenodo release was created.*

# AI-assisted implementation provenance (clean_v2)

**Namespace:** `clean_v2`  
**Session:** Cursor-assisted implementation (2026-09-02)  
**Policy:** Preserve existing git history and historical `Co-authored-by: Cursor` markers. Do not rewrite history.

## Modules introduced/modified with AI assistance in this implementation

| Path | Scientific role | Deterministic tests |
|---|---|---|
| `src/fsmreasonbench/clean_v2/views.py` | Evaluatee/Evaluator boundary (leakage control) | `test_leakage.py` |
| `src/fsmreasonbench/clean_v2/condition.py` | Factorized ConditionSpec | fingerprint / sentinel |
| `src/fsmreasonbench/clean_v2/provenance.py` | Witness origin schema + export guard | `test_fingerprint_metrics.py` |
| `src/fsmreasonbench/clean_v2/metrics.py` | Common-denominator aggregation | `test_fingerprint_metrics.py` |
| `src/fsmreasonbench/clean_v2/fingerprint.py` | Config hash + `diff_experiment` | `test_fingerprint_metrics.py` |
| `src/fsmreasonbench/clean_v2/prompts.py` | Factorized prompt blocks | fingerprint diffs |
| `src/fsmreasonbench/clean_v2/tools/*` | Causal tools + coarse T3 | `test_tools_t3.py` |
| `src/fsmreasonbench/clean_v2/contracts/*` | Bisimulation / minimized_dfa / digest_control verifiers | `test_contracts.py` |
| `src/fsmreasonbench/clean_v2/scoring.py` | Parse/score/first-failure | `test_fingerprint_metrics.py` |
| `src/fsmreasonbench/clean_v2/runner.py` | No-inject scientific runner | `test_repetitions.py`, sentinel |
| `src/fsmreasonbench/clean_v2/sentinel/*` | Mock E2E campaign | `test_sentinel.py` |
| `src/fsmreasonbench/cli/run_clean_v2_sentinel.py` | Sentinel CLI | sentinel test |
| `docs/clean_v2/HARNESS_READINESS_REPORT.md` | Readiness audit | — |

## Human review status

Known: author requested and accepted this harness design/implementation in-session.  
**Not claimed:** independent external line-by-line audit of every file.

## Historical AI commits

Pre-existing repository history contains ≥87 commits with `Co-authored-by: Cursor` on scientific paths (verifier/scoring/exports). Those markers remain intact and must be disclosed in the manuscript Methods/Artifact statement for any submission using this codebase.

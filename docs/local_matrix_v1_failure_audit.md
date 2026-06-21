# Local Matrix v1 Failure Audit

**Date:** 2026-06-20  
**Run directory:** `runs/local_matrix_v1`  
**Matrix:** 4 models × 2 families × 3 tracks × 3 temperatures = **72 cells**  
**Outcome:** **58 completed**, **14 failed** (report generated before runner hardening)

---

## Executive summary

| Failure class | Count | Root cause |
|---------------|------:|------------|
| Model timeout | 11 | `llama3.1:8b` R1/R2 tool loops exceed cell timeout (600 s); `mistral-nemo:12b` C2 R1 at T=0, T=0.2 |
| Tool routing / runner bug | 3 | C2 R2 allowed F1 `solver.distinguishing_certificate`; uncaught `RuntimeError` aborted entire cell |
| Legitimate F1 tool misuse (surfaced as runner bug) | 1 | F1 R2 `llama3.1:8b` T=0.7: model invoked distinguishing cert on equivalent pair without `check_separation` |

The error **"internal error: cannot build distinguishing trace for equivalent DFAs"** is **not** a C2 semantic failure. It is an **F1 certificate builder** (`certificates/separation.py`) invoked when:

1. **C2 R2 (2 cells):** LLM requested `solver.distinguishing_certificate` (often with the single C2 FSM id duplicated). Comparing a DFA to itself yields equivalence → builder raises → **uncaught `RuntimeError` killed the batch** (runner bug + missing family tool guard).
2. **F1 R2 (1 cell):** LLM skipped `check_separation` and called `solver.distinguishing_certificate` on an **equivalent** mixed-cohort item (~50% of F1 cohort). Same uncaught exception (runner bug; reference R2 agent already routes via `check_separation` → `equivalence_certificate`).

**Report attribution:** Failed cells were listed under correct family/track rows in `report.md`, but delegation gap tables showed misleading `+nan` for `llama3.1:8b` without explaining missing R1/R2 cells.

---

## Per failed cell

| Model | Family | Track | Temp | Failure type | Exact error | Classification |
|-------|--------|-------|-----:|--------------|-------------|----------------|
| `llama3.1:8b` | C2 | R1 | 0.0 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | C2 | R2 | 0.0 | internal_runner_error | `internal error: cannot build distinguishing trace for equivalent DFAs` | **tool routing bug** (F1 tool on C2) + runner bug (cell abort) |
| `llama3.1:8b` | F1 | R1 | 0.0 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | F1 | R2 | 0.0 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | C2 | R1 | 0.2 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | C2 | R2 | 0.2 | internal_runner_error | `internal error: cannot build distinguishing trace for equivalent DFAs` | **tool routing bug** + runner bug |
| `llama3.1:8b` | F1 | R1 | 0.2 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | F1 | R2 | 0.2 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | C2 | R1 | 0.7 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | C2 | R2 | 0.7 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | F1 | R1 | 0.7 | timeout | `timed out` | model timeout |
| `llama3.1:8b` | F1 | R2 | 0.7 | internal_runner_error | `internal error: cannot build distinguishing trace for equivalent DFAs` | model protocol failure on equivalent item + runner bug |
| `mistral-nemo:12b` | C2 | R1 | 0.0 | timeout | `timed out` | model timeout |
| `mistral-nemo:12b` | C2 | R1 | 0.2 | timeout | `timed out` | model timeout |

---

## Investigation notes

### Why distinguishing-trace error appears on C2 rows

- C2 items expose **one** FSM (`item.fsm`; no `fsm_b`).
- R2 tool executor (pre-fix) exposed **all** registered solvers to every family.
- Local models on C2 R2 sometimes emit F1-style tool plans (`solver.distinguishing_certificate` with duplicated `fsm_id`).
- Self-comparison is equivalent → `build_distinguishing_trace_certificate` raises `RuntimeError`.
- Exception was **not** converted to per-item/tool rejection → **entire cell failed** with error attributed to C2/R2 (correct cell id, misleading error semantics).

**Not** a report family mis-tag; **is** a tool-registry and error-handling defect.

### F1 R2 equivalent pairs

- Reference agent (`tracks/agents.py::_r2_solve_f1`) correctly calls `check_separation` then `equivalence_certificate` or `distinguishing_certificate`.
- LLM track path had no equivalent guard on direct `distinguishing_certificate` tool calls.
- Legitimate on equivalent items: **`equivalence_witness`** via `solver.equivalence_certificate`.
- `f1-mixed-level3` cohort includes ~50% `verdict=true` equivalent items.

### Mistral F1 R2 extractability (completed cells, not failed)

Failed cells are only mistral **C2 R1** timeouts. Completed mistral F1 R2 cells show severe **model protocol / extractability** issues (e.g. `extractability_rate` 0.05–0.10 at T=0–0.2) — separate from the 14 cell failures; document for scale-up caution, not runner bugs.

### R2 verdict vs certificate (qwen C2)

Completed qwen C2 R2: high `verdict_accuracy` (~0.95), low `certificate_valid_rate` (~0.10). R2 solver tools return oracle certificates, but **LLM final submission** often fails verifier — expected delegation gap pattern, not a scoring bug.

### Qwen F1 R2 positive signal (completed)

Qwen F1 R2: `fully_correct_rate` 0.40–0.45 across temperatures with `verdict_accuracy` 1.0 — clearest local delegation win in this matrix.

---

## Hardening applied (post-audit)

See commit **Harden local matrix runner failure handling and F1 R2 equivalent cases**:

1. Family-scoped R2 tool allowlists (`C2`: reachability only; `F1`: separation only).
2. `solver.distinguishing_certificate` checks equivalence first (`ValueError` with guidance).
3. Tool executor catches `RuntimeError`; per-item batch failures no longer abort cell.
4. `error.json` per failed cell with `error_type`.
5. `--retry-failed` / `--skip-failed` CLI; delegation tables mark incomplete rows with `—`.

---

## Recovery

Re-run **only** the 14 failed cells after upgrading the artifact:

```bash
cd ~/papers/fsmreasonbench/fsmreasonbench
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0,0.2,0.7 \
  --max-items 20 \
  --timeout 600 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed
```

Successful cells are skipped; failed directories with `error.json` are cleared and retried. Consider `--timeout 900` for `llama3.1:8b` R1/R2 if timeouts persist.

**Trust after rerun:** The pre-fix matrix is **not** trustworthy for R2 delegation claims on failed cells. After `--retry-failed` with hardened runner, completed cells should be re-validated (`error.json` absent, `summary.json` present) before any n=100 scale-up.

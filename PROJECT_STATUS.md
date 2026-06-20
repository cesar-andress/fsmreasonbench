# FSMReasonBench — Project Status

**Repository:** artifact (`fsmreasonbench`)  
**Last updated:** 2026-06-20  
**Package version:** `0.2.0-dev`  
**Branch:** `main`  
**Release notes:** [`docs/releases/v0.1-exploratory.md`](docs/releases/v0.1-exploratory.md)

> **Not a Zenodo release.** `v0.1-exploratory` documents the current development milestone (C2 + F1,
> evaluation pipeline, two exploratory frozen cohorts). It is **not** public cohort `1.0-public`
> and **not** a final benchmark release.

---

## Implementation status

**Principle:** Build the verifier before the generator. Prove one task end-to-end before widening.

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 1** — Core infrastructure | ✅ **Complete** | FSM, oracle, verifier, tests |
| **Phase 2** — First vertical (C2 reachability) | ✅ **Complete** | Difficulty controls + negative items |
| **Phase 3** — Evaluation infrastructure | ✅ **Complete** | C2 parser, scoring, transcripts, baselines |
| **Phase 4** — Flagship verticals | 🔄 **In progress** | F1 DFA non-equivalence vertical |

Roadmap detail: [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)

---

## Empirical evaluation framing

FSMReasonBench separates four **independent** measurement layers on every scored item:

| Layer | Metric | Meaning |
|-------|--------|---------|
| 1 | **Extractability** | Parseable, schema-valid submission extracted from model output |
| 2 | **Verdict accuracy** | Declared boolean verdict matches gold (when extractable) |
| 3 | **Certificate validity** | Independent verifier accepts submitted certificate |
| 4 | **Full correctness** | Verdict and certificate both correct |

Reported rates: `extractability_rate`, `verdict_accuracy`, `certificate_valid_rate`, `fully_correct_rate`, plus `failure_stage` (`not_extractable`, `verdict_wrong`, `certificate_invalid`, `correct`).

**Empirical risk under test:** verdict accuracy can **overstate verified reasoning success** — models may emit extractable JSON and plausible high-level verdicts while failing to produce executable certificates. Flagship scoring treats certificate validity as primary; verdict-only success is diagnostic, not sufficient.

**Implemented families (artifact v0.2):**

| Tier | Family | Role |
|------|--------|------|
| Calibration | **C2** Reachability | Operational literacy; sanity / drift detection |
| Flagship | **F1** Separation / Witness (DFA non-equivalence) | First flagship vertical; `distinguishing_trace` certificate |

**Evaluation tracks (current artifact):**

| Track | Purpose |
|-------|---------|
| **Oracle baseline** | Symbolic ceiling (extractable + fully correct) |
| **Random baseline** | Seeded wrong submissions; tests scoring separation |
| **Invalid baseline** | Non-extractable output probe |
| **Local Ollama (no tools)** | Exploratory model evaluation; temperature=0; not frozen |

Exploratory runs (pilots, capability-surface sweeps) may use on-demand JSONL under `runs/` (gitignored) or **sealed exploratory cohorts** under `cohorts/v0.1-exploratory/`. Committed summaries in `docs/pilot_v0_*` and `docs/pilot_v1_*` are illustrative only — not paper claims or final benchmark results.

**Exploratory frozen cohorts (valid, non-public):** two snapshots pass `validate_cohort` and are intended for reproducibility smoke testing and artifact validation — **not** final public `v1.0-public` cohorts and not citable as benchmark results.

| `cohort_id` | Path | Fingerprint |
|-------------|------|-------------|
| `c2-reachability-level3-v0.1-exploratory` | [`cohorts/v0.1-exploratory/c2-reachability-level3/`](cohorts/v0.1-exploratory/c2-reachability-level3/) | `77d3bfa104266396d016415527c2cc74eea545bec2bf1295bf0d2ee1c1086230` |
| `f1-mixed-level3-v0.1-exploratory` | [`cohorts/v0.1-exploratory/f1-mixed-level3/`](cohorts/v0.1-exploratory/f1-mixed-level3/) | `4e1e662307456c871ed8c424a4ba493ab041b3d32530feecdef7c19ffe634a67` |

Full milestone summary (CLIs, evaluation pipeline, capability-surface reproduction, limitations):
[`docs/releases/v0.1-exploratory.md`](docs/releases/v0.1-exploratory.md).

**Dataset card:** [`docs/dataset_card.md`](docs/dataset_card.md) — draft overview for downstream publication (e.g. Hugging Face); references normative docs and distinguishes exploratory from future frozen public cohorts.

---

## Milestone achieved: first self-verifying item

```
generator → oracle → certificate → verifier  ✅
```

- **Family:** C2 (basic reachability, calibration)
- **Difficulty dimension:** `|Q|` (state count) only
- **Example:** `examples/item_C2_reachability_seed42.json`
- **CLI:** `python3 -m fsmreasonbench.cli.generate_one --seed 42`
- **Difficulty controls:** `min_witness_length=1`, `max_witness_length=12`, `allow_initial_target=false`
- **Negative items:** unreachable targets with `unreachability_witness`
- **Tests:** 91+ passing (`pytest`)

---

## Phase 4 deliverables (F1 separation / witness)

| Component | Path |
|-----------|------|
| Separation oracle (shortest distinguishing trace) | `oracle/separation.py` |
| Certificate builder | `certificates/separation.py` |
| Independent verifier | `verifier/separation.py` |
| Seeded F1 generator (non-equivalent DFA pairs) | `generator/separation.py`, `generator/separation_constructive.py` |
| F1 item assembly + self-verify | `items/assembly.py` |
| F1 parser / scorer | `evaluator/parser.py`, `scorer_f1.py` |
| F1 baselines | `baselines/f1.py`, `baselines/runner.py` |
| Schema | `schema/certificate/separation.schema.json` |
| Example item | `examples/item_F1_separation_seed42.json` |
| Hard example (`ℓ_dist≥3`) | `examples/item_F1_separation_seed6_hard.json` |
| F1 batch + smoke | `cli/generate_batch --family F1`, `run_f1_smoke_baselines.py` |

**Generator defaults:** `min_distinguishing_trace_length=2`, `max_distinguishing_trace_length=12`, `max_retries=64`. Auto mode uses **constructive_decoy** generation when `min_distinguishing_trace_length ≥ 3` (decoy branches with exact witness length); legacy **constructive** chain+sink mode remains for regression tests; lower levels use random rejection sampling unless a constructive mode is set explicitly. Smoke item seed 42 uses `--min-distinguishing-trace-length 1`.

**CLI:** `python3 -m fsmreasonbench.cli.generate_one --family F1 --seed 42`

---

## Phase 3 deliverables (C2 evaluation)

| Component | Path |
|-----------|------|
| C2 submission schema | `schema/c2_submission.schema.json` |
| Answer parser + extractability gate | `src/fsmreasonbench/evaluator/parser.py` |
| Scoring | `src/fsmreasonbench/evaluator/scorer.py` |
| Transcript + rescore | `src/fsmreasonbench/evaluator/transcript.py` |
| CLI score / rescore | `cli/score_submission.py`, `cli/rescore_transcript.py` |
| Example submissions + transcript | `examples/submission_C2_*.json`, `transcript_C2_correct.json` |
| C2 baselines | `src/fsmreasonbench/baselines/` |
| CLI run baseline | `cli/run_baseline.py` |
| C2 batch generation + evaluation | `evaluator/batch.py`, `evaluator/summary.py` |
| CLI batch tools | `cli/generate_batch.py`, `evaluate_baseline_batch.py`, `summarize_scores.py` |
| C2 smoke baseline runner | `cli/run_c2_smoke_baselines.py` |
| Exploratory capability surface | `evaluator/capability_surface.py`, `cli/run_capability_surface.py` |
| Ollama batch runner | `runners/`, `cli/run_ollama_batch.py` |
| Multi-model pilot runner | `runners/pilot_models.py`, `cli/run_pilot_models.py` |
| Model capability-surface runner | `evaluator/capability_surface_models.py`, `cli/run_capability_surface_models.py` |
| Capability-surface plotting | `evaluator/capability_surface_plots.py`, `cli/plot_capability_surface.py` |
| Capability-surface report export | `evaluator/capability_surface_report_export.py`, `cli/export_capability_surface_report.py` |
| Documentation consistency checker | `dev/doc_consistency.py`, `cli/check_docs.py` |
| Artifact health check | `dev/artifact_health.py`, `cli/artifact_health.py` — package import, required schemas, example self-verify, CLI imports; `--json` |
| F1 item audit diagnostics | `evaluator/f1_item_audit.py`, `cli/audit_f1_items.py` |
| Failure inspection CLI | `evaluator/inspect_failures.py`, `cli/inspect_failures.py` — rates + per-stage failure samples |
| Failure taxonomy analysis | `evaluator/failure_taxonomy.py`, `cli/failure_taxonomy.py`, `cli/failure_taxonomy_batch.py` — classify `certificate_invalid` errors into interpretable categories |
| Exploratory cohort freeze | `cohort/freeze.py`, `cohort/validate.py`, `cli/freeze_cohort.py`, `cli/validate_cohort.py` — seal JSONL snapshots with manifest + checksums (no DOI) |
| Dataset card | [`docs/dataset_card.md`](docs/dataset_card.md) — HuggingFace-adaptable overview; references normative docs |
| Publication readiness report | `reporting/publication_readiness.py`, `cli/publication_readiness.py` — read-only Markdown snapshot for paper/release prep |
| Pilot report generator | `evaluator/pilot_report.py`, `cli/generate_pilot_report.py` |

**End-to-end path:** item → response → parser → extractability → verifier → scoring → transcript → rescore

**Reference baselines:** `oracle` (symbolic ceiling), `random` (seeded, usually wrong), `invalid` (extractability probe)

**Exploratory batch (on-demand):** generate JSONL cohort → evaluate baseline → aggregate summary

**Exploratory cohort freeze (sealed):** `freeze_cohort` / `validate_cohort` — manifest `0.1-exploratory`; see [`cohorts/v0.1-exploratory/`](cohorts/v0.1-exploratory/)

---

## Pilot evaluation summaries (committed)

Exploratory local-model runs; **not frozen cohorts**. Raw transcripts and JSONL live under `runs/` (gitignored).

| Pilot | Committed artifacts | Run data |
|-------|---------------------|----------|
| v0 (single model) | [`docs/pilot_v0_report.md`](docs/pilot_v0_report.md), [`docs/pilot_v0_summary.json`](docs/pilot_v0_summary.json) | `runs/pilot_v0/` |
| v1 (multi-model) | [`docs/pilot_v1_report.md`](docs/pilot_v1_report.md), [`docs/pilot_v1_summary.json`](docs/pilot_v1_summary.json), [`docs/pilot_v1_summary.csv`](docs/pilot_v1_summary.csv) | `runs/pilot_v1/` |

### Pilot v1 exploratory observations (non-frozen, n=20 per family)

Items: C2 `min_witness_length=2`, F1 `min_distinguishing_trace_length=2` from `capability_surface_smoke2`. See [`docs/pilot_v1_report.md`](docs/pilot_v1_report.md) for full tables.

**Pattern (not a general claim):** all four pilot models achieved extractability_rate = 1.0; F1 verdict_accuracy = 1.0 for every model, while certificate_valid_rate and fully_correct_rate remained low — consistent with the verdict-overstatement risk above.

---

## Phase 1 deliverables

| Component | Path |
|-----------|------|
| FSM model (DFA, NFA) | `src/fsmreasonbench/models/` |
| Canonical serialization + SHA-256 | `models/serialization.py` |
| Shared runtime semantics | `src/fsmreasonbench/runtime/` |
| Oracle (simulation, reachability, shortest path) | `src/fsmreasonbench/oracle/` |
| Certificate builders (oracle-side) | `src/fsmreasonbench/certificates/` |
| Independent verifier | `src/fsmreasonbench/verifier/` |
| JSON schemas | `schema/fsm.schema.json`, `schema/certificate/reachability.schema.json` |
| Unit + e2e tests | `tests/unit/` |

**Architectural rule enforced:** verifier does not import oracle or generator (see `test_verifier_independence.py`).

---

## Phase 2 deliverables

| Component | Path |
|-----------|------|
| Seeded reachability generator | `src/fsmreasonbench/generator/reachability.py` |
| | Controls: `min_witness_length`, `max_witness_length`, `allow_initial_target`, negative items |
| Item assembly + self-verify | `src/fsmreasonbench/items/assembly.py` |
| CLI | `src/fsmreasonbench/cli/generate_one.py` |

---

## Zenodo-first architecture (unchanged)

Development code on `main` is **not citable**. First Zenodo target remains **v1.0.0** after a **public** cohort freeze (`1.0-public`). Exploratory snapshots under `cohorts/v0.1-exploratory/` are sealed for smoke testing but are not that release.

Current `verifier_version` (dev): `0.2.0-dev` — will pin at release.

---

## Next implementation milestone (Phase 4 remainder)

1. **F1 equivalent-pair proof certificates** (positive items)
2. **F1 NFA / containment subtypes**

**Not next:** public `1.0-public` cohort, contamination tooling, F2 composition.

---

## Unresolved (unchanged from design phase)

| ID | Question |
|----|----------|
| U1 | F1 minimality policy |
| U9 | License (MIT vs Apache-2.0) |
| U10 | Container digest vs lockfile-only |

---

## Commands

```bash
pip install -e ".[dev]"
pytest -v
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family F1 --seed 42
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_F1_separation_seed42.json --score
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.score_submission \
  --item examples/item_C2_reachability_seed42.json \
  --submission examples/submission_C2_correct.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.rescore_transcript \
  --transcript examples/transcript_C2_correct.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_baseline \
  --baseline oracle --item examples/item_C2_reachability_seed42.json --score
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_batch \
  --n 100 --seed 1 --out runs/c2_items.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.evaluate_baseline_batch \
  --baseline oracle --items runs/c2_items.jsonl --out runs/oracle_scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.summarize_scores \
  --scores runs/oracle_scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_c2_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/c2_smoke
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_f1_smoke_baselines \
  --n 100 --seed 1 --out-dir runs/f1_smoke
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_capability_surface \
  --families C2,F1 --n-per-level 50 --seed 1 --out-dir runs/capability_surface
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_ollama_batch \
  --model qwen2.5-coder:7b \
  --items runs/c2_items.jsonl \
  --out runs/ollama_c2_qwen7b.jsonl \
  --temperature 0
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.summarize_scores \
  --scores runs/ollama_c2_qwen7b/scores.jsonl
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.inspect_failures \
  --scores runs/ollama_c2_qwen7b/scores.jsonl \
  --results runs/ollama_c2_qwen7b.jsonl \
  --limit 5
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.failure_taxonomy \
  --scores runs/capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_3/qwen2.5-coder:7b/scores.jsonl \
  --results runs/capability_surface_models_f1_mixed/F1/min_distinguishing_trace_length_3/qwen2.5-coder:7b/results.jsonl \
  --out runs/taxonomy_example.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.failure_taxonomy_batch \
  --root runs/capability_surface_models_f1_mixed \
  --out docs/f1_mixed_failure_taxonomy.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-exploratory/c2-reachability-level3
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.validate_cohort \
  --cohort-dir cohorts/v0.1-exploratory/f1-mixed-level3
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --c2-items runs/capability_surface_smoke2/C2/min_witness_length_2/items.jsonl \
  --f1-items runs/capability_surface_smoke2/F1/min_distinguishing_trace_length_2/items.jsonl \
  --max-items 20 \
  --out-dir runs/pilot_v1
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.run_capability_surface_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --levels 1,2,3,4,5 \
  --n-per-level 20 \
  --out-dir runs/capability_surface_models
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.plot_capability_surface \
  --summary runs/capability_surface_models/combined_summary.json
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.export_capability_surface_report \
  --summary runs/capability_surface_models/combined_summary.json \
  --out-md docs/capability_surface_report.md \
  --out-tex ../paper/tables/capability_surface_summary.tex \
  --out-csv docs/capability_surface_summary.csv
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.check_docs
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.publication_readiness \
  --out docs/publication_readiness.md
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.audit_f1_items \
  --items runs/capability_surface_models/F1/min_distinguishing_trace_length_5/items.jsonl \
  --out runs/f1_audit_level5.json
```

# Evaluation Protocol — FSMReasonBench v2

**Status:** draft (pre-release; not citable until Zenodo DOI)  
**Version:** 2.0.0-draft  
**Normative parent:** [`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md)  
**Archival:** Submissions MUST declare four version pins per [`../artifact/release_policy.md`](../artifact/release_policy.md).

---

## 1. Evaluation philosophy

FSMReasonBench v2 reports **capability surfaces**, not a single leaderboard rank.

Two correctness dimensions apply to every submission:

| Dimension | Question |
|-----------|----------|
| **Answer extractability** | Is the response parseable, complete, and family-typed? |
| **Certificate / artefact correctness** | Does the independent verifier accept the witness, query, or constructed FSM? |

For **flagship families F1–F4**, artefact correctness is **primary**.  
For **calibration C1–C2**, verdict correctness suffices for panel reporting.

---

## 2. Bundles

### 2.1 Evaluatee bundle

Per item: `item_id`, `family`, `family_tier`, `track_stratum`, `difficulty`, `fsm`,
`presentation`, `question`, `contamination.public_fingerprint`.

**Excluded:** `answer_key`, `hidden_probes`, seeds.

### 2.2 Evaluator bundle (separate Zenodo deposit or supplement)

- Reference certificates / artefacts
- F4 hidden probe sets
- Oracle metadata
- Embargoed seeds (separate archive)

MUST NOT be included in primary evaluatee download.

### 2.3 Paper reproduction supplement (optional DOI)

- Archived LLM/agent submissions used in paper
- `table_provenance.json`

See [`../artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md) §5.

### 2.4 Submission bundle

```json
{
  "submission_id": "uuid",
  "benchmark_version": "1.0.0",
  "cohort_version": "1.0-public",
  "schema_version": "1.0.0",
  "verifier_version": "1.0.0",
  "track": "R0 | R1 | R2",
  "system_description": {
    "name": "string",
    "version": "string",
    "tools_used": []
  },
  "responses": [
    {
      "item_id": "uuid",
      "extracted_fields": { },
      "certificate": { },
      "verdict": null,
      "explanation": "optional",
      "latency_ms": 0
    }
  ]
}
```

---

## 3. Evaluation tracks

| Track | Name | Permitted | Forbidden (normative) |
|-------|------|-----------|------------------------|
| **R0** | Pure reasoning | In-context reasoning | Code, REPL, external APIs |
| **R1** | Tool-augmented | `step(state, symbol)` | BFS/DFS libraries, model checkers, SMT, automata-lib |
| **R2** | Solver delegation | Arbitrary code and solvers | Misreporting track; F2 product in submission |

**Track MUST be declared.** Misreporting invalidates comparative leaderboard entry.

---

## 4. Per-family response requirements

| Family | Tier | Primary object | Verdict role |
|--------|------|----------------|--------------|
| F1 | flagship | `separation_witness` | diagnostic only |
| F2 | flagship | projected / compositional / bounded argument | diagnostic |
| F3 | flagship | `synthesized_fsm` | N/A (artefact is answer) |
| F4 | flagship | `formal_query` | N/A (probe score) |
| C1 | calibration | boolean + optional trace | **primary** |
| C2 | calibration | boolean + optional trace | **primary** |

---

## 5. Scoring pipeline

```
Submission
  → Schema validation (extractability)
  → Family-specific guards (F2 materialization)
  → Independent verifier
  → Per-item score record
  → Capability surface aggregation
```

### 5.1 Per-item record

```json
{
  "item_id": "uuid",
  "family": "F1",
  "extractable": true,
  "certificate_valid": true,
  "verdict_match": null,
  "probe_error_rate": null,
  "materialization_violation": false,
  "primary_score": 1.0,
  "diagnostic_score": 0.25
}
```

### 5.2 Primary score (flagship)

```
primary = 1.0  iff extractable ∧ certificate_valid ∧ ¬materialization_violation
primary = 0.0  otherwise
```

F4: `primary = 1.0 - probe_error_rate` (if extractable).

### 5.3 Primary score (calibration)

```
primary = 1.0  iff extractable ∧ verdict_match
```

---

## 6. Capability surfaces (required reporting)

### 6.1 Matrices

Report at minimum:

| Matrix | Rows | Columns |
|--------|------|---------|
| **M1** | F1, F2, F3, F4 | R0, R1, R2 |
| **M2** | F1–F4 | difficulty stratum S0–S3 |
| **M3** | F1.a, F1.b, F1.c | primary score |
| **M4** | C1, C2 | calibration panel (separate figure) |

### 6.2 Derived metrics (not for sole ranking)

| Metric | Definition |
|--------|------------|
| **Ext** | Extractability rate |
| **Cert** | Certificate validity among extractable (flagship) |
| **Full** | Primary score mean (flagship) |
| **Δ_R2_R0** | Full(R2) − Full(R0) per family — delegation gap |
| **Cal** | Calibration pass rate (C1, C2) |

### 6.3 Discouraged

- Single “FSMReasonBench accuracy” without family/track breakdown
- Headlining calibration metrics in abstract
- Ranking systems on R2 alone for reasoning claims

---

## 7. F2 materialization guard

Automatic check on submission payload:

- Reject if `product_states` or `product_transitions` present
- Reject if transition array size ≥ `|Q_A| × |Q_B| × |Σ|` threshold
- Flag `MATERIALIZATION_VIOLATION` in report

R2 solvers MAY materialize internally; output must remain compressed.

---

## 8. F4 hidden probe protocol

1. Evaluator loads `hidden_probes` for item
2. Evaluates reference query and submitted query on each probe
3. `probe_error_rate = mismatches / |probes|`
4. Probes never released in evaluatee bundle

Optional: semantic equivalence check between queries before probe evaluation.

---

## 9. Baselines (required in paper; scripts only in repo)

| Baseline | Track | Purpose |
|----------|-------|---------|
| Random witness | all | Extractability floor |
| Verdict-only (no certificate) | flagship | Shows certificate necessity |
| Step-simulator | R1 | Bounded execution ceiling |
| Symbolic oracle | R2 | Solver delegation ceiling |
| Human expert | R0/R1 | Small stratified sample |

No baseline results committed during design phase.

---

## 10. Contamination

1. Unique fingerprints per item in cohort
2. Seed embargo (duration: PROJECT_STATUS U4)
3. Optional holdout cohort
4. Post-release fingerprint list for corpus checks

---

## 11. Reproducibility tiers (Zenodo)

| Tier | Script | Requirement |
|------|--------|-------------|
| R1 Integrity | `scripts/validate_cohort_integrity.sh` | Mandatory in release |
| R2 Verification | `scripts/verify_submission.py` | Mandatory in release |
| R4 Tables | `scripts/reproduce_table.sh` | Mandatory if paper published |

See [`../artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md).

---

## 12. CLI

### 12.1 Implemented (C2 calibration slice)

Score a structured submission against a benchmark item:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.score_submission \
  --item examples/item_C2_reachability_seed42.json \
  --submission examples/submission_C2_correct.json
```

Deterministically recompute scoring from a saved transcript:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.rescore_transcript \
  --transcript examples/transcript_C2_correct.json
```

### 12.2 C2 submission schema

Structured submissions MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | string | Must match the evaluatee item |
| `verdict` | boolean | `true` = reachable, `false` = unreachable |
| `certificate` | object | `trace_witness` or `unreachability_witness` per [`certificate_formats.md`](certificate_formats.md) |

Schema: `schema/c2_submission.schema.json`.

Raw model text MAY be stored in transcripts; the parser extracts JSON objects or fenced code blocks.

### 12.3 C2 scoring record

| Field | Type | Meaning |
|-------|------|---------|
| `extractable` | bool | Parser produced a valid submission |
| `verdict_correct` | bool \| null | Null if not extractable |
| `certificate_valid` | bool \| null | Independent verifier result |
| `fully_correct` | bool | Verdict and certificate both correct |
| `failure_stage` | enum | `not_extractable`, `verdict_wrong`, `certificate_invalid`, `correct` |

### 12.4 Transcript envelope

Each evaluation transcript stores:

- `item` — full benchmark item (including answer key for offline rescore)
- `raw_response` — original model/system output string
- `parsed_submission` — present only when extractable
- `scoring_record` — result of scoring pipeline
- `scorer_version` — pinned evaluator version
- `timestamp` — ISO-8601 UTC

Rescore recomputes `scoring_record` from `item` + `raw_response` (or parsed submission if present); fields MUST match the original score when inputs are unchanged.

### 12.5 Planned (full benchmark)

```
evaluate_submission.py \
  --submission submission.json \
  --evaluator-bundle evaluator/ \
  --output capability_surface.json
```

Multi-family batch evaluation and capability surfaces are not yet implemented.

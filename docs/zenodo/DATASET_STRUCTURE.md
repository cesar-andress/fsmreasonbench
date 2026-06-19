# Dataset structure

**Status:** pre-release draft  
**Audience:** future Zenodo depositors and downstream evaluators

This document describes the JSON record layouts used in FSMReasonBench. Normative schema
files live in [`schema/`](../../schema/). At release time, schemas will be pinned in the
Zenodo tarball; this document is a human-readable map.

---

## Record types

| Record | Purpose | Typical location (future release) |
|--------|---------|-----------------------------------|
| **Item** | Benchmark question + FSM(s) + metadata | `cohorts/evaluatee/*.json` |
| **Answer key** | Gold verdict + oracle certificate | `evaluator/*.answer_keys.jsonl` (evaluator bundle) |
| **Certificate** | Verifiable witness embedded in submission or answer key | Inside answer / submission payload |
| **Transcript** | Full evaluation trace for one item response | Per-run `transcripts/*.json` |
| **Score record** | Per-item scoring outcome | `scores.jsonl` aggregates |

Evaluatee bundles MUST NOT include answer keys. Full items (with keys) appear only in
evaluator bundles and in development examples under [`examples/`](../../examples/).

---

## Item schema

An **item** is the unit presented to an evaluatee. Implemented families use
`BenchmarkItem.to_evaluatee_dict()`; the full assembly includes an `answer_key` field
when serialized for internal use (`to_full_dict()`).

### Common top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_id` | string (UUID) | yes | Stable item identifier |
| `family` | string | yes | `C2` or `F1` (implemented); `C1`, `F2`–`F4` specified |
| `family_tier` | string | yes | `calibration` or `flagship` |
| `question` | object | yes | Typed question payload (see below) |
| `difficulty` | object | yes | Generator difficulty vector + seed |
| `contamination` | object | yes | Public fingerprint for leakage detection |
| `fsm` | object | C2 | Primary FSM (`schema/fsm.schema.json`) |
| `fsm_a`, `fsm_b` | object | F1 | Pair of DFAs for non-equivalence |

### Question payload (`question`)

Conforms to [`schema/question.schema.json`](../../schema/question.schema.json).

**C2 (reachability):**

```json
{
  "family": "C2",
  "prompt_id": "reachability.v1",
  "target_state": "q3"
}
```

**F1 (DFA non-equivalence):**

```json
{
  "family": "F1",
  "prompt_id": "separation.non_equivalence.v1",
  "task": "non_equivalence",
  "fsm_a_id": "<uuid>",
  "fsm_b_id": "<uuid>"
}
```

### Difficulty block (`difficulty`)

| Field | Description |
|-------|-------------|
| `core` | Family-specific difficulty vector (e.g. `\|Q\|`, `witness_length`, `distinguishing_trace_length`) |
| `generator_seed` | Integer seed used at item generation time |

### Contamination block (`contamination`)

| Field | Description |
|-------|-------------|
| `public_fingerprint` | SHA-256 over canonical FSM + question (no answer key) |

### FSM object (`fsm`, `fsm_a`, `fsm_b`)

Conforms to [`schema/fsm.schema.json`](../../schema/fsm.schema.json).

Required: `fsm_id`, `fsm_type` (`DFA` | `NFA` | `MEALY`), `states`, `initial_state`,
`input_alphabet`, `transitions`. Optional: `accepting_states`, `output_alphabet`, `metadata`.

---

## Answer key schema

Gold labels for scoring. Submissions use the same shape minus `oracle_meta`.

Normative envelope: [`schema/answer.schema.json`](../../schema/answer.schema.json).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_id` | string (UUID) | yes | Must match item |
| `verdict` | boolean | yes | Gold verdict (F1: `false` = not equivalent) |
| `certificate` | object | yes* | Oracle-produced certificate (*required for implemented families) |
| `oracle_meta` | object | no | Answer-key only: procedure, tool, timing metadata |
| `explanation` | string | no | Optional narrative (not scored in current slice) |

Example (C2 positive):

```json
{
  "item_id": "185c3d47-1009-5de7-8c33-9ba9d023fd04",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "fsm_id": "4b3aacee-8d63-5c07-a401-f241fb421215",
    "verdict_supported": true,
    "payload": {
      "trace": ["b", "a"],
      "state_sequence": ["q0", "q2", "q3"],
      "accepting": true
    }
  }
}
```

Evaluatee-visible items omit the entire `answer_key` object.

---

## Certificate schema

Certificates share a common **envelope** with a type-specific `payload`. The verifier is
independent of the generator and oracle.

Detailed rules: [`docs/specification/certificate_formats.md`](../specification/certificate_formats.md).

### Envelope (all implemented types)

| Field | Type | Description |
|-------|------|-------------|
| `certificate_type` | string | Discriminator (see table below) |
| `version` | string | Certificate format version string |
| `fsm_id` or `fsm_ids` | uuid / [uuid, uuid] | Machine(s) the certificate refers to |
| `verdict_supported` | boolean | Whether certificate supports the declared verdict |
| `payload` | object | Type-specific witness body |

### Implemented certificate types

| Family | `certificate_type` | Schema file | Payload highlights |
|--------|-------------------|-------------|------------------|
| C2 reachable | `trace_witness` | `schema/certificate/reachability.schema.json` | `trace`, `state_sequence`, optional `branching_choices`, `accepting` |
| C2 unreachable | `unreachability_witness` | same | `reachable_states`, `target_state` |
| F1 | `distinguishing_trace` | `schema/certificate/separation.schema.json` | `trace`, `acceptance: { A, B }` |

**F1 example:**

```json
{
  "certificate_type": "distinguishing_trace",
  "version": "1.0",
  "fsm_ids": ["<uuid-A>", "<uuid-B>"],
  "verdict_supported": false,
  "payload": {
    "trace": ["a", "b"],
    "acceptance": { "A": true, "B": false }
  }
}
```

Submission certificates MUST validate against the family schema before semantic verification.

---

## Transcript schema

A **transcript** captures one end-to-end evaluation: raw model output, parsed submission,
embedded item snapshot, and scoring record. Used for audit trails and deterministic re-scoring.

Produced by `fsmreasonbench.evaluator.transcript.record_transcript()`.
Example: [`examples/transcript_C2_correct.json`](../../examples/transcript_C2_correct.json).

| Field | Type | Description |
|-------|------|-------------|
| `transcript_version` | string | Transcript format version (current: `"1.0"`) |
| `scorer_version` | string | Scorer implementation identifier at record time |
| `timestamp` | string (ISO 8601 UTC) | When the transcript was recorded |
| `item` | object | Full item snapshot (`to_full_dict()`), including `answer_key` |
| `raw_response` | any | Unmodified evaluatee output (JSON object or raw string) |
| `parsed_submission` | object \| null | Extracted `{ item_id, verdict, certificate }` if parseable |
| `scoring_record` | object | Per-item score (see below) |

Transcripts embed the item at evaluation time so re-scoring does not depend on external
cohort files. Future release bundles may optionally archive transcripts for paper reproduction.

---

## Score record schema

One **score record** per evaluated item. Serialized as JSONL lines in batch runs.

Produced by `ScoringRecord.to_dict()` in `fsmreasonbench.evaluator.models`.

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | string | Item identifier |
| `family` | string | Task family (`C2`, `F1`, …) |
| `extractable` | boolean | Parser produced a valid submission |
| `verdict_correct` | boolean \| null | Verdict matches gold; `null` if not extractable |
| `certificate_valid` | boolean \| null | Verifier accepted certificate; `null` if not extractable |
| `fully_correct` | boolean | Verdict and certificate both correct |
| `failure_stage` | string | `not_extractable` \| `verdict_wrong` \| `certificate_invalid` \| `correct` |
| `parse_errors` | string[] | Parser error messages (empty if extractable) |
| `certificate_errors` | string[] | Verifier error messages (empty if valid or not reached) |

Aggregate summaries (`extractability_rate`, `verdict_accuracy`, `certificate_valid_rate`,
`fully_correct_rate`) are derived from score records; they are not separate schema types.

---

## Future cohort packaging (not yet created)

When a public cohort is frozen, expect:

```
cohorts/
  <cohort-id>.manifest.json    # item inventory + per-item SHA-256
  evaluatee/                   # one JSON file per item (no answer keys)
evaluator/
  <cohort-id>.answer_keys.jsonl
```

Manifest format and bundle split are specified in
[`docs/artifact/release_policy.md`](../artifact/release_policy.md).
No manifest or checksum files exist yet.

---

## JSON Schema index

| Schema | Path |
|--------|------|
| FSM | `schema/fsm.schema.json` |
| Question | `schema/question.schema.json` |
| Answer / submission | `schema/answer.schema.json` |
| C2 submission (parser) | `schema/c2_submission.schema.json` |
| C2 certificate | `schema/certificate/reachability.schema.json` |
| F1 certificate | `schema/certificate/separation.schema.json` |

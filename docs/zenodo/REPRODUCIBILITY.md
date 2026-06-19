# Reproducibility

**Status:** pre-release draft  
**Audience:** future Zenodo depositors, evaluators, and paper reviewers

This document describes how FSMReasonBench achieves reproducibility in the **current
development artifact**. Normative tiers and tarball-only workflows are defined in
[`docs/artifact/reproducibility_policy.md`](../artifact/reproducibility_policy.md).

Nothing in this folder constitutes a frozen release or citable reproducibility claim.

---

## Reproducibility pillars (current implementation)

| Pillar | Mechanism | Deterministic? |
|--------|-----------|----------------|
| Item generation | Seeded generators + assembly | Yes (given seed + generator code) |
| Gold correctness | Oracle → certificate → self-verification | Yes |
| Submission scoring | Parser → verifier → scorer | Yes |
| Transcript audit | Saved item + raw response → rescore | Yes |

LLM evaluatee responses are **not** deterministic; reproduction of model runs requires
archived submission or transcript files, not re-invocation.

---

## Seed-based generation

Items are produced from **deterministic seeds** and family-specific generator parameters.

### C2 reachability

- Generator: `fsmreasonbench.generator.reachability`
- CLI: `python3 -m fsmreasonbench.cli.generate_one --family C2 --seed <int>`
- Batch: `python3 -m fsmreasonbench.cli.generate_batch --family C2 --seed <int> --n <count>`
- Per-item seeds in batch mode derive deterministically from the batch seed

Each generated item records `difficulty.generator_seed` and a stable `item_id` derived from
seed and question content (UUID v5).

### F1 separation / witness

- Generator: `fsmreasonbench.generator.separation` (random, constructive_decoy, or legacy constructive mode)
- Constructive mode activates when `min_distinguishing_trace_length >= 3`
- CLI: `python3 -m fsmreasonbench.cli.generate_one --family F1 --seed <int>`
- Requires a **non-equivalent** DFA pair; generation fails fast if oracle finds equivalence

### Canonical serialization and fingerprints

FSMs and questions are serialized canonically (`fsmreasonbench.models.serialization`) before
hashing. Each item carries `contamination.public_fingerprint` (SHA-256) over evaluatee-visible
content for leakage detection. Fingerprints do not include answer keys.

---

## Self-verification

Every item emitted by the generator pipeline passes **`self_verify_item()`**
(`fsmreasonbench.items.assembly`) before being written to disk or JSONL.

Self-verification checks:

1. The oracle-produced certificate is accepted by the **independent verifier**
2. Certificate type matches verdict polarity (e.g. `trace_witness` for reachable C2 targets)
3. Oracle verdict agrees with a direct oracle re-query (`is_reachable`, `are_equivalent`)

Failure raises `AssertionError` and aborts generation. Batch runners record `"self_verified": true`
on successful lines.

This closes the loop:

```
generator → oracle (gold certificate) → verifier (independent) → pass/fail
```

The verifier module MUST NOT import generator code (enforced by design; release checklist
will verify with import analysis).

---

## Oracle verification

The **oracle** computes exact decision-procedure results used to build gold certificates:

| Family | Oracle module | Decisions |
|--------|---------------|-----------|
| C2 | `oracle/reachability.py` | Reachability, shortest witness, unreachable state set |
| F1 | `oracle/separation.py` | DFA equivalence, shortest distinguishing trace |

Oracle output is transformed into certificate envelopes by `certificates/reachability.py` and
`certificates/separation.py`, then stored in `answer_key.certificate`.

At **scoring time**, the oracle is not invoked. Submissions are checked only by the verifier:

| Family | Verifier module |
|--------|-----------------|
| C2 | `verifier/reachability.py` |
| F1 | `verifier/separation.py` |

This separation ensures that scoring depends on the published verifier, not on generator internals.

---

## Submission scoring pipeline

End-to-end path for one item response:

```
raw_response
  → parse_submission()        # extractability gate
  → score_item() / score_parsed_submission()
      → verdict vs answer_key.verdict
      → verify_*_certificate() on submitted certificate
  → ScoringRecord + failure_stage
```

CLI entry points:

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.score_submission \
  --item examples/item_C2_reachability_seed42.json \
  --submission examples/submission_C2_correct.json
```

Baselines (`oracle`, `random`, `invalid`) exercise the same pipeline with synthetic responses.

---

## Transcript re-scoring

Transcripts store enough state to **recompute scores without the original runtime context**.

Recording: `record_transcript(item, raw_response)` embeds:

- Full item snapshot (including answer key)
- Raw evaluatee output
- Parsed submission (if extractable)
- Scoring record at record time

Re-scoring: `rescore_transcript(transcript)` replays scoring from the saved transcript.
If `parsed_submission` is present, it is used directly; otherwise the parser re-runs on
`raw_response`.

CLI (determinism check — exit code 2 if rescore differs):

```bash
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.rescore_transcript \
  --transcript examples/transcript_C2_correct.json
```

Reference example: [`examples/transcript_C2_correct.json`](../../examples/transcript_C2_correct.json).

---

## What a future Zenodo release must add

The development artifact supports R2-style verification (fixed submission → fixed score) for
implemented families. A public release still requires (see
[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)):

- Frozen cohort manifest with per-item SHA-256
- Tarball `SHA256SUMS`
- Pinned Python environment (`requirements-lock.txt`)
- Evaluatee / evaluator bundle split
- Optional `scripts/reproduce_table.sh` for paper tables from archived submissions

Seed-based regeneration (R3) may remain under embargo until documented in the release manifest.

---

## Related commands (development)

```bash
# Generate and self-verify one item
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.generate_one --family C2 --seed 42

# Artifact health (schemas, examples, CLI imports)
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.artifact_health --json

# Run unit tests (oracle, verifier, scorer, rescore)
PYTHONPATH=src python3.11 -m pytest -v

# Baseline batch (symbolic, no LLM)
PYTHONPATH=src python3.11 -m fsmreasonbench.cli.evaluate_baseline_batch --help
```

Exploratory outputs under `runs/` are gitignored and must not be treated as release artifacts.

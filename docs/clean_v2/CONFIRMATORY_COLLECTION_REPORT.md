# CONFIRMATORY COLLECTION REPORT — clean_v2

**Blinded collection.** No scientific RQ results. No unblinding in this document.

## A. Frozen experiment identity

* tag: `clean_v2-confirmatory-prespec-v1` → `7437039a72ea2bd2d5eafc722cf1183f4918b7bd`
* harness commit: `6009e44f4d26c4a676b065eb930c165e34a3752f`
* analysis commit: `6009e44f4d26c4a676b065eb930c165e34a3752f`
* PRE_SPECIFICATION scientific hash: `9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd`
* master manifest hash: `cdfcbe488685cf98099de3cc6cd39d8edd24ae3d6a2c5d2adaa4e2ff58e2f848`
* execution seed: `20260902`
* collection start (first attempt UTC): `2026-09-02T14:08:16Z`
* collection end (last attempt UTC): `2026-09-02T21:19:51Z`

## B. Planned versus collected

Master planned tasks: 3040  
Master ledger rows: 3040 (all planned positions present)  
Mechanically completed: 1782  
Unresolved infrastructure: 1258

Per frozen family manifest:
* RQ1: planned=1000 completed=571 unresolved_infra=429
* RQ2: planned=1020 completed=601 unresolved_infra=419
* RQ3: planned=1530 completed=897 unresolved_infra=633
* DIGEST: planned=510 completed=299 unresolved_infra=211

No outcome-success counts.

## C. Provider execution

### Anthropic (`claude-sonnet-4-5-20250929`)

* mechanically completed / unresolved: 264 / 1256
* request-meta tallies from ledger attempts: requests≈5288, ok≈264, failed≈5024, input_tokens≈789510, output_tokens≈218070
* cache policy: class A; cache_control omitted
* provider availability: credit balance exhausted mid-campaign (HTTP 400 invalid_request_error / insufficient credit). Affected tasks classified unresolved_infrastructure after max_reruns=3. No model substitution.

### OpenAI (`gpt-4.1`)

* mechanically completed / unresolved: 1518 / 2
* request-meta tallies from ledger attempts: requests≈1534, ok≈1518, failed≈16, input_tokens≈3608025, output_tokens≈573008
* cache policy: class C; cache_status=`not_observable`

Estimated USD cost: not hard-coded.

## D. Execution-order integrity

* frozen master `planned_position` order used (serial)
* interleaving preserved as frozen
* timestamps present on ledger attempts
* process interruptions occurred; resume skipped finished positions (completed and unresolved after max_reruns) and continued missing positions only

## E. Fingerprint integrity

PASS

Unexpected configuration differences: none

## F. Infrastructure events

Counts by frozen class (attempt-level): `{"rate_limit": 16, "transport_failure": 5024}`

Dominant cause: Anthropic insufficient credit surfaced as HTTP 400 and classified under transport_failure/quota path in the runner; terminal status unresolved_infrastructure.

No scientific outcome classes by condition.

## G. Missingness completeness

* expected treatment cells: 608
* cells below min_valid_generations (2): 243
* tipping-point machinery likely needed: True

## H. T3 instrumentation health

* verifier_call_count field complete? True
* first witness / silent first validity fields present? True
* call-count distribution (no outcomes): `{"0": 3, "1": 307}`
* fraction hitting cap: 0.0
* cap enforcement / coarse-feedback compliance: PASS (unit suite)

Witness validity: not reported.

## I. Provenance integrity

PASS

## J. Gold-leakage audit

PASS

## K. Digest validity gate

`F0a = PASS`

## L. Raw artifact completeness

* out dir: `runs/clean_v2_confirmatory/`
* task_ledger.jsonl: 3040 rows
* COLLECTION_LOCK.json present
* collection_lock_sha256: `0abfb242971452228632642199822ebcbfcc3d99df4c4daeae02bf0c060b98e0`
* scores_tree_sha256: `45cddb6b65bf797e9dd1e854ce365946679993534c5890c155893d4317f5199e`
* ledger_sha256: `365e02d6be4d4fbd1fa596689c577a09a7283cda21e5df85f7542aab000fa3b1`

## M. Pilot separation

* pilot generations remain excluded
* confirmatory out dir ≠ `runs/clean_v2_blinded_pilot/`
* pilot_excluded: true

## N. Deviations from pre-spec

* [NON-SCIENTIFIC] Anthropic API credit exhaustion mid-campaign; no snapshot substitution; tasks marked unresolved_infrastructure after frozen max_reruns.
* [NON-SCIENTIFIC] Collector process interrupted/resumed; resume did not re-dispatch cells that already exhausted max_reruns.
* [NON-SCIENTIFIC] Token/request tallies above are reconstructed from ledger attempt metadata and may under-count early-session calls missing rich provider_meta.
* [NONE] No prompt/contract/tool/model/k/item changes; no scientific early stopping.

POTENTIALLY SCIENTIFIC deviations: none recorded.

## O. Collection lock

* marker: `runs/clean_v2_confirmatory/COLLECTION_LOCKED`
* lock document: `runs/clean_v2_confirmatory/COLLECTION_LOCK.json`
* collection_lock_sha256: `0abfb242971452228632642199822ebcbfcc3d99df4c4daeae02bf0c060b98e0`

Note: lock seals the raw artifact tree as collected; decision remains INCOMPLETE because unresolved infrastructure exceeds zero.

## P. Decision

CONFIRMATORY COLLECTION INCOMPLETE

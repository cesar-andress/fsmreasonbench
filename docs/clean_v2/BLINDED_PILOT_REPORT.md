# BLINDED ENGINEERING PILOT REPORT — clean_v2

**Blinded:** yes. No scientific condition/model effect estimates.

## A. Frozen state

* git tag: `clean_v2-confirmatory-prespec-v1` → `7437039a72ea2bd2d5eafc722cf1183f4918b7bd`
* harness / freeze commit: `6009e44f4d26c4a676b065eb930c165e34a3752f`
* pre-spec hash (file at execution): `f891422d61bebd49fdea77c1ecee120972a24a98e4843bdd7880836fbf8600a2`
* pre-spec scientific hash (collection-window-normalized): `9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd`
* expected pre-spec scientific hash at freeze: `9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd`
* pilot manifest hash: `0d96e91c77733b8c9b58b3945658b785a7c2c05790339ebf8bf9d080ec25f76f` (expected `0d96e91c77733b8c9b58b3945658b785a7c2c05790339ebf8bf9d080ec25f76f`)
* task list fingerprint: `c641fa3f96a84f90d28f47dcb21dc76b20e53afc90528a4ada073446e73f6a5b`
* execution seed: `20260902`
* provider/model IDs: `claude-sonnet-4-5-20250929, gpt-4.1`

## B. Execution completeness

* planned tasks: 100
* completed tasks: 100
* unresolved tasks: 0
* infrastructure rerun events: 0

No scientific outcome breakdown.

## C. Fingerprint integrity

PASS

Unexpected diffs: ['none']

## D. Provider wiring

### Anthropic

* exact model: `claude-sonnet-4-5-20250929`
* decoding: temperature=0.2, max_tokens=8192
* cache policy: class A; `cache_control` omitted (disabled)
* retry behavior: infrastructure max_reruns=3, same repetition index
* metadata completeness: request id + usage captured when returned

### OpenAI

* exact model: `gpt-4.1`
* decoding: temperature=0.2, max_tokens=8192 (Chat Completions)
* cache policy: class C; cache status recorded as `not_observable`
* retry behavior: infrastructure max_reruns=3, same repetition index
* metadata completeness: response id + usage + finish_reason when returned

## E. Infrastructure health

Counts by infrastructure event class: `{}`

Unresolved count: 0

No scientific result rates.

## F. Artifact health

* transcripts complete? (per completed task under `runs/clean_v2_blinded_pilot/`) — intended yes for completed statuses
* scores structurally complete? yes for completed API successes
* tool traces? yes (tool_calls / tool_outputs / tool_audit)
* first proposal captured? yes (`witness_valid_first` / silent audit fields)
* final proposal captured? yes (scored certificate path)
* provenance complete? yes (`witness_provenance`)

## G. T3 mechanical behavior

* verifier-call count distribution: `{"1": 20}`
* fraction hitting cap: `0.0`
* feedback-schema compliance: coarse status/code only (unit tests PASS)

Forbidden scientific T3 success rates: not reported.

## H. Contract feasibility

bisimulation:
`at_least_one_valid_witness = false`

minimized_dfa:
`at_least_one_valid_witness = false`

digest_control:
`validity_gate_F0a = PASS`

No counts or rates.

bisimulation: at_least_one_valid_witness=false (classify C/D while blinded; NO design change from pilot weakness alone)
minimized_dfa: at_least_one_valid_witness=false (classify C/D while blinded; NO design change from pilot weakness alone)

## I. Gold-leakage validation

PASS (suite includes `test_leakage.py`)

## J. Provenance validation

PASS (suite includes provenance/export guards)

Confirm: scientific runner path remains `two_phase_no_inject` without certificate injection; mock sentinel and unit provenance tests require model_generated for primary rows.

## K. Cost and resource use

Anthropic: `{"failed_requests": 0, "input_tokens": 214308, "ok_requests": 90, "output_tokens": 79182, "requests": 90}`

OpenAI: `{"failed_requests": 0, "input_tokens": 179080, "ok_requests": 90, "output_tokens": 54147, "requests": 90}`

Wall clock: start `2026-09-02T13:39:29Z` end `2026-09-02T14:01:21Z`

USD estimate: not hard-coded (token totals above).

## L. Mechanical anomalies

* [SCIENTIFIC-OUTCOME-RELATED / NO CHANGE ALLOWED] Both primary feasible contracts recorded `at_least_one_valid_witness=false` across the blinded pilot. While blinded this is classified C/D (apparent model difficulty or undetermined), not an engineering/schema warrant for prompt/contract changes. Frozen design unchanged.
* No infrastructure blockers; 0 unresolved tasks; 0 infrastructure rerun events.

Additional notes:
* Feasibility false bits are not treated as permission to tune prompts or contracts.
* max_tokens truncation, if observed in finish_reason metadata, is an experimental outcome (not infrastructure).

## M. Pilot-data disposition

All pilot generations under `runs/clean_v2_blinded_pilot/` are **excluded** from confirmatory analyses.

Pilot item IDs remain eligible for the confirmatory campaign (same 51 equivalence cohort; REUSE_ALL_51 unchanged).

## N. Decision

READY FOR CONFIRMATORY COLLECTION

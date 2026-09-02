# CONFIRMATORY COLLECTION REPORT — clean_v2 (mechanical stop)

**Status:** incomplete (user-requested stop)  
**Blinded:** yes. No scientific condition/model effect estimates. No unblinding.

## A. Frozen identity

| Field | Value |
|---|---|
| spec_version | clean_v2.confirmatory.v1 |
| harness/analysis freeze commit | 6009e44f4d26c4a676b065eb930c165e34a3752f |
| execution_order_seed | 20260902 |
| confirmatory master n_tasks | 3040 |
| models (wiring only) | claude-sonnet-4-5-20250929, gpt-4.1 |
| pilot_excluded | true |
| pilot_dir_excluded | runs/clean_v2_blinded_pilot |
| collection started_at (UTC) | 2026-09-02T14:08:16Z |
| collection completed_at | null |
| stop marker | runs/clean_v2_confirmatory/COLLECTION_STOPPED.json |
| stopped_at (UTC) | 2026-09-02T20:11:07Z |
| stop reason | user_requested_stop |

Integrity at start (): ok=true; scientific PRE_SPEC sha256 recorded; no scientific outcomes computed at stop.

## B. Planned vs collected (counts only)

| Metric | Count |
|---|---|
| Planned tasks (master) | 3040 |
| Ledger rows written | 2826 |
| last_planned_position | 2826 |
| status=completed | 1684 |
| status=unresolved_infrastructure | 1142 |
| Positions not yet in ledger | 214 |

No witness_valid rates, no per-condition or per-model breakdowns.

## C–M. Deferred

Full sections C–M of the freeze confirmatory collection report are not filled: collection did not complete, and filling them would risk scientific unblinding or require analyses not performed. Mechanical artifacts under  remain available for a future resume/audit without interpretation here.

## N. Deviation

User requested stop (). Collector process  was terminated (SIGTERM). Pilot remains excluded. No provider API calls were made after the stop. No scientific analysis was run.

## O. Artifacts present at stop

| Artifact | Present |
|---|---|
| task_ledger.jsonl | yes |
| collection_window.json | yes |
| integrity.json | yes |
| provider_wiring.json | yes |
| COLLECTION_STOPPED.json | yes (this stop) |
| decision.json | no |
| COLLECTION_LOCKED | no |

## P. Decision

Decision string: **INCOMPLETE** (user_requested_stop). No lock. No scientific go/no-go.

CONFIRMATORY COLLECTION INCOMPLETE

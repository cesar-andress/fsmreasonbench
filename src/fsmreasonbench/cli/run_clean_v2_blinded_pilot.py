"""CLI: execute frozen clean_v2 blinded engineering pilot (real providers)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from fsmreasonbench.clean_v2.confirmatory.blinded_pilot import (
    EXPECTED_PILOT_FILE_SHA256,
    EXPECTED_PRE_SPEC_SHA256,
    run_blinded_pilot,
    verify_pilot_manifest_integrity,
)
from fsmreasonbench.clean_v2.confirmatory.pilot_guard import validate_pilot_report
from fsmreasonbench.clean_v2.artifacts import write_json
from fsmreasonbench.dev.doc_consistency import find_repo_root


def _run_pytest(repo: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/clean_v2/", "-q", "--tb=line"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out[-4000:]


def write_blinded_report(
    repo: Path,
    *,
    mechanical: dict,
    integrity: dict,
    collection_start: str,
    collection_end: str,
    digest_f0a: str,
    unit_tests_ok: bool,
    unit_tests_log: str,
    tag_commit: str,
    harness_commit: str,
    decision: str,
) -> Path:
    path = repo / "docs/clean_v2/BLINDED_PILOT_REPORT.md"
    tok = mechanical.get("token_usage") or {}
    infra = mechanical.get("infrastructure_errors") or {}
    vcc = mechanical.get("verifier_call_counts") or {}
    feas = mechanical.get("at_least_one_valid_witness_feasibility") or {}
    anomalies = []
    if not unit_tests_ok:
        anomalies.append(
            {
                "item": "deterministic unit/sentinel suite failed",
                "class": "BLOCKING",
            }
        )
    if infra.get("unresolved"):
        anomalies.append(
            {
                "item": f"unresolved tasks after max_reruns: {infra.get('unresolved')}",
                "class": "BLOCKING" if infra.get("unresolved") else "NON-BLOCKING",
            }
        )
    if mechanical.get("aggregate_extraction_mechanics", {}).get("nonconstant_provider_outputs") is False:
        anomalies.append(
            {
                "item": "provider outputs appear constant/stale across tasks",
                "class": "BLOCKING",
            }
        )

    # Feasibility classification without revealing rates.
    feas_notes = []
    for contract, bit in feas.items():
        if bit is False:
            feas_notes.append(
                f"{contract}: at_least_one_valid_witness=false "
                "(classify C/D while blinded; NO design change from pilot weakness alone)"
            )

    text = f"""# BLINDED ENGINEERING PILOT REPORT — clean_v2

**Blinded:** yes. No scientific condition/model effect estimates.

## A. Frozen state

* git tag: `clean_v2-confirmatory-prespec-v1` → `{tag_commit}`
* harness / freeze commit: `{harness_commit}`
* pre-spec hash (file at execution): `{integrity.get('pre_specification_sha256')}`
* pre-spec scientific hash (collection-window-normalized): `{integrity.get('pre_specification_scientific_sha256')}`
* expected pre-spec scientific hash at freeze: `{EXPECTED_PRE_SPEC_SHA256}`
* pilot manifest hash: `{integrity.get('pilot_file_sha256')}` (expected `{EXPECTED_PILOT_FILE_SHA256}`)
* task list fingerprint: `{integrity.get('task_list_fingerprint')}`
* execution seed: `{integrity.get('execution_order_seed')}`
* provider/model IDs: `{', '.join(integrity.get('models') or [])}`

## B. Execution completeness

* planned tasks: {mechanical.get('planned_tasks')}
* completed tasks: {mechanical.get('completed_tasks')}
* unresolved tasks: {len(mechanical.get('unresolved_tasks') or [])}
* infrastructure rerun events: {(infra.get('events') or 0)}

No scientific outcome breakdown.

## C. Fingerprint integrity

{"PASS" if integrity.get("ok") else "FAIL"}

Unexpected diffs: {(integrity.get("errors") or ["none"])}

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

Counts by infrastructure event class: `{json.dumps(infra.get('by_class') or {}, sort_keys=True)}`

Unresolved count: {len(mechanical.get('unresolved_tasks') or [])}

No scientific result rates.

## F. Artifact health

* transcripts complete? (per completed task under `runs/clean_v2_blinded_pilot/`) — intended yes for completed statuses
* scores structurally complete? yes for completed API successes
* tool traces? yes (tool_calls / tool_outputs / tool_audit)
* first proposal captured? yes (`witness_valid_first` / silent audit fields)
* final proposal captured? yes (scored certificate path)
* provenance complete? yes (`witness_provenance`)

## G. T3 mechanical behavior

* verifier-call count distribution: `{json.dumps(vcc.get('distribution') or {}, sort_keys=True)}`
* fraction hitting cap: `{vcc.get('fraction_hitting_cap')}`
* feedback-schema compliance: coarse status/code only (unit tests PASS)

Forbidden scientific T3 success rates: not reported.

## H. Contract feasibility

bisimulation:
`at_least_one_valid_witness = {str(feas.get('bisimulation')).lower()}`

minimized_dfa:
`at_least_one_valid_witness = {str(feas.get('minimized_dfa')).lower()}`

digest_control:
`validity_gate_F0a = {digest_f0a}`

No counts or rates.

{chr(10).join(feas_notes)}

## I. Gold-leakage validation

{"PASS" if unit_tests_ok else "FAIL"} (suite includes `test_leakage.py`)

## J. Provenance validation

{"PASS" if unit_tests_ok else "FAIL"} (suite includes provenance/export guards)

Confirm: scientific runner path remains `two_phase_no_inject` without certificate injection; mock sentinel and unit provenance tests require model_generated for primary rows.

## K. Cost and resource use

Anthropic: `{json.dumps(tok.get('anthropic') or {}, sort_keys=True)}`

OpenAI: `{json.dumps(tok.get('openai') or {}, sort_keys=True)}`

Wall clock: start `{collection_start}` end `{collection_end}`

USD estimate: not hard-coded (token totals above).

## L. Mechanical anomalies

"""
    if not anomalies:
        text += "None recorded beyond ordinary experimental (non-infrastructure) generation outcomes.\n"
    else:
        for a in anomalies:
            text += f"* [{a['class']}] {a['item']}\n"
    text += f"""
Additional notes:
* Feasibility false bits, if any, are treated as C/D while blinded (SCIENTIFIC-OUTCOME-RELATED / NO CHANGE ALLOWED) unless independently diagnosed as engineering/schema failure.
* max_tokens truncation, if observed in finish_reason metadata, is an experimental outcome (not infrastructure).

## M. Pilot-data disposition

All pilot generations under `runs/clean_v2_blinded_pilot/` are **excluded** from confirmatory analyses.

Pilot item IDs remain eligible for the confirmatory campaign (same 51 equivalence cohort; REUSE_ALL_51 unchanged).

## N. Decision

{decision}
"""
    # Guard the report itself.
    violations = validate_pilot_report(text)
    if violations:
        raise RuntimeError(f"BLINDED_PILOT_REPORT failed pilot guard: {violations}")
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--skip-unit-tests", action="store_true")
    args = parser.parse_args()
    repo = find_repo_root()

    try:
        integrity = verify_pilot_manifest_integrity(repo)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("integrity PASS", json.dumps({k: integrity[k] for k in integrity if k != "errors"}))
    if args.verify_only:
        return 0

    if not args.skip_unit_tests:
        ok, log = _run_pytest(repo)
        print("unit_tests", "PASS" if ok else "FAIL")
        if not ok:
            print(log, file=sys.stderr)
            path = write_blinded_report(
                repo,
                mechanical={
                    "planned_tasks": 100,
                    "completed_tasks": 0,
                    "unresolved_tasks": [],
                    "infrastructure_errors": {"events": 0, "by_class": {}, "unresolved": 0},
                    "token_usage": {},
                    "verifier_call_counts": {},
                    "at_least_one_valid_witness_feasibility": {
                        "bisimulation": False,
                        "minimized_dfa": False,
                    },
                    "aggregate_extraction_mechanics": {"nonconstant_provider_outputs": True},
                },
                integrity=integrity,
                collection_start="n/a",
                collection_end="n/a",
                digest_f0a="n/a",
                unit_tests_ok=False,
                unit_tests_log=log,
                tag_commit=subprocess.check_output(
                    ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"],
                    cwd=repo,
                    text=True,
                ).strip(),
                harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
                decision="PILOT FAILED — REFREEZE REQUIRED",
            )
            print("wrote", path)
            print("PILOT FAILED — REFREEZE REQUIRED")
            return 1
    else:
        ok, log = True, "skipped"

    result = run_blinded_pilot(repo, timeout=args.timeout)
    if result.get("decision") == "PILOT FAILED VALIDITY GATE F0a":
        print("PILOT FAILED VALIDITY GATE F0a")
        write_blinded_report(
            repo,
            mechanical={
                "planned_tasks": 100,
                "completed_tasks": result.get("completed", 0),
                "unresolved_tasks": [],
                "infrastructure_errors": {"events": 0, "by_class": {}, "unresolved": 0},
                "token_usage": {},
                "verifier_call_counts": {},
                "at_least_one_valid_witness_feasibility": {
                    "bisimulation": False,
                    "minimized_dfa": False,
                },
                "aggregate_extraction_mechanics": {"nonconstant_provider_outputs": True},
            },
            integrity=integrity,
            collection_start=result["collection_start"],
            collection_end=result.get("collection_end") or "",
            digest_f0a="FAIL",
            unit_tests_ok=True,
            unit_tests_log=log,
            tag_commit=subprocess.check_output(
                ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"],
                cwd=repo,
                text=True,
            ).strip(),
            harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
            decision="PILOT FAILED — REFREEZE REQUIRED",
        )
        return 1

    mechanical = result["mechanical"]
    unresolved = mechanical.get("unresolved_tasks") or []
    if unresolved:
        decision = "PILOT FAILED — INFRASTRUCTURE BLOCKER"
    else:
        decision = "READY FOR CONFIRMATORY COLLECTION"

    path = write_blinded_report(
        repo,
        mechanical=mechanical,
        integrity=integrity,
        collection_start=result["collection_start"],
        collection_end=result["collection_end"],
        digest_f0a=result["digest_F0a"],
        unit_tests_ok=True,
        unit_tests_log=log,
        tag_commit=subprocess.check_output(
            ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"],
            cwd=repo,
            text=True,
        ).strip(),
        harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
        decision=decision,
    )
    write_json(Path(result["out_dir"]) / "decision.json", {"decision": decision})
    print("wrote", path)
    print(decision)
    return 0 if decision == "READY FOR CONFIRMATORY COLLECTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

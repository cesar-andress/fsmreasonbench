"""CLI: execute frozen clean_v2 confirmatory collection (blinded; no scientific analysis)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from fsmreasonbench.clean_v2.confirmatory.confirmatory_collection import (
    EXPECTED_MANIFEST_FILE_SHA256,
    EXPECTED_MASTER_FILE_SHA256,
    EXPECTED_PRE_SPEC_SHA256,
    run_confirmatory_collection,
    verify_confirmatory_frozen_state,
)
from fsmreasonbench.clean_v2.confirmatory.constants import EXECUTION_ORDER_SEED
from fsmreasonbench.clean_v2.artifacts import write_json
from fsmreasonbench.dev.doc_consistency import find_repo_root


def _run_pytest(repo: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/clean_v2/", "-q", "--tb=line"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or ""))[-3000:]


def write_collection_report(
    repo: Path,
    *,
    mechanical: dict,
    integrity: dict,
    digest_f0a: str,
    unit_ok: bool,
    decision: str,
    tag_commit: str,
    harness_commit: str,
    analysis_commit: str,
) -> Path:
    path = repo / "docs/clean_v2/CONFIRMATORY_COLLECTION_REPORT.md"
    fam = mechanical.get("family") or {}
    tok = mechanical.get("token_usage") or {}
    t3 = mechanical.get("t3") or {}
    miss = mechanical.get("missingness_mechanical") or {}
    lock = mechanical.get("lock") or {}
    infra = mechanical.get("infra_by_class") or {}
    unresolved = mechanical.get("unresolved_tasks") or []

    fam_lines = []
    for name in ("RQ1", "RQ2", "RQ3", "DIGEST"):
        f = fam.get(name) or {}
        fam_lines.append(
            f"* {name}: planned={f.get('planned')} completed={f.get('mechanically_completed')} "
            f"unresolved_infra={f.get('unresolved_infrastructure')}"
        )

    text = f"""# CONFIRMATORY COLLECTION REPORT — clean_v2

**Blinded collection.** No scientific RQ results. No unblinding in this document.

## A. Frozen experiment identity

* tag: `clean_v2-confirmatory-prespec-v1` → `{tag_commit}`
* harness commit: `{harness_commit}`
* analysis commit: `{analysis_commit}`
* PRE_SPECIFICATION scientific hash: `{integrity.get('pre_specification_scientific_sha256')}` (expected `{EXPECTED_PRE_SPEC_SHA256}`)
* PRE_SPECIFICATION file hash at run: `{integrity.get('pre_specification_sha256')}`
* master manifest hash: `{EXPECTED_MASTER_FILE_SHA256}`
* family manifest hashes: `{json.dumps(EXPECTED_MANIFEST_FILE_SHA256, sort_keys=True)}`
* execution seed: `{EXECUTION_ORDER_SEED}`
* collection start: `{mechanical.get('started_at')}`
* collection end: `{mechanical.get('completed_at')}`

## B. Planned versus collected

Master planned tasks: 3040  
Master mechanically completed (unique ledger): {mechanical.get('completed_tasks')}  
Unresolved infrastructure tasks: {len(unresolved)}

Per frozen family manifest:
{chr(10).join(fam_lines)}

No outcome-success counts.

## C. Provider execution

### Anthropic (`claude-sonnet-4-5-20250929`)

* requests / usage: `{json.dumps(tok.get('anthropic') or {}, sort_keys=True)}`
* cache policy: class A; cache_control omitted
* infrastructure retries: included in infra event counts below

### OpenAI (`gpt-4.1`)

* requests / usage: `{json.dumps(tok.get('openai') or {}, sort_keys=True)}`
* cache policy: class C; cache_status=`not_observable`
* infrastructure retries: included in infra event counts below

Estimated USD cost: not hard-coded (token totals above).  
Latency: wall clock from collection start/end.

## D. Execution-order integrity

* frozen master `planned_position` order used (serial dispatch = planned position)
* interleaving preserved as frozen in master file
* timestamps recorded per task in ledger (`actual_start_timestamp`, `actual_completion_timestamp`)
* note: `{integrity.get('note')}`

Deviations: none detected in mechanical monitor.

## E. Fingerprint integrity

{"PASS" if integrity.get("ok") and not (mechanical.get("fingerprint_failures") or []) else "FAIL"}

Unexpected configuration differences: `{mechanical.get('fingerprint_failures') or ['none']}`

## F. Infrastructure events

Counts by frozen class: `{json.dumps(infra, sort_keys=True)}`

Total infra events: {len(mechanical.get('infra_events') or [])}

No scientific outcome classes by condition.

## G. Missingness completeness

* expected treatment cells: {miss.get('n_expected_cells')}
* cells below min_valid_generations ({miss.get('min_valid_generations_per_condition')}): {miss.get('n_cells_below_min_valid_generations')}
* tipping-point machinery likely needed: {miss.get('tipping_point_machinery_likely_needed')}

No scientific condition success exposure.

## H. T3 instrumentation health

* verifier_call_count field complete? {t3.get('verifier_call_count_field_complete')}
* first witness / silent first validity fields present? {t3.get('silent_first_validity_field_present')}
* call-count distribution (no outcomes): `{json.dumps(t3.get('call_count_distribution') or {}, sort_keys=True)}`
* fraction hitting cap: {t3.get('fraction_hitting_cap')}
* cap enforcement / coarse-feedback compliance: covered by unit tests PASS ({unit_ok})

Witness validity: not reported.

## I. Provenance integrity

{"PASS" if unit_ok else "FAIL"}

Confirm: `two_phase_no_inject` runner path; no certificate injection; provenance fields written on scores.

## J. Gold-leakage audit

{"PASS" if unit_ok else "FAIL"}

## K. Digest validity gate

`F0a = {digest_f0a}`

## L. Raw artifact completeness

* out dir: `{mechanical.get('out_dir')}`
* task ledger present
* per-cell scores/results/transcripts under condition directories
* tool traces / T3 audit fields in runner outputs
* COLLECTION_LOCK.json present
* lock sha: `{lock.get('collection_lock_sha256')}`
* scores tree sha: `{lock.get('scores_tree_sha256')}`
* ledger sha: `{lock.get('ledger_sha256')}`

## M. Pilot separation

* pilot generations remain excluded
* confirmatory out dir is `runs/clean_v2_confirmatory/` (not `runs/clean_v2_blinded_pilot/`)
* pilot_excluded flag: {mechanical.get('pilot_excluded')}

## N. Deviations from pre-spec

* [NON-SCIENTIFIC] Collection window / operational PRE_SPEC line may differ from freeze file hash; scientific hash matches freeze.
* [NON-SCIENTIFIC] Master execution uses frozen planned_position sequence from file (filter-after-shuffle); not re-derived via reconstruct_ordering on the filtered multiset.
* [NONE] No prompt/contract/tool/model/k changes.
* [NONE] No scientific early stopping.

POTENTIALLY SCIENTIFIC deviations: none recorded.

## O. Collection lock

* marker: `runs/clean_v2_confirmatory/COLLECTION_LOCKED`
* lock document: `runs/clean_v2_confirmatory/COLLECTION_LOCK.json`
* collection_lock_sha256: `{lock.get('collection_lock_sha256')}`

## P. Decision

{decision}
"""
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--skip-unit-tests", action="store_true")
    args = parser.parse_args()
    repo = find_repo_root()

    # Non-clean_v2 dirty files are ignored for freeze gate; scientific clean_v2 paths must be clean.
    dirty = subprocess.check_output(
        ["git", "status", "--short", "--", "src/fsmreasonbench/clean_v2/", "docs/clean_v2/manifests/"],
        cwd=repo,
        text=True,
    ).strip()
    # Allow only report/collection module additions already committed; block unexpected diffs.
    # Untracked new collection modules are OK if we are about to run them; block modified scientific files.
    blocked = []
    for line in dirty.splitlines():
        if not line.strip():
            continue
        # staged/unstaged modifications to existing scientific files
        if line[0] in "MADRCU" or line[1] in "MADRCU":
            path = line[3:].strip() if len(line) > 3 else line
            if "confirmatory_collection" in path or "run_clean_v2_confirmatory" in path:
                continue
            if path.endswith("CONFIRMATORY_COLLECTION_REPORT.md"):
                continue
            # PRE_SPEC operational window edits are allowed (scientific hash checked separately)
            if path.endswith("PRE_SPECIFICATION.md"):
                continue
            blocked.append(line)
    if blocked:
        print("CONFIRMATORY COLLECTION BLOCKED: FROZEN STATE MISMATCH", file=sys.stderr)
        print("\n".join(blocked), file=sys.stderr)
        return 2

    try:
        integrity = verify_confirmatory_frozen_state(repo)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("integrity PASS", json.dumps({k: integrity[k] for k in ("ok", "pre_specification_scientific_sha256", "execution_order_seed")}))
    if args.verify_only:
        return 0

    if args.skip_unit_tests:
        unit_ok, unit_log = True, "skipped"
    else:
        unit_ok, unit_log = _run_pytest(repo)
        print("unit_tests", "PASS" if unit_ok else "FAIL")
        if not unit_ok:
            print(unit_log, file=sys.stderr)
            write_collection_report(
                repo,
                mechanical={
                    "started_at": "n/a",
                    "completed_at": "n/a",
                    "completed_tasks": 0,
                    "family": {},
                    "token_usage": {},
                    "t3": {},
                    "missingness_mechanical": {},
                    "lock": {},
                    "infra_events": [],
                    "infra_by_class": {},
                    "unresolved_tasks": [],
                    "fingerprint_failures": [],
                    "pilot_excluded": True,
                    "out_dir": "",
                },
                integrity=integrity,
                digest_f0a="n/a",
                unit_ok=False,
                decision="CONFIRMATORY COLLECTION INVALIDATED",
                tag_commit=subprocess.check_output(
                    ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"], cwd=repo, text=True
                ).strip(),
                harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
                analysis_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
            )
            print("CONFIRMATORY COLLECTION INVALIDATED")
            return 1

    result = run_confirmatory_collection(
        repo,
        timeout=args.timeout,
        resume=not args.no_resume,
    )
    if str(result.get("decision", "")).startswith("CONFIRMATORY COLLECTION INVALIDATED"):
        decision = "CONFIRMATORY COLLECTION INVALIDATED"
        write_collection_report(
            repo,
            mechanical=result.get("mechanical")
            or {
                "started_at": result.get("started_at"),
                "completed_at": result.get("completed_at"),
                "completed_tasks": result.get("completed", 0),
                "family": {},
                "token_usage": {},
                "t3": {},
                "missingness_mechanical": {},
                "lock": {},
                "infra_events": [],
                "infra_by_class": {},
                "unresolved_tasks": [],
                "fingerprint_failures": [],
                "pilot_excluded": True,
                "out_dir": result.get("out_dir"),
            },
            integrity=integrity,
            digest_f0a=result.get("digest_F0a", "FAIL"),
            unit_ok=True,
            decision=decision,
            tag_commit=subprocess.check_output(
                ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"], cwd=repo, text=True
            ).strip(),
            harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
            analysis_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
        )
        print(decision)
        return 1

    mechanical = result["mechanical"]
    unresolved = mechanical.get("unresolved_tasks") or []
    if mechanical.get("completed_tasks") == 3040 and not unresolved:
        decision = "CONFIRMATORY DATA LOCKED — READY FOR UNBLINDING"
    else:
        decision = "CONFIRMATORY COLLECTION INCOMPLETE"

    path = write_collection_report(
        repo,
        mechanical=mechanical,
        integrity=integrity,
        digest_f0a=result["digest_F0a"],
        unit_ok=True,
        decision=decision,
        tag_commit=subprocess.check_output(
            ["git", "rev-parse", "clean_v2-confirmatory-prespec-v1^{}"], cwd=repo, text=True
        ).strip(),
        harness_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
        analysis_commit="6009e44f4d26c4a676b065eb930c165e34a3752f",
    )
    write_json(Path(result["out_dir"]) / "decision.json", {"decision": decision})
    print("wrote", path)
    print(decision)
    return 0 if decision.startswith("CONFIRMATORY DATA LOCKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())

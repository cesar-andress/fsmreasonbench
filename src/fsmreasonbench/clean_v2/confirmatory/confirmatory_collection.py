"""Frozen confirmatory collection executor (blinded to scientific outcomes).

Executes ONLY docs/clean_v2/manifests/manifest_confirmatory_master.json.
Never runs scientific RQ analysis. Excludes pilot generations.
"""

from __future__ import annotations

import hashlib
import json
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fsmreasonbench.clean_v2.confirmatory.blinded_pilot import (
    EXPECTED_PRE_SPEC_SHA256,
    InstrumentedProvider,
    PINNED_MODELS,
    _condition_from_task,
    _exception_to_missingness_fields,
    _pre_spec_scientific_sha256,
    _sha256_file,
)
from fsmreasonbench.clean_v2.confirmatory.constants import (
    CLAUDE_MODEL,
    COHORT_ITEMS_RELPATH,
    EXECUTION_ORDER_SEED,
    GPT_MODEL,
    MAX_RERUNS,
    MAX_VERIFIER_CALLS,
    MIN_VALID_GENERATIONS_PER_CONDITION,
)
from fsmreasonbench.clean_v2.confirmatory.manifests import build_condition_catalog, provider_for_model
from fsmreasonbench.clean_v2.confirmatory.missingness import classify_generation_attempt
from fsmreasonbench.clean_v2.confirmatory.scheduler import fingerprint_task_list
from fsmreasonbench.clean_v2.fingerprint import fingerprint_condition
from fsmreasonbench.clean_v2.runner import run_clean_item
from fsmreasonbench.clean_v2.artifacts import utc_timestamp, write_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl

MASTER_RELPATH = "docs/clean_v2/manifests/manifest_confirmatory_master.json"
EXPECTED_MASTER_FILE_SHA256 = "cdfcbe488685cf98099de3cc6cd39d8edd24ae3d6a2c5d2adaa4e2ff58e2f848"
EXPECTED_MANIFEST_FILE_SHA256 = {
    "RQ1": "5159299ddaac2b76bd82e5a2f774aa4ba1f542e8758f1bb71ea99597712aefd1",
    "RQ2": "b3a60854538eeb05caffe06ec054bb349f8f807dba0280f8602a658d418f7de3",
    "RQ3": "32f7216d00d7bc447b26ed6f0e8505c5102711eea84c449a85b445956213b53c",
    "DIGEST": "6753b79cd8b039d4866ebb6cc455181aa9024db336d7ac40adc6819865fe8942",
    "CONFIRMATORY_MASTER": EXPECTED_MASTER_FILE_SHA256,
}
EXPECTED_COUNTS = {
    "RQ1": 1000,
    "RQ2": 1020,
    "RQ3": 1530,
    "DIGEST": 510,
    "CONFIRMATORY_MASTER": 3040,
}
PILOT_OUT_DIRNAME = "clean_v2_blinded_pilot"
CONFIRMATORY_OUT_DIRNAME = "clean_v2_confirmatory"


def verify_confirmatory_frozen_state(repo_root: Path) -> dict[str, Any]:
    """Verify manifests + scientific PRE_SPEC; raise on mismatch."""
    errors: list[str] = []
    manifest_dir = repo_root / "docs/clean_v2/manifests"
    hashes: dict[str, str] = {}
    for name, expected in EXPECTED_MANIFEST_FILE_SHA256.items():
        fname = (
            "manifest_confirmatory_master.json"
            if name == "CONFIRMATORY_MASTER"
            else f"manifest_{name.lower()}.json"
        )
        path = manifest_dir / fname
        h = _sha256_file(path)
        hashes[name] = h
        if h != expected:
            errors.append(f"{name} file sha mismatch: {h}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("n_tasks") != EXPECTED_COUNTS[name]:
            errors.append(f"{name} n_tasks={data.get('n_tasks')} expected {EXPECTED_COUNTS[name]}")
        if name == "CONFIRMATORY_MASTER":
            if data.get("execution_order_seed") != EXECUTION_ORDER_SEED:
                errors.append("master execution_order_seed mismatch")
            if fingerprint_task_list(data["tasks"]) != data.get("task_list_fingerprint"):
                errors.append("master task_list_fingerprint recompute failed")
            if tuple(data.get("models") or []) != PINNED_MODELS:
                errors.append(f"models mismatch: {data.get('models')}")
            if data.get("max_verifier_calls") != MAX_VERIFIER_CALLS:
                errors.append("max_verifier_calls mismatch")
            if sorted({t["repetition_index"] for t in data["tasks"]}) != [1, 2, 3, 4, 5]:
                errors.append("confirmatory k must be 1..5")
            positions = [int(t["planned_position"]) for t in data["tasks"]]
            if sorted(positions) != list(range(1, 3041)):
                errors.append("master planned_position not contiguous 1..3040")
            live = {
                c["condition_id"]: c["condition_fingerprint"]
                for c in build_condition_catalog(data["cohort_fingerprint"])
            }
            for c in data["condition_catalog"]:
                if live.get(c["condition_id"]) != c["condition_fingerprint"]:
                    errors.append(f"catalog fingerprint drift: {c['condition_id']}")
            catalog = {c["condition_id"]: c for c in data["condition_catalog"]}
            for t in data["tasks"]:
                if t.get("condition_fingerprint") != catalog[t["condition_id"]]["condition_fingerprint"]:
                    errors.append(
                        f"task fingerprint mismatch at position {t['planned_position']}"
                    )
                    break

    pre_path = repo_root / "docs/clean_v2/PRE_SPECIFICATION.md"
    pre_cur, pre_sci = _pre_spec_scientific_sha256(pre_path)
    if pre_sci != EXPECTED_PRE_SPEC_SHA256:
        errors.append(f"PRE_SPEC scientific sha mismatch: {pre_sci}")

    report = {
        "ok": not errors,
        "errors": errors,
        "manifest_file_sha256": hashes,
        "pre_specification_sha256": pre_cur,
        "pre_specification_scientific_sha256": pre_sci,
        "execution_order_seed": EXECUTION_ORDER_SEED,
        "models": list(PINNED_MODELS),
        "note": (
            "Master planned_position sequence is authoritative from the frozen file; "
            "reconstruct_ordering on the filtered multiset is not used for execution."
        ),
    }
    if errors:
        raise RuntimeError(
            "CONFIRMATORY COLLECTION BLOCKED: FROZEN STATE MISMATCH: " + "; ".join(errors)
        )
    return report


def _task_key(row: dict[str, Any]) -> tuple:
    return (
        row["item_id"],
        row["model"],
        row["condition_id"],
        int(row["repetition_index"]),
    )


def _family_completion_from_manifests(
    repo_root: Path,
    ledger_path: Path,
) -> dict[str, dict[str, int]]:
    """Mechanical planned vs completed per frozen family manifest (no outcomes)."""
    completed_keys: set[tuple] = set()
    unresolved_keys: set[tuple] = set()
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = _task_key(row)
            st = str(row.get("status", ""))
            if st.startswith("completed"):
                completed_keys.add(key)
            elif "unresolved" in st:
                unresolved_keys.add(key)

    out: dict[str, dict[str, int]] = {}
    for fam, fname in (
        ("RQ1", "manifest_rq1.json"),
        ("RQ2", "manifest_rq2.json"),
        ("RQ3", "manifest_rq3.json"),
        ("DIGEST", "manifest_digest.json"),
    ):
        tasks = json.loads((repo_root / "docs/clean_v2/manifests" / fname).read_text())["tasks"]
        planned = len(tasks)
        keys = {_task_key(t) for t in tasks}
        out[fam] = {
            "planned": planned,
            "mechanically_completed": len(keys & completed_keys),
            "unresolved_infrastructure": len(keys & unresolved_keys),
        }
    return out


def _load_finished_positions(ledger_path: Path) -> set[int]:
    """Positions already attempted to terminal status (completed or unresolved after max_reruns)."""
    done: set[int] = set()
    if not ledger_path.exists():
        return done
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        st = str(row.get("status", ""))
        if st.startswith("completed") or "unresolved" in st:
            done.add(int(row["planned_position"]))
    return done


def _load_completed_positions(ledger_path: Path) -> set[int]:
    """Backward-compatible alias: finished positions (do not re-dispatch)."""
    return _load_finished_positions(ledger_path)


def run_confirmatory_collection(
    repo_root: Path,
    *,
    out_root: Path | None = None,
    timeout: float = 300.0,
    resume: bool = True,
) -> dict[str, Any]:
    integrity = verify_confirmatory_frozen_state(repo_root)
    master = json.loads((repo_root / MASTER_RELPATH).read_text(encoding="utf-8"))
    start_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = out_root or (repo_root / "runs" / CONFIRMATORY_OUT_DIRNAME)
    out.mkdir(parents=True, exist_ok=True)
    # Hard separation from pilot.
    pilot_dir = repo_root / "runs" / PILOT_OUT_DIRNAME
    write_json(
        out / "collection_window.json",
        {
            "confirmatory_collection_started_at": start_ts,
            "confirmatory_collection_completed_at": None,
            "execution_order_seed": EXECUTION_ORDER_SEED,
            "pilot_dir_excluded": str(pilot_dir),
            "pilot_excluded": True,
        },
    )
    write_json(out / "integrity.json", integrity)

    items = load_items_jsonl(repo_root / COHORT_ITEMS_RELPATH)
    items_by_id = {item.item_id: item for item in items}
    providers = {
        model: InstrumentedProvider(provider_for_model(model), model, timeout=timeout)
        for model in PINNED_MODELS
    }
    wiring = {
        "anthropic": {
            "exact_model": CLAUDE_MODEL,
            "cache_policy": providers[CLAUDE_MODEL].cache_policy,
            "timeout_s": timeout,
            "max_reruns": MAX_RERUNS,
        },
        "openai": {
            "exact_model": GPT_MODEL,
            "cache_policy": providers[GPT_MODEL].cache_policy,
            "startup": getattr(providers[GPT_MODEL], "startup", None),
            "timeout_s": timeout,
            "max_reruns": MAX_RERUNS,
        },
    }
    write_json(out / "provider_wiring.json", wiring)

    tasks = sorted(master["tasks"], key=lambda t: int(t["planned_position"]))
    catalog_by_id = {c["condition_id"]: c for c in master["condition_catalog"]}
    cohort_fp = master["cohort_fingerprint"]
    ledger_path = out / "task_ledger.jsonl"
    completed_positions = _load_completed_positions(ledger_path) if resume else set()
    if completed_positions:
        print(
            f"[confirmatory] resume: {len(completed_positions)} positions already completed",
            flush=True,
        )

    infra_events: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    completed = 0
    digest_any_valid = False
    t3_call_counts: list[int] = []
    t3_cap_hits = 0
    t3_n = 0
    t3_fields_complete = 0
    fingerprint_failures: list[str] = []
    # Blinded cell completeness: item|model|condition -> attempted count (no outcomes).
    cell_attempted: dict[str, int] = defaultdict(int)

    for task in tasks:
        position = int(task["planned_position"])
        if position in completed_positions:
            completed += 1
            continue

        item = items_by_id.get(task["item_id"])
        if item is None:
            raise RuntimeError(f"missing item {task['item_id']} at pos={position}")
        condition = _condition_from_task(task)
        catalog_fp = catalog_by_id[task["condition_id"]]["condition_fingerprint"]
        if task["condition_fingerprint"] != catalog_fp:
            msg = f"pos={position} task/catalog fingerprint mismatch"
            fingerprint_failures.append(msg)
            write_json(
                out / "FINGERPRINT_DRIFT.json",
                {"error": msg, "at": utc_timestamp()},
            )
            raise RuntimeError(f"CONFIRMATORY COLLECTION INVALIDATED: FINGERPRINT DRIFT: {msg}")

        cell_fp = fingerprint_condition(condition, item_manifest_fingerprint=cohort_fp)
        provider = providers[task["model"]]
        attempt_logs: list[dict[str, Any]] = []
        success_score: dict[str, Any] | None = None
        final_status = "unresolved"

        for attempt_idx in range(0, MAX_RERUNS + 1):
            attempt_start = utc_timestamp()
            provider.last_meta = {}
            try:
                score = run_clean_item(
                    item,
                    condition,
                    provider.generate,
                    item_manifest_fingerprint=cohort_fp,
                    out_dir=out,
                    overwrite=(attempt_idx > 0),
                )
                classif = classify_generation_attempt(
                    {
                        "provider_error_type": None,
                        "http_status": 200,
                        "harness_exception": None,
                        "finish_reason": provider.last_meta.get("finish_reason"),
                        "parse_errors": score.get("parse_errors") or [],
                        "safety_refusal": False,
                        "empty_completion": False,
                        "tool_call_invalid": False,
                        "max_tokens_reached": provider.last_meta.get("finish_reason")
                        in {"length", "max_tokens"},
                        "malformed_model_output": bool(score.get("parse_errors")),
                    }
                )
                if classif.get("missingness_class") is None:
                    classif = {
                        "missingness_class": None,
                        "reason_code": "completed",
                        "enters_n_attempted": True,
                        "rerun_same_repetition": False,
                        "is_infrastructure": False,
                    }
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": classif,
                        "provider_meta": {
                            k: provider.last_meta.get(k)
                            for k in (
                                "provider_request_id",
                                "cache_status",
                                "usage",
                                "finish_reason",
                                "ok",
                            )
                        },
                        "run_id": score.get("run_id"),
                    }
                )
                success_score = score
                final_status = "completed"
                break
            except FileExistsError:
                final_status = "completed_existing"
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": {
                            "reason_code": "already_present",
                            "is_infrastructure": False,
                            "enters_n_attempted": True,
                        },
                        "provider_meta": {},
                    }
                )
                break
            except Exception as exc:
                fields = _exception_to_missingness_fields(exc, provider.last_meta)
                classif = classify_generation_attempt(fields)
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": classif,
                        "provider_meta": provider.last_meta,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:500],
                        "traceback": traceback.format_exc()[-1500:],
                    }
                )
                if classif.get("is_infrastructure") and classif.get("rerun_same_repetition"):
                    infra_events.append(
                        {
                            "planned_position": position,
                            "reason_code": classif.get("reason_code"),
                            "attempt_index": attempt_idx,
                            "provider": condition.provider,
                        }
                    )
                    if attempt_idx < MAX_RERUNS:
                        time.sleep(min(2**attempt_idx, 30))
                        continue
                    final_status = "unresolved_infrastructure"
                    break
                final_status = "completed_with_experimental_failure"
                success_score = {
                    "item_id": item.item_id,
                    "model": task["model"],
                    "contract": task["contract"],
                    "witness_valid": None,
                }
                break

        # Mechanical-only accumulators (no scientific rates).
        if success_score is not None and final_status.startswith("completed"):
            if classif_enters_attempted(attempt_logs):
                cell_key = f"{task['item_id']}|{task['model']}|{task['condition_id']}"
                cell_attempted[cell_key] += 1
            # F0a: digest accepted witness stops collection (validity only).
            if task["contract"] == "digest_control" and success_score.get("witness_valid") is True:
                digest_any_valid = True
            if task["tool_palette"] == "T3_VERIFY":
                t3_n += 1
                if "verifier_call_count" in success_score and "witness_valid_first" in success_score:
                    t3_fields_complete += 1
                t3_call_counts.append(int(success_score.get("verifier_call_count") or 0))
                if success_score.get("verifier_call_cap_reached"):
                    t3_cap_hits += 1

        if final_status.startswith("completed"):
            completed += 1
        else:
            unresolved.append(
                {
                    "planned_position": position,
                    "status": final_status,
                    "provider": condition.provider,
                    "anonymized_cell": f"cell_{hashlib.sha256((task['condition_id']+'|'+task['model']).encode()).hexdigest()[:8]}",
                }
            )

        ledger_row = {
            "planned_position": position,
            "dispatch_position": position,  # serial execution preserves planned order
            "execution_order_seed": EXECUTION_ORDER_SEED,
            "item_id": task["item_id"],
            "model": task["model"],
            "provider": condition.provider,
            "condition_id": task["condition_id"],
            "condition_fingerprint": task["condition_fingerprint"],
            "cell_fingerprint": cell_fp,
            "repetition_index": task["repetition_index"],
            "status": final_status,
            "attempt_count": len(attempt_logs),
            "attempts": attempt_logs,
            "actual_start_timestamp": attempt_logs[0]["started_at"] if attempt_logs else None,
            "actual_completion_timestamp": attempt_logs[-1]["completed_at"] if attempt_logs else None,
            "provider_request_ids": [
                (a.get("provider_meta") or {}).get("provider_request_id") for a in attempt_logs
            ],
            "cache_statuses": [
                (a.get("provider_meta") or {}).get("cache_status") for a in attempt_logs
            ],
            # No scientific outcome fields in ledger.
        }
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ledger_row, sort_keys=True) + "\n")

        print(
            f"[confirmatory] pos={position}/3040 status={final_status} "
            f"provider={condition.provider} attempts={len(attempt_logs)}",
            flush=True,
        )

        if digest_any_valid:
            end_ts = utc_timestamp()
            write_json(
                out / "F0a_TRIGGERED.json",
                {"gate": "F0a", "triggered": True, "at": end_ts, "stopped_at_position": position},
            )
            return {
                "decision": "CONFIRMATORY COLLECTION INVALIDATED: F0a",
                "integrity": integrity,
                "started_at": start_ts,
                "completed_at": end_ts,
                "completed": completed,
                "out_dir": str(out),
            }

        # Periodic mechanical checkpoint (no science).
        if position % 50 == 0:
            write_json(
                out / "progress_mechanical.json",
                {
                    "planned_position": position,
                    "completed": completed,
                    "unresolved": len(unresolved),
                    "infra_events": len(infra_events),
                    "at": utc_timestamp(),
                },
            )

    end_ts = utc_timestamp()
    family = _family_completion_from_manifests(repo_root, ledger_path)

    # Blinded missingness: cells below min_valid after collection.
    expected_cells = {
        f"{t['item_id']}|{t['model']}|{t['condition_id']}" for t in master["tasks"]
    }
    cell_attempted_full: dict[str, int] = defaultdict(int)
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if not str(row.get("status", "")).startswith("completed"):
                continue
            attempts = row.get("attempts") or []
            enters = True
            if attempts:
                last = attempts[-1].get("classification") or {}
                if last.get("is_infrastructure"):
                    enters = False
                elif last.get("enters_n_attempted") is False:
                    enters = False
            if enters:
                key = f"{row['item_id']}|{row['model']}|{row['condition_id']}"
                cell_attempted_full[key] += 1
    missing_or_low = sum(
        1
        for key in expected_cells
        if cell_attempted_full.get(key, 0) < MIN_VALID_GENERATIONS_PER_CONDITION
    )
    tipping_needed = (missing_or_low / max(len(expected_cells), 1)) > 0.10

    def usage_summary(model: str) -> dict[str, Any]:
        p = providers[model]
        in_tok = out_tok = 0
        for c in p.calls:
            u = c.get("usage") or {}
            in_tok += int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
            out_tok += int(u.get("output_tokens") or u.get("completion_tokens") or 0)
        return {
            "requests": len(p.calls),
            "ok_requests": sum(1 for c in p.calls if c.get("ok")),
            "failed_requests": sum(1 for c in p.calls if not c.get("ok")),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }

    # Dataset lock hash over ledger + scores tree.
    lock_payload = {
        "master_sha256": EXPECTED_MASTER_FILE_SHA256,
        "ledger_sha256": _sha256_file(ledger_path) if ledger_path.exists() else None,
        "n_ledger_rows": sum(1 for _ in ledger_path.open()) if ledger_path.exists() else 0,
        "started_at": start_ts,
        "completed_at": end_ts,
    }
    score_files = sorted(out.glob("**/scores.jsonl"))
    h = hashlib.sha256()
    for sf in score_files:
        h.update(str(sf.relative_to(out)).encode())
        h.update(sf.read_bytes())
    lock_payload["scores_tree_sha256"] = h.hexdigest()
    lock_payload["collection_lock_sha256"] = hashlib.sha256(
        json.dumps(lock_payload, sort_keys=True).encode()
    ).hexdigest()
    write_json(out / "COLLECTION_LOCK.json", lock_payload)
    (out / "COLLECTION_LOCKED").write_text(
        f"locked_at={end_ts}\nlock={lock_payload['collection_lock_sha256']}\n",
        encoding="utf-8",
    )

    write_json(
        out / "collection_window.json",
        {
            "confirmatory_collection_started_at": start_ts,
            "confirmatory_collection_completed_at": end_ts,
            "execution_order_seed": EXECUTION_ORDER_SEED,
            "pilot_dir_excluded": str(pilot_dir),
            "pilot_excluded": True,
        },
    )

    ledger_completed_unique = sum(
        1
        for line in ledger_path.read_text().splitlines()
        if str(json.loads(line).get("status", "")).startswith("completed")
    )

    # Recompute T3 mechanical field completeness from scores without outcome rates.
    t3_from_disk = _t3_mechanical_from_scores(out)

    mechanical = {
        "integrity": integrity,
        "started_at": start_ts,
        "completed_at": end_ts,
        "planned_tasks": 3040,
        "completed_tasks": ledger_completed_unique,
        "unresolved_tasks": unresolved,
        "infra_events": infra_events,
        "infra_by_class": dict(Counter(e["reason_code"] for e in infra_events)),
        "family": family,
        "token_usage": {
            "anthropic": usage_summary(CLAUDE_MODEL),
            "openai": usage_summary(GPT_MODEL),
        },
        "t3": t3_from_disk,
        "missingness_mechanical": {
            "n_expected_cells": len(expected_cells),
            "n_cells_below_min_valid_generations": missing_or_low,
            "min_valid_generations_per_condition": MIN_VALID_GENERATIONS_PER_CONDITION,
            "tipping_point_machinery_likely_needed": tipping_needed,
        },
        "digest_F0a": "FAIL" if digest_any_valid else "PASS",
        "fingerprint_failures": fingerprint_failures,
        "lock": lock_payload,
        "wiring": wiring,
        "pilot_excluded": True,
        "out_dir": str(out),
    }
    write_json(out / "mechanical_summary.json", mechanical)
    return {
        "decision": None,
        "mechanical": mechanical,
        "integrity": integrity,
        "out_dir": str(out),
        "digest_F0a": mechanical["digest_F0a"],
        "started_at": start_ts,
        "completed_at": end_ts,
    }


def _t3_mechanical_from_scores(out: Path) -> dict[str, Any]:
    """T3 instrumentation health only (no witness validity rates)."""
    counts: list[int] = []
    cap_hits = 0
    fields_ok = 0
    n = 0
    for sf in out.glob("**/scores.jsonl"):
        if "T3_VERIFY" not in str(sf):
            continue
        for line in sf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("tool_palette") != "T3_VERIFY":
                continue
            n += 1
            if "verifier_call_count" in row and "witness_valid_first" in row.keys():
                fields_ok += 1
            counts.append(int(row.get("verifier_call_count") or 0))
            if row.get("verifier_call_cap_reached"):
                cap_hits += 1
    return {
        "n_tasks_observed": n,
        "fields_complete": fields_ok,
        "call_count_distribution": dict(Counter(counts)),
        "fraction_hitting_cap": (cap_hits / n) if n else None,
        "verifier_call_count_field_complete": fields_ok == n and n > 0,
        "first_witness_field_present": fields_ok == n and n > 0,
        "silent_first_validity_field_present": fields_ok == n and n > 0,
    }


def classif_enters_attempted(attempt_logs: list[dict[str, Any]]) -> bool:
    if not attempt_logs:
        return False
    last = attempt_logs[-1].get("classification") or {}
    if last.get("is_infrastructure"):
        return False
    return last.get("enters_n_attempted", True) is not False

"""Frozen confirmatory experiment manifests (no provider calls)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.clean_v2.condition import (
    ConditionSpec,
    ContractId,
    FormatAssistId,
    OracleInfoId,
    OrchestrationMode,
    ToolPaletteId,
)
from fsmreasonbench.clean_v2.confirmatory.caching_policy import caching_policy_for_provider
from fsmreasonbench.clean_v2.confirmatory.constants import (
    CLAUDE_MODEL,
    COHORT_ITEMS_RELPATH,
    EXECUTION_ORDER_SEED,
    GPT_MODEL,
    K_REPETITIONS,
    MAX_TOKENS,
    MAX_VERIFIER_CALLS,
    SPEC_VERSION,
    TEMPERATURE,
)
from fsmreasonbench.clean_v2.confirmatory.provenance_audit import run_provenance_audit
from fsmreasonbench.clean_v2.confirmatory.scheduler import (
    build_cartesian_tasks,
    fingerprint_task_list,
    interleaving_audit,
)
from fsmreasonbench.clean_v2.fingerprint import fingerprint_condition
from fsmreasonbench.evaluator.jsonl import load_items_jsonl

CONDITION_DEFS = {
    "bisimulation_T0": {
        "contract": ContractId.BISIMULATION,
        "tool_palette": ToolPaletteId.T0_NONE,
        "rq_families": ["RQ3", "RQ1"],
    },
    "bisimulation_T1": {
        "contract": ContractId.BISIMULATION,
        "tool_palette": ToolPaletteId.T1_STEP,
        "rq_families": ["RQ1", "RQ2", "RQ3"],
    },
    "bisimulation_T3": {
        "contract": ContractId.BISIMULATION,
        "tool_palette": ToolPaletteId.T3_VERIFY,
        "rq_families": ["RQ3"],
    },
    "minimized_dfa_T1": {
        "contract": ContractId.MINIMIZED_DFA,
        "tool_palette": ToolPaletteId.T1_STEP,
        "rq_families": ["RQ2"],
    },
    "digest_control_T1": {
        "contract": ContractId.DIGEST_CONTROL,
        "tool_palette": ToolPaletteId.T1_STEP,
        "rq_families": ["DIGEST"],
    },
}


def _spec_for(model: str, provider: str, cond_id: str, rep: int) -> ConditionSpec:
    d = CONDITION_DEFS[cond_id]
    return ConditionSpec(
        contract=d["contract"],
        tool_palette=d["tool_palette"],
        oracle_info=OracleInfoId.NONE,
        format_assist=FormatAssistId.OFF,
        model=model,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        repetition_index=rep,
        orchestration_mode=OrchestrationMode.TWO_PHASE_NO_INJECT,
        provider=provider,
        tool_call_budget=64 if d["tool_palette"] != ToolPaletteId.T3_VERIFY else MAX_VERIFIER_CALLS,
    )


def provider_for_model(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt"):
        return "openai"
    return "unknown"


def build_condition_catalog(item_manifest_fingerprint: str) -> list[dict[str, Any]]:
    catalog = []
    for cond_id, d in CONDITION_DEFS.items():
        # Fingerprint uses a representative model/rep; condition factors matter.
        spec = _spec_for(CLAUDE_MODEL, "anthropic", cond_id, 1)
        catalog.append(
            {
                "condition_id": cond_id,
                "contract": d["contract"].value,
                "tool_palette": d["tool_palette"].value,
                "oracle_info": "none",
                "format_assist": "off",
                "rq_families": d["rq_families"],
                "condition_fingerprint": fingerprint_condition(
                    spec, item_manifest_fingerprint=item_manifest_fingerprint
                ),
                "rq_family": ",".join(d["rq_families"]),
            }
        )
    return catalog


def generate_manifests(repo_root: Path, out_dir: Path | None = None) -> dict[str, Any]:
    out = out_dir or (repo_root / "docs/clean_v2/manifests")
    out.mkdir(parents=True, exist_ok=True)
    audit = run_provenance_audit(repo_root)
    items = load_items_jsonl(repo_root / COHORT_ITEMS_RELPATH)
    # Item manifest fingerprint from cohort.
    cohort_fp = audit["cohort_fingerprint"]
    eq_ids = audit["equivalent_ids"]
    dist_ids = audit["distinguishing_ids"]
    all_ids = sorted(eq_ids + dist_ids)
    pilot_ids = audit["pilot_item_selection"]["pilot_item_ids"]

    catalog = build_condition_catalog(cohort_fp)
    catalog_by_id = {c["condition_id"]: c for c in catalog}
    models = [CLAUDE_MODEL, GPT_MODEL]
    reps = list(range(1, K_REPETITIONS + 1))

    def tasks_for(item_ids, condition_ids, rq_name, k=None):
        conds = []
        for cid in condition_ids:
            row = dict(catalog_by_id[cid])
            row["rq_family"] = rq_name
            conds.append(row)
        return build_cartesian_tasks(
            item_ids=item_ids,
            models=models,
            conditions=conds,
            repetitions=list(range(1, (k or K_REPETITIONS) + 1)),
            execution_order_seed=EXECUTION_ORDER_SEED,
        )

    manifests = {
        "RQ1": {
            "description": "Descriptive composition on full 100-item universe; bisimulation T1.",
            "tasks": tasks_for(all_ids, ["bisimulation_T1"], "RQ1"),
        },
        "RQ2": {
            "description": "bisimulation vs minimized_dfa @ T1 on 51 equivalence items.",
            "tasks": tasks_for(eq_ids, ["bisimulation_T1", "minimized_dfa_T1"], "RQ2"),
        },
        "RQ3": {
            "description": "bisimulation T0/T1/T3 on 51 equivalence items.",
            "tasks": tasks_for(eq_ids, ["bisimulation_T0", "bisimulation_T1", "bisimulation_T3"], "RQ3"),
        },
        "DIGEST": {
            "description": "digest_control validity gate F0a @ T1 on 51 equivalence items.",
            "tasks": tasks_for(eq_ids, ["digest_control_T1"], "DIGEST"),
        },
        "PILOT": {
            "description": "Blinded engineering pilot; k=2; excluded from confirmatory analysis.",
            "tasks": tasks_for(
                pilot_ids,
                [
                    "bisimulation_T1",
                    "minimized_dfa_T1",
                    "bisimulation_T0",
                    "bisimulation_T3",
                    "digest_control_T1",
                ],
                "PILOT",
                k=2,
            ),
        },
    }

    # Deduplicate confirmatory union for a master schedule (RQ1∪RQ2∪RQ3∪DIGEST).
    # Shared cells (e.g. bisimulation_T1 on eq) appear once.
    seen = set()
    union_raw = []
    for name in ("RQ1", "RQ2", "RQ3", "DIGEST"):
        for t in manifests[name]["tasks"]:
            key = (t["item_id"], t["model"], t["condition_id"], t["repetition_index"])
            if key in seen:
                continue
            seen.add(key)
            union_raw.append(
                {k: t[k] for k in t if k not in {"planned_position", "execution_order_seed",
                                                  "actual_start_timestamp", "actual_completion_timestamp",
                                                  "provider_request_id", "cache_status"}}
            )
    master = build_cartesian_tasks(
        item_ids=sorted({t["item_id"] for t in union_raw}),
        models=models,
        conditions=[
            {**catalog_by_id[cid], "rq_family": "CONFIRMATORY"}
            for cid in sorted({t["condition_id"] for t in union_raw})
        ],
        repetitions=reps,
        execution_order_seed=EXECUTION_ORDER_SEED,
    )
    # Filter master to only keys present in union.
    union_keys = seen
    master = [
        t
        for t in master
        if (t["item_id"], t["model"], t["condition_id"], t["repetition_index"]) in union_keys
    ]
    # Re-number positions after filter while preserving relative shuffle order.
    for i, t in enumerate(master, start=1):
        t["planned_position"] = i

    meta = {
        "spec_version": SPEC_VERSION,
        "execution_order_seed": EXECUTION_ORDER_SEED,
        "k_repetitions": K_REPETITIONS,
        "max_verifier_calls": MAX_VERIFIER_CALLS,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "models": models,
        "caching_policies": {
            "anthropic": caching_policy_for_provider("anthropic"),
            "openai": caching_policy_for_provider("openai"),
        },
        "cohort_fingerprint": cohort_fp,
        "n_equivalent": len(eq_ids),
        "n_distinguishing": len(dist_ids),
        "condition_catalog": catalog,
        "provenance_decision": audit["decision"],
        "pilot_item_ids": pilot_ids,
    }

    written = {}
    for name, payload in manifests.items():
        doc = {
            **meta,
            "manifest_name": name,
            "description": payload["description"],
            "n_tasks": len(payload["tasks"]),
            "task_list_fingerprint": fingerprint_task_list(payload["tasks"]),
            "interleaving_audit": interleaving_audit(payload["tasks"]),
            "tasks": payload["tasks"],
        }
        path = out / f"manifest_{name.lower()}.json"
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = {"path": str(path.relative_to(repo_root)), "n_tasks": doc["n_tasks"],
                         "fingerprint": doc["task_list_fingerprint"]}

    master_doc = {
        **meta,
        "manifest_name": "CONFIRMATORY_MASTER",
        "description": "Deduplicated confirmatory schedule (RQ1∪RQ2∪RQ3∪DIGEST), interleaved.",
        "n_tasks": len(master),
        "task_list_fingerprint": fingerprint_task_list(master),
        "interleaving_audit": interleaving_audit(master),
        "tasks": master,
    }
    master_path = out / "manifest_confirmatory_master.json"
    master_path.write_text(json.dumps(master_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written["CONFIRMATORY_MASTER"] = {
        "path": str(master_path.relative_to(repo_root)),
        "n_tasks": master_doc["n_tasks"],
        "fingerprint": master_doc["task_list_fingerprint"],
    }

    index = {"spec_version": SPEC_VERSION, "manifests": written, "meta": {k: meta[k] for k in meta if k != "condition_catalog"}}
    (out / "INDEX.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "ITEM_IDS.json").write_text(
        json.dumps(
            {
                "equivalent_ids": eq_ids,
                "distinguishing_ids": dist_ids,
                "pilot_item_ids": pilot_ids,
                "all_ids": all_ids,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"out_dir": str(out), "written": written, "audit_decision": audit["decision"]}

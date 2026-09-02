"""End-to-end deterministic sentinel campaign for clean_v2."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fsmreasonbench.clean_v2.condition import (
    ConditionSpec,
    ContractId,
    FormatAssistId,
    OracleInfoId,
    ToolPaletteId,
)
from fsmreasonbench.clean_v2.fingerprint import assert_single_factor_diff, base_condition
from fsmreasonbench.clean_v2.metrics import summarize_attempt_records
from fsmreasonbench.clean_v2.runner import run_clean_item
from fsmreasonbench.clean_v2.sentinel.mock_provider import DeterministicMockProvider, build_generate_fn
from fsmreasonbench.clean_v2.artifacts import write_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.serialization import content_hash

__all__ = ["run_sentinel_campaign"]


def _pick_equivalence_items(items: list[BenchmarkItem], n: int = 3) -> list[BenchmarkItem]:
    eq = [item for item in items if item.family == "F1" and item.answer_key["verdict"] is True]
    if len(eq) < n:
        raise ValueError(f"need at least {n} equivalence items, found {len(eq)}")
    return eq[:n]


def run_sentinel_campaign(
    *,
    cohort_items_path: Path,
    out_root: Path,
    overwrite: bool = True,
) -> dict[str, Any]:
    """
    Execute a full mock campaign covering required sentinel scenarios.

    Guarantees: zero external model/API calls (DeterministicMockProvider only).
    """
    items = load_items_jsonl(cohort_items_path)
    eq_items = _pick_equivalence_items(items, n=3)
    item_manifest_fingerprint = content_hash(
        {"item_ids": [item.item_id for item in eq_items], "source": str(cohort_items_path)}
    )
    if out_root.exists() and overwrite:
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    items_by_id = {item.item_id: item for item in eq_items}
    provider = DeterministicMockProvider(items_by_id=items_by_id)
    # Script distinct modes onto the three items.
    provider.scripts[eq_items[0].item_id] = provider.script_for(eq_items[0].item_id)
    provider.scripts[eq_items[0].item_id].mode = "valid"
    provider.scripts[eq_items[1].item_id] = provider.script_for(eq_items[1].item_id)
    provider.scripts[eq_items[1].item_id].mode = "invalid_witness"
    provider.scripts[eq_items[2].item_id] = provider.script_for(eq_items[2].item_id)
    provider.scripts[eq_items[2].item_id].mode = "wrong_verdict"

    generate = build_generate_fn(provider)
    scores: list[dict[str, Any]] = []

    def run(condition: ConditionSpec, item: BenchmarkItem, mode: str | None = None) -> dict[str, Any]:
        if mode is not None:
            provider.script_for(item.item_id).mode = mode
            provider.script_for(item.item_id).call_count = 0
        return run_clean_item(
            item,
            condition,
            generate,
            item_manifest_fingerprint=item_manifest_fingerprint,
            out_dir=out_root,
            overwrite=overwrite,
        )

    # Core scenarios on item 0
    item0, item1, item2 = eq_items
    scores.append(run(base_condition(tool_palette=ToolPaletteId.T0_NONE, repetition_index=1), item0, "valid"))
    scores.append(run(base_condition(tool_palette=ToolPaletteId.T1_STEP, repetition_index=1), item0, "valid"))
    scores.append(
        run(
            base_condition(tool_palette=ToolPaletteId.T3_VERIFY, repetition_index=1),
            item0,
            "t3_reject_then_valid",
        )
    )
    scores.append(run(base_condition(repetition_index=1), item1, "invalid_witness"))
    scores.append(run(base_condition(repetition_index=1), item2, "wrong_verdict"))
    scores.append(run(base_condition(repetition_index=1), item0, "malformed"))

    # Oracle × format (tools fixed T1)
    for oracle in (OracleInfoId.NONE, OracleInfoId.GOLD_VERDICT):
        for fmt in (FormatAssistId.OFF, FormatAssistId.ON):
            scores.append(
                run(
                    base_condition(
                        tool_palette=ToolPaletteId.T1_STEP,
                        oracle_info=oracle,
                        format_assist=fmt,
                        repetition_index=1,
                    ),
                    item0,
                    "valid",
                )
            )

    # Contract switch
    scores.append(
        run(
            base_condition(contract=ContractId.MINIMIZED_DFA, tool_palette=ToolPaletteId.T1_STEP),
            item0,
            "valid",
        )
    )
    scores.append(
        run(
            base_condition(contract=ContractId.DIGEST_CONTROL, tool_palette=ToolPaletteId.T1_STEP),
            item0,
            "valid",
        )
    )

    # Repetitions 1..3 under fixed condition (rep_01 may replace earlier T1/none/off row)
    rep_scores = []
    for rep in (1, 2, 3):
        row = run(
            base_condition(
                tool_palette=ToolPaletteId.T1_STEP,
                repetition_index=rep,
                model="mock-deterministic-v1",
            ),
            item0,
            "valid",
        )
        rep_scores.append(row)
        scores.append(row)

    # Fingerprint proofs
    fingerprint_proofs = {
        "bisimulation_vs_minimized_dfa": assert_single_factor_diff(
            base_condition(contract=ContractId.BISIMULATION),
            base_condition(contract=ContractId.MINIMIZED_DFA),
            "contract",
            item_manifest_fingerprint=item_manifest_fingerprint,
        ),
        "T0_vs_T1": assert_single_factor_diff(
            base_condition(tool_palette=ToolPaletteId.T0_NONE),
            base_condition(tool_palette=ToolPaletteId.T1_STEP),
            "tool_palette",
            item_manifest_fingerprint=item_manifest_fingerprint,
        ),
        "T1_vs_T3": assert_single_factor_diff(
            base_condition(tool_palette=ToolPaletteId.T1_STEP),
            base_condition(tool_palette=ToolPaletteId.T3_VERIFY),
            "tool_palette",
            item_manifest_fingerprint=item_manifest_fingerprint,
        ),
        "oracle_none_vs_gold": assert_single_factor_diff(
            base_condition(oracle_info=OracleInfoId.NONE),
            base_condition(oracle_info=OracleInfoId.GOLD_VERDICT),
            "oracle_info",
            item_manifest_fingerprint=item_manifest_fingerprint,
        ),
        "format_off_vs_on": assert_single_factor_diff(
            base_condition(format_assist=FormatAssistId.OFF),
            base_condition(format_assist=FormatAssistId.ON),
            "format_assist",
            item_manifest_fingerprint=item_manifest_fingerprint,
        ),
    }
    # Strip bulky canonical strings from report payload
    fingerprint_proofs_compact = {
        key: {
            "difference_paths": value["difference_paths"],
            "unexpected_differences": value["unexpected_differences"],
            "ok": value["ok"],
            "fingerprint_a": value["fingerprint_a"],
            "fingerprint_b": value["fingerprint_b"],
        }
        for key, value in fingerprint_proofs.items()
    }

    campaign_summary = summarize_attempt_records(scores)
    payload = {
        "campaign": "clean_v2_sentinel",
        "external_model_calls": 0,
        "provider": "DeterministicMockProvider",
        "mock_generate_calls": len(provider.calls),
        "item_ids": [item.item_id for item in eq_items],
        "item_manifest_fingerprint": item_manifest_fingerprint,
        "n_scores": len(scores),
        "summary": campaign_summary,
        "repetition_run_ids": [row["run_id"] for row in rep_scores],
        "repetition_indices": [row["repetition_index"] for row in rep_scores],
        "fingerprint_proofs": fingerprint_proofs_compact,
        "out_root": str(out_root),
    }
    write_json(out_root / "sentinel_summary.json", payload)
    write_json(out_root / "sentinel_scores_rollup.json", {"scores": scores})
    return payload

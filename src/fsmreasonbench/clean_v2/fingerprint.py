"""Configuration fingerprinting and diff_experiment for clean_v2."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.condition import ConditionSpec, ContractId, FormatAssistId, OracleInfoId, ToolPaletteId
from fsmreasonbench.clean_v2.prompts import (
    contract_schema_block,
    format_assist_block,
    oracle_info_block,
    prompt_skeleton_text,
    tool_docs_for_palette,
)
from fsmreasonbench.clean_v2.tools.palettes import tool_definitions_for_palette
from fsmreasonbench.clean_v2.versions import (
    EVALUATEE_SERIALIZATION_VERSION,
    ORCHESTRATION_VERSION,
    PARSER_VERSION,
    SCORER_VERSION,
    VERIFIER_VERSION,
)
from fsmreasonbench.models.serialization import canonical_json, content_hash


def build_fingerprint_document(
    condition: ConditionSpec,
    *,
    item_manifest_fingerprint: str,
) -> dict[str, Any]:
    """Canonical scientifically relevant configuration document."""
    return {
        "namespace": condition.namespace,
        "item_manifest_fingerprint": item_manifest_fingerprint,
        "evaluatee_serialization_version": EVALUATEE_SERIALIZATION_VERSION,
        "model_id": condition.model,
        "provider": condition.provider,
        "decoding": {
            "temperature": condition.temperature,
            "max_tokens": condition.max_tokens,
            "top_p": condition.top_p,
            "seed": condition.seed,
        },
        "prompt_skeleton": prompt_skeleton_text(),
        "contract": condition.contract.value,
        "contract_schema_block": contract_schema_block(condition.contract),
        "tool_palette": condition.tool_palette.value,
        "tool_definitions": tool_definitions_for_palette(condition.tool_palette),
        "tool_docs": tool_docs_for_palette(condition.tool_palette),
        "oracle_info": condition.oracle_info.value,
        "oracle_block": oracle_info_block(condition.oracle_info),
        "format_assist": condition.format_assist.value,
        "format_block": format_assist_block(condition.format_assist),
        "parser_version": PARSER_VERSION,
        "scorer_version": SCORER_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "orchestration": condition.orchestration_mode.value,
        "orchestration_version": ORCHESTRATION_VERSION,
        "tool_call_budget": condition.tool_call_budget,
        "retry_policy": {"provider_retries": condition.provider_retries},
        "repetition_index": condition.repetition_index,
    }


def fingerprint_condition(
    condition: ConditionSpec,
    *,
    item_manifest_fingerprint: str,
) -> str:
    return content_hash(build_fingerprint_document(condition, item_manifest_fingerprint=item_manifest_fingerprint))


def _leaf_diffs(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    if type(left) is not type(right) and not (
        isinstance(left, (int, float)) and isinstance(right, (int, float))
    ):
        return [{"path": path or "$", "left": left, "right": right}]
    if isinstance(left, dict):
        keys = sorted(set(left) | set(right))
        diffs: list[dict[str, Any]] = []
        for key in keys:
            child = f"{path}.{key}" if path else key
            if key not in left:
                diffs.append({"path": child, "left": None, "right": right[key]})
            elif key not in right:
                diffs.append({"path": child, "left": left[key], "right": None})
            else:
                diffs.extend(_leaf_diffs(left[key], right[key], child))
        return diffs
    if isinstance(left, list):
        if left != right:
            return [{"path": path or "$", "left": left, "right": right}]
        return []
    if left != right:
        return [{"path": path or "$", "left": left, "right": right}]
    return []


# Paths that are allowed to differ for each intended single-factor contrast.
_ALLOWED_PATH_PREFIXES: dict[str, tuple[str, ...]] = {
    "contract": ("contract", "contract_schema_block"),
    "tool_palette": ("tool_palette", "tool_definitions", "tool_docs"),
    "oracle_info": ("oracle_info", "oracle_block"),
    "format_assist": ("format_assist", "format_block"),
    "repetition_index": ("repetition_index",),
}


def diff_experiment(
    condition_a: ConditionSpec,
    condition_b: ConditionSpec,
    *,
    item_manifest_fingerprint: str = "shared-manifest",
    expected_factor: str | None = None,
) -> dict[str, Any]:
    """Compare two conditions; optionally assert only an expected factor differs."""
    doc_a = build_fingerprint_document(
        condition_a, item_manifest_fingerprint=item_manifest_fingerprint
    )
    doc_b = build_fingerprint_document(
        condition_b, item_manifest_fingerprint=item_manifest_fingerprint
    )
    # Repetition index is part of run identity but often held fixed in factor diffs.
    diffs = _leaf_diffs(doc_a, doc_b)
    unexpected: list[dict[str, Any]] = []
    if expected_factor is not None:
        allowed = _ALLOWED_PATH_PREFIXES.get(expected_factor)
        if allowed is None:
            raise ValueError(f"unknown expected_factor: {expected_factor!r}")
        for diff in diffs:
            path = diff["path"]
            if not any(path == prefix or path.startswith(prefix + ".") for prefix in allowed):
                unexpected.append(diff)
    return {
        "differences": diffs,
        "difference_paths": [diff["path"] for diff in diffs],
        "expected_factor": expected_factor,
        "unexpected_differences": unexpected,
        "ok": not unexpected if expected_factor is not None else True,
        "fingerprint_a": content_hash(doc_a),
        "fingerprint_b": content_hash(doc_b),
        "canonical_a": canonical_json(doc_a),
        "canonical_b": canonical_json(doc_b),
    }


def assert_single_factor_diff(
    condition_a: ConditionSpec,
    condition_b: ConditionSpec,
    expected_factor: str,
    *,
    item_manifest_fingerprint: str = "shared-manifest",
) -> dict[str, Any]:
    result = diff_experiment(
        condition_a,
        condition_b,
        item_manifest_fingerprint=item_manifest_fingerprint,
        expected_factor=expected_factor,
    )
    if result["unexpected_differences"]:
        raise AssertionError(
            f"unexpected fingerprint diffs for factor {expected_factor}: "
            f"{result['unexpected_differences']}"
        )
    if not result["differences"]:
        raise AssertionError(f"expected factor {expected_factor} to differ, but fingerprints match")
    return result


def base_condition(**overrides: Any) -> ConditionSpec:
    """Factory for tests/sentinel with safe defaults."""
    payload = {
        "contract": ContractId.BISIMULATION,
        "tool_palette": ToolPaletteId.T1_STEP,
        "oracle_info": OracleInfoId.NONE,
        "format_assist": FormatAssistId.OFF,
        "model": "mock-deterministic-v1",
        "temperature": 0.0,
        "max_tokens": 1024,
        "repetition_index": 1,
        "provider": "mock",
    }
    payload.update(overrides)
    return ConditionSpec(**payload)

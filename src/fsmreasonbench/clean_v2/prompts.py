"""Clean_v2 prompt skeletons with factorized oracle/format/contract blocks."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.clean_v2.condition import (
    ConditionSpec,
    ContractId,
    FormatAssistId,
    OracleInfoId,
    ToolPaletteId,
)
from fsmreasonbench.clean_v2.views import EvaluateeView


def prompt_skeleton_text() -> str:
    return (
        "You are solving an FSMReasonBench F1 equivalence task under clean_v2.\n"
        "Respond with a single JSON object only (no markdown fences, no prose).\n"
        "Top-level keys must be exactly: item_id, verdict, certificate.\n"
    )


def contract_schema_block(contract: ContractId) -> str:
    if contract == ContractId.BISIMULATION:
        return (
            "Contract=bisimulation: certificate_type must be bisimulation_witness.\n"
            "payload.equivalent must be true.\n"
            "payload.pairs must be a non-empty array of {state_a, state_b} objects\n"
            "forming a valid bisimulation containing the initial state pair.\n"
        )
    if contract == ContractId.MINIMIZED_DFA:
        return (
            "Contract=minimized_dfa: certificate_type must be minimized_dfa_witness.\n"
            "payload.equivalent must be true.\n"
            "payload.minimized_a and payload.minimized_b must be DFA objects\n"
            "(states, initial_state, input_alphabet, transitions, accepting_states)\n"
            "that are behaviorally equivalent to fsm_a/fsm_b respectively and minimal.\n"
        )
    if contract == ContractId.DIGEST_CONTROL:
        return (
            "Contract=digest_control (infeasibility control): certificate_type must be "
            "equivalence_witness.\n"
            "payload.equivalent must be true.\n"
            "payload.minimized_hash_A and minimized_hash_B must be 64-char hex digests\n"
            "matching the verifier's canonical language-bitvector hash.\n"
        )
    raise ValueError(contract)


def oracle_info_block(oracle: OracleInfoId, *, gold_verdict: bool | None = None) -> str:
    if oracle == OracleInfoId.NONE:
        return ""
    if oracle == OracleInfoId.GOLD_VERDICT:
        if gold_verdict is None:
            # Fingerprint uses placeholder; runtime substitutes concrete value.
            return (
                "Oracle information: the gold boolean verdict is provided as "
                "{{GOLD_VERDICT}}.\n"
                "Do not treat this as permission to skip a valid certificate.\n"
            )
        literal = "true" if gold_verdict else "false"
        return (
            f"Oracle information: the gold boolean verdict for this item is {literal}.\n"
            "Do not treat this as permission to skip a valid certificate.\n"
        )
    raise ValueError(oracle)


def format_assist_block(format_assist: FormatAssistId) -> str:
    if format_assist == FormatAssistId.OFF:
        return ""
    return (
        "Format assistance (syntactic only):\n"
        "Emit JSON shaped like:\n"
        '{"item_id":"<id>","verdict":true,"certificate":{'
        '"certificate_type":"<type>","version":"1.0","fsm_ids":["<a>","<b>"],'
        '"payload":{...}}}.\n'
        "Do not invent semantic witness content from this template.\n"
        "Placeholder tokens are not gold values.\n"
    )


def tool_docs_for_palette(palette: ToolPaletteId) -> str:
    if palette == ToolPaletteId.T0_NONE:
        return "Tools: none. Do not emit tool plans.\n"
    if palette == ToolPaletteId.T1_STEP:
        return (
            "Allowed tools:\n"
            '- "step": inputs {"fsm_id","state","symbol"} -> '
            "{success, next_state?} local transition only.\n"
        )
    if palette == ToolPaletteId.T3_VERIFY:
        return (
            "Allowed tools:\n"
            '- "verifier.validate_certificate_coarse": inputs {"certificate": {...}} -> '
            "coarse status codes only (no gold fragments).\n"
        )
    if palette == ToolPaletteId.T3_VERIFY_WITH_STEP:
        return (
            "Allowed tools:\n"
            '- "step": inputs {"fsm_id","state","symbol"} -> '
            "{success, next_state?} local transition only.\n"
            '- "verifier.validate_certificate_coarse": inputs {"certificate": {...}} -> '
            "coarse status codes only (no gold fragments).\n"
        )
    raise ValueError(palette)


def render_final_prompt(
    condition: ConditionSpec,
    evaluatee: EvaluateeView,
    *,
    gold_verdict_for_oracle: bool | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> str:
    """Build the model-visible final prompt (evaluatee-safe)."""
    if condition.oracle_info == OracleInfoId.GOLD_VERDICT and gold_verdict_for_oracle is None:
        raise ValueError("gold_verdict_for_oracle required when oracle_info=gold_verdict")
    parts = [
        prompt_skeleton_text(),
        "## Item (evaluatee-visible)\n",
        json.dumps(evaluatee.to_dict(), indent=2, sort_keys=True),
        "\n## Contract\n",
        contract_schema_block(condition.contract),
        "\n## Tools\n",
        tool_docs_for_palette(condition.tool_palette),
    ]
    oracle = oracle_info_block(condition.oracle_info, gold_verdict=gold_verdict_for_oracle)
    if oracle:
        parts.extend(["\n## Oracle\n", oracle])
    fmt = format_assist_block(condition.format_assist)
    if fmt:
        parts.extend(["\n## Format\n", fmt])
    if tool_results is not None:
        parts.extend(
            [
                "\n## Tool results\n",
                json.dumps(tool_results, indent=2, sort_keys=True),
                "\n",
            ]
        )
    parts.append(
        "\nEmit final JSON submission now with item_id matching the evaluatee item.\n"
    )
    return "".join(parts)


def render_tool_plan_prompt(
    condition: ConditionSpec,
    evaluatee: EvaluateeView,
    *,
    gold_verdict_for_oracle: bool | None = None,
) -> str:
    if condition.tool_palette == ToolPaletteId.T0_NONE:
        return render_final_prompt(
            condition,
            evaluatee,
            gold_verdict_for_oracle=gold_verdict_for_oracle,
            tool_results=[],
        )
    parts = [
        prompt_skeleton_text(),
        "Phase 1: emit tool_plan JSON only.\n",
        json.dumps(evaluatee.to_dict(), indent=2, sort_keys=True),
        "\n",
        tool_docs_for_palette(condition.tool_palette),
        contract_schema_block(condition.contract),
        '\nEmit {"phase":"tool_plan","tool_calls":[{"call_id":"1","tool":"...","inputs":{...}}]}\n',
    ]
    oracle = oracle_info_block(condition.oracle_info, gold_verdict=gold_verdict_for_oracle)
    if oracle:
        parts.append(oracle)
    return "".join(parts)

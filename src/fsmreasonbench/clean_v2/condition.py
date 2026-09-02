"""Factorized immutable ConditionSpec for clean_v2 experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ContractId(str, Enum):
    BISIMULATION = "bisimulation"
    MINIMIZED_DFA = "minimized_dfa"
    DIGEST_CONTROL = "digest_control"


class ToolPaletteId(str, Enum):
    T0_NONE = "T0_NONE"
    T1_STEP = "T1_STEP"
    T3_VERIFY = "T3_VERIFY"
    # Optional composition: verify feedback plus step exploration.
    T3_VERIFY_WITH_STEP = "T3_VERIFY_WITH_STEP"


class OracleInfoId(str, Enum):
    NONE = "none"
    GOLD_VERDICT = "gold_verdict"


class FormatAssistId(str, Enum):
    OFF = "off"
    ON = "on"


class OrchestrationMode(str, Enum):
    TWO_PHASE_NO_INJECT = "two_phase_no_inject"
    SYS_CEILING = "sys_ceiling"  # explicit non-primary ceiling path
    LEGACY_V1 = "legacy_v1"  # historical interpretation only


CONTRACT_ROLE = {
    ContractId.BISIMULATION: "primary_feasible",
    ContractId.MINIMIZED_DFA: "primary_feasible",
    ContractId.DIGEST_CONTROL: "infeasibility_control",
}


@dataclass(frozen=True, slots=True)
class ConditionSpec:
    """Independent experimental factors; mutating one must not alter others."""

    contract: ContractId
    tool_palette: ToolPaletteId
    oracle_info: OracleInfoId
    format_assist: FormatAssistId
    model: str
    temperature: float
    max_tokens: int
    repetition_index: int
    orchestration_mode: OrchestrationMode = OrchestrationMode.TWO_PHASE_NO_INJECT
    provider: str = "mock"
    top_p: float | None = None
    seed: int | None = None
    tool_call_budget: int = 64
    provider_retries: int = 0
    namespace: str = "clean_v2"

    def __post_init__(self) -> None:
        if self.repetition_index < 1:
            raise ValueError("repetition_index must be >= 1")
        if self.temperature < 0:
            raise ValueError("temperature must be >= 0")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        if self.namespace != "clean_v2":
            raise ValueError("ConditionSpec.namespace must be 'clean_v2'")
        if (
            self.orchestration_mode == OrchestrationMode.TWO_PHASE_NO_INJECT
            and self.contract == ContractId.DIGEST_CONTROL
            and self.tool_palette
            not in {ToolPaletteId.T0_NONE, ToolPaletteId.T1_STEP, ToolPaletteId.T3_VERIFY, ToolPaletteId.T3_VERIFY_WITH_STEP}
        ):
            raise ValueError("digest_control uses the same causal palettes as other contracts")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract"] = self.contract.value
        payload["tool_palette"] = self.tool_palette.value
        payload["oracle_info"] = self.oracle_info.value
        payload["format_assist"] = self.format_assist.value
        payload["orchestration_mode"] = self.orchestration_mode.value
        payload["contract_role"] = CONTRACT_ROLE[self.contract]
        return payload

    def with_updates(self, **changes: Any) -> ConditionSpec:
        """Return a new ConditionSpec changing only the provided fields."""
        current = {
            "contract": self.contract,
            "tool_palette": self.tool_palette,
            "oracle_info": self.oracle_info,
            "format_assist": self.format_assist,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "repetition_index": self.repetition_index,
            "orchestration_mode": self.orchestration_mode,
            "provider": self.provider,
            "top_p": self.top_p,
            "seed": self.seed,
            "tool_call_budget": self.tool_call_budget,
            "provider_retries": self.provider_retries,
            "namespace": self.namespace,
        }
        current.update(changes)
        return ConditionSpec(**current)


def legacy_label_to_factors(label: str) -> dict[str, str]:
    """Historical interpretation only — not used to construct clean runs."""
    mapping = {
        "R0": {"tools": "T0_NONE", "note": "approx; legacy single-shot"},
        "R1": {"tools": "T1_STEP", "note": "approx; legacy prompts differ"},
        "R2": {"tools": "RETIRED_builders", "note": "not causal clean_v2"},
        "Oracle+Format": {"note": "RETIRED confound: gold+format-step"},
        "R2A": {"tools": "T3_VERIFY", "note": "approx if prompts aligned"},
        "R2B": {"format": "on", "note": "absorbed into format_assist"},
        "R2C": {"orchestration": "SYS_CEILING", "note": "system ceiling only"},
    }
    return mapping.get(label, {"note": "unknown legacy label"})

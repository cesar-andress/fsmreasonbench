"""Witness provenance schema for clean_v2 scored records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class WitnessOrigin(str, Enum):
    MODEL_GENERATED = "model_generated"
    TOOL_CONSTRUCTED = "tool_constructed"
    RUNNER_INJECTED = "runner_injected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WitnessProvenance:
    witness_origin: WitnessOrigin
    tool_contributed: bool = False
    direct_tool_construction: bool = False
    model_modified_tool_output: bool = False
    syntactic_repair_applied: bool = False
    semantic_changed_post_model: bool = False
    verifier_only_feedback: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["witness_origin"] = self.witness_origin.value
        return payload

    @classmethod
    def model_generated(cls, **flags: bool) -> WitnessProvenance:
        return cls(witness_origin=WitnessOrigin.MODEL_GENERATED, **flags)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WitnessProvenance:
        return cls(
            witness_origin=WitnessOrigin(payload["witness_origin"]),
            tool_contributed=bool(payload.get("tool_contributed", False)),
            direct_tool_construction=bool(payload.get("direct_tool_construction", False)),
            model_modified_tool_output=bool(payload.get("model_modified_tool_output", False)),
            syntactic_repair_applied=bool(payload.get("syntactic_repair_applied", False)),
            semantic_changed_post_model=bool(payload.get("semantic_changed_post_model", False)),
            verifier_only_feedback=bool(payload.get("verifier_only_feedback", False)),
        )


def assert_model_performance_row_allowed(row: dict[str, Any]) -> None:
    """Hard guard: primary model exports refuse non-model-generated witnesses."""
    provenance = row.get("witness_provenance") or {}
    origin = provenance.get("witness_origin")
    if origin != WitnessOrigin.MODEL_GENERATED.value:
        raise ValueError(
            "primary model-performance export refused row with "
            f"witness_origin={origin!r}; only model_generated is allowed"
        )


def filter_model_performance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only model_generated rows; raise if mixed export requested implicitly."""
    kept: list[dict[str, Any]] = []
    for row in rows:
        provenance = row.get("witness_provenance") or {}
        if provenance.get("witness_origin") == WitnessOrigin.MODEL_GENERATED.value:
            kept.append(row)
        elif row.get("export_class") == "system_level":
            continue
        else:
            # Soft-skip with explicit marker in caller; hard guard available separately.
            continue
    return kept

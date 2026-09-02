"""Clean_v2 tool palette definitions (causal RQ3)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.condition import ToolPaletteId

# No scientifically clean T2_COMPUTE exists in-repo without revealing
# equivalence or constructing witnesses. T2 is omitted.
T2_COMPUTE_AVAILABLE = False
T2_OMISSION_REASON = (
    "No non-answer-producing computational primitive exists that is strictly "
    "stronger than step exploration without revealing equivalence/non-equivalence "
    "or emitting witness-copyable content. check_separation is forbidden (verdict leak). "
    "Certificate builders are forbidden (witness construction)."
)

T0_TOOLS: frozenset[str] = frozenset()
T1_TOOLS: frozenset[str] = frozenset({"step"})
T3_TOOLS: frozenset[str] = frozenset({"verifier.validate_certificate_coarse"})
T3_WITH_STEP_TOOLS: frozenset[str] = T1_TOOLS | T3_TOOLS

FORBIDDEN_CAUSAL_TOOLS: frozenset[str] = frozenset(
    {
        "solver.check_separation",
        "solver.equivalence_certificate",
        "solver.bisimulation_certificate",
        "solver.distinguishing_certificate",
        "solver.is_reachable",
        "solver.reachability_certificate",
        "solver.minimized_dfa",
        "solver.minimized_dfa_hash",
    }
)


def tools_for_palette(palette: ToolPaletteId) -> frozenset[str]:
    if palette == ToolPaletteId.T0_NONE:
        return T0_TOOLS
    if palette == ToolPaletteId.T1_STEP:
        return T1_TOOLS
    if palette == ToolPaletteId.T3_VERIFY:
        return T3_TOOLS
    if palette == ToolPaletteId.T3_VERIFY_WITH_STEP:
        return T3_WITH_STEP_TOOLS
    raise ValueError(palette)


def tool_definitions_for_palette(palette: ToolPaletteId) -> dict[str, Any]:
    """Stable definition payloads for fingerprinting."""
    defs: dict[str, Any] = {}
    allowed = tools_for_palette(palette)
    if "step" in allowed:
        defs["step"] = {
            "inputs": ["fsm_id", "state", "symbol"],
            "outputs": ["success", "next_state?"],
            "semantics": "local DFA transition; no verdict; no witness",
            "verdict_revealing": False,
            "witness_constructing": False,
            "certificate_copyable": False,
        }
    if "verifier.validate_certificate_coarse" in allowed:
        defs["verifier.validate_certificate_coarse"] = {
            "inputs": ["certificate"],
            "outputs": ["status", "code"],
            "semantics": "coarse non-constructive verification feedback",
            "verdict_revealing": False,
            "witness_constructing": False,
            "certificate_copyable": False,
        }
    return {
        "palette": palette.value,
        "allowed_tools": sorted(allowed),
        "definitions": defs,
        "t2_compute_available": T2_COMPUTE_AVAILABLE,
        "t2_omission_reason": T2_OMISSION_REASON,
        "forbidden_causal_tools": sorted(FORBIDDEN_CAUSAL_TOOLS),
    }


def assert_palette_is_causal(palette: ToolPaletteId) -> None:
    allowed = tools_for_palette(palette)
    overlap = allowed & FORBIDDEN_CAUSAL_TOOLS
    if overlap:
        raise AssertionError(f"causal palette includes forbidden tools: {sorted(overlap)}")

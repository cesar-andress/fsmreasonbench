"""Mandatory F1 R2C certificate-builder synthesis (reference R2 agent parity)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.solver_tools import SolverToolRegistry


@dataclass(frozen=True, slots=True)
class F1R2cSynthesisResult:
    tool_outputs: list[dict[str, Any]]
    verdict: bool
    certificate: dict[str, Any]


def _executed_tool_names(tool_outputs: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["tool"])
        for row in tool_outputs
        if row.get("status") == "executed" and row.get("tool")
    }


def _find_executed_outputs(
    tool_outputs: list[dict[str, Any]],
    tool_name: str,
) -> dict[str, Any] | None:
    for row in tool_outputs:
        if row.get("tool") == tool_name and row.get("status") == "executed":
            outputs = row.get("outputs")
            if isinstance(outputs, dict):
                return outputs
    return None


def _append_supplement_call(
    tool_outputs: list[dict[str, Any]],
    *,
    tool: str,
    outputs: dict[str, Any],
    call_id: str,
) -> list[dict[str, Any]]:
    return [
        *tool_outputs,
        {
            "call_id": call_id,
            "tool": tool,
            "status": "executed",
            "outputs": outputs,
            "runner_supplement": True,
        },
    ]


def ensure_f1_r2c_certificate_synthesis(
    item: BenchmarkItem,
    tool_outputs: list[dict[str, Any]],
    audit: AuditLogBuilder,
) -> F1R2cSynthesisResult:
    """
    Mirror ``tracks.agents._r2_solve_f1``: always invoke the canonical certificate
    builder after separation is known, and record ``certificate_assembly`` steps.
    """
    if item.fsm_b is None:
        raise ValueError("F1 R2C synthesis requires fsm_b")

    fsm_a = item.fsm_a
    fsm_b = item.fsm_b
    outputs = list(tool_outputs)
    executed = _executed_tool_names(outputs)
    solvers = SolverToolRegistry(audit=audit)
    supplement_index = 1

    separation = _find_executed_outputs(outputs, "solver.check_separation")
    if separation is None:
        audit.certificate_step(
            "invoke solver.check_separation",
            details={"fsm_id_a": fsm_a.fsm_id, "fsm_id_b": fsm_b.fsm_id},
        )
        separation = solvers.check_separation(fsm_a, fsm_b)
        outputs = _append_supplement_call(
            outputs,
            tool="solver.check_separation",
            outputs=separation,
            call_id=f"runner-supplement-{supplement_index}",
        )
        supplement_index += 1
        executed.add("solver.check_separation")

    if separation.get("equivalent"):
        certificate = _find_executed_outputs(outputs, "solver.equivalence_certificate")
        certificate_obj = (
            certificate.get("certificate")
            if isinstance(certificate, dict) and isinstance(certificate.get("certificate"), dict)
            else None
        )
        if certificate_obj is None:
            audit.certificate_step(
                "invoke solver.equivalence_certificate",
                details={"fsm_id_a": fsm_a.fsm_id, "fsm_id_b": fsm_b.fsm_id},
            )
            certificate_obj = solvers.equivalence_certificate(fsm_a, fsm_b)
            outputs = _append_supplement_call(
                outputs,
                tool="solver.equivalence_certificate",
                outputs={
                    "certificate_type": certificate_obj["certificate_type"],
                    "certificate": certificate_obj,
                },
                call_id=f"runner-supplement-{supplement_index}",
            )
            executed.add("solver.equivalence_certificate")
        audit.certificate_step(
            "bind verdict true for equivalent DFAs",
            details={
                "certificate_type": certificate_obj.get("certificate_type"),
                "minimized_hash_A": certificate_obj.get("payload", {}).get(
                    "minimized_hash_A"
                ),
                "minimized_hash_B": certificate_obj.get("payload", {}).get(
                    "minimized_hash_B"
                ),
            },
        )
        return F1R2cSynthesisResult(
            tool_outputs=outputs,
            verdict=True,
            certificate=certificate_obj,
        )

    certificate = _find_executed_outputs(outputs, "solver.distinguishing_certificate")
    certificate_obj = (
        certificate.get("certificate")
        if isinstance(certificate, dict) and isinstance(certificate.get("certificate"), dict)
        else None
    )
    if certificate_obj is None:
        audit.certificate_step(
            "invoke solver.distinguishing_certificate",
            details={"fsm_id_a": fsm_a.fsm_id, "fsm_id_b": fsm_b.fsm_id},
        )
        certificate_obj = solvers.distinguishing_certificate(fsm_a, fsm_b)
        outputs = _append_supplement_call(
            outputs,
            tool="solver.distinguishing_certificate",
            outputs={
                "certificate_type": certificate_obj["certificate_type"],
                "certificate": certificate_obj,
            },
            call_id=f"runner-supplement-{supplement_index}",
        )
    audit.certificate_step(
        "bind verdict false for non-equivalent DFAs",
        details={"certificate_type": certificate_obj.get("certificate_type")},
    )
    return F1R2cSynthesisResult(
        tool_outputs=outputs,
        verdict=False,
        certificate=certificate_obj,
    )

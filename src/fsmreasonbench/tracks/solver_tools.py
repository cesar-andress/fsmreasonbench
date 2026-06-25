"""R2 controlled solver tool interface."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.certificates.separation import (
    build_bisimulation_witness_certificate,
    build_distinguishing_trace_certificate,
    build_equivalence_witness_certificate,
)
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.oracle.reachability import is_reachable
from fsmreasonbench.oracle.separation import check_separation
from fsmreasonbench.tracks.audit import AuditLogBuilder

SOLVER_REGISTRY_VERSION = "1.0"

REGISTERED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "solver.is_reachable",
        "solver.reachability_certificate",
        "solver.check_separation",
        "solver.equivalence_certificate",
        "solver.bisimulation_certificate",
        "solver.distinguishing_certificate",
    }
)


class SolverToolRegistry:
    """
    R2-permitted closed-world solver interface.

    May invoke oracle modules internally; every call is logged with provenance.
    """

    def __init__(self, *, audit: AuditLogBuilder) -> None:
        self._audit = audit

    def is_reachable(self, fsm: ExecutableFSM, target_state: str) -> bool:
        reachable = is_reachable(fsm, target_state)
        self._audit.record_tool(
            "solver.is_reachable",
            {
                "fsm_id": fsm.fsm_id,
                "target_state": target_state,
            },
            {"reachable": reachable},
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="oracle.reachability.is_reachable",
        )
        return reachable

    def reachability_certificate(
        self,
        fsm: ExecutableFSM,
        target_state: str,
    ) -> dict[str, Any]:
        certificate = build_reachability_certificate(fsm, target_state)
        self._audit.record_tool(
            "solver.reachability_certificate",
            {
                "fsm_id": fsm.fsm_id,
                "target_state": target_state,
            },
            {
                "certificate_type": certificate["certificate_type"],
                "verdict_supported": certificate["verdict_supported"],
            },
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="certificates.reachability.build_reachability_certificate",
        )
        return certificate

    def check_separation(
        self,
        fsm_a: ExecutableFSM,
        fsm_b: ExecutableFSM,
    ) -> dict[str, Any]:
        result = check_separation(fsm_a, fsm_b)
        outputs = {
            "equivalent": result.equivalent,
            "distinguishing_trace": (
                list(result.distinguishing_trace)
                if result.distinguishing_trace is not None
                else None
            ),
            "acceptance_a": result.acceptance_a,
            "acceptance_b": result.acceptance_b,
        }
        self._audit.record_tool(
            "solver.check_separation",
            {
                "fsm_id_a": fsm_a.fsm_id,
                "fsm_id_b": fsm_b.fsm_id,
            },
            outputs,
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="oracle.separation.check_separation",
        )
        return outputs

    def equivalence_certificate(
        self,
        fsm_a: ExecutableFSM,
        fsm_b: ExecutableFSM,
    ) -> dict[str, Any]:
        certificate = build_equivalence_witness_certificate(fsm_a, fsm_b)
        self._audit.record_tool(
            "solver.equivalence_certificate",
            {
                "fsm_id_a": fsm_a.fsm_id,
                "fsm_id_b": fsm_b.fsm_id,
            },
            {
                "certificate_type": certificate["certificate_type"],
                "verdict_supported": certificate["verdict_supported"],
            },
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="certificates.separation.build_equivalence_witness_certificate",
        )
        return certificate

    def bisimulation_certificate(
        self,
        fsm_a: ExecutableFSM,
        fsm_b: ExecutableFSM,
    ) -> dict[str, Any]:
        certificate = build_bisimulation_witness_certificate(fsm_a, fsm_b)
        self._audit.record_tool(
            "solver.bisimulation_certificate",
            {
                "fsm_id_a": fsm_a.fsm_id,
                "fsm_id_b": fsm_b.fsm_id,
            },
            {
                "certificate_type": certificate["certificate_type"],
                "verdict_supported": certificate["verdict_supported"],
                "pair_count": len(certificate.get("payload", {}).get("pairs", [])),
            },
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="certificates.separation.build_bisimulation_witness_certificate",
        )
        return certificate

    def distinguishing_certificate(
        self,
        fsm_a: ExecutableFSM,
        fsm_b: ExecutableFSM,
    ) -> dict[str, Any]:
        separation = check_separation(fsm_a, fsm_b)
        if separation.equivalent:
            raise ValueError(
                "DFAs are equivalent; use solver.equivalence_certificate instead of "
                "solver.distinguishing_certificate"
            )
        certificate = build_distinguishing_trace_certificate(fsm_a, fsm_b)
        self._audit.record_tool(
            "solver.distinguishing_certificate",
            {
                "fsm_id_a": fsm_a.fsm_id,
                "fsm_id_b": fsm_b.fsm_id,
            },
            {
                "certificate_type": certificate["certificate_type"],
                "verdict_supported": certificate["verdict_supported"],
            },
            tool_version=SOLVER_REGISTRY_VERSION,
            provenance="certificates.separation.build_distinguishing_trace_certificate",
        )
        return certificate

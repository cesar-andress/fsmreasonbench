"""Non-constructive coarse verifier feedback for T3_VERIFY."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.condition import ContractId
from fsmreasonbench.clean_v2.contracts import verify_certificate_for_contract
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.verifier.result import VerifyResult

# Coarse codes exposed to the model. Never include gold fragments.
COARSE_CODES = frozenset(
    {
        "accepted",
        "malformed_certificate",
        "initial_state_condition_failed",
        "relation_closure_failed",
        "transition_consistency_failed",
        "minimization_requirement_failed",
        "behavioral_equivalence_failed",
        "digest_mismatch",
        "unsupported_certificate_type",
        "rejected",
    }
)


def _map_errors_to_coarse(errors: tuple[str, ...]) -> str:
    joined = " ".join(errors).lower()
    if not errors:
        return "accepted"
    if "unsupported certificate_type" in joined or "must be" in joined and "certificate_type" in joined:
        return "unsupported_certificate_type"
    if "malformed" in joined or "must be a" in joined or "payload" in joined and "object" in joined:
        if "pairs" in joined or "minimized_" in joined or "hash" in joined:
            return "malformed_certificate"
        return "malformed_certificate"
    if "initial" in joined:
        return "initial_state_condition_failed"
    if "closure" in joined or "bisimulation" in joined or "relation" in joined:
        return "relation_closure_failed"
    if "transition" in joined:
        return "transition_consistency_failed"
    if "minimal" in joined or "minimization" in joined:
        return "minimization_requirement_failed"
    if "equivalent" in joined or "behavioral" in joined or "language" in joined:
        return "behavioral_equivalence_failed"
    if "hash" in joined or "digest" in joined:
        return "digest_mismatch"
    return "rejected"


def coarse_validate_certificate(
    item: BenchmarkItem,
    certificate: dict[str, Any],
    *,
    contract: ContractId,
) -> dict[str, Any]:
    """
    Model-facing validation result.

    Returns only coarse status/code. Detailed errors remain evaluator-internal
    and are not included in the returned object.
    """
    if item.fsm_b is None:
        return {"status": "rejected", "code": "malformed_certificate"}
    result: VerifyResult = verify_certificate_for_contract(
        item.fsm_a,
        item.fsm_b,
        certificate,
        contract=contract,
    )
    if result.valid:
        return {"status": "accepted", "code": "accepted"}
    code = _map_errors_to_coarse(result.errors)
    if code not in COARSE_CODES:
        code = "rejected"
    # Intentionally omit result.errors from model-visible outputs.
    return {"status": "rejected", "code": code}


def model_visible_feedback_is_safe(outputs: dict[str, Any], gold_tokens: set[str]) -> bool:
    """Return False if coarse outputs leak gold token strings."""
    blob = str(outputs)
    return not any(token and token in blob for token in gold_tokens)

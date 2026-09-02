"""Generation-time missingness classification (deterministic)."""

from __future__ import annotations

from enum import Enum
from typing import Any


class MissingnessClass(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    EXPERIMENTAL_OUTCOME = "experimental_outcome"


# Machine-readable reason codes.
INFRA_REASONS = frozenset(
    {
        "http_timeout",
        "rate_limit",
        "quota",
        "transport_failure",
        "provider_5xx",
        "provider_stream_abort",
        "harness_internal_exception",
        "harness_tool_crash",
        "verifier_harness_crash",
    }
)

EXPERIMENTAL_REASONS = frozenset(
    {
        "malformed_model_output",
        "invalid_model_tool_call",
        "model_tool_validation_error",
        "max_tokens_reached",
        "safety_refusal",
        "empty_completion",
        "parser_failure",
    }
)


def classify_generation_attempt(fields: dict[str, Any]) -> dict[str, Any]:
    """
    Assign INFRASTRUCTURE vs EXPERIMENTAL_OUTCOME from machine-readable fields.

    Required keys (use None when absent):
      provider_error_type, http_status, finish_reason, harness_exception,
      parse_errors, safety_refusal, empty_completion, tool_call_invalid,
      max_tokens_reached
    """
    provider_error = fields.get("provider_error_type")
    http_status = fields.get("http_status")
    harness_exception = fields.get("harness_exception")
    finish_reason = fields.get("finish_reason")

    if harness_exception in {"harness_internal_exception", "harness_tool_crash", "verifier_harness_crash"}:
        reason = harness_exception
        return _pack(MissingnessClass.INFRASTRUCTURE, reason, enters_n_attempted=False, rerun=True)

    if provider_error in {"timeout", "http_timeout"}:
        return _pack(MissingnessClass.INFRASTRUCTURE, "http_timeout", False, True)
    if provider_error in {"rate_limit", "quota", "quota_exceeded"}:
        reason = "quota" if "quota" in str(provider_error) else "rate_limit"
        return _pack(MissingnessClass.INFRASTRUCTURE, reason, False, True)
    if provider_error in {"transport", "network", "transport_failure"}:
        return _pack(MissingnessClass.INFRASTRUCTURE, "transport_failure", False, True)
    if provider_error in {"stream_abort", "provider_stream_abort"}:
        return _pack(MissingnessClass.INFRASTRUCTURE, "provider_stream_abort", False, True)
    if isinstance(http_status, int) and http_status >= 500:
        return _pack(MissingnessClass.INFRASTRUCTURE, "provider_5xx", False, True)

    if fields.get("safety_refusal") is True:
        return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, "safety_refusal", True, False)
    if fields.get("max_tokens_reached") is True or finish_reason in {"length", "max_tokens"}:
        return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, "max_tokens_reached", True, False)
    if fields.get("empty_completion") is True:
        return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, "empty_completion", True, False)
    if fields.get("tool_call_invalid") is True:
        return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, "invalid_model_tool_call", True, False)
    if fields.get("model_tool_validation_error") is True:
        return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, "model_tool_validation_error", True, False)
    parse_errors = fields.get("parse_errors") or []
    if parse_errors:
        if fields.get("malformed_model_output") is True or True:
            # Parser failure is an experimental outcome.
            reason = (
                "malformed_model_output"
                if fields.get("malformed_model_output")
                else "parser_failure"
            )
            return _pack(MissingnessClass.EXPERIMENTAL_OUTCOME, reason, True, False)

    # Successful generation path (may still have wrong verdict / invalid witness).
    return {
        "missingness_class": None,
        "reason_code": "completed",
        "enters_n_attempted": True,
        "rerun_same_repetition": False,
        "is_infrastructure": False,
        "is_experimental_outcome_failure": False,
    }


def _pack(
    cls: MissingnessClass,
    reason: str,
    enters_n_attempted: bool,
    rerun: bool,
) -> dict[str, Any]:
    return {
        "missingness_class": cls.value,
        "reason_code": reason,
        "enters_n_attempted": enters_n_attempted,
        "rerun_same_repetition": rerun,
        "is_infrastructure": cls is MissingnessClass.INFRASTRUCTURE,
        "is_experimental_outcome_failure": cls is MissingnessClass.EXPERIMENTAL_OUTCOME,
    }

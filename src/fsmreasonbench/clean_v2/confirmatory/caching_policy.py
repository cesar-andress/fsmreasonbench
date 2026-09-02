"""Provider caching policy (no live API calls; adapter inspection only)."""

from __future__ import annotations

from typing import Any


def caching_policy_for_provider(provider: str) -> dict[str, Any]:
    """
    Classify caching based on existing adapter implementation.

    A = can be explicitly disabled
    B = cannot disable but cache status observable
    C = cannot disable and cache status not observable
    """
    p = provider.lower().strip()
    if p == "anthropic":
        # build_anthropic_messages_request sends a plain user message with no
        # cache_control / beta prompt-caching fields. Anthropic prompt caching
        # is opt-in via cache_control; our adapter never sets it.
        return {
            "provider": "anthropic",
            "class": "A",
            "can_disable": True,
            "disabled_in_confirmatory": True,
            "cache_status_observable": False,
            "mechanism": (
                "Prompt caching is opt-in via cache_control on content blocks; "
                "clean_v2 confirmatory requests omit cache_control (adapter default)."
            ),
            "sensitivity_analysis": "timestamp_decile_diagnostic",
        }
    if p == "openai":
        # Chat Completions adapter does not set prompt_cache_key / cache controls.
        # Automatic prompt caching may still occur server-side on some models
        # without an exposed per-request disable in this adapter; cache hit is
        # not currently parsed from responses.
        return {
            "provider": "openai",
            "class": "C",
            "can_disable": False,
            "disabled_in_confirmatory": False,
            "cache_status_observable": False,
            "mechanism": (
                "OpenAI Chat Completions adapter has no explicit cache-disable field; "
                "response cache-hit metadata is not parsed. Record timestamps and run "
                "pre-specified drift/cache sensitivity."
            ),
            "sensitivity_analysis": "timestamp_decile_diagnostic",
        }
    if p in {"mock", "deterministic_mock"}:
        return {
            "provider": p,
            "class": "A",
            "can_disable": True,
            "disabled_in_confirmatory": True,
            "cache_status_observable": True,
            "mechanism": "Deterministic mock provider has no remote cache.",
            "sensitivity_analysis": "none_required",
        }
    return {
        "provider": provider,
        "class": "C",
        "can_disable": False,
        "disabled_in_confirmatory": False,
        "cache_status_observable": False,
        "mechanism": "Unknown provider; treat as non-observable cache.",
        "sensitivity_analysis": "timestamp_decile_diagnostic",
    }

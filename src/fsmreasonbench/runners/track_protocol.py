"""Parse LLM track protocol messages."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.runners.response_extract import extract_submission_payload

VALID_PHASES = frozenset({"tool_plan", "final_submission"})


class TrackProtocolError(ValueError):
    """Raised when model output does not match the track protocol."""


def parse_track_message(raw_text: str) -> dict[str, Any]:
    """Extract and validate a track protocol JSON object from model text."""
    payload = extract_submission_payload(raw_text)
    if not isinstance(payload, dict):
        raise TrackProtocolError("model output is not a JSON object")
    phase = payload.get("phase")
    if phase not in VALID_PHASES:
        raise TrackProtocolError(f"unsupported phase: {phase!r}")
    return payload


def parse_tool_plan(raw_text: str) -> tuple[list[dict[str, Any]], str | None]:
    payload = parse_track_message(raw_text)
    if payload["phase"] != "tool_plan":
        raise TrackProtocolError("expected phase=tool_plan")
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        raise TrackProtocolError("tool_calls must be a list")
    normalized: list[dict[str, Any]] = []
    for index, call in enumerate(tool_calls):
        if not isinstance(call, dict):
            raise TrackProtocolError(f"tool_calls[{index}] must be an object")
        tool = call.get("tool")
        inputs = call.get("inputs")
        if not isinstance(tool, str) or not tool:
            raise TrackProtocolError(f"tool_calls[{index}] missing tool name")
        if not isinstance(inputs, dict):
            raise TrackProtocolError(f"tool_calls[{index}] inputs must be an object")
        normalized.append(
            {
                "call_id": str(call.get("call_id", index + 1)),
                "tool": tool,
                "inputs": inputs,
            }
        )
    notes = payload.get("notes")
    return normalized, notes if isinstance(notes, str) else None


def parse_final_submission(raw_text: str) -> dict[str, Any]:
    payload = parse_track_message(raw_text)
    if payload["phase"] != "final_submission":
        raise TrackProtocolError("expected phase=final_submission")
    submission = payload.get("submission")
    if not isinstance(submission, dict):
        raise TrackProtocolError("submission must be an object")
    return submission

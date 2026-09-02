"""Deterministic mock model provider for clean_v2 sentinel campaigns.

Never calls external model APIs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.clean_v2.contracts.minimized_dfa import is_minimal_dfa
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.serialization import fsm_to_dict
from fsmreasonbench.runtime.dfa_minimize import minimize_dfa


@dataclass
class MockScript:
    """Per-item scripted behavior for the sentinel."""

    mode: str = "valid"
    # Modes: valid, invalid_witness, wrong_verdict, malformed,
    # t3_reject_then_valid, tool_plan_then_valid
    call_count: int = 0


@dataclass
class DeterministicMockProvider:
    """Stateful mock generate() keyed by item_id extracted from prompts."""

    items_by_id: dict[str, BenchmarkItem]
    scripts: dict[str, MockScript] = field(default_factory=dict)
    default_mode: str = "valid"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def script_for(self, item_id: str) -> MockScript:
        if item_id not in self.scripts:
            self.scripts[item_id] = MockScript(mode=self.default_mode)
        return self.scripts[item_id]

    def _extract_item_id(self, prompt: str) -> str:
        match = re.search(r'"item_id"\s*:\s*"([^"]+)"', prompt)
        if not match:
            raise ValueError("mock provider could not find item_id in prompt")
        return match.group(1)

    def _detect_contract(self, prompt: str) -> str:
        if "minimized_dfa_witness" in prompt or "Contract=minimized_dfa" in prompt:
            return "minimized_dfa"
        if "digest_control" in prompt or "equivalence_witness" in prompt and "infeasibility" in prompt:
            return "digest_control"
        return "bisimulation"

    def _valid_certificate(self, item: BenchmarkItem, contract: str) -> dict[str, Any]:
        assert item.fsm_b is not None
        if contract == "bisimulation":
            return build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
        if contract == "minimized_dfa":
            min_a = minimize_dfa(item.fsm_a)
            min_b = minimize_dfa(item.fsm_b)
            assert is_minimal_dfa(min_a) and is_minimal_dfa(min_b)
            return {
                "certificate_type": "minimized_dfa_witness",
                "version": "1.0",
                "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
                "verdict_supported": True,
                "payload": {
                    "equivalent": True,
                    "minimized_a": fsm_to_dict(min_a, include_metadata=False),
                    "minimized_b": fsm_to_dict(min_b, include_metadata=False),
                },
            }
        if contract == "digest_control":
            from fsmreasonbench.certificates.separation import (
                build_equivalence_witness_certificate,
            )

            return build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
        raise ValueError(contract)

    def _invalid_bisimulation(self, item: BenchmarkItem) -> dict[str, Any]:
        assert item.fsm_b is not None
        return {
            "certificate_type": "bisimulation_witness",
            "version": "1.0",
            "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
            "payload": {
                "equivalent": True,
                "pairs": [{"state_a": item.fsm_a.initial_state, "state_b": "___nope___"}],
            },
        }

    def generate(self, *, prompt: str, model: str, temperature: float, **_: Any) -> str:
        item_id = self._extract_item_id(prompt)
        item = self.items_by_id[item_id]
        script = self.script_for(item_id)
        script.call_count += 1
        self.calls.append(
            {
                "item_id": item_id,
                "model": model,
                "temperature": temperature,
                "call_index": script.call_count,
                "prompt_chars": len(prompt),
            }
        )
        contract = self._detect_contract(prompt)
        is_tool_plan_phase = "Phase 1: emit tool_plan" in prompt or '"phase":"tool_plan"' in prompt

        if is_tool_plan_phase:
            if "validate_certificate_coarse" in prompt and script.mode == "t3_reject_then_valid":
                # Ask verifier about an invalid certificate first.
                bad = self._invalid_bisimulation(item)
                return json.dumps(
                    {
                        "phase": "tool_plan",
                        "tool_calls": [
                            {
                                "call_id": "1",
                                "tool": "verifier.validate_certificate_coarse",
                                "inputs": {"certificate": bad},
                            }
                        ],
                    },
                    sort_keys=True,
                )
            if "step" in prompt:
                assert item.fsm_b is not None
                return json.dumps(
                    {
                        "phase": "tool_plan",
                        "tool_calls": [
                            {
                                "call_id": "1",
                                "tool": "step",
                                "inputs": {
                                    "fsm_id": item.fsm_a.fsm_id,
                                    "state": item.fsm_a.initial_state,
                                    "symbol": item.fsm_a.input_alphabet[0],
                                },
                            }
                        ],
                    },
                    sort_keys=True,
                )
            return json.dumps({"phase": "tool_plan", "tool_calls": []}, sort_keys=True)

        # Final submission phase
        mode = script.mode
        if mode == "t3_reject_then_valid":
            mode = "valid"
        if mode == "tool_plan_then_valid":
            mode = "valid"

        if mode == "malformed":
            return "this is not json at all"
        if mode == "wrong_verdict":
            cert = self._valid_certificate(item, contract)
            return json.dumps(
                {
                    "item_id": item.item_id,
                    "verdict": not item.answer_key["verdict"],
                    "certificate": cert,
                },
                sort_keys=True,
            )
        if mode == "invalid_witness":
            return json.dumps(
                {
                    "item_id": item.item_id,
                    "verdict": True,
                    "certificate": self._invalid_bisimulation(item),
                },
                sort_keys=True,
            )
        # valid
        return json.dumps(
            {
                "item_id": item.item_id,
                "verdict": True,
                "certificate": self._valid_certificate(item, contract),
            },
            sort_keys=True,
        )


def build_generate_fn(provider: DeterministicMockProvider) -> Callable[..., str]:
    return provider.generate

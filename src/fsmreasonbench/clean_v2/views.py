"""Hard Evaluatee / Evaluator context boundary for clean_v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.models.serialization import fsm_to_dict

# Metadata keys that reveal gold / generator regime / transforms.
_PRIVATE_METADATA_KEYS = frozenset(
    {
        "equivalent_transform",
        "construction",
        "distinguishing_trace_length",
        "witness_symbols",
        "generator",
        "generator_id",
        "pair_construction",
        "construction_mode",
        "label",  # internal generator label; not needed by evaluatee
    }
)

_PRIVATE_DIFFICULTY_CORE_KEYS = frozenset(
    {
        "equivalent",
        "distinguishing_trace_length",  # reveals polarity for F1
        "witness_length",
    }
)


def _public_fsm_dict(fsm: ExecutableFSM) -> dict[str, Any]:
    """FSM JSON without gold-revealing metadata."""
    data = fsm_to_dict(fsm, include_metadata=True)
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        public_meta = {
            key: value
            for key, value in metadata.items()
            if key not in _PRIVATE_METADATA_KEYS
        }
        # Keep only non-revealing structural hints (e.g. generator_seed, state_count).
        if public_meta:
            data["metadata"] = public_meta
        else:
            data.pop("metadata", None)
    return data


def _public_difficulty(difficulty: dict[str, Any]) -> dict[str, Any]:
    core = difficulty.get("core")
    public: dict[str, Any] = {}
    if isinstance(core, dict):
        public_core = {
            key: value
            for key, value in core.items()
            if key not in _PRIVATE_DIFFICULTY_CORE_KEYS
        }
        if public_core:
            public["core"] = public_core
    # generator_seed is not the gold verdict; allowed as public structural seed id.
    if "generator_seed" in difficulty:
        public["generator_seed"] = difficulty["generator_seed"]
    return public


@dataclass(frozen=True, slots=True)
class EvaluateeView:
    """Model-safe item surface. Must never contain gold verdict/certificate."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    def canonical_dict(self) -> dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True, slots=True)
class EvaluatorOnly:
    """Post-generation scoring context. Never passed to prompts or tools."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    @property
    def gold_verdict(self) -> bool:
        return bool(self.payload["gold_verdict"])

    @property
    def gold_certificate(self) -> dict[str, Any] | None:
        cert = self.payload.get("gold_certificate")
        return cert if isinstance(cert, dict) else None


def build_evaluatee_view(item: BenchmarkItem) -> EvaluateeView:
    """Construct scrubbed evaluatee JSON for clean_v2 prompts/tools."""
    data: dict[str, Any] = {
        "item_id": item.item_id,
        "family": item.family,
        "family_tier": item.family_tier,
        "question": dict(item.question),
        "difficulty": _public_difficulty(dict(item.difficulty)),
        "contamination": {
            key: value
            for key, value in dict(item.contamination).items()
            if key == "public_fingerprint"
        },
        "evaluatee_serialization_version": "clean_v2.evaluatee.v1",
    }
    if item.family in {"F1", "F2"}:
        if item.fsm_b is None:
            raise ValueError(f"{item.family} item requires fsm_b")
        data["fsm_a"] = _public_fsm_dict(item.fsm_a)
        data["fsm_b"] = _public_fsm_dict(item.fsm_b)
    else:
        data["fsm"] = _public_fsm_dict(item.fsm)
    return EvaluateeView(payload=data)


def build_evaluator_only(item: BenchmarkItem) -> EvaluatorOnly:
    """Construct evaluator-only gold and private generator fields."""
    core = dict(item.difficulty.get("core") or {})
    private_meta_a = dict(item.fsm_a.metadata or {})
    private_meta_b = dict((item.fsm_b.metadata if item.fsm_b else {}) or {})
    payload: dict[str, Any] = {
        "item_id": item.item_id,
        "family": item.family,
        "gold_verdict": item.answer_key["verdict"],
        "gold_certificate": item.answer_key.get("certificate"),
        "equivalence_flag": core.get("equivalent"),
        "private_difficulty_core": {
            key: core[key] for key in _PRIVATE_DIFFICULTY_CORE_KEYS if key in core
        },
        "private_fsm_a_metadata": {
            key: private_meta_a[key]
            for key in _PRIVATE_METADATA_KEYS
            if key in private_meta_a
        },
        "private_fsm_b_metadata": {
            key: private_meta_b[key]
            for key in _PRIVATE_METADATA_KEYS
            if key in private_meta_b
        },
        "generator_seed": item.difficulty.get("generator_seed"),
    }
    return EvaluatorOnly(payload=payload)


def collect_item_specific_gold_tokens(item: BenchmarkItem) -> set[str]:
    """Concrete gold strings that must not appear in model-visible payloads."""
    tokens: set[str] = set()
    evaluator = build_evaluator_only(item)
    gold_cert = evaluator.gold_certificate
    if isinstance(gold_cert, dict):
        payload = gold_cert.get("payload")
        if isinstance(payload, dict):
            for key in ("minimized_hash_A", "minimized_hash_B"):
                value = payload.get(key)
                if isinstance(value, str) and len(value) >= 16:
                    tokens.add(value)
            pairs = payload.get("pairs")
            if isinstance(pairs, list):
                # Do not treat common state names alone as gold tokens;
                # pair encodings of the full gold relation are sensitive.
                tokens.add(str(sorted(
                    (
                        (entry.get("state_a"), entry.get("state_b"))
                        for entry in pairs
                        if isinstance(entry, dict)
                    ),
                    key=lambda pair: (str(pair[0]), str(pair[1])),
                )))
    # Boolean equivalent flag as JSON literals is checked structurally, not as token.
    transform = (item.fsm_b.metadata or {}).get("equivalent_transform") if item.fsm_b else None
    if isinstance(transform, str) and transform:
        tokens.add(transform)
    return {token for token in tokens if token}

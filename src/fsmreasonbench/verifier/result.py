"""Verifier result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """Outcome of independent certificate verification."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def ok(cls) -> VerifyResult:
        return cls(valid=True)

    @classmethod
    def fail(cls, *errors: str) -> VerifyResult:
        return cls(valid=False, errors=errors)

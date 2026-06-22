"""Shared generate callable protocol for batch runners."""

from __future__ import annotations

from typing import Protocol


class GenerateFn(Protocol):
    def __call__(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str: ...

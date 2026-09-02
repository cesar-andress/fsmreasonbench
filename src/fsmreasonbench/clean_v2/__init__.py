"""Clean experimental harness (clean_v2) for scientifically auditable runs.

Legacy v1 paths remain immutable under ``legacy_v1`` interpretation.
This package never injects certificates on scientific paths and never
exposes evaluator-only gold to model-visible surfaces.
"""

from __future__ import annotations

from fsmreasonbench.clean_v2.versions import CLEAN_V2_NAMESPACE

__all__ = ["CLEAN_V2_NAMESPACE"]

"""CLI wiring tests for F1 R2 attribution ablation."""

from __future__ import annotations

import pytest

from fsmreasonbench.cli.run_f1_r2_attribution_ablation import (
    _resolve_max_items,
    _validate_openai_modes,
    main,
)
from fsmreasonbench.runners.r2_attribution_prompts import R2AttributionMode


def test_openai_rejects_non_r2c_modes() -> None:
    with pytest.raises(SystemExit, match="R2C only"):
        _validate_openai_modes([R2AttributionMode.R2A])


def test_openai_allows_r2c_mode() -> None:
    _validate_openai_modes([R2AttributionMode.R2C])


def test_smoke_max_items_openai_uses_one() -> None:
    args = pytest.importorskip("argparse").Namespace(
        smoke=True,
        provider="openai",
        max_items=100,
    )
    assert _resolve_max_items(args) == 1


def test_smoke_max_items_anthropic_uses_five() -> None:
    args = pytest.importorskip("argparse").Namespace(
        smoke=True,
        provider="anthropic",
        max_items=100,
    )
    assert _resolve_max_items(args) == 5


def test_openai_all_modes_rejected() -> None:
    with pytest.raises(SystemExit, match="does not support --all"):
        main(
            [
                "--provider",
                "openai",
                "--all",
                "--force",
                "--max-items",
                "1",
            ]
        )


def test_openai_r2a_mode_rejected_before_api() -> None:
    with pytest.raises(SystemExit, match="R2C only"):
        main(
            [
                "--provider",
                "openai",
                "--mode",
                "R2A",
                "--force",
                "--max-items",
                "1",
            ]
        )

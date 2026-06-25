"""CLI wiring tests for F1 R2 attribution ablation."""

from __future__ import annotations

import pytest

from fsmreasonbench.cli.run_f1_r2_attribution_ablation import (
    _default_oracle_dir,
    _default_parent_dir,
    _resolve_max_items,
)
from fsmreasonbench.runners.r2_attribution_prompts import R2AttributionMode


def test_openai_default_paths(tmp_path) -> None:
    parent = _default_parent_dir("openai", tmp_path)
    oracle = _default_oracle_dir("openai", tmp_path)
    assert parent.name == "ablations_f1_r2_attribution_gpt_n100_v1"
    assert oracle.name == "ablations_f1_oracle_verdict_format_control_gpt_n100_v1"


def test_anthropic_default_paths(tmp_path) -> None:
    parent = _default_parent_dir("anthropic", tmp_path)
    oracle = _default_oracle_dir("anthropic", tmp_path)
    assert parent.name == "ablations_f1_r2_attribution_claude_n100_v1"
    assert oracle.name == "ablations_f1_oracle_verdict_format_control_claude_n100_v1"


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


def test_modes_from_args_all_includes_r2a_r2b_r2c() -> None:
    from fsmreasonbench.cli.run_f1_r2_attribution_ablation import _modes_from_args

    args = pytest.importorskip("argparse").Namespace(all_modes=True, mode=None)
    modes = _modes_from_args(args)
    assert [mode.value for mode in modes] == ["R2A", "R2B", "R2C"]

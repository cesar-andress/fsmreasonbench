"""Tests for local matrix bootstrap export."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.evaluator.local_matrix_bootstrap_export import (
    analyze_local_matrix_bootstrap,
    export_local_matrix_bootstrap_package,
)


def test_local_matrix_bootstrap_has_twenty_four_cells() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    payload = analyze_local_matrix_bootstrap(repo_root, n_resamples=200, seed_base=4242)
    assert len(payload["cells"]) == 24
    assert payload["bootstrap_settings"]["n_resamples"] == 200
    assert payload["bootstrap_settings"]["method"] == "percentile_bootstrap"


def test_local_matrix_bootstrap_qwen_f1_r2_matches_frozen_point_rate() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    payload = analyze_local_matrix_bootstrap(repo_root, n_resamples=500, seed_base=4242)
    qwen = next(
        row
        for row in payload["cells"]
        if row["model"] == "qwen2.5-coder:7b" and row["family"] == "F1" and row["track"] == "R2"
    )
    full = qwen["metrics"]["fully_correct_rate"]
    assert full["rate"] == 0.3
    assert full["n"] == 100
    assert full["successes"] == 30
    assert full["ci_low"] <= full["rate"] <= full["ci_high"]


def test_export_local_matrix_bootstrap_writes_json_and_latex(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    json_out = tmp_path / "local_bootstrap.json"
    latex_out = tmp_path / "local_matrix.tex"
    payload = export_local_matrix_bootstrap_package(
        repo_root,
        json_out=json_out,
        latex_out=latex_out,
        n_resamples=200,
    )
    assert json_out.is_file()
    assert latex_out.is_file()
    assert "[0." in latex_out.read_text(encoding="utf-8")
    saved = json.loads(json_out.read_text(encoding="utf-8"))
    assert saved["cells"][0]["metrics"]["extractability_rate"]["ci_low"] is not None

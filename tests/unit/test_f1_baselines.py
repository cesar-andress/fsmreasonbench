"""F1 baseline CLI tests."""

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.generate_one import main as generate_one_main
from fsmreasonbench.cli.run_baseline import main as run_baseline_main
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item


SMOKE_CONFIG = SeparationGeneratorConfig(min_distinguishing_trace_length=1)


@pytest.fixture
def f1_item_path(tmp_path: Path) -> Path:
    item = generate_separation_item(42, SMOKE_CONFIG)
    path = tmp_path / "item_F1.json"
    path.write_text(json.dumps(item.to_full_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_generate_one_family_f1(capsys: pytest.CaptureFixture[str]) -> None:
    assert generate_one_main(["--family", "F1", "--seed", "42"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["family"] == "F1"
    assert "fsm_a" in payload
    assert "fsm_b" in payload


def test_run_baseline_oracle_f1(f1_item_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        run_baseline_main(
            ["--baseline", "oracle", "--item", str(f1_item_path), "--score"]
        )
        == 0
    )
    captured = capsys.readouterr()
    scoring = json.loads(captured.err)
    assert scoring["fully_correct"] is True


def test_run_baseline_invalid_f1(f1_item_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        run_baseline_main(
            ["--baseline", "invalid", "--item", str(f1_item_path), "--score"]
        )
        == 1
    )
    captured = capsys.readouterr()
    scoring = json.loads(captured.err)
    assert scoring["failure_stage"] == "not_extractable"

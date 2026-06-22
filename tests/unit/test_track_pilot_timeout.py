"""Track pilot timeout handling regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.cell_failure import ERROR_JSON, read_cell_error
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    format_cell_timeout_message,
    format_item_timeout_message,
    run_track_pilot_models,
)


def test_format_timeout_messages() -> None:
    assert format_cell_timeout_message(138.0) == "cell exceeded timeout of 138s"
    assert format_item_timeout_message(120.0) == "item request exceeded timeout of 120s"
    assert format_item_timeout_message(None) == "operation timed out (no item timeout configured)"


def test_item_timeout_error_without_cell_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(42)

    def fail_batch(*_args, **_kwargs) -> None:
        raise TimeoutError("simulated item timeout")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fail_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    out_dir = tmp_path / "matrix"
    run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock",),
            families=("C2",),
            tracks=("R0",),
            c2_items_path=".",
            f1_items_path=".",
            out_dir=out_dir,
            max_items=1,
            timeout=None,
            item_timeout=None,
            cell_timeout=None,
            skip_completed=False,
        ),
        lambda _m, _t: lambda *_a, **_k: "{}",
    )

    run_dir = out_dir / "mock" / "C2" / "R0"
    error = read_cell_error(run_dir)
    assert error is not None
    assert "Nones" not in error["error_message"]
    assert error["error_message"] == format_item_timeout_message(None)
    assert error["error_type"] == "timeout"


def test_cell_timeout_error_uses_cell_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(43)

    def slow_batch(*_args, **_kwargs) -> None:
        raise TimeoutError("simulated inner timeout")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        slow_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    class FakeFuture:
        def __init__(self) -> None:
            self._done = False

        def result(self, timeout=None):  # noqa: ANN001
            raise TimeoutError()

        def done(self) -> bool:
            return self._done

        def exception(self) -> None:
            return None

    class FakePool:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            _ = (args, kwargs)

        def submit(self, fn):  # noqa: ANN001
            _ = fn
            return FakeFuture()

        def shutdown(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            return None

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models.ThreadPoolExecutor",
        FakePool,
    )

    out_dir = tmp_path / "matrix"
    run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock",),
            families=("C2",),
            tracks=("R0",),
            c2_items_path=".",
            f1_items_path=".",
            out_dir=out_dir,
            max_items=1,
            timeout=120.0,
            cell_timeout=138.0,
            skip_completed=False,
        ),
        lambda _m, _t: lambda *_a, **_k: "{}",
    )

    run_dir = out_dir / "mock" / "C2" / "R0"
    payload = json.loads((run_dir / ERROR_JSON).read_text(encoding="utf-8"))
    assert payload["error_message"] == format_cell_timeout_message(138.0)

"""Pytest fixtures for clean_v2 tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.dev.doc_consistency import find_repo_root


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root()

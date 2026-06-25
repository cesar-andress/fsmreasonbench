"""Smoke tests for read-only TOSEM reproduction scripts (no inference)."""

from __future__ import annotations

from pathlib import Path


def test_reproduce_tosem_tables_script_exists_and_is_executable() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "reproduce_tosem_tables.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111
    text = script.read_text(encoding="utf-8")
    assert "export_tosem_empirical_package" in text
    assert "export_tmlr_empirical_package" in text
    assert "OPENAI" not in text.upper()


def test_reproduce_table_delegates_to_tosem_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    wrapper = repo_root / "scripts" / "reproduce_table.sh"
    text = wrapper.read_text(encoding="utf-8")
    assert "reproduce_tosem_tables.sh" in text

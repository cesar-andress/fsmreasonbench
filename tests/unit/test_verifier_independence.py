"""Verifier must not depend on oracle or generator modules."""

import ast
from pathlib import Path


def test_verifier_module_has_no_oracle_imports() -> None:
    verifier_dir = Path(__file__).resolve().parents[2] / "src" / "fsmreasonbench" / "verifier"
    forbidden = {"fsmreasonbench.oracle", "fsmreasonbench.generator", "fsmreasonbench.certificates"}
    for path in verifier_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name.startswith(prefix) for prefix in forbidden
                    ), f"{path.name} imports forbidden module {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(
                    node.module.startswith(prefix) for prefix in forbidden
                ), f"{path.name} imports forbidden module {node.module}"

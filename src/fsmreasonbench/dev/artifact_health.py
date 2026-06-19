"""Artifact health checks for local development and release prep."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import fsmreasonbench
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.items.assembly import self_verify_item

AVAILABLE_FAMILIES: tuple[tuple[str, str], ...] = (
    ("C2", "calibration"),
    ("F1", "flagship"),
)

DEFAULT_TESTS_COMMAND = "PYTHONPATH=src python3.11 -m pytest -v"


@dataclass(frozen=True, slots=True)
class ExampleVerifyResult:
    """Self-verification outcome for one example item."""

    path: str
    family: str
    ok: bool
    error: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactHealthReport:
    """Summary of artifact health signals."""

    package_version: str
    families: tuple[tuple[str, str], ...]
    schemas: tuple[str, ...]
    schema_version: str | None
    examples: tuple[ExampleVerifyResult, ...]
    tests_command: str

    @property
    def ok(self) -> bool:
        return (
            bool(self.schemas)
            and bool(self.examples)
            and all(example.ok for example in self.examples)
        )


def build_artifact_health_report(repo_root: Path | None = None) -> ArtifactHealthReport:
    """Collect artifact health information without reading ``runs/``."""
    root = repo_root or find_repo_root()
    schemas = discover_schemas(root)
    schema_version = read_schema_version(root)
    examples = verify_example_items(root)
    return ArtifactHealthReport(
        package_version=fsmreasonbench.__version__,
        families=AVAILABLE_FAMILIES,
        schemas=schemas,
        schema_version=schema_version,
        examples=examples,
        tests_command=suggest_tests_command(),
    )


def format_artifact_health_report(report: ArtifactHealthReport) -> str:
    """Render a human-readable health report."""
    lines = [
        "FSMReasonBench artifact health",
        "",
        f"Package version: {report.package_version}",
        "",
        "Available families:",
    ]
    for family, tier in report.families:
        lines.append(f"  - {family} ({tier})")

    lines.extend(["", f"Schemas present ({len(report.schemas)}):"])
    if report.schemas:
        lines.extend(f"  - {path}" for path in report.schemas)
    else:
        lines.append("  (none)")

    if report.schema_version is not None:
        lines.extend(["", f"Schema bundle version: {report.schema_version}"])

    lines.extend(["", "Example items (self-verify):"])
    if report.examples:
        for example in report.examples:
            status = "OK" if example.ok else "FAIL"
            lines.append(f"  [{status}] {example.path} ({example.family})")
            if example.error:
                lines.append(f"         {example.error}")
    else:
        lines.append("  (none)")

    lines.extend(["", f"Tests: {report.tests_command}", ""])
    if report.ok:
        lines.append("Status: healthy")
    else:
        lines.append("Status: unhealthy")
    return "\n".join(lines)


def discover_schemas(repo_root: Path) -> tuple[str, ...]:
    """List JSON schema files under ``schema/``."""
    schema_root = repo_root / "schema"
    if not schema_root.is_dir():
        return ()
    paths = sorted(
        path.relative_to(repo_root).as_posix()
        for path in schema_root.rglob("*.json")
        if path.is_file()
    )
    return tuple(paths)


def read_schema_version(repo_root: Path) -> str | None:
    """Read ``schema/VERSION`` when present."""
    version_path = repo_root / "schema" / "VERSION"
    if not version_path.is_file():
        return None
    return version_path.read_text(encoding="utf-8").strip()


def verify_example_items(repo_root: Path) -> tuple[ExampleVerifyResult, ...]:
    """Run self-verification on committed ``examples/item_*.json`` files."""
    examples_dir = repo_root / "examples"
    if not examples_dir.is_dir():
        return ()

    results: list[ExampleVerifyResult] = []
    for path in sorted(examples_dir.glob("item_*.json")):
        relative = path.relative_to(repo_root).as_posix()
        family = "?"
        try:
            item = load_item(path)
            family = item.family
            self_verify_item(item)
        except (AssertionError, ValueError, KeyError, TypeError) as exc:
            results.append(
                ExampleVerifyResult(
                    path=relative,
                    family=family,
                    ok=False,
                    error=str(exc),
                )
            )
        else:
            results.append(
                ExampleVerifyResult(
                    path=relative,
                    family=family,
                    ok=True,
                )
            )
    return tuple(results)


DEFAULT_TESTS_COMMAND = "PYTHONPATH=src python3.11 -m pytest -v"


def suggest_tests_command() -> str:
    """Suggest a pytest command using the current interpreter."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return DEFAULT_TESTS_COMMAND.replace("python3.11", f"python{version}")

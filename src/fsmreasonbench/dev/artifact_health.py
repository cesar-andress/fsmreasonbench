"""Artifact health checks for local development and release prep."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.items.assembly import self_verify_item

REQUIRED_SCHEMAS: tuple[str, ...] = (
    "schema/fsm.schema.json",
    "schema/question.schema.json",
    "schema/answer.schema.json",
    "schema/c2_submission.schema.json",
    "schema/certificate/separation.schema.json",
)

REQUIRED_EXAMPLES: tuple[str, ...] = (
    "examples/item_C2_reachability_seed42.json",
    "examples/item_F1_separation_seed42.json",
    "examples/item_F1_separation_seed6_hard.json",
)

REQUIRED_CLI_MODULES: tuple[str, ...] = (
    "fsmreasonbench.cli.generate_one",
    "fsmreasonbench.cli.generate_batch",
    "fsmreasonbench.cli.run_baseline",
    "fsmreasonbench.cli.run_c2_smoke_baselines",
    "fsmreasonbench.cli.run_f1_smoke_baselines",
    "fsmreasonbench.cli.run_capability_surface",
    "fsmreasonbench.cli.run_ollama_batch",
    "fsmreasonbench.cli.run_ollama_track_batch",
    "fsmreasonbench.cli.run_pilot_models",
    "fsmreasonbench.cli.run_track_pilot_models",
    "fsmreasonbench.cli.plot_local_matrix",
    "fsmreasonbench.cli.run_capability_surface_models",
    "fsmreasonbench.cli.plot_capability_surface",
    "fsmreasonbench.cli.export_capability_surface_report",
    "fsmreasonbench.cli.audit_f1_items",
)


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """Outcome of one artifact health check."""

    name: str
    ok: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ArtifactHealthReport:
    """Summary of artifact health signals."""

    checks: tuple[HealthCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def status(self) -> str:
        return "PASS" if self.ok else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }


def build_artifact_health_report(repo_root: Path | None = None) -> ArtifactHealthReport:
    """Collect artifact health information without reading ``runs/``."""
    root = repo_root or find_repo_root()
    checks = (
        check_package_import(),
        check_required_schemas(root),
        check_example_items(root),
        check_cli_imports(),
    )
    return ArtifactHealthReport(checks=checks)


def check_package_import() -> HealthCheck:
    """Verify the package imports and expose a version string."""
    try:
        import fsmreasonbench

        version = getattr(fsmreasonbench, "__version__", "")
        if not version:
            return HealthCheck(
                name="package_import",
                ok=False,
                message="fsmreasonbench imported but __version__ is missing",
            )
        return HealthCheck(
            name="package_import",
            ok=True,
            message=f"fsmreasonbench {version}",
        )
    except Exception as exc:  # noqa: BLE001 - report any import failure
        return HealthCheck(
            name="package_import",
            ok=False,
            message=str(exc),
        )


def check_required_schemas(repo_root: Path) -> HealthCheck:
    """Verify required JSON Schema files exist under the repository root."""
    missing = [
        relative_path
        for relative_path in REQUIRED_SCHEMAS
        if not (repo_root / relative_path).is_file()
    ]
    if missing:
        return HealthCheck(
            name="required_schemas",
            ok=False,
            message=f"missing: {', '.join(missing)}",
        )
    return HealthCheck(
        name="required_schemas",
        ok=True,
        message=f"{len(REQUIRED_SCHEMAS)}/{len(REQUIRED_SCHEMAS)} present",
    )


def check_example_items(repo_root: Path) -> HealthCheck:
    """Self-verify the committed reference example items."""
    failures: list[str] = []
    verified = 0
    for relative_path in REQUIRED_EXAMPLES:
        path = repo_root / relative_path
        if not path.is_file():
            failures.append(f"{relative_path}: missing")
            continue
        try:
            item = load_item(path)
            self_verify_item(item)
        except (AssertionError, ValueError, KeyError, TypeError, OSError) as exc:
            failures.append(f"{relative_path}: {exc}")
            continue
        verified += 1

    if failures:
        return HealthCheck(
            name="example_items",
            ok=False,
            message="; ".join(failures),
        )
    return HealthCheck(
        name="example_items",
        ok=True,
        message=f"{verified}/{len(REQUIRED_EXAMPLES)} self-verify",
    )


def check_cli_imports() -> HealthCheck:
    """Verify core CLI modules are importable."""
    failures: list[str] = []
    imported = 0
    for module_name in REQUIRED_CLI_MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 - report any import failure
            failures.append(f"{module_name}: {exc}")
            continue
        if not callable(getattr(module, "main", None)):
            failures.append(f"{module_name}: missing main()")
            continue
        imported += 1

    if failures:
        return HealthCheck(
            name="cli_imports",
            ok=False,
            message="; ".join(failures),
        )
    return HealthCheck(
        name="cli_imports",
        ok=True,
        message=f"{imported}/{len(REQUIRED_CLI_MODULES)} importable",
    )


def format_artifact_health_report(report: ArtifactHealthReport) -> str:
    """Render a human-readable health report."""
    lines = [
        "FSMReasonBench artifact health",
        "",
    ]
    for check in report.checks:
        status = "PASS" if check.ok else "FAIL"
        suffix = f": {check.message}" if check.message else ""
        lines.append(f"[{status}] {check.name}{suffix}")
    lines.extend(["", f"Status: {report.status}"])
    return "\n".join(lines)

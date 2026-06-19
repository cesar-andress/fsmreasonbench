"""Documentation consistency checks for the FSMReasonBench artifact."""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path

CANONICAL_IMPLEMENTED_FAMILIES = frozenset({"C2", "F1"})

DEFAULT_DOC_PATHS = (
    "PROJECT_STATUS.md",
    "README.md",
    "examples/README.md",
)

DEFAULT_DOC_GLOBS = (
    "docs/**/*.md",
)

SKIP_FILE_SUBSTRINGS = (
    "{",
    "}",
    "*",
    "<",
    ">",
    "...",
    "http://",
    "https://",
    "runs/",
    "README-RELEASE.md",
    "release_manifest.json",
    "SHA256SUMS",
    "1.0-public.manifest.json",
    "paper_reproduction/",
    "cohorts/",
    "evaluator/1.0-public",
    "BENCHMARK_SPEC-v",
    "requirements-lock.txt",
    "CONTAINER.md",
    "CITATION.cff",
    "ERRATA.md",
    "datasheet",
    "Zenodo DOI",
    ".zenodo.json",
)

SKIP_FILE_BASENAMES = frozenset(
    {
        "combined_summary.json",
        "combined_summary.csv",
        "scores.jsonl",
        "results.jsonl",
        "summary.json",
        "report.md",
        "c2_items.jsonl",
        "table_provenance.json",
        "manifest.json",
    }
)

CLI_MODULE_PATTERN = re.compile(r"fsmreasonbench\.cli\.([a-z][a-z0-9_]*)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BACKTICK_PATH_PATTERN = re.compile(
    r"`("
    r"(?:docs|examples|schema|src|scripts|tests)(?:/[^\s`]+)?"
    r"|(?:src/fsmreasonbench/)?(?:cli|evaluator|generator|oracle|verifier|baselines|"
    r"certificates|items|models|runners)/[^\s`]+"
    r"|[A-Za-z0-9_./-]+\.(?:md|json|py|csv|jsonl|tex|sh)"
    r")`"
)
FAMILY_ARG_PATTERN = re.compile(r"--family(?:ies)?\s+([A-Za-z0-9_,]+)")
STATUS_DOC_SUFFIXES = (
    "PROJECT_STATUS.md",
    "docs/zenodo/README.md",
)


@dataclass(frozen=True, slots=True)
class DocIssue:
    """Single documentation consistency problem."""

    path: str
    kind: str
    message: str
    detail: str = ""


@dataclass
class DocConsistencyReport:
    """Aggregated documentation check results."""

    issues: list[DocIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, issue: DocIssue) -> None:
        self.issues.append(issue)


def find_repo_root(start: Path | None = None) -> Path:
    """Locate repository root (directory containing pyproject.toml)."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "fsmreasonbench").exists():
            return candidate
    raise FileNotFoundError("could not locate fsmreasonbench repository root")


def discover_doc_files(repo_root: Path, extra_paths: tuple[str, ...] = ()) -> list[Path]:
    """Collect markdown files to scan."""
    paths: list[Path] = []
    for relative in DEFAULT_DOC_PATHS:
        path = repo_root / relative
        if path.exists():
            paths.append(path)
    for pattern in DEFAULT_DOC_GLOBS:
        paths.extend(sorted(repo_root.glob(pattern)))
    for relative in extra_paths:
        path = Path(relative)
        if not path.is_absolute():
            path = repo_root / path
        if path.exists():
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def check_documentation(
    repo_root: Path | None = None,
    *,
    extra_paths: tuple[str, ...] = (),
) -> DocConsistencyReport:
    """Run all documentation consistency checks."""
    root = repo_root or find_repo_root()
    report = DocConsistencyReport()
    doc_files = discover_doc_files(root, extra_paths=extra_paths)

    for doc_path in doc_files:
        text = doc_path.read_text(encoding="utf-8")
        _check_cli_modules(root, doc_path, text, report)
        _check_file_references(root, doc_path, text, report)
        _check_family_consistency(doc_path, text, report)

    return report


def format_report(report: DocConsistencyReport) -> str:
    """Render human-readable report."""
    if report.ok:
        return "Documentation consistency checks passed."
    lines = ["Documentation consistency issues:", ""]
    for issue in report.issues:
        lines.append(f"- [{issue.kind}] {issue.path}: {issue.message}")
        if issue.detail:
            lines.append(f"  {issue.detail}")
    return "\n".join(lines)


def _check_cli_modules(
    repo_root: Path,
    doc_path: Path,
    text: str,
    report: DocConsistencyReport,
) -> None:
    for module_name in sorted(set(CLI_MODULE_PATTERN.findall(text))):
        cli_path = repo_root / "src" / "fsmreasonbench" / "cli" / f"{module_name}.py"
        if cli_path.exists():
            continue
        report.add(
            DocIssue(
                path=str(doc_path.relative_to(repo_root)),
                kind="missing_cli",
                message=f"documented CLI module does not exist: fsmreasonbench.cli.{module_name}",
                detail=f"expected {cli_path.relative_to(repo_root)}",
            )
        )


def _check_file_references(
    repo_root: Path,
    doc_path: Path,
    text: str,
    report: DocConsistencyReport,
) -> None:
    candidates: set[str] = set()
    for match in MARKDOWN_LINK_PATTERN.findall(text):
        if not match.startswith("#"):
            candidates.add(match.strip())
    for match in BACKTICK_PATH_PATTERN.findall(text):
        candidates.add(match.strip())

    for raw in sorted(candidates):
        if _should_skip_file_reference(raw):
            continue
        resolved = resolve_doc_reference(repo_root, doc_path, raw)
        if resolved is None:
            report.add(
                DocIssue(
                    path=str(doc_path.relative_to(repo_root)),
                    kind="unresolved_reference",
                    message=f"could not resolve referenced path: {raw!r}",
                )
            )
        elif not resolved.exists():
            report.add(
                DocIssue(
                    path=str(doc_path.relative_to(repo_root)),
                    kind="missing_file",
                    message=f"referenced file does not exist: {raw!r}",
                    detail=f"checked {resolved.relative_to(repo_root)}",
                )
            )


def _check_family_consistency(
    doc_path: Path,
    text: str,
    report: DocConsistencyReport,
) -> None:
    relative = doc_path.as_posix()
    if relative.endswith(STATUS_DOC_SUFFIXES):
        for family in CANONICAL_IMPLEMENTED_FAMILIES:
            if family not in text:
                report.add(
                    DocIssue(
                        path=relative,
                        kind="family_status",
                        message=f"status document must mention implemented family {family}",
                    )
                )

    for match in FAMILY_ARG_PATTERN.findall(text):
        for token in match.split(","):
            family = token.strip()
            if family and family not in CANONICAL_IMPLEMENTED_FAMILIES:
                report.add(
                    DocIssue(
                        path=relative,
                        kind="family_cli",
                        message=f"documented --family value {family!r} is not in {{C2, F1}}",
                    )
                )

    for line_no, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "implemented" not in lowered and "currently implement" not in lowered:
            continue
        if any(
            phrase in lowered
            for phrase in (
                "not yet implemented",
                "not implemented",
                "specified but not",
                "specified, not",
                "are specified",
                " specified",
            )
        ):
            continue
        for family in ("F2", "F3", "F4", "C1", "T1", "T2", "T3", "T4", "T5", "T6", "T7"):
            if not re.search(rf"\b{family}\b", line):
                continue
            if re.search(rf"\b{family}\b[^|\n]{{0,40}}\bimplemented\b", line, re.IGNORECASE):
                report.add(
                    DocIssue(
                        path=relative,
                        kind="family_claim",
                        message=(
                            f"line {line_no} may claim non-implemented family {family} "
                            "is implemented"
                        ),
                        detail=line.strip(),
                    )
                )
            elif re.search(rf"\bimplemented\b[^|\n]{{0,40}}\b{family}\b", line, re.IGNORECASE):
                report.add(
                    DocIssue(
                        path=relative,
                        kind="family_claim",
                        message=(
                            f"line {line_no} may claim non-implemented family {family} "
                            "is implemented"
                        ),
                        detail=line.strip(),
                    )
                )


def _should_skip_file_reference(raw: str) -> bool:
    if not raw or raw.startswith("#"):
        return True
    if any(marker in raw for marker in SKIP_FILE_SUBSTRINGS):
        return True
    if raw.endswith("/"):
        return True
    if raw in {".", ".."}:
        return True
    basename = Path(raw.split("#", 1)[0]).name
    if basename in SKIP_FILE_BASENAMES and "/" not in raw.strip("/"):
        return True
    return False


def resolve_doc_reference(
    repo_root: Path,
    doc_path: Path,
    raw: str,
) -> Path | None:
    """Resolve a documentation path reference to an absolute path."""
    cleaned = raw.split("#", 1)[0].strip()
    if not cleaned or _should_skip_file_reference(cleaned):
        return None

    path = Path(cleaned)
    if path.is_absolute():
        return path

    candidates: list[Path] = []
    if cleaned.startswith(("docs/", "examples/", "schema/", "src/", "scripts/", "tests/")):
        candidates.append(repo_root / cleaned)
    if cleaned.startswith("src/fsmreasonbench/"):
        candidates.append(repo_root / cleaned)
    if cleaned.startswith(("cli/", "evaluator/", "generator/", "oracle/", "verifier/", "baselines/", "certificates/", "items/", "models/", "runners/")):
        candidates.append(repo_root / "src" / "fsmreasonbench" / cleaned)
    if cleaned.startswith("test_") and cleaned.endswith(".py"):
        candidates.append(repo_root / "tests" / "unit" / cleaned)
    if cleaned.endswith(".py") and "/" not in cleaned:
        candidates.extend(
            [
                repo_root / "src" / "fsmreasonbench" / "cli" / cleaned,
                repo_root / "src" / "fsmreasonbench" / "evaluator" / cleaned,
                repo_root / "scripts" / cleaned,
            ]
        )
    if cleaned.endswith(".md") and "/" not in cleaned:
        candidates.extend(
            [
                repo_root / "docs" / cleaned,
                repo_root / "docs" / "artifact" / cleaned,
            ]
        )
    if cleaned.endswith(".sh") and "/" not in cleaned:
        candidates.append(repo_root / "scripts" / cleaned)
    if "/" not in cleaned and cleaned.endswith((".json", ".md", ".csv", ".py")):
        candidates.extend(
            [
                doc_path.parent / cleaned,
                repo_root / "examples" / cleaned,
                repo_root / cleaned,
            ]
        )
    candidates.extend(
        [
            doc_path.parent / cleaned,
            repo_root / cleaned,
            repo_root / "src" / "fsmreasonbench" / cleaned,
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return resolved
    return candidates[0].resolve() if candidates else None


def cli_module_exists(repo_root: Path, module_name: str) -> bool:
    """Return True when ``fsmreasonbench.cli.<module_name>`` is present."""
    path = repo_root / "src" / "fsmreasonbench" / "cli" / f"{module_name}.py"
    return path.exists() and importlib.util.find_spec(f"fsmreasonbench.cli.{module_name}") is not None

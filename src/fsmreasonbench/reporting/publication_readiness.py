"""Publication readiness report for paper and release preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.cohort.validate import validate_cohort
from fsmreasonbench.dev.doc_consistency import CANONICAL_IMPLEMENTED_FAMILIES
from fsmreasonbench.evaluator.io import load_json

CheckStatus = Literal["PASS", "FAIL"]

ZENODO_PREP_DOCS: tuple[str, ...] = (
    "docs/zenodo/REPRODUCIBILITY.md",
    "docs/zenodo/RELEASE_CHECKLIST.md",
    "docs/zenodo/DATASET_STRUCTURE.md",
)

RELEASE_NOTES_GLOB = "docs/releases/*.md"

EVIDENCE_INVENTORY: tuple[tuple[str, str], ...] = (
    ("pilot_report", "docs/pilot_v*_report.md"),
    ("pilot_summary_json", "docs/pilot_v*_summary.json"),
    ("pilot_summary_csv", "docs/pilot_v*_summary.csv"),
    ("capability_surface_report", "docs/capability_surface_report.md"),
    ("capability_surface_summary_csv", "docs/capability_surface_summary.csv"),
    ("failure_taxonomy_report", "docs/*failure_taxonomy*report.md"),
    ("failure_taxonomy_json", "docs/*failure_taxonomy*.json"),
    ("f1_mixed_report", "docs/f1_mixed_*report.md"),
    ("f1_mixed_summary_csv", "docs/f1_mixed_*summary.csv"),
    ("f1_mixed_summary_tex", "docs/f1_mixed_*summary.tex"),
)

PAPER_TABLES_GLOB = "*.tex"


@dataclass(frozen=True, slots=True)
class ChecklistEntry:
    """One PASS/FAIL checklist row."""

    name: str
    status: CheckStatus
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class CohortSummary:
    """One discovered cohort snapshot."""

    cohort_dir: str
    cohort_id: str
    item_count: int | None
    cohort_fingerprint: str
    release_tier: str
    validation_status: CheckStatus
    validation_errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_dir": self.cohort_dir,
            "cohort_id": self.cohort_id,
            "item_count": self.item_count,
            "cohort_fingerprint": self.cohort_fingerprint,
            "release_tier": self.release_tier,
            "validation_status": self.validation_status,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    """One committed experimental or paper artifact."""

    path: str
    artifact_type: str
    last_modified: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "type": self.artifact_type,
            "last_modified": self.last_modified,
        }


@dataclass(frozen=True, slots=True)
class PublicationReadinessReport:
    """Structured publication readiness snapshot."""

    repo_root: str
    implemented_families: tuple[str, ...]
    frozen_cohort_count: int
    exploratory_cohort_count: int
    dataset_card_present: bool
    release_notes_present: bool
    zenodo_docs_present: bool
    cohorts: tuple[CohortSummary, ...]
    evidence: tuple[EvidenceArtifact, ...]
    reproducibility_checklist: tuple[ChecklistEntry, ...]
    paper_readiness_checklist: tuple[ChecklistEntry, ...]
    open_issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "implemented_families": list(self.implemented_families),
            "frozen_cohort_count": self.frozen_cohort_count,
            "exploratory_cohort_count": self.exploratory_cohort_count,
            "dataset_card_present": self.dataset_card_present,
            "release_notes_present": self.release_notes_present,
            "zenodo_docs_present": self.zenodo_docs_present,
            "cohorts": [cohort.to_dict() for cohort in self.cohorts],
            "evidence": [artifact.to_dict() for artifact in self.evidence],
            "reproducibility_checklist": [entry.to_dict() for entry in self.reproducibility_checklist],
            "paper_readiness_checklist": [entry.to_dict() for entry in self.paper_readiness_checklist],
            "open_issues": list(self.open_issues),
        }


def build_publication_readiness_report(repo_root: str | Path) -> PublicationReadinessReport:
    """Build a read-only publication readiness snapshot."""
    root = Path(repo_root).resolve()
    cohorts = _discover_cohorts(root)
    evidence = _discover_evidence(root)
    open_issues = _collect_open_issues(root, cohorts)

    frozen_count = sum(1 for cohort in cohorts if cohort.release_tier == "frozen")
    exploratory_count = sum(1 for cohort in cohorts if cohort.release_tier == "exploratory")

    dataset_card_present = (root / "docs/dataset_card.md").is_file()
    release_notes_present = bool(list(root.glob(RELEASE_NOTES_GLOB)))
    zenodo_docs_present = all((root / relative).is_file() for relative in ZENODO_PREP_DOCS)

    reproducibility_checklist = _build_reproducibility_checklist(
        root,
        cohorts,
        dataset_card_present,
        release_notes_present,
        zenodo_docs_present,
    )
    paper_readiness_checklist = _build_paper_readiness_checklist(
        root,
        cohorts,
        evidence,
        dataset_card_present,
    )

    return PublicationReadinessReport(
        repo_root=str(root),
        implemented_families=tuple(sorted(CANONICAL_IMPLEMENTED_FAMILIES)),
        frozen_cohort_count=frozen_count,
        exploratory_cohort_count=exploratory_count,
        dataset_card_present=dataset_card_present,
        release_notes_present=release_notes_present,
        zenodo_docs_present=zenodo_docs_present,
        cohorts=cohorts,
        evidence=evidence,
        reproducibility_checklist=reproducibility_checklist,
        paper_readiness_checklist=paper_readiness_checklist,
        open_issues=tuple(open_issues),
    )


def render_publication_readiness_report(report: PublicationReadinessReport) -> str:
    """Render the report as deterministic Markdown."""
    repo_label = Path(report.repo_root).name or report.repo_root
    lines = [
        "# Publication Readiness Report",
        "",
        f"Repository root: `{repo_label}`",
        "",
        "## Repository status",
        "",
        f"* **Implemented task families:** {', '.join(report.implemented_families) or 'none detected'}",
        f"* **Frozen cohorts:** {report.frozen_cohort_count}",
        f"* **Exploratory cohorts:** {report.exploratory_cohort_count}",
        f"* **Dataset card (`docs/dataset_card.md`):** {'present' if report.dataset_card_present else 'missing'}",
        f"* **Release notes (`docs/releases/`):** {'present' if report.release_notes_present else 'missing'}",
        f"* **Zenodo preparation docs:** {'present' if report.zenodo_docs_present else 'missing'}",
        "",
        "## Frozen cohorts",
        "",
    ]

    if report.cohorts:
        lines.extend(
            [
                "| cohort_id | item_count | cohort_fingerprint | validation_status |",
                "|-----------|------------|--------------------|-------------------|",
            ]
        )
        for cohort in report.cohorts:
            item_count = "—" if cohort.item_count is None else str(cohort.item_count)
            lines.append(
                f"| `{cohort.cohort_id}` | {item_count} | `{cohort.cohort_fingerprint}` | {cohort.validation_status} |"
            )
    else:
        lines.append("_No cohort manifests discovered under `cohorts/`._")

    lines.extend(["", "## Experimental evidence inventory", ""])

    if report.evidence:
        lines.extend(
            [
                "| path | type | last modified |",
                "|------|------|---------------|",
            ]
        )
        for artifact in report.evidence:
            lines.append(
                f"| `{artifact.path}` | {artifact.artifact_type} | {artifact.last_modified} |"
            )
    else:
        lines.append("_No matching experimental evidence artifacts detected._")

    lines.extend(["", "## Reproducibility checklist", ""])
    lines.extend(_render_checklist(report.reproducibility_checklist))
    lines.extend(["", "## Paper readiness checklist", ""])
    lines.extend(_render_checklist(report.paper_readiness_checklist))
    lines.extend(["", "## Open issues", ""])

    if report.open_issues:
        for issue in report.open_issues:
            lines.append(f"* {issue}")
    else:
        lines.append("* None detected.")

    lines.append("")
    return "\n".join(lines)


def write_publication_readiness_report(
    repo_root: str | Path,
    out_path: str | Path,
) -> PublicationReadinessReport:
    """Generate and write the publication readiness report (read-only on repo inputs)."""
    report = build_publication_readiness_report(repo_root)
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_publication_readiness_report(report), encoding="utf-8")
    return report


def _discover_cohorts(repo_root: Path) -> tuple[CohortSummary, ...]:
    cohorts_root = repo_root / "cohorts"
    if not cohorts_root.is_dir():
        return ()

    summaries: list[CohortSummary] = []
    for manifest_path in sorted(cohorts_root.glob("**/manifest.json")):
        cohort_dir = manifest_path.parent
        relative_dir = _relative_path(cohort_dir, repo_root)
        try:
            manifest = load_json(manifest_path)
        except (OSError, ValueError) as exc:
            summaries.append(
                CohortSummary(
                    cohort_dir=relative_dir,
                    cohort_id="<unreadable>",
                    item_count=None,
                    cohort_fingerprint="—",
                    release_tier="unknown",
                    validation_status="FAIL",
                    validation_errors=(f"failed to read manifest.json: {exc}",),
                )
            )
            continue

        validation = validate_cohort(cohort_dir)
        summaries.append(
            CohortSummary(
                cohort_dir=relative_dir,
                cohort_id=str(manifest.get("cohort_id", "<missing>")),
                item_count=_coerce_int(manifest.get("item_count")),
                cohort_fingerprint=str(manifest.get("cohort_fingerprint", "—")),
                release_tier=_cohort_release_tier(manifest),
                validation_status="PASS" if validation.valid else "FAIL",
                validation_errors=validation.errors,
            )
        )
    return tuple(summaries)


def _discover_evidence(repo_root: Path) -> tuple[EvidenceArtifact, ...]:
    artifacts: dict[str, EvidenceArtifact] = {}

    for artifact_type, pattern in EVIDENCE_INVENTORY:
        for path in sorted(repo_root.glob(pattern)):
            if path.is_file():
                relative = _relative_path(path, repo_root)
                artifacts[relative] = EvidenceArtifact(
                    path=relative,
                    artifact_type=artifact_type,
                    last_modified=_format_mtime(path),
                )

    paper_tables_root = repo_root.parent / "paper" / "tables"
    if paper_tables_root.is_dir():
        for path in sorted(paper_tables_root.glob(PAPER_TABLES_GLOB)):
            if path.is_file():
                relative = f"../paper/tables/{path.name}"
                artifacts[relative] = EvidenceArtifact(
                    path=relative,
                    artifact_type="paper_table",
                    last_modified=_format_mtime(path),
                )

    return tuple(artifacts[path] for path in sorted(artifacts))


def _build_reproducibility_checklist(
    repo_root: Path,
    cohorts: tuple[CohortSummary, ...],
    dataset_card_present: bool,
    release_notes_present: bool,
    zenodo_docs_present: bool,
) -> tuple[ChecklistEntry, ...]:
    cohort_dirs = _cohort_snapshot_dirs(repo_root)
    manifest_ok = bool(cohort_dirs) and all((path / "manifest.json").is_file() for path in cohort_dirs)
    checksums_ok = bool(cohort_dirs) and all((path / "sha256sums.txt").is_file() for path in cohort_dirs)
    readme_ok = bool(cohort_dirs) and all((path / "README.md").is_file() for path in cohort_dirs)
    validation_ok = bool(cohorts) and all(cohort.validation_status == "PASS" for cohort in cohorts)

    return (
        ChecklistEntry(
            "manifest.json present",
            "PASS" if manifest_ok else "FAIL",
            _cohort_file_detail(repo_root, cohort_dirs, "manifest.json"),
        ),
        ChecklistEntry(
            "sha256sums.txt present",
            "PASS" if checksums_ok else "FAIL",
            _cohort_file_detail(repo_root, cohort_dirs, "sha256sums.txt"),
        ),
        ChecklistEntry(
            "README.md present",
            "PASS" if readme_ok else "FAIL",
            _cohort_file_detail(repo_root, cohort_dirs, "README.md"),
        ),
        ChecklistEntry(
            "dataset card present",
            "PASS" if dataset_card_present else "FAIL",
            "docs/dataset_card.md",
        ),
        ChecklistEntry(
            "release notes present",
            "PASS" if release_notes_present else "FAIL",
            RELEASE_NOTES_GLOB,
        ),
        ChecklistEntry(
            "reproducibility docs present",
            "PASS" if zenodo_docs_present else "FAIL",
            ", ".join(ZENODO_PREP_DOCS),
        ),
        ChecklistEntry(
            "frozen cohort validation passes",
            "PASS" if validation_ok else "FAIL",
            "all discovered cohort manifests pass validate_cohort",
        ),
    )


def _build_paper_readiness_checklist(
    repo_root: Path,
    cohorts: tuple[CohortSummary, ...],
    evidence: tuple[EvidenceArtifact, ...],
    dataset_card_present: bool,
) -> tuple[ChecklistEntry, ...]:
    evidence_types = {artifact.artifact_type for artifact in evidence}

    def _doc(path: str) -> bool:
        return (repo_root / path).is_file()

    return (
        ChecklistEntry(
            "benchmark specification documented",
            "PASS" if _doc("docs/specification/BENCHMARK_SPEC.md") else "FAIL",
            "docs/specification/BENCHMARK_SPEC.md",
        ),
        ChecklistEntry(
            "certificate formats documented",
            "PASS" if _doc("docs/specification/certificate_formats.md") else "FAIL",
            "docs/specification/certificate_formats.md",
        ),
        ChecklistEntry(
            "reproducibility documented",
            "PASS" if _doc("docs/zenodo/REPRODUCIBILITY.md") else "FAIL",
            "docs/zenodo/REPRODUCIBILITY.md",
        ),
        ChecklistEntry(
            "exploratory results documented",
            "PASS"
            if {"pilot_report", "capability_surface_report", "f1_mixed_report"} & evidence_types
            else "FAIL",
            "pilot, capability surface, or F1 mixed report present in docs/",
        ),
        ChecklistEntry(
            "frozen cohorts available",
            "PASS" if cohorts else "FAIL",
            "at least one cohort manifest under cohorts/",
        ),
        ChecklistEntry(
            "capability surface available",
            "PASS" if "capability_surface_report" in evidence_types else "FAIL",
            "docs/capability_surface_report.md",
        ),
        ChecklistEntry(
            "failure taxonomy available",
            "PASS"
            if any("failure_taxonomy" in artifact.path for artifact in evidence)
            else "FAIL",
            "docs/*failure_taxonomy*report.md",
        ),
        ChecklistEntry(
            "dataset card available",
            "PASS" if dataset_card_present else "FAIL",
            "docs/dataset_card.md",
        ),
    )


def _collect_open_issues(
    repo_root: Path,
    cohorts: tuple[CohortSummary, ...],
) -> list[str]:
    issues: list[str] = []

    cohort_ids = [cohort.cohort_id for cohort in cohorts if cohort.cohort_id not in {"<missing>", "<unreadable>"}]
    seen: set[str] = set()
    for cohort_id in cohort_ids:
        if cohort_id in seen:
            issues.append(f"duplicate cohort_id detected: `{cohort_id}`")
        seen.add(cohort_id)

    for cohort in cohorts:
        if cohort.validation_status == "FAIL":
            detail = "; ".join(cohort.validation_errors[:3])
            if len(cohort.validation_errors) > 3:
                detail += f"; … ({len(cohort.validation_errors)} errors total)"
            issues.append(
                f"invalid cohort `{cohort.cohort_id}` at `{cohort.cohort_dir}`: {detail or 'validation failed'}"
            )

    for cohort_dir in _cohort_snapshot_dirs(repo_root):
        relative = _relative_path(cohort_dir, repo_root)
        if not (cohort_dir / "manifest.json").is_file():
            issues.append(f"missing manifest.json in `{relative}`")
        if (cohort_dir / "items.jsonl").is_file() and not (cohort_dir / "manifest.json").is_file():
            issues.append(f"items.jsonl present without manifest in `{relative}`")

    if not (repo_root / "docs/dataset_card.md").is_file():
        issues.append("missing documentation: docs/dataset_card.md")
    if not list(repo_root.glob(RELEASE_NOTES_GLOB)):
        issues.append("missing documentation: docs/releases/*.md")
    for relative in ZENODO_PREP_DOCS:
        if not (repo_root / relative).is_file():
            issues.append(f"missing documentation: {relative}")

    return sorted(dict.fromkeys(issues))


def _cohort_snapshot_dirs(repo_root: Path) -> list[Path]:
    cohorts_root = repo_root / "cohorts"
    if not cohorts_root.is_dir():
        return []

    dirs: set[Path] = set()
    for manifest_path in cohorts_root.glob("**/manifest.json"):
        dirs.add(manifest_path.parent)
    for items_path in cohorts_root.glob("**/items.jsonl"):
        dirs.add(items_path.parent)
    return sorted(dirs, key=lambda path: str(path.relative_to(repo_root)))


def _cohort_release_tier(manifest: dict[str, Any]) -> str:
    release_tier = manifest.get("release_tier")
    if release_tier == "exploratory":
        return "exploratory"
    manifest_version = str(manifest.get("manifest_version", ""))
    if "exploratory" in manifest_version:
        return "exploratory"
    if release_tier in {None, "", "public"} or "public" in manifest_version:
        return "frozen"
    return "frozen"


def _cohort_file_detail(repo_root: Path, cohort_dirs: list[Path], filename: str) -> str:
    if not cohort_dirs:
        return "no cohort snapshot directories discovered"
    missing = [
        _relative_path(path, repo_root) for path in cohort_dirs if not (path / filename).is_file()
    ]
    if missing:
        return f"missing {filename} in: {', '.join(missing)}"
    return f"{filename} present in all {len(cohort_dirs)} cohort snapshot directories"


def _relative_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _format_mtime(path: Path) -> str:
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).replace(microsecond=0)
    return timestamp.isoformat().replace("+00:00", "Z")


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _render_checklist(entries: tuple[ChecklistEntry, ...]) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        line = f"* **{entry.name}:** {entry.status}"
        if entry.detail:
            line += f" — {entry.detail}"
        lines.append(line)
    return lines

#!/usr/bin/env python3
"""Archival QA audit — checks links, paths, DOI consistency, freeze alignment."""
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT.parent / "paper"
CANONICAL_DOI = "10.5281/zenodo.20897937"
OLD_DOI = "10.5281/zenodo.20836348"
GITHUB_RELEASE = "https://github.com/cesar-andress/fsmreasonbench/releases/tag/v1.0.0"


@dataclass
class Item:
    category: str
    component: str
    status: str  # pass | fail | warn
    detail: str = ""


results: list[Item] = []


def add(category: str, component: str, ok: bool, detail: str = "", warn: bool = False) -> None:
    if ok:
        status = "pass"
    elif warn:
        status = "warn"
    else:
        status = "fail"
    results.append(Item(category, component, status, detail))


def audit_doi() -> None:
    add("doi", f"canonical DOI {CANONICAL_DOI}", True)
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or path.suffix in {".pyc"}:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if OLD_DOI in text and "legacy" not in str(path) and path.name not in {
            "archival_qa_audit.py",
            "_archival_qa_audit.json",
        }:
            add("doi", f"stale DOI in {path.relative_to(ROOT)}", False, OLD_DOI)
    # ARTIFACT_VERSION + manifest
    av = (ROOT / "ARTIFACT_VERSION").read_text()
    add("doi", "ARTIFACT_VERSION", CANONICAL_DOI in av and "v1.0.0" in av)
    manifest = json.loads((ROOT / "releases/1.0.0/release_manifest.json").read_text())
    add(
        "doi",
        "release_manifest.json zenodo.primary_doi",
        manifest["zenodo"]["primary_doi"] == CANONICAL_DOI,
    )


def audit_markdown_links() -> None:
    link_re = re.compile(r"\]\(([^)]+)\)")
    for md in sorted(ROOT.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in link_re.finditer(text):
            target = m.group(1).split("#")[0].split("?")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (md.parent / target).resolve()
            ok = resolved.exists()
            add(
                "readme_link",
                f"{md.relative_to(ROOT)} → {target}",
                ok,
                str(resolved) if not ok else "",
            )


def audit_scripts() -> None:
    scripts = [
        "scripts/reproduce_tosem_tables.sh",
        "scripts/archival_qa_audit.py",
    ]
    for s in scripts:
        add("script", s, (ROOT / s).exists())
    manifest = json.loads((ROOT / "releases/1.0.0/release_manifest.json").read_text())
    for name, cmd in manifest.get("reproduction", {}).items():
        if "-m " not in cmd:
            continue
        mod = cmd.split("-m ")[1].split()[0]
        parts = mod.split(".")
        cli_path = ROOT / "src" / Path(*parts[:-1]) / f"{parts[-1]}.py"
        add("script", f"cli {mod} ({name})", cli_path.exists(), str(cli_path))


def audit_paper_assets() -> None:
    if not PAPER.exists():
        add("manuscript", "paper/ directory", False, "monorepo sibling missing")
        return
    add("manuscript", "paper/ directory", True)
    fig_refs: set[str] = set()
    tab_refs: set[str] = set()
    for tex in PAPER.rglob("*.tex"):
        text = tex.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            fig_refs.add(m.group(1))
        for m in re.finditer(r"\\input\{([^}]+)\}", text):
            ref = m.group(1)
            if ref.startswith("sections/") or ref.startswith("appendix/") or ref == "macros":
                p = PAPER / f"{ref}.tex" if not ref.endswith(".tex") else PAPER / ref
            else:
                p = PAPER / f"{ref}.tex"
            add(
                "manuscript_table",
                f"\\input{{{ref}}}",
                p.exists(),
                str(p),
            )
    for fig in sorted(fig_refs):
        p = PAPER / fig
        add("manuscript_figure", fig, p.exists(), str(p))


def campaign_roots(paths: set[str]) -> set[str]:
    roots: set[str] = set()
    for p in paths:
        p = p.rstrip("/")
        parts = p.split("/")
        if len(parts) >= 2 and parts[0] == "runs":
            roots.add(f"runs/{parts[1]}/")
    return roots


def audit_freeze_alignment() -> None:
    art_freeze = ROOT / "docs/EXPERIMENTAL_FREEZE_TOSEM.md"
    paper_freeze = PAPER / "EXPERIMENTAL_FREEZE_TOSEM.md"
    add("freeze", "artifact docs/EXPERIMENTAL_FREEZE_TOSEM.md", art_freeze.exists())
    add("freeze", "paper EXPERIMENTAL_FREEZE_TOSEM.md", paper_freeze.exists())
    if art_freeze.exists() and paper_freeze.exists():
        art_paths = set(re.findall(r"`(runs/[^`*]+)`", art_freeze.read_text()))
        paper_paths = {
            m.replace("fsmreasonbench/", "")
            for m in re.findall(r"`fsmreasonbench/(runs/[^`*]+)`", paper_freeze.read_text())
        }
        for m in re.finditer(
            r"`fsmreasonbench/(runs/[^`]*\{[^}]+\}[^`]*)`", paper_freeze.read_text()
        ):
            template = m.group(1)
            for expanded in re.findall(r"\{([^}]+)\}", template):
                for part in expanded.split(","):
                    paper_paths.add(template.replace("{" + expanded + "}", part.strip()))
        art_roots = campaign_roots(art_paths | paper_paths)
        paper_roots = campaign_roots(paper_paths)
        # TOSEM paper claims use campaign roots listed in artifact summary table.
        art_summary_roots = campaign_roots(art_paths)
        missing_in_paper = sorted(art_summary_roots - paper_roots)
        add(
            "freeze",
            "campaign roots in paper cover artifact summary",
            not missing_in_paper,
            str(missing_in_paper[:5]),
        )
    for rp in sorted(set(re.findall(r"`(runs/[^`*]+)`", art_freeze.read_text()))):
        if "*" in rp:
            add("freeze_run", rp, True, "glob pattern (excluded runs)")
            continue
        p = ROOT / rp
        add("freeze_run", rp, p.exists())


def audit_package_manifests() -> None:
    for manifest_path in [
        ROOT / "docs/tosem_empirical_package_v1/package_manifest.json",
        ROOT / "docs/tmlr_empirical_package_v1/package_manifest.json",
        ROOT / "docs/a1_constructible_equivalence_v1/constructible_equivalence_analysis.json",
    ]:
        add("export", str(manifest_path.relative_to(ROOT)), manifest_path.exists())


def main() -> int:
    audit_doi()
    audit_markdown_links()
    audit_scripts()
    audit_paper_assets()
    audit_freeze_alignment()
    audit_package_manifests()

    fails = [r for r in results if r.status == "fail"]
    warns = [r for r in results if r.status == "warn"]
    passes = [r for r in results if r.status == "pass"]

    print(f"PASS={len(passes)} WARN={len(warns)} FAIL={len(fails)}")
    for r in fails[:50]:
        print(f"FAIL [{r.category}] {r.component} — {r.detail}")
    out = ROOT / "docs" / "_archival_qa_audit.json"
    out.write_text(
        json.dumps([r.__dict__ for r in results], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

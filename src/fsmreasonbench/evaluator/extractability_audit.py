"""Extractability and metric-denominator audit for matrix experiment cells."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records

CELL_SCORES_RE = re.compile(
    r"(?P<model_dir>[^/]+)/(?P<family>C2|F1)/temp_(?P<temp>[^/]+)/(?P<track>R0|R1|R2)/scores\.jsonl$"
)


@dataclass(frozen=True, slots=True)
class CellExtractabilityAudit:
    model_dir: str
    family: str
    temperature: float
    track: str
    scores_path: str
    total_items: int
    extractable_items: int
    non_extractable_items: int
    verdict_denominator: int
    certificate_denominator: int
    verdict_scored_items: int
    certificate_scored_items: int
    verdict_correct_items: int
    certificate_valid_items: int
    extractability_rate: float
    verdict_accuracy: float
    certificate_valid_rate: float
    fully_correct_rate: float
    summary_on_disk: dict[str, Any] | None
    denominators_match: bool
    summary_matches_scores: bool

    @property
    def model(self) -> str:
        return self.model_dir.replace("_", ":", 1).replace("_", "/")


def audit_cell_scores(scores_path: Path, *, root: Path) -> CellExtractabilityAudit | None:
    rel = scores_path.relative_to(root).as_posix()
    match = CELL_SCORES_RE.search(rel)
    if match is None:
        return None

    records = [ScoringRecord.from_dict(row) for row in read_jsonl(scores_path)]
    summary = summarize_scoring_records(records)
    total = len(records)
    extractable = sum(1 for record in records if record.extractable)
    verdict_scored = sum(1 for record in records if record.verdict_correct is not None)
    certificate_scored = sum(1 for record in records if record.certificate_valid is not None)
    verdict_correct = sum(1 for record in records if record.verdict_correct is True)
    certificate_valid = sum(1 for record in records if record.certificate_valid is True)

    summary_path = scores_path.parent / "summary.json"
    summary_on_disk = None
    if summary_path.exists():
        summary_on_disk = json.loads(summary_path.read_text(encoding="utf-8"))

    summary_matches = True
    if summary_on_disk is not None:
        summary_matches = (
            abs(float(summary_on_disk.get("verdict_accuracy", 0.0)) - summary["verdict_accuracy"])
            < 1e-9
            and abs(
                float(summary_on_disk.get("certificate_valid_rate", 0.0))
                - summary["certificate_valid_rate"]
            )
            < 1e-9
        )

    return CellExtractabilityAudit(
        model_dir=match.group("model_dir"),
        family=match.group("family"),
        temperature=float(match.group("temp")),
        track=match.group("track"),
        scores_path=str(scores_path),
        total_items=total,
        extractable_items=extractable,
        non_extractable_items=total - extractable,
        verdict_denominator=extractable,
        certificate_denominator=extractable,
        verdict_scored_items=verdict_scored,
        certificate_scored_items=certificate_scored,
        verdict_correct_items=verdict_correct,
        certificate_valid_items=certificate_valid,
        extractability_rate=float(summary["extractability_rate"]),
        verdict_accuracy=float(summary["verdict_accuracy"]),
        certificate_valid_rate=float(summary["certificate_valid_rate"]),
        fully_correct_rate=float(summary["fully_correct_rate"]),
        summary_on_disk=summary_on_disk,
        denominators_match=(
            verdict_scored == certificate_scored == extractable
        ),
        summary_matches_scores=summary_matches,
    )


def audit_matrix_scores(root: str | Path) -> list[CellExtractabilityAudit]:
    root_path = Path(root)
    audits: list[CellExtractabilityAudit] = []
    for scores_path in sorted(root_path.rglob("scores.jsonl")):
        row = audit_cell_scores(scores_path, root=root_path)
        if row is not None:
            audits.append(row)
    return audits


def render_extractability_audit_markdown(
    audits: list[CellExtractabilityAudit],
    *,
    root: str | Path,
    expected_items_per_cell: int = 20,
) -> str:
    root_path = Path(root)
    lines = [
        "# Extractability Audit",
        "",
        f"**Source:** `{root_path}`",
        f"**Cells audited:** {len(audits)}",
        "",
        "## Denominator policy (code)",
        "",
        "From `summarize_scoring_records()` in `evaluator/summary.py`:",
        "",
        "| Metric | Numerator | Denominator |",
        "|--------|-----------|-------------|",
        "| `extractability_rate` | extractable items | **total items** (`n`) |",
        "| `verdict_accuracy` | items with `verdict_correct is True` | **extractable items** |",
        "| `certificate_valid_rate` | items with `certificate_valid is True` | **extractable items** |",
        "| `fully_correct_rate` | items with `fully_correct is True` | **total items** (`n`) |",
        "",
        "**Conclusion:** `verdict_accuracy` and `certificate_valid_rate` share the same denominator: "
        "the count of extractable items, not total items.",
        "",
        "## Audit summary",
        "",
    ]

    all_match = all(row.denominators_match for row in audits)
    summary_match = all(row.summary_matches_scores for row in audits)
    partial = [row for row in audits if row.total_items < expected_items_per_cell]

    lines.extend(
        [
            f"- **Verdict/certificate denominators identical in all cells:** {all_match}",
            f"- **`summary.json` matches recomputation from `scores.jsonl`:** {summary_match}",
            f"- **Partial cells (< {expected_items_per_cell} scored items):** {len(partial)}",
            "",
        ]
    )

    if partial:
        lines.extend(["### Partial cells", ""])
        for row in partial:
            lines.append(
                f"- `{row.model_dir}` / {row.family} / {row.track} / T={row.temperature:g}: "
                f"{row.total_items}/{expected_items_per_cell} items"
            )
        lines.append("")

    for family in ("C2", "F1"):
        family_rows = [row for row in audits if row.family == family]
        if not family_rows:
            continue
        lines.extend([f"## {family}", ""])
        lines.append(
            "| Model | Track | Temp | Total | Extractable | Non-extractable | "
            "Verdict denom. | Cert denom. | Verdict acc. | Cert valid | Fully correct |"
        )
        lines.append(
            "|-------|-------|-----:|------:|------------:|----------------:|"
            "--------------:|------------:|-------------:|-----------:|--------------:|"
        )
        for row in sorted(
            family_rows,
            key=lambda r: (r.model_dir, r.temperature, r.track),
        ):
            lines.append(
                "| `{model}` | {track} | {temp:g} | {total} | {extractable} | {non} | "
                "{vd} | {cd} | {va:.3f} | {cv:.3f} | {fc:.3f} |".format(
                    model=row.model_dir,
                    track=row.track,
                    temp=row.temperature,
                    total=row.total_items,
                    extractable=row.extractable_items,
                    non=row.non_extractable_items,
                    vd=row.verdict_denominator,
                    cd=row.certificate_denominator,
                    va=row.verdict_accuracy,
                    cv=row.certificate_valid_rate,
                    fc=row.fully_correct_rate,
                )
            )
        lines.append("")

    mismatches = [row for row in audits if not row.denominators_match]
    if mismatches:
        lines.extend(["## Denominator mismatches", ""])
        for row in mismatches:
            lines.append(
                f"- `{row.scores_path}`: verdict_scored={row.verdict_scored_items}, "
                f"certificate_scored={row.certificate_scored_items}, "
                f"extractable={row.extractable_items}"
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation notes",
            "",
            "- Non-extractable items (`extractable=false`) are excluded from both "
            "`verdict_accuracy` and `certificate_valid_rate`; they still count toward "
            "`extractability_rate` and `fully_correct_rate` denominators differently.",
            "- On extractable items with wrong verdict, the certificate is still validated; "
            "both metrics remain conditioned on extractability only.",
            "- Compare delegation gaps using cells with the same extractable denominator, "
            "especially when extractability drops sharply (e.g. R2 tool-protocol failures).",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"

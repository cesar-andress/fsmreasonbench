"""Plan reruns for local matrix experiments from integrity audit rules."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.evaluator.extractability_audit import (
    CellExtractabilityAudit,
    audit_matrix_scores,
)
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.runners.experiment_cells import detect_cell_status
from fsmreasonbench.runners.track_pilot_models import build_cell_dir

CellTier = Literal["safe", "marginal", "unsafe", "partial", "missing"]
RerunTier = Literal["mandatory", "recommended"]
ExtendedCellStatus = Literal[
    "completed",
    "failed",
    "missing",
    "partial",
    "running",
    "stale-running",
]

# Reference thresholds at max_items=20 (scaled proportionally elsewhere).
SAFE_MIN_EXTRACTABLE = 15
MARGINAL_MIN_EXTRACTABLE = 10
MANDATORY_MAX_EXTRACTABLE = 5
RECOMMENDED_MAX_EXTRACTABLE = 10
LOW_EXTRACTABILITY_RATE = 0.5

INFRA_PARSE_PATTERNS = (
    re.compile(r"connection refused", re.I),
    re.compile(r"remote end closed", re.I),
    re.compile(r"timed out", re.I),
)
PARSER_FAILURE_PATTERNS = (
    re.compile(r"^timed out$", re.I),
    re.compile(r"connection refused", re.I),
    re.compile(r"remote end closed", re.I),
)

SKIP_ROOT_DIRS = frozenset({"plots", "rerun_plans"})


@dataclass(frozen=True, slots=True)
class MatrixCellRef:
    model: str
    family: str
    temperature: float
    track: str

    def key(self) -> tuple[str, str, float, str]:
        return (self.model, self.family, self.temperature, self.track)


@dataclass(frozen=True, slots=True)
class CellIntegritySnapshot:
    ref: MatrixCellRef
    tier: CellTier
    total_items: int
    extractable_items: int
    max_items: int
    extended_status: ExtendedCellStatus | None = None
    extractability_rate: float = 0.0
    reasons: tuple[str, ...] = ()
    infra_failure_items: int = 0
    parser_failure_items: int = 0
    scores_path: str | None = None
    run_dir: str | None = None

    @property
    def infrastructure_flagged(self) -> bool:
        if self.tier in {"missing", "partial"}:
            return False
        if self.infra_failure_items == 0 and self.parser_failure_items == 0:
            return False
        if self.infra_failure_items >= 3:
            return True
        if self.total_items > 0 and self.infra_failure_items / self.total_items >= 0.25:
            return True
        if self.parser_failure_items >= 3 and self.extractable_items < MARGINAL_MIN_EXTRACTABLE:
            return True
        return False


@dataclass(frozen=True, slots=True)
class RerunCommandGroup:
    models: tuple[str, ...]
    families: tuple[str, ...]
    tracks: tuple[str, ...]
    temperatures: tuple[float, ...]
    cells: tuple[MatrixCellRef, ...]
    tier: RerunTier

    def to_command(
        self,
        *,
        out_dir: Path,
        max_items: int,
        timeout: float,
        incremental_safe: bool,
    ) -> str:
        return build_track_pilot_command(
            models=self.models,
            families=self.families,
            tracks=self.tracks,
            temperatures=self.temperatures,
            out_dir=out_dir,
            max_items=max_items,
            timeout=timeout,
            incremental_safe=incremental_safe,
        )


@dataclass(frozen=True, slots=True)
class RerunPlan:
    root: Path
    max_items: int
    models: tuple[str, ...]
    families: tuple[str, ...]
    tracks: tuple[str, ...]
    temperatures: tuple[float, ...]
    cells: tuple[CellIntegritySnapshot, ...]
    mandatory_groups: tuple[RerunCommandGroup, ...]
    recommended_groups: tuple[RerunCommandGroup, ...]

    def tier_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "safe": 0,
            "marginal": 0,
            "unsafe": 0,
            "partial": 0,
            "missing": 0,
        }
        for cell in self.cells:
            counts[cell.tier] += 1
        return counts

    def cells_by_tier(self, tier: CellTier) -> tuple[CellIntegritySnapshot, ...]:
        return tuple(cell for cell in self.cells if cell.tier == tier)


def model_dir_to_name(model_dir: str) -> str:
    return model_dir.replace("_", ":", 1).replace("_", "/")


def discover_matrix_models(root: Path) -> tuple[str, ...]:
    models: list[str] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name in SKIP_ROOT_DIRS:
            continue
        if (child / "C2").is_dir() or (child / "F1").is_dir():
            models.append(model_dir_to_name(child.name))
    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        for model in payload.get("models", []) or []:
            name = str(model)
            if name not in models:
                models.append(name)
    return tuple(sorted(set(models)))


def _audit_key(audit: CellExtractabilityAudit) -> tuple[str, str, float, str]:
    return (audit.model, audit.family, audit.temperature, audit.track)


def _count_failure_items(scores_path: Path) -> tuple[int, int]:
    infra = 0
    parser = 0
    for row in read_jsonl(scores_path):
        errors = row.get("parse_errors") or []
        if not isinstance(errors, list):
            continue
        for error in errors:
            text = str(error)
            if any(pattern.search(text) for pattern in INFRA_PARSE_PATTERNS):
                infra += 1
            elif any(pattern.search(text) for pattern in PARSER_FAILURE_PATTERNS):
                parser += 1
            elif text.strip():
                parser += 1
    return infra, parser


def scaled_extractability_thresholds(max_items: int) -> tuple[int, int, int, int]:
    """Return safe_min, marginal_min, mandatory_max, recommended_max for ``max_items``."""
    scale = max_items / 20.0
    return (
        max(1, round(SAFE_MIN_EXTRACTABLE * scale)),
        max(1, round(MARGINAL_MIN_EXTRACTABLE * scale)),
        max(1, round(MANDATORY_MAX_EXTRACTABLE * scale)),
        max(1, round(RECOMMENDED_MAX_EXTRACTABLE * scale)),
    )


def _classify_tier(
    *,
    total_items: int,
    extractable_items: int,
    max_items: int,
    present: bool,
    extended_status: ExtendedCellStatus | None = None,
) -> CellTier:
    safe_min, marginal_min, _, _ = scaled_extractability_thresholds(max_items)
    if not present or extended_status == "missing":
        return "missing"
    if extended_status in {"failed", "running", "stale-running"}:
        return "partial"
    if extended_status == "partial" or total_items < max_items:
        return "partial"
    if extractable_items >= safe_min:
        return "safe"
    if extractable_items >= marginal_min:
        return "marginal"
    return "unsafe"


def _resolve_extended_status(
    run_dir: Path,
    *,
    total_items: int,
    max_items: int,
) -> ExtendedCellStatus:
    detected = detect_cell_status(run_dir)
    if detected in {"running", "stale-running", "failed"}:
        return detected
    if total_items <= 0:
        return "missing"
    if total_items < max_items:
        return "partial"
    return "completed"


def _extractability_rate(total_items: int, extractable_items: int) -> float:
    if total_items <= 0:
        return 0.0
    return extractable_items / total_items


def _snapshot_from_scores(
    *,
    ref: MatrixCellRef,
    run_dir: Path,
    total_items: int,
    extractable_items: int,
    max_items: int,
    scores_path: str,
) -> CellIntegritySnapshot:
    infra, parser = _count_failure_items(Path(scores_path))
    rate = _extractability_rate(total_items, extractable_items)
    extended_status = _resolve_extended_status(
        run_dir,
        total_items=total_items,
        max_items=max_items,
    )
    tier = _classify_tier(
        total_items=total_items,
        extractable_items=extractable_items,
        max_items=max_items,
        present=True,
        extended_status=extended_status,
    )
    return CellIntegritySnapshot(
        ref=ref,
        tier=tier,
        total_items=total_items,
        extractable_items=extractable_items,
        max_items=max_items,
        extended_status=extended_status,
        extractability_rate=rate,
        infra_failure_items=infra,
        parser_failure_items=parser,
        scores_path=scores_path,
        run_dir=str(run_dir),
    )


def _mandatory_reasons(cell: CellIntegritySnapshot) -> tuple[str, ...]:
    _, _, mandatory_max, _ = scaled_extractability_thresholds(cell.max_items)
    reasons: list[str] = []
    if cell.tier == "missing":
        reasons.append("missing cell")
    if cell.extended_status == "failed":
        reasons.append("failed cell")
    if cell.extended_status == "running":
        reasons.append("running cell")
    if cell.extended_status == "stale-running":
        reasons.append("stale-running cell")
    if cell.tier == "partial":
        reasons.append(f"partial ({cell.total_items}/{cell.max_items} items)")
    if cell.total_items > 0 and cell.extractability_rate < LOW_EXTRACTABILITY_RATE:
        reasons.append(
            f"extractability_rate<{LOW_EXTRACTABILITY_RATE:.0%} "
            f"({cell.extractable_items}/{cell.total_items})"
        )
    elif cell.tier not in {"missing", "partial"} and cell.extractable_items < mandatory_max:
        reasons.append(
            f"extractable<{mandatory_max} ({cell.extractable_items}/{cell.max_items})"
        )
    return tuple(dict.fromkeys(reasons))


def _recommended_reasons(cell: CellIntegritySnapshot) -> tuple[str, ...]:
    if _mandatory_reasons(cell):
        return ()
    _, marginal_min, _, recommended_max = scaled_extractability_thresholds(cell.max_items)
    reasons: list[str] = []
    if marginal_min <= cell.extractable_items < recommended_max:
        reasons.append(
            f"extractable<{recommended_max} ({cell.extractable_items}/{cell.max_items})"
        )
    if cell.infrastructure_flagged:
        reasons.append(
            f"infrastructure/parser failures ({cell.infra_failure_items} infra, "
            f"{cell.parser_failure_items} parser items)"
        )
    return tuple(reasons)


def build_track_pilot_command(
    *,
    models: tuple[str, ...],
    families: tuple[str, ...],
    tracks: tuple[str, ...],
    temperatures: tuple[float, ...],
    out_dir: Path,
    max_items: int,
    timeout: float,
    incremental_safe: bool,
) -> str:
    model_arg = ",".join(models)
    temp_arg = ",".join(str(t) for t in temperatures)
    parts = [
        "PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models",
        f"--models {model_arg}",
        f"--families {','.join(families)}",
        f"--tracks {','.join(tracks)}",
        f"--temperatures {temp_arg}",
        f"--max-items {max_items}",
        f"--timeout {timeout:g}",
        f"--out-dir {out_dir}",
        "--retry-failed",
    ]
    if incremental_safe:
        parts.append("--incremental-safe")
    return " \\\n  ".join(parts)


def group_rerun_cells(
    cells: tuple[MatrixCellRef, ...],
    *,
    tier: RerunTier,
) -> tuple[RerunCommandGroup, ...]:
    if not cells:
        return ()

    cell_index: dict[tuple[str, str, float, str], MatrixCellRef] = {
        cell.key(): cell for cell in cells
    }
    per_model_family: dict[tuple[str, str], list[MatrixCellRef]] = defaultdict(list)
    for cell in cells:
        per_model_family[(cell.model, cell.family)].append(cell)

    groups: list[RerunCommandGroup] = []
    for (model, family), refs in sorted(per_model_family.items()):
        temp_to_tracks: dict[float, set[str]] = defaultdict(set)
        for ref in refs:
            temp_to_tracks[ref.temperature].add(ref.track)

        trackset_to_temps: dict[frozenset[str], set[float]] = defaultdict(set)
        for temp, track_set in temp_to_tracks.items():
            trackset_to_temps[frozenset(track_set)].add(temp)

        for tracks, temps in sorted(
            trackset_to_temps.items(),
            key=lambda item: (sorted(item[0]), sorted(item[1])),
        ):
            group_cells = tuple(
                sorted(
                    (
                        cell_index[(model, family, temp, track)]
                        for temp in temps
                        for track in tracks
                    ),
                    key=lambda ref: (ref.temperature, ref.track),
                )
            )
            groups.append(
                RerunCommandGroup(
                    models=(model,),
                    families=(family,),
                    tracks=tuple(sorted(tracks)),
                    temperatures=tuple(sorted(temps)),
                    cells=group_cells,
                    tier=tier,
                )
            )
    return tuple(groups)


def scan_matrix_integrity(
    root: Path,
    *,
    models: tuple[str, ...] | None = None,
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = ("R0", "R1", "R2"),
    temperatures: tuple[float, ...] = (0.0, 0.2, 0.7),
    max_items: int = 20,
) -> tuple[CellIntegritySnapshot, ...]:
    root_path = root.resolve()
    resolved_models = models or discover_matrix_models(root_path)
    audits = {_audit_key(row): row for row in audit_matrix_scores(root_path)}
    snapshots: list[CellIntegritySnapshot] = []

    for model in resolved_models:
        for family in families:
            for temperature in temperatures:
                for track in tracks:
                    run_dir = build_cell_dir(
                        root_path,
                        model,
                        family,
                        temperature,
                        track,
                        matrix_layout=True,
                    )
                    ref = MatrixCellRef(
                        model=model,
                        family=family,
                        temperature=temperature,
                        track=track,
                    )
                    key = ref.key()
                    audit = audits.get(key)
                    scores_path = run_dir / "scores.jsonl"

                    if audit is not None:
                        snapshots.append(
                            _snapshot_from_scores(
                                ref=ref,
                                run_dir=run_dir,
                                total_items=audit.total_items,
                                extractable_items=audit.extractable_items,
                                max_items=max_items,
                                scores_path=audit.scores_path,
                            )
                        )
                        continue

                    if scores_path.exists():
                        records = read_jsonl(scores_path)
                        extractable = sum(1 for row in records if row.get("extractable"))
                        snapshots.append(
                            _snapshot_from_scores(
                                ref=ref,
                                run_dir=run_dir,
                                total_items=len(records),
                                extractable_items=extractable,
                                max_items=max_items,
                                scores_path=str(scores_path),
                            )
                        )
                    else:
                        extended_status = detect_cell_status(run_dir)
                        snapshots.append(
                            CellIntegritySnapshot(
                                ref=ref,
                                tier="missing",
                                total_items=0,
                                extractable_items=0,
                                max_items=max_items,
                                extended_status=extended_status,
                                extractability_rate=0.0,
                                run_dir=str(run_dir),
                            )
                        )

    return tuple(
        sorted(
            snapshots,
            key=lambda row: (
                row.ref.model,
                row.ref.family,
                row.ref.temperature,
                row.ref.track,
            ),
        )
    )


def build_rerun_plan(
    root: Path,
    *,
    models: tuple[str, ...] | None = None,
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = ("R0", "R1", "R2"),
    temperatures: tuple[float, ...] = (0.0, 0.2, 0.7),
    max_items: int = 20,
    timeout: float = 900.0,
    incremental_safe: bool = True,
) -> RerunPlan:
    root_path = root.resolve()
    resolved_models = models or discover_matrix_models(root_path)
    cells = scan_matrix_integrity(
        root_path,
        models=resolved_models,
        families=families,
        tracks=tracks,
        temperatures=temperatures,
        max_items=max_items,
    )

    mandatory_refs: list[MatrixCellRef] = []
    recommended_refs: list[MatrixCellRef] = []

    for cell in cells:
        if _mandatory_reasons(cell):
            mandatory_refs.append(cell.ref)
        elif _recommended_reasons(cell):
            recommended_refs.append(cell.ref)

    mandatory_groups = group_rerun_cells(tuple(mandatory_refs), tier="mandatory")
    recommended_groups = group_rerun_cells(tuple(recommended_refs), tier="recommended")

    return RerunPlan(
        root=root_path,
        max_items=max_items,
        models=resolved_models,
        families=families,
        tracks=tracks,
        temperatures=temperatures,
        cells=cells,
        mandatory_groups=mandatory_groups,
        recommended_groups=recommended_groups,
    )


def render_rerun_plan_summary(plan: RerunPlan) -> str:
    counts = plan.tier_counts()
    lines = [
        f"# Rerun plan — {plan.root}",
        "",
        "## Summary",
        "",
        f"- **Expected cells:** {len(plan.cells)}",
        f"- **Safe:** {counts['safe']}",
        f"- **Marginal:** {counts['marginal']}",
        f"- **Unsafe:** {counts['unsafe']}",
        f"- **Partial:** {counts['partial']}",
        f"- **Missing:** {counts['missing']}",
        "",
        f"- **Mandatory rerun cells:** {len(plan.mandatory_groups)} command group(s), "
        f"{sum(len(group.cells) for group in plan.mandatory_groups)} cell(s)",
        f"- **Recommended rerun cells:** {len(plan.recommended_groups)} command group(s), "
        f"{sum(len(group.cells) for group in plan.recommended_groups)} cell(s)",
        "",
    ]

    for tier in ("missing", "partial", "unsafe", "marginal", "safe"):
        tier_cells = plan.cells_by_tier(tier)
        if not tier_cells:
            continue
        lines.extend([f"## {tier.title()} cells", ""])
        lines.append("| Model | Family | Track | Temp | n | Extractable | Rate | Status | Notes |")
        lines.append("|-------|--------|-------|-----:|--:|------------:|-----:|--------|-------|")
        for cell in tier_cells:
            notes = "; ".join(_mandatory_reasons(cell) + _recommended_reasons(cell)) or "—"
            lines.append(
                "| `{model}` | {family} | {track} | {temp:g} | {n} | {ext} | {rate} | {status} | {notes} |".format(
                    model=cell.ref.model,
                    family=cell.ref.family,
                    track=cell.ref.track,
                    temp=cell.ref.temperature,
                    n=cell.total_items,
                    ext=cell.extractable_items,
                    rate=f"{cell.extractability_rate:.0%}" if cell.total_items else "—",
                    status=cell.extended_status or cell.tier,
                    notes=notes.replace("|", "\\|"),
                )
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_rerun_shell_script(
    plan: RerunPlan,
    groups: tuple[RerunCommandGroup, ...],
    *,
    title: str,
    timeout: float,
    incremental_safe: bool,
) -> str:
    repo_root_hint = "$(cd \"$(dirname \"$0\")/../../..\" && pwd)"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"# {title}",
        f"# Generated for {plan.root}",
        "",
        f"REPO_ROOT={repo_root_hint}",
        "cd \"$REPO_ROOT\"",
        "",
    ]
    if not groups:
        lines.append("echo \"No rerun commands planned.\"")
        return "\n".join(lines) + "\n"

    for index, group in enumerate(groups, start=1):
        cell_desc = ", ".join(
            f"{ref.family}/{ref.track}/T={ref.temperature:g}" for ref in group.cells
        )
        lines.extend(
            [
                f"echo \"[{index}/{len(groups)}] {group.models[0]} — {cell_desc}\"",
                group.to_command(
                    out_dir=plan.root,
                    max_items=plan.max_items,
                    timeout=timeout,
                    incremental_safe=incremental_safe,
                ),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_rerun_plan_artifacts(
    plan: RerunPlan,
    out_dir: Path,
    *,
    timeout: float,
    incremental_safe: bool,
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    summary_md = render_rerun_plan_summary(plan)
    summary_path = out_dir / "summary.md"
    summary_path.write_text(summary_md, encoding="utf-8")
    paths["summary_md"] = str(summary_path)

    plan_json = {
        "root": str(plan.root),
        "max_items": plan.max_items,
        "models": list(plan.models),
        "families": list(plan.families),
        "tracks": list(plan.tracks),
        "temperatures": list(plan.temperatures),
        "tier_counts": plan.tier_counts(),
        "cells": [
            {
                **asdict(cell.ref),
                "tier": cell.tier,
                "total_items": cell.total_items,
                "extractable_items": cell.extractable_items,
                "extractability_rate": cell.extractability_rate,
                "extended_status": cell.extended_status,
                "mandatory_reasons": list(_mandatory_reasons(cell)),
                "recommended_reasons": list(_recommended_reasons(cell)),
                "infra_failure_items": cell.infra_failure_items,
                "parser_failure_items": cell.parser_failure_items,
                "scores_path": cell.scores_path,
                "run_dir": cell.run_dir,
            }
            for cell in plan.cells
        ],
        "mandatory_groups": [
            {
                "models": list(group.models),
                "families": list(group.families),
                "tracks": list(group.tracks),
                "temperatures": list(group.temperatures),
                "cells": [asdict(ref) for ref in group.cells],
            }
            for group in plan.mandatory_groups
        ],
        "recommended_groups": [
            {
                "models": list(group.models),
                "families": list(group.families),
                "tracks": list(group.tracks),
                "temperatures": list(group.temperatures),
                "cells": [asdict(ref) for ref in group.cells],
            }
            for group in plan.recommended_groups
        ],
    }
    plan_path = out_dir / "plan.json"
    plan_path.write_text(json.dumps(plan_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["plan_json"] = str(plan_path)

    mandatory_path = out_dir / "mandatory_rerun.sh"
    mandatory_path.write_text(
        render_rerun_shell_script(
            plan,
            plan.mandatory_groups,
            title="Mandatory reruns (missing, partial, failed, running, extractability < 50%)",
            timeout=timeout,
            incremental_safe=incremental_safe,
        ),
        encoding="utf-8",
    )
    mandatory_path.chmod(mandatory_path.stat().st_mode | 0o111)
    paths["mandatory_sh"] = str(mandatory_path)

    recommended_path = out_dir / "recommended_rerun.sh"
    recommended_path.write_text(
        render_rerun_shell_script(
            plan,
            plan.recommended_groups,
            title="Recommended reruns (marginal extractability, infrastructure failures)",
            timeout=timeout,
            incremental_safe=incremental_safe,
        ),
        encoding="utf-8",
    )
    recommended_path.chmod(recommended_path.stat().st_mode | 0o111)
    paths["recommended_sh"] = str(recommended_path)

    return paths

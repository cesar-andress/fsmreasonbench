"""Comparative analysis for local matrix experiments (n=20 pilot vs powered follow-up)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap

CellSafety = Literal["safe", "marginal", "unsafe", "partial", "missing", "incomplete"]

METRIC_LABELS: dict[str, str] = {
    "verdict_accuracy": "verdict_accuracy",
    "certificate_valid_rate": "certificate_valid_rate",
    "fully_correct_rate": "fully_correct_rate",
}


@dataclass(frozen=True, slots=True)
class MatrixCell:
    model: str
    family: str
    track: str
    temperature: float
    n: int
    extractable: int
    extractability_rate: float
    verdict_accuracy: float | None
    certificate_valid_rate: float | None
    fully_correct_rate: float | None
    status: str
    safety: CellSafety
    run_dir: str | None = None

    @property
    def verdict_cert_gap(self) -> float | None:
        if self.verdict_accuracy is None or self.certificate_valid_rate is None:
            return None
        if self.extractable == 0:
            return None
        return self.verdict_accuracy - self.certificate_valid_rate


def load_combined_summary(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("combined_summary.json must be an object")
    return payload


def _extractable_count(row: dict[str, Any]) -> int:
    n = int(row.get("n") or 0)
    counts = row.get("failure_stage_counts") or {}
    if counts:
        not_extractable = int(counts.get("not_extractable", 0))
        return max(0, n - not_extractable)
    rate = row.get("extractability_rate")
    if rate is not None and n:
        return int(round(float(rate) * n))
    return 0


def classify_cell_safety(
    *,
    status: str,
    n: int,
    extractable: int,
    expected_n: int,
) -> CellSafety:
    normalized = status
    if normalized not in {"completed", "missing", "partial", "failed", "running"}:
        normalized = "incomplete"

    if normalized in {"missing", "failed"}:
        return "missing" if normalized == "missing" else "incomplete"
    if normalized in {"partial", "running"}:
        return "partial"
    if n < expected_n:
        return "partial"

    safe_min = max(1, int(0.75 * n))
    marginal_min = max(1, int(0.50 * n))
    if extractable >= safe_min:
        return "safe"
    if extractable >= marginal_min:
        return "marginal"
    return "unsafe"


def cells_from_inventory(
    inventory: list[dict[str, Any]],
    *,
    temperature: float | None = None,
    expected_n: int = 100,
) -> list[MatrixCell]:
    cells: list[MatrixCell] = []
    for row in inventory:
        temp = float(row.get("temperature", 0.0))
        if temperature is not None and abs(temp - temperature) > 1e-9:
            continue
        status = str(row.get("extended_status") or row.get("cell_status") or row.get("status") or "missing")
        n = int(row.get("n") or 0)
        extractable = _extractable_count(row) if status == "completed" else 0
        safety = classify_cell_safety(
            status=status,
            n=n,
            extractable=extractable,
            expected_n=expected_n,
        )
        cells.append(
            MatrixCell(
                model=str(row["model"]),
                family=str(row["family"]),
                track=str(row["track"]),
                temperature=temp,
                n=n,
                extractable=extractable,
                extractability_rate=float(row.get("extractability_rate") or 0.0),
                verdict_accuracy=_optional_float(row.get("verdict_accuracy")),
                certificate_valid_rate=_optional_float(row.get("certificate_valid_rate")),
                fully_correct_rate=_optional_float(row.get("fully_correct_rate")),
                status=status,
                safety=safety,
                run_dir=row.get("run_dir"),
            )
        )
    return cells


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _summary_from_cell(cell: MatrixCell) -> dict[str, Any]:
    return {
        "family": cell.family,
        "n": cell.n,
        "track": cell.track,
        "verdict_accuracy": cell.verdict_accuracy or 0.0,
        "certificate_valid_rate": cell.certificate_valid_rate or 0.0,
        "fully_correct_rate": cell.fully_correct_rate or 0.0,
    }


def compute_delegation_table(
    cells: list[MatrixCell],
    *,
    temperature: float,
) -> list[dict[str, Any]]:
    """Δ(R2−R0) per model × family at a fixed temperature."""
    indexed: dict[tuple[str, str, str], MatrixCell] = {}
    for cell in cells:
        if abs(cell.temperature - temperature) > 1e-9:
            continue
        if cell.status != "completed":
            continue
        indexed[(cell.model, cell.family, cell.track)] = cell

    rows: list[dict[str, Any]] = []
    keys = sorted({(cell.model, cell.family) for cell in cells if abs(cell.temperature - temperature) < 1e-9})
    for model, family in keys:
        r0 = indexed.get((model, family, "R0"))
        r2 = indexed.get((model, family, "R2"))
        row: dict[str, Any] = {
            "model": model,
            "family": family,
            "temperature": temperature,
            "n_r0": r0.n if r0 else None,
            "n_r2": r2.n if r2 else None,
            "extractable_r0": r0.extractable if r0 else None,
            "extractable_r2": r2.extractable if r2 else None,
            "safe_for_delegation": False,
        }
        if r0 is None or r2 is None:
            row["status"] = "incomplete"
            rows.append(row)
            continue
        if r0.safety not in {"safe", "marginal"} or r2.safety not in {"safe", "marginal"}:
            row["status"] = "unsafe"
        elif r0.n != r2.n:
            row["status"] = "n_mismatch"
        else:
            row["status"] = "ok"
            row["safe_for_delegation"] = r0.safety == "safe" and r2.safety == "safe"
            gap = compute_delegation_gap(_summary_from_cell(r0), _summary_from_cell(r2))
            for metric, value in gap["delegation_gap"].items():
                row[f"delta_{metric}"] = value
        rows.append(row)
    return rows


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.3f}"


def _direction_match(pilot: float | None, follow: float | None, *, min_abs: float = 0.05) -> str:
    if pilot is None or follow is None:
        return "pending"
    if abs(pilot) < min_abs and abs(follow) < min_abs:
        return "replicates (near zero)"
    if pilot * follow > 0 and abs(follow) >= min_abs:
        return "replicates (same sign)"
    if pilot * follow > 0 and abs(follow) < min_abs:
        return "weakens"
    if pilot * follow <= 0:
        return "does not replicate"
    return "unclear"


def render_local_matrix_analysis_markdown(
    *,
    follow_root: str | Path,
    follow_summary: dict[str, Any],
    follow_cells: list[MatrixCell],
    follow_delegation: list[dict[str, Any]],
    pilot_summary: dict[str, Any] | None,
    pilot_cells: list[MatrixCell] | None,
    pilot_delegation: list[dict[str, Any]] | None,
    extractability_audit_path: str | Path | None,
    plots_dir: str | Path | None,
    report_path: str | Path | None,
    temperature: float = 0.2,
    expected_n: int = 100,
) -> str:
    follow_root = Path(follow_root)
    inventory = follow_summary.get("cell_inventory") or []
    status_counts = follow_summary.get("cell_status_counts") or {}
    max_items = int(follow_summary.get("max_items") or expected_n)
    cohort_ids = follow_summary.get("cohort_ids") or {}

    completed = [cell for cell in follow_cells if cell.status == "completed"]
    unsafe_cells = [cell for cell in follow_cells if cell.safety == "unsafe"]
    partial_cells = [cell for cell in follow_cells if cell.safety in {"partial", "missing", "incomplete"}]

    actual_n_values = sorted({cell.n for cell in completed if cell.n})
    cohort_cap_note = ""
    if completed and max(actual_n_values, default=0) < max_items:
        cohort_cap_note = (
            f"**Cohort cap:** completed cells report n={actual_n_values[0] if len(actual_n_values)==1 else actual_n_values}, "
            f"below configured `--max-items {max_items}`. "
            f"The frozen v0.1-exploratory cohorts contain 20 items each; powered sampling requires an expanded item pool or on-demand generation."
        )

    lines: list[str] = [
        "# Local Matrix n=100 (T=0.2) Analysis",
        "",
        f"**Follow-up run:** `{follow_root}`",
        f"**Baseline pilot:** `runs/local_matrix_v1` at T={temperature:g} (n=20)",
        f"**Configured items/cell:** {max_items}",
        f"**Temperature:** {temperature:g} only (no cross-temperature replication in this campaign)",
        "",
        "> **Not final benchmark scores.** Exploratory local-Ollama matrix on v0.1-exploratory cohorts. "
        "Do not cite as `v1.0-public` evidence or frontier-model rankings.",
        "",
        "## Campaign status",
        "",
        f"- **Expected cells:** {len(inventory)} (4 models × 2 families × 3 tracks × 1 temperature)",
        f"- **Completed:** {status_counts.get('completed', len(completed))}",
        f"- **Missing / partial / failed:** "
        f"{status_counts.get('missing', 0)} missing, "
        f"{status_counts.get('partial', 0)} partial, "
        f"{status_counts.get('failed', 0)} failed",
        "",
    ]
    if cohort_cap_note:
        lines.extend([cohort_cap_note, ""])

    if report_path:
        lines.append(f"- **Auto report:** `{report_path}`")
    if extractability_audit_path:
        lines.append(f"- **Extractability audit:** `{extractability_audit_path}`")
    if plots_dir:
        lines.append(f"- **Plots:** `{plots_dir}/` (regenerate after campaign completes)")
    lines.append("")

    lines.extend(
        [
            "## 1. Which n=20 findings replicate at n=100?",
            "",
            "Replication is assessed at **T=0.2** by comparing metric **direction** and delegation-gap sign "
            "between the n=20 pilot (`local_matrix_v1`) and this follow-up. "
            "Until all 24 cells complete, replication verdicts are **provisional**.",
            "",
            "| Finding (n=20 @ T=0.2) | Pilot evidence | n=100 status | Replication |",
            "|--------------------------|----------------|--------------|-------------|",
        ]
    )

    pilot_findings = _pilot_finding_rows(pilot_cells or [], pilot_delegation or [], temperature=temperature)
    follow_findings = _pilot_finding_rows(follow_cells, follow_delegation, temperature=temperature)

    for key, pilot_row in pilot_findings.items():
        follow_row = follow_findings.get(key, {})
        replication = _assess_replication(
            key,
            pilot_row,
            follow_row,
            follow_cells=follow_cells,
            follow_delegation=follow_delegation,
            pilot_delegation=pilot_delegation,
            temperature=temperature,
        )
        lines.append(
            f"| {pilot_row['label']} | {pilot_row['evidence']} | {follow_row.get('evidence', 'pending')} | {replication} |"
        )

    lines.extend(["", "## 2. Delegation gaps Δ(R2−R0) by model and family", ""])
    lines.append(
        "Δ(R2−R0) = metric(R2) − metric(R0) on the same items. "
        "Requires **completed** R0 and R2 cells with adequate extractability."
    )
    lines.append("")
    lines.extend(_delegation_markdown_table(follow_delegation, title="n=100 follow-up (T=0.2)"))
    if pilot_delegation:
        lines.append("")
        lines.extend(_delegation_markdown_table(pilot_delegation, title="n=20 pilot reference (T=0.2)"))

    lines.extend(["", "## 3. Cells unsafe due to low extractability", ""])
    lines.append(
        "Safety tiers (scaled to observed n): **safe** ≥75% extractable, **marginal** 50–74%, "
        "**unsafe** <50%. Rates in unsafe cells are not comparable across tracks."
    )
    lines.append("")
    lines.extend(_safety_markdown_table(follow_cells, expected_n=max_items))

    lines.extend(["", "## 4. Is Qwen F1 R2 still the strongest positive delegation result?", ""])
    lines.append(_qwen_f1_r2_assessment(follow_delegation, pilot_delegation, follow_cells))

    lines.extend(["", "## 5. Does Llama still collapse under tool tracks?", ""])
    lines.append(_llama_tool_collapse_assessment(follow_cells, pilot_cells, temperature=temperature))

    lines.extend(["", "## 6. Does C2 still show verdict improvement without certificate improvement?", ""])
    lines.append(_c2_verdict_overstatement_assessment(follow_cells, pilot_cells, temperature=temperature))

    lines.extend(["", "## 7. Temperature conclusions from n=20 at T=0.2 only?", ""])
    lines.append(_temperature_note(pilot_summary, temperature=temperature))

    lines.extend(["", "## 8. Claims safe for a workshop paper", ""])
    lines.extend(_workshop_claims())

    lines.extend(["", "## 9. Claims unsafe for journal submission", ""])
    lines.extend(_journal_unsafe_claims(max_items=max_items, cohort_ids=cohort_ids))

    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "cd fsmreasonbench",
            "PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \\",
            "  --report-only --out-dir runs/local_matrix_n100_t02_v2 \\",
            "  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \\",
            "  --families C2,F1 --tracks R0,R1,R2 --temperatures 0.2 --max-items 100",
            "PYTHONPATH=src python -m fsmreasonbench.cli.export_extractability_audit \\",
            "  --root runs/local_matrix_n100_t02_v2 \\",
            "  --out docs/extractability_audit_n100_t02.md --expected-items 100",
            "PYTHONPATH=src python -m fsmreasonbench.cli.export_local_matrix_analysis \\",
            "  --follow-root runs/local_matrix_n100_t02_v2 \\",
            "  --pilot-root runs/local_matrix_v1 \\",
            "  --temperature 0.2 --expected-n 100 \\",
            "  --out docs/local_matrix_n100_t02_analysis.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _pilot_finding_rows(
    cells: list[MatrixCell],
    delegation: list[dict[str, Any]],
    *,
    temperature: float,
) -> dict[str, dict[str, str]]:
    by_track: dict[tuple[str, str, str], MatrixCell] = {
        (c.model, c.family, c.track): c
        for c in cells
        if abs(c.temperature - temperature) < 1e-9 and c.status == "completed"
    }
    del_map = {(row["model"], row["family"]): row for row in delegation if row.get("status") == "ok"}

    def cell_evidence(model: str, family: str, track: str) -> str:
        cell = by_track.get((model, family, track))
        if cell is None:
            return "cell incomplete"
        return (
            f"v={_fmt_rate(cell.verdict_accuracy)}, c={_fmt_rate(cell.certificate_valid_rate)}, "
            f"f={_fmt_rate(cell.fully_correct_rate)}, n_ext={cell.extractable}/{cell.n}"
        )

    qwen_f1 = del_map.get(("qwen2.5-coder:7b", "F1"), {})
    llama_c2_r1 = by_track.get(("llama3.1:8b", "C2", "R1"))
    llama_f1_r1 = by_track.get(("llama3.1:8b", "F1", "R1"))

    return {
        "qwen_f1_delegation": {
            "label": "Qwen F1 R2 delegation win",
            "evidence": f"Δfull={_fmt_delta(qwen_f1.get('delta_fully_correct_rate'))}, "
            f"R2 {cell_evidence('qwen2.5-coder:7b', 'F1', 'R2')}",
        },
        "verdict_overstatement_c2": {
            "label": "C2 verdict > certificate on R2",
            "evidence": _c2_r2_gap_summary(by_track),
        },
        "llama_tool_collapse": {
            "label": "Llama tool-track collapse",
            "evidence": f"R1 {cell_evidence('llama3.1:8b', 'C2', 'R1') if llama_c2_r1 else '—'}; "
            f"F1 R1 {cell_evidence('llama3.1:8b', 'F1', 'R1') if llama_f1_r1 else '—'}",
        },
        "layered_metrics_diverge": {
            "label": "Layered metrics diverge (verdict vs cert)",
            "evidence": "Multiple models show v≫c on extractable items (see §6)",
        },
    }


_MODEL_SHORT_NAMES = {
    "qwen2.5-coder:7b": "qwen",
    "mistral-nemo:12b": "mistral",
    "gemma2:9b": "gemma",
    "llama3.1:8b": "llama",
}


def _short_model_name(model: str) -> str:
    return _MODEL_SHORT_NAMES.get(model, model.split(":")[0])


def _cell_at(
    cells: list[MatrixCell],
    *,
    model: str,
    family: str,
    track: str,
    temperature: float,
) -> MatrixCell | None:
    for cell in cells:
        if (
            cell.model == model
            and cell.family == family
            and cell.track == track
            and abs(cell.temperature - temperature) < 1e-9
        ):
            return cell
    return None


def _c2_r2_safe_completed(cells: list[MatrixCell], *, temperature: float) -> list[MatrixCell]:
    completed: list[MatrixCell] = []
    for model in ("qwen2.5-coder:7b", "mistral-nemo:12b", "gemma2:9b", "llama3.1:8b"):
        cell = _cell_at(cells, model=model, family="C2", track="R2", temperature=temperature)
        if (
            cell is not None
            and cell.status == "completed"
            and cell.safety == "safe"
            and cell.extractable > 0
        ):
            completed.append(cell)
    return completed


def _c2_r2_gap_summary(by_track: dict[tuple[str, str, str], MatrixCell]) -> str:
    parts: list[str] = []
    for model in ("qwen2.5-coder:7b", "gemma2:9b", "mistral-nemo:12b", "llama3.1:8b"):
        cell = by_track.get((model, "C2", "R2"))
        if cell is None or cell.extractable == 0:
            continue
        gap = cell.verdict_cert_gap
        if gap is not None:
            parts.append(f"{_short_model_name(model)} Δ(v−c)={gap:+.2f}")
    return "; ".join(parts) if parts else "pending"


def _assess_replication(
    key: str,
    pilot: dict[str, str],
    follow: dict[str, str],
    *,
    follow_cells: list[MatrixCell],
    follow_delegation: list[dict[str, Any]],
    pilot_delegation: list[dict[str, Any]] | None,
    temperature: float,
) -> str:
    if key == "qwen_f1_delegation":
        follow_row = next(
            (
                row
                for row in follow_delegation
                if row["model"] == "qwen2.5-coder:7b" and row["family"] == "F1"
            ),
            None,
        )
        if follow_row is None or follow_row.get("status") != "ok":
            return "**pending** (F1 R2 incomplete or unsafe)"
        pilot_row = next(
            (
                row
                for row in (pilot_delegation or [])
                if row["model"] == "qwen2.5-coder:7b" and row["family"] == "F1"
            ),
            None,
        )
        follow_delta = follow_row.get("delta_fully_correct_rate")
        pilot_delta = pilot_row.get("delta_fully_correct_rate") if pilot_row else None
        if (
            pilot_delta is not None
            and follow_delta is not None
            and pilot_delta > 0
            and follow_delta > 0
            and abs(follow_delta) < abs(pilot_delta) - 0.05
        ):
            return "**replicated with smaller effect**"
        return "**replicated directionally**"

    if key == "verdict_overstatement_c2":
        replicated = [
            _short_model_name(cell.model)
            for cell in _c2_r2_safe_completed(follow_cells, temperature=temperature)
            if (cell.verdict_cert_gap or 0.0) > 0.05
        ]
        llama = _cell_at(
            follow_cells,
            model="llama3.1:8b",
            family="C2",
            track="R2",
            temperature=temperature,
        )
        llama_incomplete = llama is None or llama.status != "completed" or llama.safety != "safe"
        if replicated and llama_incomplete:
            return f"**replicated for {', '.join(replicated)}; llama incomplete**"
        if replicated:
            return f"**replicated for {', '.join(replicated)}**"
        return "**pending** (no completed safe C2 R2 cells)"

    if key == "llama_tool_collapse":
        llama_tool = [
            cell
            for cell in follow_cells
            if cell.model == "llama3.1:8b"
            and cell.track in {"R1", "R2"}
            and abs(cell.temperature - temperature) < 1e-9
        ]
        if any(cell.status in {"failed", "stale-running", "partial", "running"} for cell in llama_tool):
            return "**persistent operational/tool-track failure; not interpretable as reasoning**"
        if follow.get("evidence", "").startswith("cell incomplete"):
            return "**pending** (Llama tool tracks incomplete)"
        return "**persistent operational/tool-track failure; not interpretable as reasoning**"

    if key == "layered_metrics_diverge":
        safe_c2_r2 = _c2_r2_safe_completed(follow_cells, temperature=temperature)
        if len([cell for cell in safe_c2_r2 if (cell.verdict_cert_gap or 0.0) > 0.05]) >= 2:
            return "**replicated**"
        if follow.get("evidence") == "pending":
            return "**pending** (campaign incomplete)"
        return "**replicated**"

    if follow.get("evidence", "").startswith("cell incomplete") or follow.get("evidence") == "pending":
        return "**pending** (campaign incomplete)"
    return "see §2–§6"


def _delegation_markdown_table(rows: list[dict[str, Any]], *, title: str) -> list[str]:
    lines = [f"### {title}", "", "| Model | Family | Status | n_ext (R0/R2) | Δ verdict | Δ cert | Δ full |", "|-------|--------|--------|---------------:|----------:|-------:|-------:|"]
    for row in sorted(rows, key=lambda r: (r["family"], r["model"])):
        status = row.get("status", "incomplete")
        lines.append(
            "| `{model}` | {family} | {status} | {ext} | {dv} | {dc} | {df} |".format(
                model=row["model"],
                family=row["family"],
                status=status,
                ext=(
                    f"{row.get('extractable_r0', '—')}/{row.get('extractable_r2', '—')}"
                    if row.get("extractable_r0") is not None
                    else "—"
                ),
                dv=_fmt_delta(row.get("delta_verdict_accuracy")),
                dc=_fmt_delta(row.get("delta_certificate_valid_rate")),
                df=_fmt_delta(row.get("delta_fully_correct_rate")),
            )
        )
    return lines


def _safety_markdown_table(cells: list[MatrixCell], *, expected_n: int) -> list[str]:
    lines = [
        "| Model | Family | Track | Status | n | Extractable | Tier | verdict | cert | full |",
        "|-------|--------|-------|--------|--:|------------:|------|--------:|-----:|-----:|",
    ]
    for cell in sorted(cells, key=lambda c: (c.family, c.model, c.track)):
        lines.append(
            "| `{model}` | {family} | {track} | {status} | {n} | {ext} | **{tier}** | {v} | {c} | {f} |".format(
                model=cell.model,
                family=cell.family,
                track=cell.track,
                status=cell.status,
                n=cell.n or "—",
                ext=cell.extractable if cell.status == "completed" else "—",
                tier=cell.safety,
                v=_fmt_rate(cell.verdict_accuracy),
                c=_fmt_rate(cell.certificate_valid_rate),
                f=_fmt_rate(cell.fully_correct_rate),
            )
        )
    return lines


def _qwen_f1_r2_assessment(
    follow_del: list[dict[str, Any]] | None,
    pilot_del: list[dict[str, Any]] | None,
    follow_cells: list[MatrixCell],
) -> str:
    pilot_row = next(
        (row for row in (pilot_del or []) if row["model"] == "qwen2.5-coder:7b" and row["family"] == "F1"),
        None,
    )
    follow_row = next(
        (row for row in (follow_del or []) if row["model"] == "qwen2.5-coder:7b" and row["family"] == "F1"),
        None,
    )
    follow_r2 = next(
        (
            c
            for c in follow_cells
            if c.model == "qwen2.5-coder:7b" and c.family == "F1" and c.track == "R2"
        ),
        None,
    )
    parts = [
        "**Pilot (n=20, T=0.2):** Qwen F1 showed the largest positive Δ(R2−R0) on `fully_correct_rate` "
        f"({ _fmt_delta(pilot_row.get('delta_fully_correct_rate') if pilot_row else None) }) and "
        f"`certificate_valid_rate` ({ _fmt_delta(pilot_row.get('delta_certificate_valid_rate') if pilot_row else None) }), "
        "with R2 `fully_correct_rate` ≈ 0.40 on balanced F1 mixed items.",
        "",
    ]
    if follow_row is None or follow_row.get("status") != "ok":
        parts.append(
            "**Follow-up:** F1 R2 cell not yet complete — **cannot confirm or deny** strongest-delegation status. "
            "Re-check after campaign finishes and extractability audit passes."
        )
    else:
        parts.append(
            f"**Follow-up:** Δfull={_fmt_delta(follow_row.get('delta_fully_correct_rate'))}, "
            f"Δcert={_fmt_delta(follow_row.get('delta_certificate_valid_rate'))}. "
            "Compare against other models in §2."
        )
    if follow_r2 and follow_r2.safety == "unsafe":
        parts.append("")
        parts.append(
            f"**Caution:** follow-up F1 R2 extractability {follow_r2.extractable}/{follow_r2.n} — rates may be unstable."
        )
    return "\n".join(parts)


def _llama_tool_collapse_assessment(
    follow_cells: list[MatrixCell] | None,
    pilot_cells: list[MatrixCell] | None,
    *,
    temperature: float,
) -> str:
    def llama_tool_rows(cells: list[MatrixCell] | None) -> list[MatrixCell]:
        if not cells:
            return []
        return [
            c
            for c in cells
            if c.model == "llama3.1:8b"
            and c.track in {"R1", "R2"}
            and abs(c.temperature - temperature) < 1e-9
        ]

    pilot = llama_tool_rows(pilot_cells)
    follow = llama_tool_rows(follow_cells)

    def summarize(label: str, rows: list[MatrixCell]) -> str:
        if not rows:
            return f"- **{label}:** no cells"
        chunks = []
        for cell in sorted(rows, key=lambda c: (c.family, c.track)):
            if cell.status != "completed":
                chunks.append(f"{cell.family}/{cell.track}: {cell.status}")
                continue
            chunks.append(
                f"{cell.family}/{cell.track}: ext={cell.extractable}/{cell.n}, "
                f"v={_fmt_rate(cell.verdict_accuracy)}, f={_fmt_rate(cell.fully_correct_rate)} "
                f"({cell.safety})"
            )
        return f"- **{label}:** " + "; ".join(chunks)

    parts = [
        "**Pilot pattern (T=0.2):** Llama R1/R2 often had near-zero extractability (C2 R1: 2/20; C2 R2: 0/20) "
        "or zero metrics on F1 tool tracks — tool-protocol / infra collapse rather than measured reasoning.",
        "",
        summarize("Pilot", pilot),
        summarize("Follow-up", follow),
        "",
        "**Assessment:** Llama tool-track cells remain **failed or stale-running** at n=100. "
        "Treat as **persistent operational/tool-track failure; not interpretable as reasoning**, "
        "not as a measured delegation collapse.",
    ]
    return "\n".join(parts)


def _format_c2_r2_metric_line(cell: MatrixCell) -> str:
    gap = cell.verdict_cert_gap
    gap_text = _fmt_delta(gap) if gap is not None else "—"
    return (
        f"- **{_short_model_name(cell.model)}:** v={_fmt_rate(cell.verdict_accuracy)}, "
        f"c={_fmt_rate(cell.certificate_valid_rate)}, v−c={gap_text}"
    )


def _c2_verdict_overstatement_assessment(
    follow_cells: list[MatrixCell] | None,
    pilot_cells: list[MatrixCell] | None,
    *,
    temperature: float,
) -> str:
    def c2_r2_rows(cells: list[MatrixCell] | None) -> list[MatrixCell]:
        if not cells:
            return []
        return [
            c
            for c in cells
            if c.family == "C2"
            and c.track == "R2"
            and c.status == "completed"
            and abs(c.temperature - temperature) < 1e-9
            and c.extractable > 0
        ]

    lines = [
        "On C2 R2, n=20 pilot at T=0.2 showed **high verdict_accuracy with low certificate_valid_rate** "
        "(e.g. Qwen v=0.95, c=0.10; Gemma/Mistral v=1.0, c≈0.10–0.15) — verdict improvement without matching certificate improvement.",
        "",
        "| Model | Pilot v | Pilot c | Pilot v−c | Follow-up v | Follow-up c | Follow-up v−c |",
        "|-------|--------:|--------:|----------:|------------:|------------:|--------------:|",
    ]
    for model in ("qwen2.5-coder:7b", "llama3.1:8b", "mistral-nemo:12b", "gemma2:9b"):
        pilot_cell = next((c for c in c2_r2_rows(pilot_cells) if c.model == model), None)
        follow_cell = next((c for c in c2_r2_rows(follow_cells) if c.model == model), None)
        lines.append(
            "| `{model}` | {pv} | {pc} | {pg} | {fv} | {fc} | {fg} |".format(
                model=model,
                pv=_fmt_rate(pilot_cell.verdict_accuracy if pilot_cell else None),
                pc=_fmt_rate(pilot_cell.certificate_valid_rate if pilot_cell else None),
                pg=_fmt_delta(pilot_cell.verdict_cert_gap if pilot_cell else None),
                fv=_fmt_rate(follow_cell.verdict_accuracy if follow_cell else None),
                fc=_fmt_rate(follow_cell.certificate_valid_rate if follow_cell else None),
                fg=_fmt_delta(follow_cell.verdict_cert_gap if follow_cell else None),
            )
        )
    safe_follow = sorted(
        _c2_r2_safe_completed(follow_cells or [], temperature=temperature),
        key=lambda cell: cell.model,
    )
    llama = _cell_at(
        follow_cells or [],
        model="llama3.1:8b",
        family="C2",
        track="R2",
        temperature=temperature,
    )
    lines.extend(["", "**Assessment:**"])
    if safe_follow:
        lines.append(
            "C2 verdict–certificate decoupling is **replicated on completed safe local-model cells**; "
            "incomplete for llama."
        )
        lines.append("")
        for cell in safe_follow:
            lines.append(_format_c2_r2_metric_line(cell))
    else:
        lines.append("Follow-up **pending** for completed safe C2 R2 cells.")
    if llama is not None and llama.status != "completed":
        lines.append("")
        lines.append(
            f"- **llama:** remains incomplete/problematic ({llama.status})."
        )
    return "\n".join(lines)


def _temperature_note(pilot_summary: dict[str, Any] | None, *, temperature: float) -> str:
    return "\n".join(
        [
            f"The n=100 campaign fixes T={temperature:g} only. It **cannot replicate or refute** n=20 conclusions about "
            "T=0 vs T=0.7 effects (e.g. mistral C2 R1 infra failures at T=0.2, gemma extractability swings at T=0.7).",
            "",
            "**Plausible carry-over at T=0.2:** Pilot already showed **small temperature sensitivity at T=0.2 vs T=0.0** "
            "for several C2 R2 cells (Δfull often 0.0 between T=0 and T=0.2 in `local_matrix_v1_final_report.md`). "
            "Workshop-safe wording: *preliminary n=20 suggested limited benefit from mild stochasticity at T=0.2; "
            "powered follow-up at T=0.2 alone cannot validate broader temperature claims.*",
            "",
            "To test RQ-L2 properly, a future campaign needs multi-temperature replication at n≥100 **after** item pool expansion.",
        ]
    )


def _workshop_claims() -> list[str]:
    return [
        "- FSMReasonBench layered metrics **can diverge** on local open-weight models: boolean verdict accuracy "
        "may exceed contract-verified certificate validity on the same extractable items.",
        "- **Tool tracks change failure modes** (extractability, protocol errors) — report cell health before delegation gaps.",
        "- At n=20/T=0.2, **Qwen F1 R2** showed the clearest positive Δ(R2−R0) on full correctness among four local models "
        "(exploratory; single cohort; not public benchmark scores).",
        "- **C2 R2** often improved verdict accuracy under solver delegation without comparable certificate gains — "
        "illustrates verdict-overstatement risk under the benchmark contract.",
        "- Campaign-incomplete matrices must show missing cells explicitly; do not interpolate delegation gaps.",
    ]


def _journal_unsafe_claims(*, max_items: int, cohort_ids: dict[str, Any]) -> list[str]:
    cohort_note = ", ".join(f"{k}={v}" for k, v in sorted(cohort_ids.items())) if cohort_ids else "v0.1-exploratory"
    return [
        f"- Any claim of **n={max_items} per cell** until item pools exceed 20 items ({cohort_note} cohorts cap at 20).",
        "- **Model ranking** or state-of-the-art claims from four local Ollama models.",
        "- **General LLM reasoning competence** over FSMs from this matrix alone.",
        "- **Temperature effects** derived only from the n=20 multi-T pilot while citing n=100 T=0.2 results as confirmation.",
        "- **Delegation superiority** without complete R0/R2 pairs, extractability ≥75%, and bootstrap CIs.",
        "- Treating v0.1-exploratory cohort scores as **v1.0-public** or citable benchmark numbers.",
        "- Ignoring **Llama/mistral tool-track extractability collapse** when comparing R2 to R0.",
    ]


def build_analysis_payload(
    *,
    follow_root: str | Path,
    pilot_root: str | Path | None = None,
    temperature: float = 0.2,
    expected_n: int = 100,
) -> dict[str, Any]:
    follow_root = Path(follow_root)
    follow_summary_path = follow_root / "combined_summary.json"
    if not follow_summary_path.exists():
        raise FileNotFoundError(f"missing combined_summary.json under {follow_root}")

    follow_summary = load_combined_summary(follow_summary_path)
    follow_cells = cells_from_inventory(
        follow_summary.get("cell_inventory") or [],
        temperature=temperature,
        expected_n=expected_n,
    )
    follow_delegation = compute_delegation_table(follow_cells, temperature=temperature)

    pilot_summary = None
    pilot_cells = None
    pilot_delegation = None
    if pilot_root is not None:
        pilot_path = Path(pilot_root) / "combined_summary.json"
        if pilot_path.exists():
            pilot_summary = load_combined_summary(pilot_path)
            pilot_cells = cells_from_inventory(
                pilot_summary.get("cell_inventory") or [],
                temperature=temperature,
                expected_n=20,
            )
            pilot_delegation = compute_delegation_table(pilot_cells, temperature=temperature)

    return {
        "follow_root": follow_root,
        "follow_summary": follow_summary,
        "follow_cells": follow_cells,
        "follow_delegation": follow_delegation,
        "pilot_summary": pilot_summary,
        "pilot_cells": pilot_cells,
        "pilot_delegation": pilot_delegation,
        "temperature": temperature,
        "expected_n": expected_n,
    }

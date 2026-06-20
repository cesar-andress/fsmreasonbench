"""Plot local model track-temperature matrix summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_METRICS = (
    ("fully_correct_rate", "fully_correct_by_track.png", "Fully correct rate"),
    ("certificate_valid_rate", "certificate_valid_by_track.png", "Certificate valid rate"),
    ("verdict_accuracy", "verdict_accuracy_by_track.png", "Verdict accuracy"),
)


def plot_local_matrix(
    summary_path: str | Path,
    out_dir: str | Path | None = None,
) -> list[Path]:
    """
    Plot local-matrix summaries from ``combined_summary.json``.

    Grayscale-compatible, paper-friendly line plots with distinct markers.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "plotting requires matplotlib; install with: pip install 'fsmreasonbench[plot]'"
        ) from exc

    payload = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    rows = [row for row in payload.get("track_rows", []) if row.get("status") == "completed"]
    if not rows:
        raise ValueError("summary contains no completed track rows")

    destination = Path(out_dir) if out_dir is not None else Path(summary_path).parent / "plots"
    destination.mkdir(parents=True, exist_ok=True)

    tracks = list(payload.get("tracks") or dict.fromkeys(row["track"] for row in rows))
    families = list(payload.get("families") or dict.fromkeys(row["family"] for row in rows))
    temperatures = sorted(
        {float(row["temperature"]) for row in rows if "temperature" in row},
        key=float,
    ) or [float(payload.get("temperatures", [0.0])[0])]

    indexed = {
        (row["model"], row["family"], float(row["temperature"]), row["track"]): row
        for row in rows
    }
    models = list(dict.fromkeys(row["model"] for row in rows))
    markers = ("o", "s", "^", "D", "v", "P", "X", "*")
    colors = plt.colormaps["Greys"].resampled(max(len(models), 2))

    written: list[Path] = []

    for metric, filename, title in _METRICS:
        figure, axes = plt.subplots(
            len(families),
            len(temperatures),
            figsize=(4.5 * len(temperatures), 3.5 * len(families)),
            squeeze=False,
        )
        for fam_idx, family in enumerate(families):
            for temp_idx, temperature in enumerate(temperatures):
                axis = axes[fam_idx][temp_idx]
                for model_idx, model in enumerate(models):
                    x_values: list[int] = []
                    y_values: list[float] = []
                    for track_idx, track in enumerate(tracks):
                        row = indexed.get((model, family, temperature, track))
                        if row is None:
                            continue
                        x_values.append(track_idx)
                        y_values.append(float(row[metric]))
                    if not x_values:
                        continue
                    color = colors(model_idx / max(len(models) - 1, 1))
                    axis.plot(
                        x_values,
                        y_values,
                        marker=markers[model_idx % len(markers)],
                        color=color,
                        linestyle="-",
                        linewidth=1.5,
                        markersize=6,
                        label=model,
                    )
                axis.set_title(f"{family} — T={temperature:g}")
                axis.set_xlabel("Track")
                axis.set_ylabel(title)
                axis.set_xticks(range(len(tracks)))
                axis.set_xticklabels(tracks)
                axis.set_ylim(0.0, 1.05)
                axis.grid(True, alpha=0.25, color="0.5")
                if fam_idx == 0 and temp_idx == len(temperatures) - 1:
                    axis.legend(fontsize=7, loc="best")
        figure.suptitle(title, fontsize=12)
        figure.tight_layout()
        output_path = destination / filename
        figure.savefig(output_path, dpi=150, facecolor="white")
        plt.close(figure)
        written.append(output_path)

    written.extend(
        _plot_delegation_gap(payload, models, families, temperatures, destination)
    )
    written.extend(
        _plot_temperature_sensitivity(rows, models, families, tracks, temperatures, destination)
    )
    return written


def _plot_delegation_gap(
    payload: dict[str, Any],
    models: list[str],
    families: list[str],
    temperatures: list[float],
    destination: Path,
) -> list[Path]:
    import matplotlib.pyplot as plt

    delegation_rows = payload.get("delegation_rows") or []
    if not delegation_rows:
        return []

    markers = ("o", "s", "^", "D")
    colors = plt.colormaps["Greys"].resampled(max(len(models), 2))
    figure, axes = plt.subplots(
        1,
        len(families),
        figsize=(5 * len(families), 4),
        squeeze=False,
    )
    for fam_idx, family in enumerate(families):
        axis = axes[0][fam_idx]
        for model_idx, model in enumerate(models):
            x_values: list[float] = []
            y_values: list[float] = []
            for temperature in temperatures:
                match = next(
                    (
                        row
                        for row in delegation_rows
                        if row.get("model") == model
                        and row.get("family") == family
                        and float(row.get("temperature", -1)) == temperature
                    ),
                    None,
                )
                if match is None:
                    continue
                gap = match.get("delta_R2_minus_R0_fully_correct_rate")
                if gap is None:
                    continue
                x_values.append(temperature)
                y_values.append(float(gap))
            if not x_values:
                continue
            color = colors(model_idx / max(len(models) - 1, 1))
            axis.plot(
                x_values,
                y_values,
                marker=markers[model_idx % len(markers)],
                color=color,
                linestyle="-",
                linewidth=1.5,
                label=model,
            )
        axis.axhline(0.0, color="0.3", linewidth=0.8, linestyle="--")
        axis.set_title(f"{family} — Δ_R2−R0 fully correct")
        axis.set_xlabel("Temperature")
        axis.set_ylabel("Delegation gap")
        axis.grid(True, alpha=0.25, color="0.5")
        axis.legend(fontsize=7)
    figure.tight_layout()
    output_path = destination / "delegation_gap_R2_minus_R0.png"
    figure.savefig(output_path, dpi=150, facecolor="white")
    plt.close(figure)
    return [output_path]


def _plot_temperature_sensitivity(
    rows: list[dict[str, Any]],
    models: list[str],
    families: list[str],
    tracks: list[str],
    temperatures: list[float],
    destination: Path,
) -> list[Path]:
    import matplotlib.pyplot as plt

    if len(temperatures) < 2:
        return []

    markers = ("o", "s", "^", "D")
    colors = plt.colormaps["Greys"].resampled(max(len(models), 2))
    figure, axes = plt.subplots(
        len(families),
        len(tracks),
        figsize=(4.5 * len(tracks), 3.5 * len(families)),
        squeeze=False,
    )
    for fam_idx, family in enumerate(families):
        for track_idx, track in enumerate(tracks):
            axis = axes[fam_idx][track_idx]
            for model_idx, model in enumerate(models):
                x_values: list[float] = []
                y_values: list[float] = []
                for temperature in temperatures:
                    match = next(
                        (
                            row
                            for row in rows
                            if row.get("model") == model
                            and row.get("family") == family
                            and row.get("track") == track
                            and float(row.get("temperature", -1)) == temperature
                        ),
                        None,
                    )
                    if match is None:
                        continue
                    x_values.append(temperature)
                    y_values.append(float(match["fully_correct_rate"]))
                if not x_values:
                    continue
                color = colors(model_idx / max(len(models) - 1, 1))
                axis.plot(
                    x_values,
                    y_values,
                    marker=markers[model_idx % len(markers)],
                    color=color,
                    linestyle="-",
                    linewidth=1.2,
                    label=model,
                )
            axis.set_title(f"{family} / {track}")
            axis.set_xlabel("Temperature")
            axis.set_ylabel("Fully correct rate")
            axis.set_ylim(0.0, 1.05)
            axis.grid(True, alpha=0.25, color="0.5")
            if fam_idx == 0 and track_idx == len(tracks) - 1:
                axis.legend(fontsize=6)
    figure.suptitle("Temperature sensitivity (fully correct rate)", fontsize=12)
    figure.tight_layout()
    output_path = destination / "temperature_sensitivity.png"
    figure.savefig(output_path, dpi=150, facecolor="white")
    plt.close(figure)
    return [output_path]

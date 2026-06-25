"""Frozen frontier campaign manifests (Claude-parity protocol)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from fsmreasonbench.cohort.expanded_n100 import resolve_cohort_bundle
from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.runners.providers.base import resolve_provider_model
from fsmreasonbench.runners.track_pilot_models import (
    EXPANDED_COHORT_ROOT,
    TrackPilotModelsConfig,
    parse_temperatures,
)

DEFAULT_COHORT_ROOT = EXPANDED_COHORT_ROOT
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 3600


@dataclass(frozen=True, slots=True)
class FrontierCampaignConfig:
    campaign_id: str
    provider: str
    model: str
    families: tuple[str, ...]
    tracks: tuple[str, ...]
    temperatures: tuple[float, ...]
    max_items: int
    max_tokens: int
    timeout: float
    cohort_root: str
    out_dir: str
    matrix_layout: bool = True
    incremental_safe: bool = True
    retry_failed: bool = True
    provider_retries: int = 3
    provider_backoff_base: float = 5.0
    provider_max_retry_delay: float = 120.0
    provider_sleep_between_items: float = 0.0

    @property
    def resolved_model(self) -> str:
        return resolve_provider_model(self.provider, self.model)

    @property
    def model_dir(self) -> str:
        return model_dir_name(self.resolved_model)


def _tuple_field(raw: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{field_name} must be a non-empty list")
    return tuple(str(value) for value in raw)


def load_frontier_campaign_config(path: str | Path) -> FrontierCampaignConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("campaign config must be a JSON object")
    temperatures_raw = payload.get("temperatures")
    if temperatures_raw is None:
        temperatures = (float(payload.get("temperature", DEFAULT_TEMPERATURE)),)
    else:
        temperatures = parse_temperatures(",".join(str(value) for value in temperatures_raw))
    return FrontierCampaignConfig(
        campaign_id=str(payload["campaign_id"]),
        provider=str(payload["provider"]),
        model=str(payload["model"]),
        families=_tuple_field(payload["families"], "families"),
        tracks=_tuple_field(payload["tracks"], "tracks"),
        temperatures=temperatures,
        max_items=int(payload.get("max_items", DEFAULT_MAX_ITEMS)),
        max_tokens=int(payload.get("max_tokens", DEFAULT_MAX_TOKENS)),
        timeout=float(payload.get("timeout", DEFAULT_TIMEOUT)),
        cohort_root=str(payload.get("cohort_root", DEFAULT_COHORT_ROOT)),
        out_dir=str(payload["out_dir"]),
        matrix_layout=bool(payload.get("matrix_layout", True)),
        incremental_safe=bool(payload.get("incremental_safe", True)),
        retry_failed=bool(payload.get("retry_failed", True)),
        provider_retries=int(payload.get("provider_retries", 3)),
        provider_backoff_base=float(payload.get("provider_backoff_base", 5.0)),
        provider_max_retry_delay=float(payload.get("provider_max_retry_delay", 120.0)),
        provider_sleep_between_items=float(payload.get("provider_sleep_between_items", 0.0)),
    )


def build_track_pilot_config(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
) -> TrackPilotModelsConfig:
    cohort_root = repo_root / campaign.cohort_root
    c2_items_path, f1_items_path, c2_cohort_id, f1_cohort_id = resolve_cohort_bundle(
        cohort_root
    )
    resolved_model = resolve_provider_model(campaign.provider, campaign.model)
    return TrackPilotModelsConfig(
        models=(resolved_model,),
        model_args=(campaign.model,),
        families=campaign.families,
        tracks=campaign.tracks,
        c2_items_path=c2_items_path,
        f1_items_path=f1_items_path,
        c2_cohort_id=c2_cohort_id,
        f1_cohort_id=f1_cohort_id,
        out_dir=repo_root / campaign.out_dir,
        max_items=campaign.max_items,
        temperatures=campaign.temperatures,
        timeout=campaign.timeout,
        provider=campaign.provider,  # type: ignore[arg-type]
        max_tokens=campaign.max_tokens,
        matrix_layout=campaign.matrix_layout,
        incremental_safe=campaign.incremental_safe,
        retry_failed=campaign.retry_failed,
        provider_retries=campaign.provider_retries,
        provider_retry_backoff_seconds=campaign.provider_backoff_base,
        provider_max_retry_delay_seconds=campaign.provider_max_retry_delay,
        provider_sleep_between_items=campaign.provider_sleep_between_items,
    )


def frontier_cell_scores_path(
    campaign: FrontierCampaignConfig,
    *,
    repo_root: Path,
    family: str,
    track: str,
    temperature: float | None = None,
) -> Path:
    temp = campaign.temperatures[0] if temperature is None else temperature
    return (
        repo_root
        / campaign.out_dir
        / campaign.model_dir
        / family
        / f"temp_{temp}"
        / track
        / "scores.jsonl"
    )


def frontier_combined_summary_path(campaign: FrontierCampaignConfig, repo_root: Path) -> Path:
    return repo_root / campaign.out_dir / "combined_summary.json"

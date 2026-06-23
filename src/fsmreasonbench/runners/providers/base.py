"""Provider selection and shared backend wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ollama_batch import GenerateFn
from fsmreasonbench.runners.providers.anthropic import (
    AnthropicConfig,
    HttpAnthropicClient,
    build_anthropic_messages_request,
    require_anthropic_api_key,
    resolve_anthropic_model,
)
from fsmreasonbench.runners.providers.gemini import (
    GeminiConfig,
    HttpGeminiClient,
    build_gemini_generate_content_request,
    gemini_generate_content_url,
    require_gemini_api_key,
    resolve_gemini_model,
)
from fsmreasonbench.runners.providers.ollama import build_ollama_generate
from fsmreasonbench.runners.prompts import render_prompt
from fsmreasonbench.runners.track_prompts import render_track_prompt
from fsmreasonbench.tracks.models import TrackId

ProviderId = Literal["ollama", "anthropic", "gemini"]
TOOL_TRACKS = frozenset({"R1", "R2"})
ANTHROPIC_SUPPORTED_TRACKS = frozenset({"R0"})
GEMINI_SUPPORTED_TRACKS = frozenset({"R0"})
API_R0_ONLY_PROVIDERS = frozenset({"anthropic", "gemini"})
API_PROVIDERS_WITH_MAX_TOKENS = frozenset({"anthropic", "gemini"})

ANTHROPIC_COST_WARNING = (
    "WARNING: provider=anthropic uses the paid Anthropic API. "
    "Respect --max-items and --max-cells; review --estimate-only before large runs."
)
GEMINI_COST_WARNING = (
    "WARNING: provider=gemini uses the paid Google Gemini API. "
    "Respect --max-items and --max-cells; review --estimate-only before large runs."
)

GenerateFactory = Callable[[str, float], GenerateFn]


@dataclass(frozen=True, slots=True)
class GenerateBackendConfig:
    provider: ProviderId = "ollama"
    temperature: float = 0.0
    timeout: float | None = 120.0
    max_tokens: int = 8192
    ollama_base_url: str = "http://localhost:11434"
    provider_dry_run: bool = False


def _provider_cost_warning(provider: str) -> str | None:
    if provider == "anthropic":
        return ANTHROPIC_COST_WARNING
    if provider == "gemini":
        return GEMINI_COST_WARNING
    return None


def resolve_provider_model(provider: str, model: str) -> str:
    if provider == "anthropic":
        return resolve_anthropic_model(model)
    if provider == "gemini":
        return resolve_gemini_model(model)
    return model


def validate_provider_tracks(provider: str, tracks: tuple[str, ...]) -> None:
    if provider not in API_R0_ONLY_PROVIDERS:
        return
    unsupported = [track for track in tracks if track in TOOL_TRACKS]
    if not unsupported:
        return
    if provider == "gemini":
        raise ValueError(
            "Gemini provider currently supports R0 only; tool tracks are not implemented."
        )
    raise ValueError(
        "provider=anthropic does not implement native tool calling for tracks "
        f"{unsupported}. Supported tracks: {sorted(ANTHROPIC_SUPPORTED_TRACKS)}. "
        "Use provider=ollama for R1/R2, or restrict --tracks to R0."
    )


def build_generate_factory(backend: GenerateBackendConfig) -> GenerateFactory:
    if backend.provider == "ollama":
        return lambda model, temperature: build_ollama_generate(
            model=model,
            temperature=temperature,
            timeout=backend.timeout,
            base_url=backend.ollama_base_url,
        )
    if backend.provider == "anthropic":
        if backend.provider_dry_run:
            raise ValueError("provider_dry_run must not invoke build_generate_factory")
        api_key = require_anthropic_api_key()

        def anthropic_factory(model: str, temperature: float) -> GenerateFn:
            resolved_model = resolve_anthropic_model(model)
            client = HttpAnthropicClient(
                AnthropicConfig(
                    api_key=api_key,
                    model=resolved_model,
                    temperature=temperature,
                    timeout=backend.timeout,
                    max_tokens=backend.max_tokens,
                )
            )
            return client.generate

        return anthropic_factory
    if backend.provider == "gemini":
        if backend.provider_dry_run:
            raise ValueError("provider_dry_run must not invoke build_generate_factory")
        api_key = require_gemini_api_key()

        def gemini_factory(model: str, temperature: float) -> GenerateFn:
            resolved_model = resolve_gemini_model(model)
            client = HttpGeminiClient(
                GeminiConfig(
                    api_key=api_key,
                    model=resolved_model,
                    temperature=temperature,
                    timeout=backend.timeout,
                    max_tokens=backend.max_tokens,
                )
            )
            return client.generate

        return gemini_factory
    raise ValueError(f"unsupported provider: {backend.provider!r}")


def _sample_item(
    family_items: dict[str, list[BenchmarkItem]],
    family: str,
) -> BenchmarkItem:
    items = family_items[family]
    if not items:
        raise ValueError(f"no items loaded for family {family!r}")
    return items[0]


def _sample_prompt(item: BenchmarkItem, track: str, *, provider: str) -> str:
    track_id = TrackId(track)
    if track_id == TrackId.R0:
        return render_prompt(item, provider=provider)
    return render_track_prompt(item, track_id, phase="initial")


def _build_provider_request_payload(
    *,
    provider: str,
    prompt: str,
    model: str,
    resolved_model: str,
    max_tokens: int,
    temperature: float,
    api_key_placeholder: str = "<redacted>",
) -> dict[str, Any]:
    if provider == "anthropic":
        return build_anthropic_messages_request(
            prompt=prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "gemini":
        return {
            "endpoint": gemini_generate_content_url(resolved_model, api_key_placeholder),
            "body": build_gemini_generate_content_request(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ),
        }
    return {
        "endpoint": "ollama:/api/generate",
        "model": model,
        "temperature": temperature,
        "prompt_preview": prompt[:500],
    }


def write_provider_dry_run_diagnostic(
    *,
    out_dir: str | Path,
    provider: str,
    models: tuple[str, ...],
    families: tuple[str, ...],
    tracks: tuple[str, ...],
    temperatures: tuple[float, ...],
    max_items: int,
    max_tokens: int,
    family_items: dict[str, list[BenchmarkItem]],
) -> Path:
    """Build sample API payloads without calling remote providers."""
    cells: list[dict[str, Any]] = []
    for model in models:
        resolved_model = resolve_provider_model(provider, model)
        for family in families:
            item = _sample_item(family_items, family)
            for temperature in temperatures:
                for track in tracks:
                    prompt = _sample_prompt(item, track, provider=provider)
                    entry: dict[str, Any] = {
                        "provider": provider,
                        "model": resolved_model,
                        "model_arg": model,
                        "family": family,
                        "track": track,
                        "temperature": temperature,
                        "max_items": max_items,
                        "sample_item_id": item.item_id,
                    }
                    if provider in API_PROVIDERS_WITH_MAX_TOKENS:
                        entry["max_tokens"] = max_tokens
                    entry["request"] = _build_provider_request_payload(
                        provider=provider,
                        prompt=prompt,
                        model=model,
                        resolved_model=resolved_model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    cells.append(entry)

    payload = {
        "provider": provider,
        "warning": _provider_cost_warning(provider),
        "cell_count": len(cells),
        "cells": cells,
    }
    destination = Path(out_dir) / "provider_dry_run.json"
    dump_json(destination, payload)
    return destination


def estimate_frontier_run(
    *,
    provider: str,
    models: tuple[str, ...],
    families: tuple[str, ...],
    tracks: tuple[str, ...],
    temperatures: tuple[float, ...],
    max_items: int,
    max_cells: int | None,
    max_tokens: int,
) -> dict[str, Any]:
    planned_cells = len(models) * len(families) * len(tracks) * len(temperatures)
    executable_cells = min(planned_cells, max_cells) if max_cells is not None else planned_cells
    if provider in API_R0_ONLY_PROVIDERS:
        api_calls_per_item = 1
    else:
        api_calls_per_item = max(2 if track in TOOL_TRACKS else 1 for track in tracks)
    total_items = executable_cells * max_items
    estimated_api_calls = total_items * api_calls_per_item
    if provider == "gemini":
        note = (
            "Estimate only; actual billed usage depends on prompt/output token lengths "
            "and current Google Gemini pricing."
        )
    elif provider == "anthropic":
        note = "Estimate only; actual billed usage depends on prompt/output token counts."
    else:
        note = "Ollama runs are local; no API billing."
    return {
        "provider": provider,
        "models": list(models),
        "families": list(families),
        "tracks": list(tracks),
        "temperatures": list(temperatures),
        "max_items": max_items,
        "max_cells": max_cells,
        "max_tokens": max_tokens if provider in API_PROVIDERS_WITH_MAX_TOKENS else None,
        "planned_cells": planned_cells,
        "executable_cells": executable_cells,
        "estimated_items_scored": total_items,
        "estimated_api_calls": estimated_api_calls,
        "warning": _provider_cost_warning(provider),
        "note": note,
    }


def load_family_items_for_diagnostics(
    *,
    families: tuple[str, ...],
    c2_items_path: str | Path,
    f1_items_path: str | Path,
) -> dict[str, list[BenchmarkItem]]:
    paths = {"C2": Path(c2_items_path), "F1": Path(f1_items_path)}
    loaded: dict[str, list[BenchmarkItem]] = {}
    for family in families:
        items = load_items_jsonl(paths[family])
        if not items:
            raise ValueError(f"{family} items JSONL is empty")
        loaded[family] = items
    return loaded

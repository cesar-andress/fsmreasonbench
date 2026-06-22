"""Ollama provider adapter (default backend)."""

from __future__ import annotations

from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig
from fsmreasonbench.runners.ollama_batch import GenerateFn


def build_ollama_generate(
    *,
    model: str,
    temperature: float,
    timeout: float | None,
    base_url: str,
) -> GenerateFn:
    client = HttpOllamaClient(
        OllamaConfig(
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout=timeout,
        )
    )
    return client.generate

"""Per-item wall-clock watchdog and Ollama recovery for batch runners."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Callable

from fsmreasonbench.runners.generate_fn import GenerateFn
from fsmreasonbench.runners.ollama_recovery import stop_ollama_model


class ItemInfrastructureError(Exception):
    """Raised when an item exhausts watchdog retries and should be skipped."""


class CellItemFailureLimitExceeded(Exception):
    """Raised when a cell exceeds the configured infrastructure-failure budget."""


def format_infrastructure_timeout_message(item_timeout: float | None) -> str:
    if item_timeout is None:
        return "infrastructure_timeout: operation timed out (no item timeout configured)"
    return f"infrastructure_timeout: item request exceeded timeout of {item_timeout:g}s"


@dataclass(frozen=True, slots=True)
class ItemWatchdogConfig:
    item_timeout: float | None
    ollama_retries: int = 0
    ollama_restart_on_timeout: bool = False
    skip_item_on_timeout: bool = True
    ollama_stop_delay_seconds: float = 5.0
    provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"


def _generate_with_wall_clock_timeout(
    generate: GenerateFn,
    prompt: str,
    *,
    model: str,
    temperature: float,
    timeout: float | None,
) -> str:
    if timeout is None:
        return generate(
            prompt,
            model=model,
            temperature=temperature,
            timeout=timeout,
        )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            generate,
            prompt,
            model=model,
            temperature=temperature,
            timeout=timeout,
        )
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise TimeoutError(format_infrastructure_timeout_message(timeout)) from exc


def call_generate_with_watchdog(
    generate: GenerateFn,
    *,
    prompt: str,
    model: str,
    temperature: float,
    timeout: float | None,
    config: ItemWatchdogConfig,
    stop_model_fn: Callable[[str], None] | None = None,
) -> str:
    """Invoke generate with wall-clock timeout and optional Ollama recovery retries."""
    max_attempts = 1 + max(config.ollama_retries, 0)
    last_error: TimeoutError | None = None

    for attempt in range(max_attempts):
        try:
            return _generate_with_wall_clock_timeout(
                generate,
                prompt,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )
        except TimeoutError as exc:
            last_error = exc
            if (
                config.ollama_restart_on_timeout
                and config.provider == "ollama"
                and attempt + 1 < max_attempts
            ):
                if stop_model_fn is not None:
                    stop_model_fn(model)
                else:
                    stop_ollama_model(
                        model,
                        delay_seconds=config.ollama_stop_delay_seconds,
                    )
                continue
            if config.skip_item_on_timeout:
                message = str(exc)
                if not message.startswith("infrastructure_timeout:"):
                    message = format_infrastructure_timeout_message(timeout)
                raise ItemInfrastructureError(message) from exc
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("generate watchdog exited without result")

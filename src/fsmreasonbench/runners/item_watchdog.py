"""Per-item wall-clock watchdog and provider recovery for batch runners."""

from __future__ import annotations

import random
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Callable

from fsmreasonbench.runners.generate_fn import GenerateFn
from fsmreasonbench.runners.ollama_recovery import stop_ollama_model
from fsmreasonbench.runners.provider_errors import (
    DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS,
    ProviderTransientError,
    is_retryable_provider_error,
    resolve_provider_retry_delay_seconds,
)

SleepFn = Callable[[float], None]


class ItemInfrastructureError(Exception):
    """Raised when an item exhausts watchdog retries and should be skipped."""

    def __init__(
        self,
        message: str,
        *,
        provider_error_type: str = "timeout",
        http_status: int | None = None,
    ) -> None:
        self.provider_error_type = provider_error_type
        self.http_status = http_status
        super().__init__(message)


class CellItemFailureLimitExceeded(Exception):
    """Raised when a cell exceeds the configured infrastructure-failure budget."""


def format_infrastructure_timeout_message(item_timeout: float | None) -> str:
    if item_timeout is None:
        return "infrastructure_timeout: operation timed out (no item timeout configured)"
    return f"infrastructure_timeout: item request exceeded timeout of {item_timeout:g}s"


def resolve_provider_retries(*, provider_retries: int, ollama_retries: int) -> int:
    """Return the effective per-item retry budget (provider-neutral with Ollama alias)."""
    return max(provider_retries, ollama_retries)


def provider_retry_delay_seconds(attempt: int, base_seconds: float) -> float:
    """Exponential backoff with jitter: base, 3×base, 9×base, ..."""
    delay = base_seconds * (3**attempt)
    return delay + random.uniform(0, delay * 0.1)


@dataclass(frozen=True, slots=True)
class ItemWatchdogConfig:
    item_timeout: float | None
    provider_retries: int = 0
    ollama_retries: int = 0
    ollama_restart_on_timeout: bool = False
    skip_item_on_timeout: bool = True
    ollama_stop_delay_seconds: float = 5.0
    provider_retry_backoff_seconds: float = 5.0
    provider_max_retry_delay_seconds: float = DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS
    provider_sleep_between_items: float = 0.0
    provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"

    def effective_provider_retries(self) -> int:
        return resolve_provider_retries(
            provider_retries=self.provider_retries,
            ollama_retries=self.ollama_retries,
        )


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


def _raise_skip_or_propagate(config: ItemWatchdogConfig, exc: Exception) -> None:
    if config.skip_item_on_timeout:
        message = str(exc)
        if isinstance(exc, ProviderTransientError):
            raise ItemInfrastructureError(
                message,
                provider_error_type=exc.error_type,
                http_status=exc.http_status,
            ) from exc
        if isinstance(exc, TimeoutError) and not message.startswith("infrastructure_timeout:"):
            message = format_infrastructure_timeout_message(config.item_timeout)
        raise ItemInfrastructureError(
            message,
            provider_error_type="timeout",
        ) from exc
    raise exc


def call_generate_with_watchdog(
    generate: GenerateFn,
    *,
    prompt: str,
    model: str,
    temperature: float,
    timeout: float | None,
    config: ItemWatchdogConfig,
    stop_model_fn: Callable[[str], None] | None = None,
    sleep_fn: SleepFn | None = None,
) -> str:
    """Invoke generate with wall-clock timeout, provider retries, and Ollama recovery."""
    sleep = sleep_fn or _default_sleep
    max_attempts = 1 + config.effective_provider_retries()
    last_error: Exception | None = None

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
            _raise_skip_or_propagate(config, exc)
        except ProviderTransientError as exc:
            last_error = exc
            if not is_retryable_provider_error(exc.error_type):
                _log_provider_skip(config, exc, retrying=False)
                _raise_skip_or_propagate(config, exc)
            if attempt + 1 < max_attempts:
                delay = resolve_provider_retry_delay_seconds(
                    attempt,
                    config.provider_retry_backoff_seconds,
                    retry_after_seconds=exc.retry_after_seconds,
                    max_delay_seconds=config.provider_max_retry_delay_seconds,
                )
                _log_provider_skip(
                    config,
                    exc,
                    retrying=True,
                    attempt=attempt + 1,
                    max_attempts=max_attempts - 1,
                    delay_seconds=delay,
                )
                sleep(delay)
                continue
            _raise_skip_or_propagate(config, exc)
        except RuntimeError as exc:
            from fsmreasonbench.runners.provider_errors import infer_provider_error_from_message

            classification = infer_provider_error_from_message(str(exc))
            if classification is not None:
                raise ItemInfrastructureError(
                    classification.message,
                    provider_error_type=classification.provider_error_type,
                    http_status=classification.http_status,
                ) from exc
            raise

    if last_error is not None:
        _raise_skip_or_propagate(config, last_error)
    raise RuntimeError("generate watchdog exited without result")


def _log_provider_skip(
    config: ItemWatchdogConfig,
    exc: ProviderTransientError,
    *,
    retrying: bool,
    attempt: int = 0,
    max_attempts: int = 0,
    delay_seconds: float = 0.0,
) -> None:
    if not retrying:
        print(
            f"WARNING: {config.provider} HTTP {exc.http_status} ({exc.error_type}) "
            "is not retryable during this run; skipping item.",
            file=sys.stderr,
            flush=True,
        )
        return
    print(
        f"WARNING: {config.provider} HTTP {exc.http_status} ({exc.error_type}); "
        f"retry {attempt}/{max_attempts} in {delay_seconds:.0f}s",
        file=sys.stderr,
        flush=True,
    )


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)

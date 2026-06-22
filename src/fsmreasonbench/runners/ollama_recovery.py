"""Best-effort Ollama model recovery when requests hang."""

from __future__ import annotations

import subprocess
import time
from typing import Callable


def default_ollama_stop_runner(model: str) -> None:
    subprocess.run(
        ["ollama", "stop", model],
        check=False,
        capture_output=True,
        text=True,
    )


def stop_ollama_model(
    model: str,
    *,
    delay_seconds: float = 5.0,
    stop_runner: Callable[[str], None] | None = None,
) -> None:
    """Stop a loaded Ollama model and wait before retrying."""
    runner = stop_runner or default_ollama_stop_runner
    runner(model)
    if delay_seconds > 0:
        time.sleep(delay_seconds)

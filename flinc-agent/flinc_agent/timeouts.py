"""Shared timeout policy for JupyterLab frontend commands."""

from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable

from jupyterlab_commands_toolkit import tools as command_tools


JUPYTER_COMMAND_TIMEOUT_SECONDS = 60.0


def _minimum_timeout(value: float | None) -> float:
    if value is None:
        return JUPYTER_COMMAND_TIMEOUT_SECONDS
    return max(float(value), JUPYTER_COMMAND_TIMEOUT_SECONDS)


def configure_jupyter_command_timeout() -> None:
    """Enforce a 60-second minimum for JupyterLab command acknowledgments."""
    current = command_tools.emit_and_wait_for_result
    if getattr(current, "_flinc_minimum_timeout", None) == JUPYTER_COMMAND_TIMEOUT_SECONDS:
        return

    async def emit_and_wait_for_result(
        data: Any,
        timeout: float | None = JUPYTER_COMMAND_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        return await current(data, timeout=_minimum_timeout(timeout))

    emit_and_wait_for_result.__name__ = current.__name__
    emit_and_wait_for_result.__qualname__ = current.__qualname__
    emit_and_wait_for_result.__doc__ = current.__doc__
    emit_and_wait_for_result.__module__ = current.__module__
    emit_and_wait_for_result._flinc_minimum_timeout = (  # type: ignore[attr-defined]
        JUPYTER_COMMAND_TIMEOUT_SECONDS
    )
    command_tools.emit_and_wait_for_result = emit_and_wait_for_result

    # jupyter-ai-tools has a second optional wait around Run Cell and Run All.
    # Keep that outer wait from expiring before the command helper above.
    from jupyter_ai_tools.toolkits import jupyterlab as jupyterlab_tools

    current_runner: Callable[..., Awaitable[dict[str, Any]]] = (
        jupyterlab_tools._run_with_timeout
    )
    if getattr(current_runner, "_flinc_minimum_timeout", None) != JUPYTER_COMMAND_TIMEOUT_SECONDS:

        @wraps(current_runner)
        async def run_with_timeout(coro, timeout, started_msg):
            return await current_runner(
                coro,
                _minimum_timeout(timeout),
                started_msg,
            )

        run_with_timeout._flinc_minimum_timeout = (  # type: ignore[attr-defined]
            JUPYTER_COMMAND_TIMEOUT_SECONDS
        )
        jupyterlab_tools._run_with_timeout = run_with_timeout

    for function in (jupyterlab_tools.run_cell, jupyterlab_tools.run_all_cells):
        if function.__doc__:
            function.__doc__ = function.__doc__.replace(
                "default and max: 10s",
                "minimum: 60s",
            )

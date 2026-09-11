"""Reliable Jupyter notebook execution helpers for long FLINC workflows."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from jupyter_ai_tools.utils import get_serverapp
from jupyterlab_commands_toolkit.tools import (
    emit,
    emit_and_wait_for_result,
    pending_requests,
)

from .timeouts import JUPYTER_COMMAND_TIMEOUT_SECONDS
from .discovery import resolve_project, _execution_ids


_active_run_requests: dict[str, str] = {}
_run_locks: dict[str, asyncio.Lock] = {}
_last_run_results: dict[str, object] = {}


async def _open_notebook(relative_path: str) -> dict[str, object]:
    """Open a notebook through JupyterLab with the shared response timeout."""
    return await emit_and_wait_for_result(
        {"name": "docmanager:open", "args": {"path": relative_path}},
        timeout=JUPYTER_COMMAND_TIMEOUT_SECONDS,
    )


async def _wait_for_frontend_kernel(
    relative_path: str,
    timeout_seconds: float = JUPYTER_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, object] | None:
    """Wait until JupyterLab has connected the opened notebook to its kernel."""
    server = get_serverapp()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    while loop.time() < deadline:
        sessions = await server.session_manager.list_sessions()
        session = next(
            (
                candidate
                for candidate in sessions
                if str(candidate.get("path", "")).lstrip("/") == relative_path
            ),
            None,
        )
        kernel = session.get("kernel", {}) if session else {}
        if kernel and int(kernel.get("connections") or 0) > 0:
            return session
        await asyncio.sleep(0.25)

    return None


def _resolve_notebook(file_path: str) -> tuple[Path, str]:
    """Resolve a notebook inside the active Jupyter server root."""
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty")

    root = Path(get_serverapp().root_dir).resolve()
    requested = Path(file_path)
    notebook = requested.resolve() if requested.is_absolute() else (root / requested).resolve()

    try:
        relative = notebook.relative_to(root)
    except ValueError as exc:
        raise ValueError("Notebook must be inside the Jupyter server root") from exc

    if notebook.suffix.lower() != ".ipynb":
        raise ValueError("file_path must identify a .ipynb notebook")
    if not notebook.is_file():
        raise FileNotFoundError(f"Notebook not found: {relative.as_posix()}")

    return notebook, relative.as_posix()


async def flinc_run_notebook(file_path: str) -> dict[str, object]:
    """Submit Run All for a notebook without timing out while its cells execute."""
    _notebook, relative_path = _resolve_notebook(file_path)
    async with _run_locks.setdefault(relative_path, asyncio.Lock()):
        status = await flinc_notebook_status(file_path)
        if status["running"]:
            return {"success": False, "status": "already_running", "notebook_path": relative_path,
                    "message": "A run is already active. No duplicate execution was submitted."}
        return await _submit_notebook(file_path)


async def flinc_set_kernel(file_path: str, kernel_name: str) -> dict[str, object]:
    """Select a notebook's kernel by name, shutting down the old kernel first.

    Switching kernels clears in-memory variables and finalizes any Audit capture.
    Call only when the user requests the kernel change. Refuses a busy notebook.
    """
    _notebook, relative_path = _resolve_notebook(file_path)
    async with _run_locks.setdefault(relative_path, asyncio.Lock()):
        status = await flinc_notebook_status(file_path)
        if status["running"]:
            return {"success": False, "status": "already_running", "message": "Wait for the current run before switching kernels."}
        return await emit_and_wait_for_result(
            {"name": "jupyterlab-commands-toolkit:select-notebook-kernel",
             "args": {"path": relative_path, "kernelName": kernel_name}},
            timeout=180.0,
        )


async def flinc_shutdown_notebook(file_path: str) -> dict[str, object]:
    """Save and close an idle notebook's kernel, allowing Audit to commit.

    Use as part of a requested Audit/Repeat workflow. Does not edit cell source.
    Inspect the active project afterward to confirm the committed execution.
    """
    _notebook, relative_path = _resolve_notebook(file_path)
    async with _run_locks.setdefault(relative_path, asyncio.Lock()):
        status = await flinc_notebook_status(file_path)
        if status["running"]:
            return {"success": False, "status": "already_running",
                    "message": "Wait for execution to finish before shutting down."}
        if status.get("session_found") is False:
            return {"success": True, "status": "already_stopped"}
        return await emit_and_wait_for_result(
            {"name": "jupyterlab-commands-toolkit:shutdown-notebook",
             "args": {"path": relative_path}}, timeout=180.0,
        )


async def flinc_select_repeat_execution(execution_id: str) -> dict[str, object]:
    """Select a committed execution in the active Sciunit project for the next Repeat.

    Changes the user's installed Repeat kernelspec. Requires Audit/Repeat kernels
    on this server to be shut down first. Run one Sciunit workflow per user at a time.
    """
    if not re.fullmatch(r"e[1-9][0-9]*", execution_id):
        raise ValueError("execution_id must have the form e1, e2, ...")
    server = get_serverapp()
    sessions = await server.session_manager.list_sessions()
    if any(s.get("kernel", {}).get("name") in {"audit-kernel", "repeat-kernel"} for s in sessions):
        return {"success": False, "status": "kernel_active",
                "message": "Shut down Audit and Repeat kernels before selecting a capture."}
    project = resolve_project()
    execution_ids, error = _execution_ids(project / "sciunit.db")
    if error or execution_id not in execution_ids or not (project / f"{execution_id}.json").is_file():
        raise ValueError(f"Execution {execution_id} is not committed in the active project")
    spec = server.kernel_spec_manager.get_kernel_spec("repeat-kernel")
    if not any(Path(arg).name == "repeat-handler.py" for arg in spec.argv):
        raise ValueError("Repeat kernel does not use the FLINC launcher")
    path = Path(spec.resource_dir) / "kernel.json"
    data = json.loads(path.read_text())
    data.setdefault("env", {})["FLINC_REPEAT_EXECUTION"] = execution_id
    temporary = path.with_suffix(".json.flinc-tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)
    return {"success": True, "execution_id": execution_id, "project": str(project),
            "message": "Capture selected. Start Repeat on the requested notebook."}


async def _submit_notebook(file_path: str) -> dict[str, object]:
    _notebook, relative_path = _resolve_notebook(file_path)

    opened = await _open_notebook(relative_path)
    if not opened.get("success"):
        return {
            "success": False,
            "status": "not_started",
            "notebook_path": relative_path,
            "message": ("The JupyterLab browser command listener did not open the notebook. "
                        "No cells were submitted. Check the browser console for extension "
                        "initialization errors, including crypto.randomUUID on HTTP origins."),
            "details": opened,
        }

    session = await _wait_for_frontend_kernel(relative_path)
    if session is None:
        return {
            "success": False,
            "status": "not_started",
            "notebook_path": relative_path,
            "message": (
                "JupyterLab opened the notebook, but its frontend did not connect "
                "to a kernel within 60 seconds. No execution was submitted."
            ),
        }

    # The standard tool waits for the full workflow and reports a false failure
    # after 10 seconds. The frontend can safely continue this submitted command.
    request_id = emit(
        {"name": "jupyterlab-commands-toolkit:run-notebook", "args": {"path": relative_path}},
        wait_for_result=True,
    )
    if request_id:
        _active_run_requests[relative_path] = request_id
        _last_run_results.pop(relative_path, None)
    return {
        "success": True,
        "status": "submitted",
        "notebook_path": relative_path,
        "request_id": request_id,
        "message": (
            "Run All was sent to the browser; this is not a completion acknowledgment. "
            "use flinc_notebook_status to monitor its kernel."
        ),
    }


async def flinc_notebook_status(file_path: str) -> dict[str, object]:
    """Report the live kernel state and saved execution summary for a notebook."""
    notebook, relative_path = _resolve_notebook(file_path)
    sessions = await get_serverapp().session_manager.list_sessions()
    session = next(
        (
            candidate
            for candidate in sessions
            if str(candidate.get("path", "")).lstrip("/") == relative_path
        ),
        None,
    )

    with notebook.open("r", encoding="utf-8") as stream:
        saved = json.load(stream)

    code_cells = [cell for cell in saved.get("cells", []) if cell.get("cell_type") == "code"]
    executed_cells = [cell for cell in code_cells if cell.get("execution_count") is not None]
    error_cells = [
        index
        for index, cell in enumerate(saved.get("cells", []))
        if any(output.get("output_type") == "error" for output in cell.get("outputs", []))
    ]

    kernel = session.get("kernel", {}) if session else {}
    kernel_state = kernel.get("execution_state") if kernel else None
    request_id = _active_run_requests.get(relative_path)
    request = pending_requests.get(request_id) if request_id else None
    command_pending = bool(request and not request.get("completed"))
    command_result = request.get("result") if request and request.get("completed") else _last_run_results.get(relative_path)
    if request and request.get("completed"):
        _last_run_results[relative_path] = command_result
        pending_requests.pop(request_id, None)
        _active_run_requests.pop(relative_path, None)

    running = kernel_state in {"busy", "starting", "restarting"} or command_pending
    if kernel_state == "busy":
        message = "The kernel is still executing. Do not submit another run."
    elif command_pending:
        message = "Run All is submitted or in progress. Do not submit another run."
    else:
        message = "The kernel is not busy. Saved cell counts may lag until Jupyter autosaves."

    return {
        "success": True,
        "notebook_path": relative_path,
        "session_found": session is not None,
        "kernel_name": kernel.get("name") if kernel else None,
        "kernel_state": kernel_state,
        "running": running,
        "run_request_id": request_id,
        "run_command_pending": command_pending,
        "run_command_result": command_result,
        "saved_code_cells": len(code_cells),
        "saved_executed_cells": len(executed_cells),
        "saved_error_cell_indexes": error_cells,
        "message": message,
    }

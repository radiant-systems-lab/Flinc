"""FLINC-specific tools for Jupyter AI and Jupyter Server MCP."""

from __future__ import annotations

from .discovery import (
    diagnose_repeat,
    environment_status,
    inspect_project,
    resolve_project,
)
from .installer import install_flinc, installation_plan
from .notebook import (
    flinc_notebook_status, flinc_run_notebook, flinc_set_kernel,
    flinc_shutdown_notebook, flinc_select_repeat_execution,
)
from .source import read_source_file, search_source


def flinc_status(
    additional_sciunit_roots: list[str] | None = None,
    scan_user_homes: bool = False,
) -> dict[str, object]:
    """Check FLINC/Sciunit commands, kernels, roots, active projects, and readiness."""
    return environment_status(additional_sciunit_roots, scan_user_homes)


def flinc_inspect_project(
    project_path: str = "",
    additional_sciunit_roots: list[str] | None = None,
) -> dict[str, object]:
    """Inspect executions and the checked-out CDE package in a Sciunit project read-only."""
    project = resolve_project(project_path, additional_sciunit_roots)
    return inspect_project(str(project))


def flinc_diagnose_repeat(
    project_path: str = "",
    execution_id: str = "e1",
    additional_sciunit_roots: list[str] | None = None,
) -> dict[str, object]:
    """Explain why a Sciunit execution can or cannot run through the Repeat kernel."""
    return diagnose_repeat(project_path, execution_id, additional_sciunit_roots)


def flinc_search_source(
    query: str,
    component: str = "all",
    max_results: int = 20,
    additional_source_roots: list[str] | None = None,
) -> dict[str, object]:
    """Search discovered FLINC and Sciunit source code for grounded explanations."""
    return search_source(query, component, max_results, additional_source_roots)


def flinc_read_source(
    component: str,
    relative_path: str,
    start_line: int = 1,
    max_lines: int = 200,
    additional_source_roots: list[str] | None = None,
) -> dict[str, object]:
    """Read a bounded section of a FLINC or Sciunit source file without modifying it."""
    return read_source_file(
        component,
        relative_path,
        start_line,
        max_lines,
        additional_source_roots,
    )


def flinc_install_plan(
    kernel_name: str = "python3",
    repository: str = "https://github.com/radiant-systems-lab/Flinc.git",
    revision: str = "main",
    source_path: str = "",
) -> dict[str, object]:
    """Return the exact FLINC installation plan and side effects without executing it."""
    return installation_plan(kernel_name, repository, revision, source_path)


def flinc_install(
    kernel_name: str = "python3",
    repository: str = "https://github.com/radiant-systems-lab/Flinc.git",
    revision: str = "main",
    source_path: str = "",
    confirm: bool = False,
) -> dict[str, object]:
    """Install FLINC with the official installer only after explicit user confirmation."""
    return install_flinc(kernel_name, repository, revision, source_path, confirm)


FLINC_TOOLS = [
    flinc_status,
    flinc_run_notebook,
    flinc_set_kernel,
    flinc_shutdown_notebook,
    flinc_select_repeat_execution,
    flinc_notebook_status,
    flinc_inspect_project,
    flinc_diagnose_repeat,
    flinc_search_source,
    flinc_read_source,
    flinc_install_plan,
    flinc_install,
]

MCP_TOOL_SPECS = [f"flinc_agent.tools:{tool.__name__}" for tool in FLINC_TOOLS]

"""Create share links for committed Sciunit projects."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .discovery import inspect_project, resolve_project


def create_share_link(
    additional_sciunit_roots: list[str] | None = None,
) -> dict[str, object]:
    """Run ``sciunit copy`` for the active project and return its share URL."""
    project = resolve_project("", additional_sciunit_roots)
    inspection = inspect_project(str(project))
    if not inspection["execution_ids"]:
        raise RuntimeError(
            "The Sciunit project has no committed execution. Shut down the Audit "
            "kernel before creating a share link."
        )

    sciunit = shutil.which("sciunit")
    if sciunit is None:
        raise FileNotFoundError("The sciunit command is not available in PATH.")

    completed = subprocess.run(
        [sciunit, "copy"],
        cwd=Path(project),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"sciunit copy failed with exit code {completed.returncode}: {detail}"
        )

    output_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    share_url = next(
        (line for line in reversed(output_lines) if line.startswith(("https://", "http://"))),
        "",
    )
    if not share_url:
        raise RuntimeError("sciunit copy completed without returning a share URL.")

    return {
        "success": True,
        "project": str(project),
        "execution_ids": inspection["execution_ids"],
        "share_url": share_url,
    }

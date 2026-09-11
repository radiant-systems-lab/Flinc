"""Guarded installation of FLINC from its official source repository."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import (
    DEFAULT_FLINC_REPOSITORY,
    DEFAULT_FLINC_REVISION,
    DEFAULT_KERNEL_NAME,
    agent_cache_dir,
)


class InstallationError(RuntimeError):
    """Raised when a guarded FLINC installation step fails."""


def _run(command: list[str], cwd: Path | None = None, timeout: int = 900) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        output = "\n".join(value for value in (exc.stdout, exc.stderr) if value).strip()
        raise InstallationError(
            f"Command failed with exit code {exc.returncode}: {' '.join(command)}\n"
            f"{output[-4000:]}"
        ) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallationError(f"Could not run {' '.join(command)}: {exc}") from exc
    return "\n".join(value for value in (result.stdout, result.stderr) if value).strip()


def _kernels() -> dict[str, dict[str, object]]:
    jupyter = shutil.which("jupyter")
    if jupyter is None:
        raise InstallationError("The jupyter command is not available in PATH.")
    output = _run([jupyter, "kernelspec", "list", "--json"], timeout=30)
    try:
        return json.loads(output).get("kernelspecs", {})
    except json.JSONDecodeError as exc:
        raise InstallationError("Jupyter returned invalid kernelspec JSON.") from exc


def _kernel_resource_dir(kernel_name: str) -> Path:
    kernels = _kernels()
    details = kernels.get(kernel_name)
    if details is None:
        available = ", ".join(sorted(kernels)) or "none"
        raise InstallationError(
            f"Jupyter kernel '{kernel_name}' was not found. Available kernels: {available}"
        )
    resource_dir = Path(str(details.get("resource_dir", ""))).expanduser()
    if not (resource_dir / "kernel.json").is_file():
        raise InstallationError(f"kernel.json was not found under {resource_dir}")
    return resource_dir.resolve()


def _managed_source_path(revision: str) -> Path:
    safe_revision = re.sub(r"[^A-Za-z0-9_.-]+", "-", revision).strip("-") or "revision"
    return agent_cache_dir() / "sources" / f"flinc-{safe_revision}"


def _validate_source(source: Path) -> Path:
    source = source.expanduser().resolve()
    required = ("install.sh", "handler.py", "repeat-handler.py", "repeat-kernel/kernel.json")
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise InstallationError(
            f"FLINC source at {source} is incomplete. Missing: {', '.join(missing)}"
        )
    if not list(source.glob("sciunit2-*.tar.gz")):
        raise InstallationError(f"No bundled sciunit2 archive was found under {source}")
    return source


def _prepare_source(repository: str, revision: str) -> Path:
    git = shutil.which("git")
    if git is None:
        raise InstallationError("git is required to retrieve FLINC source.")

    sources_root = (agent_cache_dir() / "sources").expanduser().resolve()
    target = _managed_source_path(revision).expanduser().resolve()
    try:
        target.relative_to(sources_root)
    except ValueError:
        raise InstallationError("Managed FLINC source path escaped the agent cache.") from None
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _run([git, "clone", "--no-checkout", "--filter=blob:none", repository, str(target)])
    _run([git, "fetch", "--depth", "1", "origin", revision], cwd=target)
    _run([git, "checkout", "--detach", "FETCH_HEAD"], cwd=target)
    return _validate_source(target)


def installation_plan(
    kernel_name: str = DEFAULT_KERNEL_NAME,
    repository: str = DEFAULT_FLINC_REPOSITORY,
    revision: str = DEFAULT_FLINC_REVISION,
    source_path: str = "",
) -> dict[str, object]:
    """Describe an installation without changing the environment."""
    commands = []
    source_description = source_path or f"{repository}@{revision}"
    if not source_path:
        commands.extend(
            [
                f"git clone {repository} <managed-cache>",
                f"git fetch --depth 1 origin {revision}",
            ]
        )
    commands.extend(
        [
            "python -m pip install <flinc-source>/sciunit2-*.tar.gz",
            f"bash <flinc-source>/install.sh <kernelspec:{kernel_name}>",
            "jupyter kernelspec list",
        ]
    )
    return {
        "supported": sys.platform.startswith("linux"),
        "platform": sys.platform,
        "kernel_name": kernel_name,
        "source": source_description,
        "managed_source": not bool(source_path),
        "commands": commands,
        "effects": [
            "Installs the bundled Sciunit Python package and native runtime.",
            "Creates or replaces the audit-kernel Sciunit project.",
            "Installs Sciunit Audit and Sciunit Repeat Jupyter kernels for the current user.",
        ],
        "requires_confirmation": True,
    }


def install_flinc(
    kernel_name: str = DEFAULT_KERNEL_NAME,
    repository: str = DEFAULT_FLINC_REPOSITORY,
    revision: str = DEFAULT_FLINC_REVISION,
    source_path: str = "",
    confirm: bool = False,
) -> dict[str, object]:
    """Install FLINC after explicit confirmation; otherwise return only the plan."""
    plan = installation_plan(kernel_name, repository, revision, source_path)
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Review the installation plan and explicitly confirm before installing.",
            "plan": plan,
        }
    if not sys.platform.startswith("linux"):
        raise InstallationError("FLINC/Sciunit execution is supported only on Linux.")

    for command in ("bash", "cmake", "git", "jupyter", "make"):
        if shutil.which(command) is None:
            raise InstallationError(f"Required command is not available: {command}")

    kernel_dir = _kernel_resource_dir(kernel_name)
    source = _validate_source(Path(source_path)) if source_path else _prepare_source(
        repository, revision
    )
    sciunit_archive = max(source.glob("sciunit2-*.tar.gz"))

    pip_output = _run(
        [sys.executable, "-m", "pip", "install", str(sciunit_archive)],
        cwd=source,
    )
    install_output = _run(
        [shutil.which("bash") or "bash", str(source / "install.sh"), str(kernel_dir)],
        cwd=source,
    )
    kernels = _kernels()
    audit_kernels = sorted(name for name in kernels if "audit" in name.casefold())
    repeat_kernels = sorted(name for name in kernels if "repeat" in name.casefold())
    if not audit_kernels or not repeat_kernels:
        raise InstallationError(
            "Installation completed without both Audit and Repeat kernels appearing in Jupyter."
        )

    return {
        "status": "installed",
        "source": str(source),
        "kernel_source": str(kernel_dir),
        "audit_kernels": audit_kernels,
        "repeat_kernels": repeat_kernels,
        "pip_output_tail": pip_output[-2000:],
        "install_output_tail": install_output[-2000:],
    }

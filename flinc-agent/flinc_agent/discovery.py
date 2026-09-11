"""Portable discovery of Sciunit projects and captured CDE packages."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .config import STALE_RUNTIME_ENVIRONMENT_VARIABLES


def _path_key(path: Path) -> str:
    try:
        return os.path.normcase(str(path.expanduser().resolve()))
    except OSError:
        return os.path.normcase(str(path.expanduser()))


def _existing_directories(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        expanded = path.expanduser()
        key = _path_key(expanded)
        if key in seen:
            continue
        try:
            if not expanded.is_dir():
                continue
            resolved = expanded.resolve()
        except OSError:
            continue
        seen.add(key)
        result.append(resolved)
    return result


def _sciunit_api_root() -> Path | None:
    try:
        from sciunit2 import workspace

        return Path(workspace.location_for(""))
    except (ImportError, OSError):
        return None


def discover_sciunit_roots(
    additional_roots: list[str] | None = None,
    scan_user_homes: bool = False,
) -> list[Path]:
    """Find likely Sciunit roots using APIs, configuration, and bounded home scans."""
    candidates: list[Path] = []
    for variable in ("FLINC_SCIUNIT_ROOT", "SCIUNIT_ROOT"):
        value = os.environ.get(variable)
        if value:
            candidates.append(Path(value))

    api_root = _sciunit_api_root()
    if api_root is not None:
        candidates.append(api_root)

    candidates.extend([Path.home() / "sciunit", Path.cwd() / "sciunit"])
    candidates.extend(Path(value) for value in additional_roots or [])

    if scan_user_homes and os.name == "posix":
        candidates.append(Path("/root/sciunit"))
        home_root = Path("/home")
        try:
            candidates.extend(path / "sciunit" for path in home_root.iterdir())
        except OSError:
            pass

    return _existing_directories(candidates)


def _read_active_project(root: Path) -> Path | None:
    marker = root / ".activated"
    try:
        first_line = marker.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return None
    if not first_line:
        return None
    candidate = Path(first_line).expanduser()
    return candidate.resolve() if candidate.exists() else candidate


def _project_directories(root: Path) -> list[Path]:
    projects: list[Path] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return projects
    for child in children:
        if not child.is_dir():
            continue
        if (child / "sciunit.db").is_file() or (child / "cde-package").is_dir():
            projects.append(child.resolve())
    return sorted(projects, key=lambda value: value.name.casefold())


def _kernel_specs() -> dict[str, str]:
    jupyter = shutil.which("jupyter")
    if jupyter is None:
        return {}
    try:
        result = subprocess.run(
            [jupyter, "kernelspec", "list", "--json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}
    return {
        name: str(details.get("resource_dir", ""))
        for name, details in payload.get("kernelspecs", {}).items()
    }


def environment_status(
    additional_roots: list[str] | None = None,
    scan_user_homes: bool = False,
) -> dict[str, object]:
    """Return FLINC/Sciunit readiness without exposing credential values."""
    roots = discover_sciunit_roots(additional_roots, scan_user_homes)
    root_details = []
    for root in roots:
        active = _read_active_project(root)
        root_details.append(
            {
                "root": str(root),
                "active_project": str(active) if active else None,
                "projects": [str(path) for path in _project_directories(root)],
            }
        )

    spec = importlib.util.find_spec("sciunit2")
    kernels = _kernel_specs()
    return {
        "platform": os.name,
        "sciunit_command": shutil.which("sciunit"),
        "sciunit_python_package": spec.origin if spec and spec.origin else None,
        "sciunit_roots": root_details,
        "kernels": kernels,
        "audit_kernel_installed": any("audit" in name.casefold() for name in kernels),
        "repeat_kernel_installed": any("repeat" in name.casefold() for name in kernels),
    }


def _execution_ids(database: Path) -> tuple[list[str], str | None]:
    if not database.is_file():
        return [], "sciunit.db is missing"
    connection = None
    try:
        uri = f"file:{database.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        rows = connection.execute("select id from revs order by id").fetchall()
        return [f"e{int(row[0])}" for row in rows], None
    except (sqlite3.Error, OSError, ValueError) as exc:
        return [], f"Could not read sciunit.db: {exc}"
    finally:
        if connection is not None:
            connection.close()


def _bounded_tree_summary(root: Path, limit: int = 10_000) -> dict[str, object]:
    file_count = 0
    directory_count = 0
    total_bytes = 0
    truncated = False
    try:
        for current_root, directories, files in os.walk(root):
            directories[:] = [name for name in directories if name != ".git"]
            directory_count += len(directories)
            for filename in files:
                file_count += 1
                try:
                    total_bytes += (Path(current_root) / filename).stat().st_size
                except OSError:
                    pass
                if file_count >= limit:
                    truncated = True
                    return {
                        "files": file_count,
                        "directories": directory_count,
                        "bytes": total_bytes,
                        "truncated": truncated,
                    }
    except OSError:
        truncated = True
    return {
        "files": file_count,
        "directories": directory_count,
        "bytes": total_bytes,
        "truncated": truncated,
    }


def _captured_runtime_environment(package: Path) -> list[str]:
    environment_file = package / "cde.full-environment.cde-root"
    try:
        content = environment_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    ignored: set[str] = set()
    try:
        for line in (package / "cde.options").read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            option, separator, value = line.strip().partition("=")
            if separator and option == "ignore_environment_var" and value:
                ignored.add(value.strip())
    except OSError:
        pass

    return sorted(
        name
        for name in STALE_RUNTIME_ENVIRONMENT_VARIABLES
        if f"{name}=" in content and name not in ignored
    )


def inspect_project(project_path: str) -> dict[str, object]:
    """Inspect a Sciunit project and its checked-out CDE package read-only."""
    project = Path(project_path).expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"Sciunit project not found: {project}")

    execution_ids, database_error = _execution_ids(project / "sciunit.db")
    package = project / "cde-package"
    required_package_files = (
        "cde-exec",
        "cde-root",
        "cde.options",
        "cde.full-environment.cde-root",
    )
    missing_package_files = [
        name for name in required_package_files if not (package / name).exists()
    ]
    issues: list[str] = []
    if database_error:
        issues.append(database_error)
    if not execution_ids:
        issues.append("No committed executions were found; Repeat has no execution to run.")
    if package.is_dir() and missing_package_files:
        issues.append(
            "The checked-out cde-package is incomplete: " + ", ".join(missing_package_files)
        )

    stale_environment = _captured_runtime_environment(package)
    if stale_environment:
        issues.append(
            "Captured runtime-specific environment variables may override the current "
            "Repeat session: " + ", ".join(stale_environment)
        )

    archives = sorted(path.name for path in project.glob("e*.json") if path.is_file())
    return {
        "project": str(project),
        "database": str(project / "sciunit.db"),
        "execution_ids": execution_ids,
        "execution_archives": archives,
        "cde_package": str(package),
        "cde_package_present": package.is_dir(),
        "cde_root": str(package / "cde-root"),
        "missing_package_entries": missing_package_files,
        "captured_runtime_environment_names": stale_environment,
        "package_summary": _bounded_tree_summary(package) if package.is_dir() else None,
        "issues": issues,
    }


def resolve_project(project_path: str = "", additional_roots: list[str] | None = None) -> Path:
    """Resolve an explicit project or the active project across discovered roots."""
    if project_path:
        project = Path(project_path).expanduser()
        if not project.is_dir():
            raise FileNotFoundError(f"Sciunit project not found: {project}")
        return project.resolve()

    active_projects = [
        active
        for root in discover_sciunit_roots(additional_roots)
        if (active := _read_active_project(root)) is not None and active.is_dir()
    ]
    unique = _existing_directories(active_projects)
    if len(unique) == 1:
        return unique[0]
    if not unique:
        raise FileNotFoundError(
            "No active Sciunit project was found. Provide project_path or additional_roots."
        )
    raise RuntimeError(
        "Multiple active Sciunit projects were found; provide project_path explicitly: "
        + ", ".join(str(path) for path in unique)
    )


def diagnose_repeat(
    project_path: str = "",
    execution_id: str = "e1",
    additional_roots: list[str] | None = None,
) -> dict[str, object]:
    """Diagnose whether a Sciunit execution is ready for the Repeat kernel."""
    project = resolve_project(project_path, additional_roots)
    report = inspect_project(str(project))
    issues = list(report["issues"])
    execution_ids = report["execution_ids"]
    if execution_id not in execution_ids:
        issues.append(
            f"Execution {execution_id} is not committed. Available executions: "
            + (", ".join(execution_ids) if execution_ids else "none")
        )
    expected_archive = f"{execution_id}.json"
    if execution_id in execution_ids and expected_archive not in report["execution_archives"]:
        issues.append(
            f"Execution metadata contains {execution_id}, but {expected_archive} is missing."
        )

    recommendations: list[str] = []
    if not execution_ids:
        recommendations.append(
            "Finish the Audit run, shut down the Audit kernel, and wait for Sciunit to commit it."
        )
    elif execution_id not in execution_ids:
        recommendations.append("Select an execution ID returned by sciunit list.")
    if not report["cde_package_present"]:
        recommendations.append(
            f"Run 'sciunit checkout {execution_id}' only if you want to inspect its CDE package; "
            "the Repeat command checks it out automatically."
        )
    if report["captured_runtime_environment_names"]:
        recommendations.append(
            "Exclude runtime credentials, metadata endpoints, session IDs, hostnames, and "
            "Jupyter tokens in cde.options, then create a new Audit execution."
        )

    return {
        "ready": not issues,
        "execution_id": execution_id,
        "project": str(project),
        "issues": issues,
        "recommendations": recommendations,
        "inspection": report,
    }

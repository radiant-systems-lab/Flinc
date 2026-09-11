"""Read-only discovery and inspection of FLINC and Sciunit source code."""

from __future__ import annotations

import importlib.util
import os
import json
from collections.abc import Iterable
from pathlib import Path

from .config import IGNORED_SOURCE_DIRECTORIES, SOURCE_SUFFIXES, agent_cache_dir


def _unique_existing_directories(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if resolved.is_dir() and key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def _editable_flinc_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "install.sh").is_file() and (candidate / "handler.py").is_file():
        return candidate
    return None


def _installed_sciunit_root() -> Path | None:
    spec = importlib.util.find_spec("sciunit2")
    if spec is None or spec.origin is None:
        return None
    package_dir = Path(spec.origin).resolve().parent
    return package_dir


def discover_source_roots(additional_roots: list[str] | None = None) -> dict[str, list[str]]:
    """Discover source roots without scanning the entire filesystem."""
    flinc_candidates: list[Path] = []
    sciunit_candidates: list[Path] = []

    for raw_root in additional_roots or []:
        root = Path(raw_root)
        if (root / "install.sh").is_file() or (root / "handler.py").is_file():
            flinc_candidates.append(root)
        if (root / "sciunit2").is_dir() or root.name == "sciunit2":
            sciunit_candidates.append(root)

    if os.environ.get("FLINC_SOURCE_ROOT"):
        flinc_candidates.append(Path(os.environ["FLINC_SOURCE_ROOT"]))
    from jupyter_core.paths import jupyter_config_dir
    try:
        configured = json.loads((Path(jupyter_config_dir()) / 'flinc-agent.json').read_text())
        if configured.get('flinc_source_root'):
            flinc_candidates.append(Path(configured['flinc_source_root']))
    except (OSError, ValueError):
        pass
    if os.environ.get("SCIUNIT_SOURCE_ROOT"):
        sciunit_candidates.append(Path(os.environ["SCIUNIT_SOURCE_ROOT"]))

    editable_root = _editable_flinc_root()
    if editable_root is not None:
        flinc_candidates.append(editable_root)

    managed_sources = agent_cache_dir() / "sources"
    try:
        flinc_candidates.extend(
            path
            for path in managed_sources.iterdir()
            if path.name.startswith("flinc-") and (path / "install.sh").is_file()
        )
    except OSError:
        pass

    installed_sciunit = _installed_sciunit_root()
    if installed_sciunit is not None:
        sciunit_candidates.append(installed_sciunit)

    return {
        "flinc": [str(path) for path in _unique_existing_directories(flinc_candidates)],
        "sciunit": [str(path) for path in _unique_existing_directories(sciunit_candidates)],
    }


def _component_roots(
    component: str,
    additional_roots: list[str] | None,
) -> list[tuple[str, Path]]:
    roots = discover_source_roots(additional_roots)
    normalized = component.lower()
    if normalized not in {"all", "flinc", "sciunit"}:
        raise ValueError("component must be one of: all, flinc, sciunit")

    selected: list[tuple[str, Path]] = []
    for name in ("flinc", "sciunit"):
        if normalized in {"all", name}:
            selected.extend((name, Path(path)) for path in roots[name])
    return selected


def search_source(
    query: str,
    component: str = "all",
    max_results: int = 20,
    additional_roots: list[str] | None = None,
) -> dict[str, object]:
    """Search trusted FLINC/Sciunit source roots and return bounded snippets."""
    if not query.strip():
        raise ValueError("query must not be empty")
    max_results = max(1, min(max_results, 100))
    needle = query.casefold()
    matches: list[dict[str, object]] = []
    searched_roots: list[str] = []

    for name, root in _component_roots(component, additional_roots):
        searched_roots.append(str(root))
        for path in root.rglob("*"):
            if len(matches) >= max_results:
                break
            if any(part in IGNORED_SOURCE_DIRECTORIES for part in path.parts):
                continue
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if needle in line.casefold():
                    matches.append(
                        {
                            "component": name,
                            "path": path.relative_to(root).as_posix(),
                            "line": line_number,
                            "text": line.strip()[:500],
                        }
                    )
                    if len(matches) >= max_results:
                        break

    return {
        "query": query,
        "searched_roots": searched_roots,
        "matches": matches,
        "truncated": len(matches) >= max_results,
    }


def read_source_file(
    component: str,
    relative_path: str,
    start_line: int = 1,
    max_lines: int = 200,
    additional_roots: list[str] | None = None,
) -> dict[str, object]:
    """Read a bounded section of a file under a discovered source root."""
    roots = _component_roots(component, additional_roots)
    if not roots:
        raise FileNotFoundError(f"No source root found for {component}")
    if Path(relative_path).is_absolute():
        raise ValueError("relative_path must be relative to a discovered source root")

    start_line = max(1, start_line)
    max_lines = max(1, min(max_lines, 500))
    for name, root in roots:
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise ValueError("relative_path must stay inside the source root") from None
        if not candidate.is_file():
            continue
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = lines[start_line - 1 : start_line - 1 + max_lines]
        return {
            "component": name,
            "root": str(root),
            "path": relative_path,
            "start_line": start_line,
            "end_line": start_line + len(selected) - 1,
            "content": "\n".join(selected),
            "truncated": start_line - 1 + len(selected) < len(lines),
        }
    raise FileNotFoundError(f"Source file not found: {relative_path}")

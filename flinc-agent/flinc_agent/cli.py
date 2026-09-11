"""Command-line access to flinc-agent's deterministic services."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .discovery import diagnose_repeat, environment_status, inspect_project
from .installer import install_flinc, installation_plan
from .source import read_source_file, search_source
from .version import __version__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flinc-agent")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="discover FLINC/Sciunit state")
    status.add_argument("--root", action="append", default=[])
    status.add_argument("--no-home-scan", action="store_true")

    inspect = subparsers.add_parser("inspect", help="inspect a Sciunit project")
    inspect.add_argument("project_path")

    diagnose = subparsers.add_parser("diagnose-repeat", help="diagnose Repeat readiness")
    diagnose.add_argument("--project", default="")
    diagnose.add_argument("--execution", default="e1")
    diagnose.add_argument("--root", action="append", default=[])

    search = subparsers.add_parser("search-source", help="search FLINC/Sciunit source")
    search.add_argument("query")
    search.add_argument("--component", choices=("all", "flinc", "sciunit"), default="all")
    search.add_argument("--root", action="append", default=[])
    search.add_argument("--max-results", type=int, default=20)

    read = subparsers.add_parser("read-source", help="read a source file")
    read.add_argument("component", choices=("flinc", "sciunit"))
    read.add_argument("relative_path")
    read.add_argument("--root", action="append", default=[])
    read.add_argument("--start-line", type=int, default=1)
    read.add_argument("--max-lines", type=int, default=200)

    for name, help_text in (
        ("install-plan", "show the FLINC installation plan"),
        ("install", "install FLINC after explicit confirmation"),
    ):
        install = subparsers.add_parser(name, help=help_text)
        install.add_argument("--kernel", default="python3")
        install.add_argument(
            "--repository", default="https://github.com/radiant-systems-lab/Flinc.git"
        )
        install.add_argument("--revision", default="main")
        install.add_argument("--source", default="")
        if name == "install":
            install.add_argument("--yes", action="store_true")

    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "status":
        return environment_status(args.root, not args.no_home_scan)
    if args.command == "inspect":
        return inspect_project(args.project_path)
    if args.command == "diagnose-repeat":
        return diagnose_repeat(args.project, args.execution, args.root)
    if args.command == "search-source":
        return search_source(args.query, args.component, args.max_results, args.root)
    if args.command == "read-source":
        return read_source_file(
            args.component,
            args.relative_path,
            args.start_line,
            args.max_lines,
            args.root,
        )
    if args.command == "install-plan":
        return installation_plan(args.kernel, args.repository, args.revision, args.source)
    if args.command == "install":
        return install_flinc(
            args.kernel,
            args.repository,
            args.revision,
            args.source,
            args.yes,
        )
    raise ValueError(f"Unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the flinc-agent command-line interface."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = _dispatch(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

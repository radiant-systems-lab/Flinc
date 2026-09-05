#!/usr/bin/env python
"""Apply FLINC CDE environment policy before Sciunit commits an audit."""

from pathlib import Path
import sys


LIVE_ENVIRONMENT_KEYS = (
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
    "ECS_AGENT_URI",
    "ECS_CONTAINER_METADATA_URI",
    "ECS_CONTAINER_METADATA_URI_V4",
    "JUPYTER_TOKEN",
    "SESSION_ID",
    "SESSION_OWNER_ID",
    "SESSION_MODE",
    "SCIUNIT_MODE",
    "HOSTNAME",
    "JPY_SESSION_NAME",
    "JPY_PARENT_PID",
)


def apply_cde_options(pkgdir):
    options = Path(pkgdir) / "cde.options"
    original = options.read_text()
    existing = set(original.splitlines())
    additions = [
        f"ignore_environment_var={key}"
        for key in LIVE_ENVIRONMENT_KEYS
        if f"ignore_environment_var={key}" not in existing
    ]
    if additions:
        options.write_text(original.rstrip("\n") + "\n" + "\n".join(additions) + "\n")


def main():
    import sciunit2.core
    from sciunit2.cli import main as sciunit_main

    original_capture = sciunit2.core.capture

    def capture_with_cde_options(args):
        result = original_capture(args)
        apply_cde_options("cde-package")
        return result

    sciunit2.core.capture = capture_with_cde_options
    return sciunit_main()


if __name__ == "__main__":
    sys.exit(main())

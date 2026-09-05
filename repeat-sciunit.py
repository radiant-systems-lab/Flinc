"""Apply live-container environment policy after Sciunit restores a replay."""

from pathlib import Path
import os
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


def prepare_replay_environment(pkgdir):
    package = Path(pkgdir)
    keys = {key.encode() for key in LIVE_ENVIRONMENT_KEYS}
    for path in package.glob("cde.full-environment*"):
        original = path.read_bytes()
        entries = original.split(b"\0")
        cleaned = b"\0".join(
            entry for entry in entries if entry.split(b"=", 1)[0] not in keys
        )
        if cleaned != original:
            path.write_bytes(cleaned)

    # CDE must inherit these values from the launching container, even when
    # a captured environment is restored by CheckoutContext on every restart.
    options = package / "cde.options"
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

    original_repeat = sciunit2.core.repeat

    def repeat_with_live_environment(pkgdir, orig, newargs):
        prepare_replay_environment(pkgdir)
        if newargs[:2] == ["-m", "ipykernel_launcher"]:
            # CDE does not retain variables missing from its captured file.
            # Read the still-running launcher's environment through /proc,
            # which CDE excludes from replay. Never write live values to disk.
            bootstrap = (
                "import os, runpy, sys; "
                f"raw = open('/proc/{os.getpid()}/environ', 'rb').read(); "
                "live = dict(entry.split(b'=', 1) for entry in raw.split(b'\\0') if b'=' in entry); "
                f"keys = {LIVE_ENVIRONMENT_KEYS!r}; "
                "[(os.environ.__setitem__(key, os.fsdecode(live[os.fsencode(key)])) "
                "if os.fsencode(key) in live else os.environ.pop(key, None)) for key in keys]; "
                "sys.argv = ['ipykernel_launcher', *sys.argv[1:]]; "
                "runpy.run_module('ipykernel_launcher', run_name='__main__')"
            )
            newargs = ["-c", bootstrap, *newargs[2:]]
        return original_repeat(pkgdir, orig, newargs)

    sciunit2.core.repeat = repeat_with_live_environment
    return sciunit_main()


if __name__ == "__main__":
    sys.exit(main())

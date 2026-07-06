#!/usr/bin/env python
import os
import re
import signal
import subprocess
import sys

import psutil


def _signal_children(sig):
    print("Inside signal handler", file=sys.__stderr__)
    parent = psutil.Process(os.getpid())
    print("parent:", parent.exe(), file=sys.__stderr__)
    for child in parent.children(recursive=True):
        print("child:", child.exe(), file=sys.__stderr__)
        child.send_signal(sig)


def sigIntHandler(*_):
    _signal_children(signal.SIGKILL)


def sigTermHandler(*_):
    _signal_children(signal.SIGKILL)


def _active_project_dir():
    activated = os.path.expanduser('~/sciunit/.activated')
    try:
        with open(activated, encoding='utf-8') as f:
            project = f.readline().strip()
    except OSError:
        return None
    return project or None


def _extract_locked_rev(output):
    match = re.search(r"execution ['\"]([^'\"]+)['\"] is encrypted", output)
    if match:
        return match.group(1)
    return None


def _write_locked_message(rev):
    project = _active_project_dir()
    unlock = f"sciunit unlock {rev} --key <shared-key>"
    lines = [
        "",
        "Sciunit repeat cannot start because the selected execution is encrypted.",
        "Protected files must be unlocked before the Repeat Kernel can replay this notebook.",
        "",
        "Run this in a terminal:",
    ]
    if project:
        lines.append(f"  cd {project}")
    lines.extend([
        f"  {unlock}",
        "",
        "Then restart the Sciunit Repeat Kernel and run the notebook again.",
        "See flinc.log for the full sciunit error output.",
        "",
    ])
    sys.__stderr__.write("\n".join(lines))
    sys.__stderr__.flush()


def main():
    print("Repeat Kernel", file=sys.__stderr__)
    signal.signal(signal.SIGINT, sigIntHandler)
    signal.signal(signal.SIGTERM, sigTermHandler)

    with open('flinc.log', 'a', encoding='utf-8') as log:
        log.write("Repeat Kernel\n")
        log.flush()
        proc = subprocess.run(sys.argv[1:], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
        if proc.stdout:
            log.write(proc.stdout)
        if proc.stderr:
            log.write(proc.stderr)
        log.flush()

    if proc.returncode != 0:
        output = (proc.stdout or '') + (proc.stderr or '')
        rev = _extract_locked_rev(output)
        if rev:
            _write_locked_message(rev)
        else:
            sys.__stderr__.write(output)
            sys.__stderr__.flush()
        return proc.returncode
    return 0


if __name__ == '__main__':
    sys.exit(main())

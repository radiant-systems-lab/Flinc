#!/usr/bin/env python
import os
import signal
import subprocess
import sys

import psutil


def proc_exe(proc):
    try:
        return proc.exe()
    except (psutil.Error, FileNotFoundError):
        return '<exited>'


def terminate_children(sig=signal.SIGKILL):
    print("Inside signal handler")
    parent = psutil.Process(os.getpid())
    print("parent:", proc_exe(parent))
    for child in parent.children(recursive=True):
        print("child:", proc_exe(child))
        try:
            child.send_signal(sig)
        except psutil.Error:
            pass


def sigIntHandler(*_):
    terminate_children(signal.SIGKILL)


def sigTermHandler(*_):
    terminate_children(signal.SIGKILL)


def normalized_args():
    args = sys.argv[1:]
    this_script = os.path.abspath(__file__)
    while args and os.path.abspath(args[0]) == this_script:
        args = args[1:]
    return args


def repeat_unlock_error(args):
    if len(args) < 5 or args[0] != 'sciunit' or args[1] != 'given':
        return None, None
    if args[3] != 'repeat':
        return None, None

    connection_file = args[2]
    rev = args[4]

    import sciunit2.security
    import sciunit2.workspace
    from sciunit2.command.context import CheckoutContext

    project_root = sciunit2.workspace.at()
    if rev == 'latest':
        emgr, _ = sciunit2.workspace.current()
        with emgr.exclusive():
            rev, _ = emgr.last()

    if sciunit2.security.cached_shared_key(project_root, rev):
        return None, connection_file

    with CheckoutContext(rev) as (pkgdir, _orig):
        if not sciunit2.security.package_requires_unlock(pkgdir):
            return None, connection_file
        shared_key = sciunit2.security.cached_shared_key(project_root, rev)
        if shared_key:
            return None, connection_file

    message = (
        "sciunit: repeat: execution %r is encrypted and cannot be repeated yet.\n"
        "Run this command in a terminal, then come back and restart the Sciunit Repeat Kernel:\n"
        "  sciunit unlock %s --key <shared-key>"
    ) % (rev, rev)
    return message, connection_file


def launch_error_kernel(connection_file, message, log):
    env = os.environ.copy()
    env['FLINC_REPEAT_ERROR'] = message
    error_kernel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'error-kernel.py')
    return subprocess.run([sys.executable, error_kernel, '-f', connection_file],
                          stdout=log, stderr=log, env=env).returncode


def main():
    log = open('flinc.log', 'a', buffering=1)
    sys.stdout = log
    sys.stderr = log
    print("Repeat Kernel")
    signal.signal(signal.SIGINT, sigIntHandler)
    signal.signal(signal.SIGTERM, sigTermHandler)
    args = normalized_args()

    try:
        error_message, connection_file = repeat_unlock_error(args)
    except Exception as exc:
        error_message = "sciunit: repeat: failed before the kernel started: %s" % exc
        connection_file = args[2] if len(args) > 2 else None

    if error_message and connection_file:
        print(error_message)
        return launch_error_kernel(connection_file, error_message, log)

    result = subprocess.run(args, stdout=log, stderr=log)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())

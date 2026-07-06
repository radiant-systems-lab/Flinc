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


def terminate_python_grandchildren(sig=signal.SIGTERM):
    print("Inside signal handler")
    try:
        parent = psutil.Process(sciunit_pid)
    except (NameError, psutil.Error):
        return
    print("parent:", proc_exe(parent))
    for child1 in parent.children(recursive=False):
        print("child1:", proc_exe(child1))
        for child2 in child1.children(recursive=False):
            exe = proc_exe(child2)
            print("child2:", exe)
            if "bin/python" in exe:
                try:
                    child2.send_signal(sig)
                except psutil.Error:
                    pass


def sigIntHandler(*_):
    terminate_python_grandchildren(signal.SIGTERM)


def sigTermHandler(*_):
    terminate_python_grandchildren(signal.SIGTERM)


sys.stdout = open('flinc.log', 'a', buffering=1)
sys.stderr = open('flinc.log', 'a', buffering=1)
signal.signal(signal.SIGINT, sigIntHandler)
signal.signal(signal.SIGTERM, sigTermHandler)
p = subprocess.Popen(sys.argv[1:], stdout=sys.stdout, stderr=sys.stderr,
                     start_new_session=True)
sciunit_pid = p.pid
sys.exit(p.wait())

#!/usr/bin/env python
import signal
import os
import psutil
import sys
import subprocess

def sigIntHandler(*_):
    print("Inside sigIntHandler")
    parent = psutil.Process(os.getpid())
    print("parent:", parent.exe())
    for child in parent.children(recursive=True):
        print("child:", child.exe())
        child.send_signal(signal.SIGKILL)

def sigTermHandler(*_):
    print("Inside sigTermHandler")
    parent = psutil.Process(os.getpid())
    print("parent:", parent.exe())
    for child in parent.children(recursive=True):
        print("child:", child.exe())
        child.send_signal(signal.SIGKILL)


print("Repeat Kernel")
sys.stdout = open('flinc.log', 'a')
sys.stderr = open('flinc.log', 'a')
signal.signal(signal.SIGINT, sigIntHandler)
signal.signal(signal.SIGTERM, sigTermHandler)
command = sys.argv[1:]
if command and os.path.basename(command[0]) == 'sciunit':
    wrapper = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repeat-sciunit.py')
    command = [sys.executable, wrapper, *command[1:]]
sys.exit(subprocess.run(command).returncode)

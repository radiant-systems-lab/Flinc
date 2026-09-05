#!/usr/bin/env python
import signal
import os
import psutil
import sys
import subprocess


def sigIntHandler(*_):
    print("Inside sigIntHandler")
    parent = psutil.Process(sciunit_pid)
    print("parent:", parent.exe())
    for child1 in parent.children(recursive=False):
        print("child1:", child1.exe())
        for child2 in child1.children(recursive=False):
            print("child2:", child2.exe())
            if "bin/python" in child2.exe():
                child2.send_signal(signal.SIGTERM)

def sigTermHandler(*_):
    print("Inside sigTermHandler")    
    parent = psutil.Process(sciunit_pid)
    print("parent:", parent.exe())
    for child1 in parent.children(recursive=False):
        print("child1:", child1.exe())
        for child2 in child1.children(recursive=False):
            print("child2:", child2.exe())
            if "bin/python" in child2.exe():
                child2.send_signal(signal.SIGTERM)


sys.stdout = open('flinc.log', 'a')
sys.stderr = open('flinc.log', 'a')
signal.signal(signal.SIGINT, sigIntHandler)
signal.signal(signal.SIGTERM, sigTermHandler)
command = sys.argv[1:]
if command[:2] == ['sciunit', 'exec']:
    wrapper = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit-sciunit.py')
    command = [sys.executable, wrapper, *command[1:]]
p = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr, start_new_session=True)
sciunit_pid = p.pid
sys.exit(p.wait())

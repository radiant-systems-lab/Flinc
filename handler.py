#!/usr/bin/env python
import signal
import os
import psutil
import sys
import subprocess
from sciunit2.records import ExecutionManager
import json

REPEAT_KERNEL_TEMPLATE = {
    "argv": [
	os.path.expanduser('~') + "/sciunit/repeat-handler.py",
    "sciunit", "given", "{connection_file}", "repeat", "EXECUTION_ID",
    "-m",
    "ipykernel_launcher",
    "-f",
    "%"
    ],
    "display_name": "Sciunit Repeat Kernel",
    "language": "python"
}

def get_last_execution():
    em = ExecutionManager(os.path.expanduser('~') + '/sciunit/audit-kernel')
    return em.get_last_id()

def createRepeatKernel(eid):

    repeat_kernel_path = os.path.expanduser('~') + '/sciunit/repeat-kernel-e' +str(eid)

    if eid == 1 and os.path.isdir(repeat_kernel_path):
        eid= eid+1
        repeat_kernel_path = os.path.expanduser('~') + '/sciunit/repeat-kernel-e' +str(eid)

    os.makedirs(repeat_kernel_path, exist_ok=True)

    REPEAT_KERNEL_TEMPLATE['argv'][5] = "e" + str(eid)
    REPEAT_KERNEL_TEMPLATE['display_name'] = REPEAT_KERNEL_TEMPLATE['display_name'] + " E-" + str(eid) 

    # Writing JSON data to a file
    with open(repeat_kernel_path + "/kernel.json", "w") as json_file:
        json.dump(REPEAT_KERNEL_TEMPLATE, json_file, indent=4)

    # install repeat kernel
    subprocess.run(["jupyter", "kernelspec", "install", "--user", repeat_kernel_path], check=True)
    print(f"Kernel '{repeat_kernel_path}' installed successfully.")
    
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
    createRepeatKernel(get_last_execution())

sys.stdout = open('flinc.log', 'a')
sys.stderr = open('flinc.log', 'a')
signal.signal(signal.SIGINT, sigIntHandler)
signal.signal(signal.SIGTERM, sigTermHandler)
p = subprocess.Popen(sys.argv[1:], stdout=sys.stdout, stderr=sys.stderr, start_new_session=True)
sciunit_pid = p.pid
p.wait()

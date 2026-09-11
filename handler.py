#!/usr/bin/env python
"""Launch Audit and let Sciunit commit after kernel shutdown."""
from pathlib import Path
import json
import sys
from kernel_process import run


def main():
    command = sys.argv[1:]
    if command[:2] == ['sciunit', 'exec']:
        if 'ipykernel_launcher' in command:
            bootstrap = str(Path(__file__).with_name('kernel_bootstrap.py'))
            command += [
                '--HistoryManager.hist_file=:memory:',
                '--IPKernelApp.exec_lines=' + json.dumps([
                    'import runpy; _flinc_warmup = runpy.run_path(' + repr(bootstrap) + '); del _flinc_warmup'
                ]),
            ]
        command = [sys.executable, str(Path(__file__).with_name('audit-sciunit.py')), *command[1:]]
    return run(command)


if __name__ == '__main__':
    sys.exit(main())

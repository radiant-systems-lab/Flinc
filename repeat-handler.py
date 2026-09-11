#!/usr/bin/env python
"""Launch Repeat with normal interrupts and accurate exit status."""
import os
import re
import sys
from kernel_process import run

def repeat_command(args, execution_id=None):
    command = list(args)
    if execution_id:
        if not re.fullmatch(r'e[1-9][0-9]*', execution_id):
            raise ValueError('FLINC_REPEAT_EXECUTION must have the form e1, e2, ...')
        command[command.index('repeat') + 1] = execution_id
    if 'ipykernel_launcher' in command:
        command.append('--HistoryManager.hist_file=:memory:')
    return command


if __name__ == '__main__':
    sys.exit(run(repeat_command(sys.argv[1:], os.environ.get('FLINC_REPEAT_EXECUTION'))))

#!/usr/bin/env python
import os

from ipykernel.kernelapp import IPKernelApp
from ipykernel.kernelbase import Kernel


class FlincErrorKernel(Kernel):
    implementation = 'flinc_error'
    implementation_version = '1.0'
    language = 'python'
    language_version = '3'
    language_info = {
        'name': 'python',
        'mimetype': 'text/x-python',
        'file_extension': '.py',
    }
    banner = 'Sciunit repeat failed'

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        text = os.environ.get('FLINC_REPEAT_ERROR',
                              'Sciunit repeat failed before the kernel started.')
        lines = text.splitlines() or ['Sciunit repeat failed']
        if not silent:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': text if text.endswith('\n') else text + '\n',
            })
        return {
            'status': 'error',
            'execution_count': self.execution_count,
            'ename': 'SciunitRepeatError',
            'evalue': lines[0],
            'traceback': lines,
        }


if __name__ == '__main__':
    IPKernelApp.launch_instance(kernel_class=FlincErrorKernel)

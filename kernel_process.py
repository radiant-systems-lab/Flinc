"""Forward kernel signals without killing Sciunit's capture/commit process."""
import signal
import subprocess
import psutil


def forward_signal(process, signum, kernel_only=False):
    """Signal the actual Python kernel, tolerating shutdown races."""
    try:
        parent = psutil.Process(process.pid)
        candidates = []
        for child in parent.children(recursive=True):
            try:
                # CDE executes Python through ld-linux; its process name is not
                # necessarily "python". Identify the module in argv instead.
                args = child.cmdline()
                if 'ipykernel_launcher' in args and '-m' in args:
                    candidates.append(child)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Launcher wrappers also contain kernel arguments; only signal leaves.
        parent_ids = set()
        for child in candidates:
            try:
                parent_ids.update(p.pid for p in child.parents())
            except psutil.NoSuchProcess:
                pass
        targets = [child for child in candidates if child.pid not in parent_ids]
        # After the kernel exits, Audit may still be archiving. Leave that
        # process alive; Jupyter's configured shutdown grace period covers it.
        if not targets and kernel_only:
            return
        for child in targets or [parent]:
            try:
                child.send_signal(signum)
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass


def run(command):
    with open('flinc.log', 'a', buffering=1) as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
        def handler(signum, _frame):
            forward_signal(process, signum, kernel_only='ipykernel_launcher' in command)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        code = process.wait()
    return code if code >= 0 else 128 - code

"""Configure an existing Linux FLINC/Jupyter installation without running notebooks."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from jupyter_core.paths import jupyter_config_dir, jupyter_path
from jupyter_client.kernelspec import KernelSpecManager


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flinc-root', type=Path, required=True)
    parser.add_argument('--kernel', default='python3')
    parser.add_argument('--toolkit-root', type=Path)
    parser.add_argument('--check', action='store_true', help='Check prerequisites without changing files')
    parser.add_argument('--initial-agent-mode', choices=['read-only', 'agent', 'agent-full-access'],
                        help='Explicit deployment choice; omitted preserves existing mode')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('FLINC Audit/Repeat currently requires Linux.')
    root = args.flinc_root.expanduser().resolve()
    for name in ['install_kernels.py', 'handler.py', 'repeat-handler.py', 'kernel_process.py', 'kernel_bootstrap.py']:
        if not (root / name).is_file():
            parser.error(f'Missing FLINC integration source: {root / name}')
    for command in ['sciunit', 'codex-acp', 'codex']:
        if not shutil.which(command):
            parser.error(f'Required command is not installed: {command}')
    if importlib.metadata.version('jupyterlab-commands-toolkit') != '0.2.0':
        parser.error('Browser compatibility patch supports commands-toolkit 0.2.0 only.')
    kernel = KernelSpecManager().get_kernel_spec(args.kernel)
    if 'ipykernel_launcher' not in kernel.argv:
        parser.error('Choose an existing Python/IPython kernel.')
    roots = [args.toolkit_root] if args.toolkit_root else [
        Path(p) / 'jupyterlab-commands-toolkit' for p in jupyter_path('labextensions')
    ]
    toolkit = next((p for p in roots if (p / 'package.json').is_file()), None)
    if toolkit is None:
        parser.error('Cannot find the browser extension; supply --toolkit-root.')
    from .browser_patch.apply_browser_patch import patch
    # Validate the exact prebuilt bundle before touching the installed extension.
    with tempfile.TemporaryDirectory(prefix='flinc-agent-check-') as temporary:
        staged = Path(temporary) / 'toolkit'
        shutil.copytree(toolkit, staged)
        patch(staged)
    if args.check:
        print('Prerequisites and browser patch compatibility checked. No files changed.')
        return
    backups = Path.home() / '.local/state/flinc-agent/backups'
    backups.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='setup-', dir=backups))
    shutil.copytree(toolkit, backup / 'commands-toolkit')
    config = Path(jupyter_config_dir()) / 'jupyter_server_config.d/flinc.json'
    config.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(config.read_text()) if config.exists() else {}
    if config.exists():
        shutil.copy2(config, backup / 'flinc.json')
    data.setdefault('KernelManager', {}).setdefault('shutdown_wait_time', 120.0)
    if args.initial_agent_mode:
        data.setdefault('FlincAgentPersona', {})['initial_agent_mode'] = args.initial_agent_mode
    subprocess.run([sys.executable, str(root / 'install_kernels.py'), kernel.resource_dir], check=True)
    patch(toolkit)
    config.write_text(json.dumps(data, indent=2) + '\n')
    source_config = Path(jupyter_config_dir()) / 'flinc-agent.json'
    if source_config.exists():
        shutil.copy2(source_config, backup / 'flinc-agent.json')
    source_config.write_text(json.dumps({'flinc_source_root': str(root)}, indent=2) + '\n')
    print(f'Agent integration configured. Backups: {backup}')
    print('Restart Jupyter, reload JupyterLab, and start a fresh Flinc Agent chat.')


if __name__ == '__main__':
    main()

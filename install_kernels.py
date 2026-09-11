"""Install kernel specs idempotently, preserving every existing Sciunit project."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from jupyter_client.kernelspec import KernelSpecManager


def main(kernel_dir):
    root = Path(__file__).resolve().parent
    source = json.loads((Path(kernel_dir) / 'kernel.json').read_text())
    if 'ipykernel_launcher' not in source['argv']:
        raise ValueError('FLINC Audit/Repeat requires a Python ipykernel specification')
    if any(Path(arg).name in {'handler.py', 'repeat-handler.py'} for arg in source['argv']):
        raise ValueError('Use the original Python kernel, not an already wrapped FLINC kernel')
    if not (Path.home() / 'sciunit' / 'audit-kernel').exists():
        subprocess.run(['sciunit', 'create', 'audit-kernel'], check=True)
    audit = json.loads(json.dumps(source))
    audit['argv'] = [str(root/'handler.py'), 'sciunit', 'exec', *source['argv']]
    audit['display_name'] = f"Sciunit Audit({source['display_name']})"
    repeat = {
        'argv': [str(root/'repeat-handler.py'), 'sciunit', 'given', '{connection_file}',
                 'repeat', 'e1', '-m', 'ipykernel_launcher', '-f', '%'],
        'display_name': 'Sciunit Repeat Kernel', 'language': 'python',
        'metadata': {'debugger': False},
    }
    manager = KernelSpecManager()
    if 'repeat-kernel' in manager.find_kernel_specs():
        repeat['env'] = dict(manager.get_kernel_spec('repeat-kernel').env)
    for name, spec in [('audit-kernel', audit), ('repeat-kernel', repeat)]:
        with tempfile.TemporaryDirectory(prefix='flinc-kernel-') as temporary:
            directory = Path(temporary) / name
            directory.mkdir()
            (directory/'kernel.json').write_text(json.dumps(spec, indent=2)+'\n')
            manager.install_kernel_spec(str(directory), kernel_name=name, user=True)
        print(f'Installed {name}; existing captures preserved')


if __name__ == '__main__':
    main(sys.argv[1])

import asyncio
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from flinc_agent.browser_patch.apply_browser_patch import patch
from flinc_agent.notebook_compat import configure_notebook_read_errors


@pytest.fixture
def unpatched_toolkit(tmp_path):
    root = tmp_path / 'toolkit'
    (root / 'static').mkdir(parents=True)
    (root / 'package.json').write_text(json.dumps({
        'version': '0.2.0',
        'jupyterlab': {'_build': {'load': 'static/remoteEntry.abc.js'}},
    }))
    (root / 'static/remoteEntry.abc.js').write_text('const chunks={509:"abc"};')
    (root / 'static/509.abc.js').write_text(
        'const n=crypto.randomUUID();const plugin={activate:e=>{'
        'const{commands:t}=e,o=e.serviceManager.events;}};'
    )
    return root


def test_uuid_startup_without_random_uuid(unpatched_toolkit):
    original = (unpatched_toolkit / 'static/509.abc.js').read_text().split(';const plugin')[0]
    chunk, _ = patch(unpatched_toolkit)
    repaired = (unpatched_toolkit / 'static' / chunk).read_text().split(';const plugin')[0]
    script = '''
const vm=require('node:vm'), assert=require('node:assert/strict');
const crypto={getRandomValues: a=>{a.fill(42);return a;}};
assert.throws(()=>vm.runInNewContext(ORIGINAL,{crypto}),/randomUUID/);
const uuid=vm.runInNewContext(REPAIRED+';n',{crypto});
assert.match(uuid,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
assert.equal(vm.runInNewContext(REPAIRED+';n',{crypto:{randomUUID:()=> 'native'}}),'native');
'''.replace('ORIGINAL', json.dumps(original)).replace('REPAIRED', json.dumps(repaired))
    subprocess.run(['node', '-e', script], check=True)


def test_browser_only_reports_and_repairs_without_kernel_setup(monkeypatch, capsys, unpatched_toolkit, tmp_path):
    from flinc_agent import setup
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path / 'home'))
    monkeypatch.setattr(setup, 'KernelSpecManager', lambda: pytest.fail('Kernel setup must not run'))
    monkeypatch.setattr(setup.shutil, 'which', lambda _: pytest.fail('Agent/Sciunit prerequisites must not be needed'))
    command = ['flinc-agent-setup', '--browser-only', '--toolkit-root', str(unpatched_toolkit)]
    before = {p.relative_to(unpatched_toolkit): p.read_bytes() for p in unpatched_toolkit.rglob('*') if p.is_file()}
    monkeypatch.setattr(sys, 'argv', command + ['--check'])
    setup.main()
    assert 'NEEDS REPAIR' in capsys.readouterr().out
    after = {p.relative_to(unpatched_toolkit): p.read_bytes() for p in unpatched_toolkit.rglob('*') if p.is_file()}
    assert before == after
    monkeypatch.setattr(sys, 'argv', command)
    setup.main()
    assert 'Browser repair applied' in capsys.readouterr().out
    monkeypatch.setattr(sys, 'argv', command + ['--check'])
    setup.main()
    assert 'CURRENT' in capsys.readouterr().out


@pytest.mark.parametrize('response,expected', [
    ({'success': False, 'error': 'Command timed out after 60 seconds'}, 'timed out after 60'),
    ({'success': True, 'result': None}, 'invalid response'),
    ({'success': True, 'result': {}}, 'invalid response'),
])
def test_live_reader_reports_bridge_failure(monkeypatch, response, expected):
    from jupyter_ai_tools.toolkits import notebook
    command = AsyncMock(return_value=response)
    command._flinc_content_guard = False
    monkeypatch.setattr(notebook, 'run_lab_command', command)
    monkeypatch.setattr(notebook, 'rtc_available', lambda: False)
    configure_notebook_read_errors()
    wrapped = notebook.run_lab_command
    configure_notebook_read_errors()
    assert notebook.run_lab_command is wrapped
    with pytest.raises(RuntimeError, match=expected):
        asyncio.run(notebook.read_notebook_json('example.ipynb'))


@pytest.mark.parametrize('wrapped', [True, False])
def test_live_reader_preserves_unsaved_content(monkeypatch, wrapped):
    from jupyter_ai_tools.toolkits import notebook
    content = {'cells': [{'cell_type': 'code', 'source': 'unsaved = 1'}]}
    payload = {'content': content}
    response = {'success': True, 'result': payload} if wrapped else payload
    command = AsyncMock(return_value=response)
    command._flinc_content_guard = False
    monkeypatch.setattr(notebook, 'run_lab_command', command)
    monkeypatch.setattr(notebook, 'rtc_available', lambda: False)
    configure_notebook_read_errors()
    assert asyncio.run(notebook.read_notebook_json('example.ipynb')) == content
    command.assert_awaited_once_with('jupyterlab-ai-commands:get-notebook-content', {'notebookPath': 'example.ipynb'})


def test_content_guard_leaves_other_commands_unchanged(monkeypatch):
    from jupyter_ai_tools.toolkits import notebook
    response = {'success': False, 'error': 'other failure'}
    command = AsyncMock(return_value=response)
    command._flinc_content_guard = False
    monkeypatch.setattr(notebook, 'run_lab_command', command)
    configure_notebook_read_errors()
    assert asyncio.run(notebook.run_lab_command('other:command')) == response

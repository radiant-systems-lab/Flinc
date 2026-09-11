import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import sys
import subprocess
import signal
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import kernel_process
from flinc_agent import notebook


def test_refuses_duplicate_busy_run(monkeypatch):
    monkeypatch.setattr(notebook, '_resolve_notebook', lambda _: (Path('/tmp/n.ipynb'), 'n.ipynb'))
    monkeypatch.setattr(notebook, 'flinc_notebook_status', AsyncMock(return_value={'running':True}))
    submit=AsyncMock();monkeypatch.setattr(notebook,'_submit_notebook',submit)
    assert asyncio.run(notebook.flinc_run_notebook('n.ipynb'))['status']=='already_running'
    submit.assert_not_awaited()


def test_serializes_concurrent_submissions(monkeypatch):
    async def check():
        submitted=False
        async def status(_):return {'running':submitted}
        async def submit(_):
            nonlocal submitted
            await asyncio.sleep(.01)
            submitted=True
            return {'status':'submitted'}
        monkeypatch.setattr(notebook,'_resolve_notebook',lambda _: (Path('/tmp/c.ipynb'),'c.ipynb'))
        monkeypatch.setattr(notebook,'flinc_notebook_status',status)
        monkeypatch.setattr(notebook,'_submit_notebook',submit)
        results=await asyncio.gather(notebook.flinc_run_notebook('c.ipynb'),notebook.flinc_run_notebook('c.ipynb'))
        assert [r['status'] for r in results]==['submitted','already_running']
    asyncio.run(check())


def test_path_cannot_escape_root(monkeypatch,tmp_path):
    monkeypatch.setattr(notebook,'get_serverapp',lambda:SimpleNamespace(root_dir=str(tmp_path)))
    with pytest.raises(ValueError,match='inside'):
        notebook._resolve_notebook('../outside.ipynb')


def test_busy_kernel_cannot_be_switched(monkeypatch):
    monkeypatch.setattr(notebook,'_resolve_notebook',lambda _: (Path('/tmp/n.ipynb'),'n.ipynb'))
    monkeypatch.setattr(notebook,'flinc_notebook_status',AsyncMock(return_value={'running':True}))
    emit=AsyncMock();monkeypatch.setattr(notebook,'emit_and_wait_for_result',emit)
    assert asyncio.run(notebook.flinc_set_kernel('n.ipynb','repeat-kernel'))['status']=='already_running'
    emit.assert_not_awaited()


@pytest.mark.parametrize('handler',['handler.py','repeat-handler.py'])
def test_launcher_preserves_child_failure(handler,tmp_path):
    result=subprocess.run([sys.executable,str(ROOT / handler),sys.executable,'-c','raise SystemExit(17)'],cwd=tmp_path)
    assert result.returncode==17


@pytest.mark.parametrize('process_name',['python','ld-linux-x86-64.so.2'])
def test_interrupt_reaches_kernel_not_capture(monkeypatch,process_name):
    calls=[]
    class Proc:
        def __init__(self,pid,parent=None):self.pid=pid;self.parent=parent
        def children(self,recursive=False):return [wrapper,kernel]
        def cmdline(self):return ['python','-m','ipykernel_launcher']
        def name(self):return process_name
        def parents(self):return [self.parent] if self.parent else []
        def send_signal(self,signum):calls.append((self.pid,signum))
    parent=Proc(10);wrapper=Proc(11,parent);kernel=Proc(12,wrapper)
    monkeypatch.setattr(kernel_process.psutil,'Process',lambda _:parent)
    kernel_process.forward_signal(SimpleNamespace(pid=10),signal.SIGINT,kernel_only=True)
    assert calls==[(12,signal.SIGINT)]


def test_capture_commit_is_not_interrupted(monkeypatch):
    parent=SimpleNamespace(children=lambda recursive:[],send_signal=lambda _:pytest.fail('commit was signaled'))
    monkeypatch.setattr(kernel_process.psutil,'Process',lambda _:parent)
    kernel_process.forward_signal(SimpleNamespace(pid=10),signal.SIGTERM,kernel_only=True)


def test_repeat_execution_override():
    spec=importlib.util.spec_from_file_location('repeat_handler',str(ROOT / 'repeat-handler.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cmd=['sciunit','given','conn.json','repeat','e1','-m','ipykernel_launcher','-f','%']
    assert module.repeat_command(cmd,'e3')[4]=='e3'
    assert cmd[4]=='e1'
    with pytest.raises(ValueError):module.repeat_command(cmd,'latest;bad')


def test_flinc_mode_is_explicit_and_scoped(monkeypatch):
    from traitlets.config import Config, Configurable
    from flinc_agent.persona import FlincAgentPersona, build_codex_environment
    from jupyter_ai_acp_client.acp_personas.codex import CodexAcpPersona
    from unittest.mock import AsyncMock
    assert 'INITIAL_AGENT_MODE' not in build_codex_environment({})
    persona=FlincAgentPersona.__new__(FlincAgentPersona)
    Configurable.__init__(persona, config=Config({'FlincAgentPersona':{'initial_agent_mode':'agent-full-access'}}))
    launch=AsyncMock()
    monkeypatch.setattr(CodexAcpPersona,'_init_agent_subprocess',launch)
    asyncio.run(persona._init_agent_subprocess(env={}))
    assert launch.call_args.kwargs['env']['INITIAL_AGENT_MODE']=='agent-full-access'
    persona.initial_agent_mode='invalid'
    with pytest.raises(ValueError):asyncio.run(persona._init_agent_subprocess(env={}))


def test_browser_patch_is_repeatable(tmp_path):
    import shutil
    from flinc_agent.browser_patch.apply_browser_patch import patch
    root=tmp_path/'toolkit'
    from jupyter_core.paths import jupyter_path
    source = next(Path(p) / 'jupyterlab-commands-toolkit' for p in jupyter_path('labextensions') if (Path(p) / 'jupyterlab-commands-toolkit/package.json').is_file())
    shutil.copytree(source,root)
    first=patch(root);second=patch(root)
    assert first==second
    content=(root/'static'/first[0]).read_text()
    assert 'const n=crypto.randomUUID()' not in content
    assert 'getRandomValues' in content
    assert 'select-notebook-kernel' in content
    assert 'run-notebook' in content
    subprocess.run(['node','--check',str(root/'static'/first[0])],check=True)


def test_shutdown_does_not_start_a_missing_kernel(monkeypatch):
    monkeypatch.setattr(notebook, '_resolve_notebook', lambda _: (Path('/tmp/closed.ipynb'), 'closed.ipynb'))
    monkeypatch.setattr(notebook, 'flinc_notebook_status', AsyncMock(return_value={'running': False, 'session_found': False}))
    emit = AsyncMock()
    monkeypatch.setattr(notebook, 'emit_and_wait_for_result', emit)
    assert asyncio.run(notebook.flinc_shutdown_notebook('closed.ipynb'))['status'] == 'already_stopped'
    emit.assert_not_awaited()


def test_repeat_selection_rejects_active_kernel(monkeypatch):
    server = SimpleNamespace(session_manager=SimpleNamespace(list_sessions=AsyncMock(return_value=[{'kernel': {'name': 'audit-kernel'}}])))
    monkeypatch.setattr(notebook, 'get_serverapp', lambda: server)
    assert asyncio.run(notebook.flinc_select_repeat_execution('e1'))['status'] == 'kernel_active'


def test_repeat_selection_requires_committed_capture(monkeypatch, tmp_path):
    server = SimpleNamespace(session_manager=SimpleNamespace(list_sessions=AsyncMock(return_value=[])))
    monkeypatch.setattr(notebook, 'get_serverapp', lambda: server)
    monkeypatch.setattr(notebook, 'resolve_project', lambda: tmp_path)
    monkeypatch.setattr(notebook, '_execution_ids', lambda _: (['e1'], None))
    with pytest.raises(ValueError, match='not committed'):
        asyncio.run(notebook.flinc_select_repeat_execution('e1'))


def test_repeat_selection_preserves_other_settings(monkeypatch, tmp_path):
    (tmp_path / 'e2.json').write_text('{}')
    spec_path = tmp_path / 'kernel.json'
    spec_path.write_text(json.dumps({'argv': ['repeat-handler.py'], 'env': {'EXISTING': 'keep'}}))
    spec = SimpleNamespace(argv=['/some/clone/repeat-handler.py'], resource_dir=str(tmp_path))
    server = SimpleNamespace(session_manager=SimpleNamespace(list_sessions=AsyncMock(return_value=[])),
                             kernel_spec_manager=SimpleNamespace(get_kernel_spec=lambda _: spec))
    monkeypatch.setattr(notebook, 'get_serverapp', lambda: server)
    monkeypatch.setattr(notebook, 'resolve_project', lambda: tmp_path)
    monkeypatch.setattr(notebook, '_execution_ids', lambda _: (['e2'], None))
    assert asyncio.run(notebook.flinc_select_repeat_execution('e2'))['success']
    assert json.loads(spec_path.read_text())['env'] == {'EXISTING': 'keep', 'FLINC_REPEAT_EXECUTION': 'e2'}

def test_persona_resolves_dynamic_mcp_port_and_preserves_identity(monkeypatch, tmp_path):
    import os
    from traitlets.config import Config, Configurable
    from flinc_agent import persona as module
    from jupyter_ai_acp_client.acp_personas.codex import CodexAcpPersona
    from jupyter_ai_persona_manager import McpSettings, McpServerHttp
    headers=[{'name': 'X-Jupyter-Chat-Id', 'value': 'test-chat'}]
    original=McpSettings(mcp_servers=[McpServerHttp(type='http',name='Jupyter MCP Server',url='http://localhost:0/mcp',headers=headers),McpServerHttp(type='http',name='external',url='http://localhost:9876/mcp',headers=[])])
    monkeypatch.setattr(CodexAcpPersona,'get_mcp_settings',lambda _: original)
    monkeypatch.setattr(module,'jupyter_runtime_dir',lambda: str(tmp_path))
    (tmp_path/f'jpserver-mcp-{os.getpid()}.json').write_text(json.dumps({'pid':os.getpid(),'url':'http://127.0.0.1:34567/mcp'}))
    persona=module.FlincAgentPersona.__new__(module.FlincAgentPersona)
    Configurable.__init__(persona,config=Config({'MCPExtensionApp':{'mcp_port':0}}))
    updated=persona.get_mcp_settings()
    assert updated.mcp_servers[0].url=='http://127.0.0.1:34567/mcp'
    assert updated.mcp_servers[0].headers==original.mcp_servers[0].headers
    assert updated.mcp_servers[1]==original.mcp_servers[1]
    assert original.mcp_servers[0].url=='http://localhost:0/mcp'

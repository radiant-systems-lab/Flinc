# Generic Flinc Agent for JupyterLab

The agent controls existing Python notebooks through Jupyter and FLINC: select
Audit, execute and monitor, finalize the capture, select a committed execution,
then run Repeat. Notebook cell source is preserved. Kernel metadata and saved
execution outputs may change. No IMERG notebook, Dask patch, AWS account, or
container is required by this integration.

## Supported setup

Use Linux with a working Sciunit/CDE installation and a Python/IPython kernel.
JupyterLab, the kernel, and FLINC must share accessible local paths. This is not
yet support for R/Julia kernels, remote kernel gateways, Windows/macOS native
replay, or concurrent independent Sciunit workflows under one user. Run one
Sciunit workflow per user at a time, including across Jupyter servers.

The integration was developed with Python 3.11, JupyterLab 4.6.3,
ipykernel 7.3.0, Sciunit2 0.4.post163.dev71963249, Jupyter AI 3.2.0,
Jupyter AI ACP Client 0.3.0, Jupyter AI Tools 0.7.0, Jupyter Server MCP 0.3.0,
commands-toolkit 0.2.0, and codex-acp 1.11.0. Python package constraints are in
`flinc-agent/pyproject.toml`. The browser patch targets toolkit 0.2.0 exactly;
setup rejects unsupported bundles instead of modifying them blindly.

The existing Sciunit archive in this repository is an older version than the
tested installation. Cloning this repository does not itself reproduce the
native Sciunit/CDE environment. Supply a working compatible installation; a
clean native build on other platforms has not been validated by this repair.

## Install into the Jupyter environment

With the Jupyter server stopped, run from the cloned repository:

```bash
python -m pip install ./flinc-agent
flinc-agent-setup --flinc-root "$PWD" --kernel python3 --check
flinc-agent-setup --flinc-root "$PWD" --kernel python3
```

`python3` is the name from `jupyter kernelspec list`. The setup command requires
`sciunit`, `codex`, and `codex-acp` on PATH. Install/authenticate those using your
deployment's normal process; setup does not log in or copy credentials. The
current persona uses the Codex ACP adapter. Each user supplies their own login.

Run setup as the Jupyter user, in its Python environment, with permission to
update the installed browser extension. It detects extension and config paths
through Jupyter APIs; `--toolkit-root` can override extension discovery. Backups
are stored under `~/.local/state/flinc-agent/backups/` outside the repository.

Setup installs the kernel specs, patches browser commands, adds a shutdown grace
setting if absent, and records the clone location for source discovery in
Jupyter's config directory as `flinc-agent.json`. It does not modify notebook
code, install cloud integrations, or alter credentials. It preserves existing
configuration and captures. Inspect any existing shorter shutdown setting:
setup preserves it rather than overriding an administrator's explicit value.

Restart Jupyter, reload the browser page, and create a fresh **flinc-agent** chat.
A running Python server keeps previously imported tools until restart.

## Configuration

Generic Jupyter configuration (`jupyter_server_config.d/flinc.json`):

```json
{
  "KernelManager": {"shutdown_wait_time": 120.0}
}
```

The grace period allows Sciunit to archive after kernel shutdown. It applies to
Jupyter kernel shutdown generally. A template is supplied under
`flinc-agent/config/`. The generic configuration does not select full access.

If a deployment explicitly requires a particular ACP mode, setup accepts
`--initial-agent-mode agent`, `read-only`, or `agent-full-access`. Full access
removes the agent filesystem sandbox and is an explicit deployment choice,
not an automatic response to sandbox errors. This repair container retains its
previously configured full-access mode because its Bubblewrap namespaces fail.
Other deployments need not use that mode.

The agent's `flinc_select_repeat_execution` tool writes the selected ID into the
installed Repeat kernelspec's `env.FLINC_REPEAT_EXECUTION`. It validates that
the execution is committed in the active project and refuses selection while
this server has an Audit/Repeat kernel. There is no hardcoded deployment ID.
Other servers using the same user/project must also be idle.

## End-to-end operation

Example request in a fresh Flinc Agent chat:

> Run Audit and then Repeat on my-notebook.ipynb. Keep every source cell unchanged,
> confirm the committed execution ID, and report the results of both runs.

The agent checks installation and the active project, records existing capture
IDs, selects Audit, submits execution, and monitors completion. It then uses
`flinc_shutdown_notebook`, which saves and closes the notebook tab while waiting
for kernel shutdown. Closing the tab avoids accidentally restoring another
Audit kernel. After checking the committed capture it selects that execution
and opens Repeat. The browser command supplies the requested kernel when opening
the notebook by opening without auto-start and then selecting the kernel, so its
previous Audit metadata does not start another capture.

FLINC's `sciunit given ... repeat` supplies the new connection file. The supported
Sciunit implementation commits a new execution record after successful replay.
That Repeat record is expected and is distinct from starting a new Audit kernel.

No cell-source changes are needed for these operations. A notebook's own missing
dependencies, credentials, inputs, external services, or interactive prompts can
still prevent it from completing. The agent reports those failures; it does not
silently rewrite the notebook or promise offline reproduction of remote services.

## Required changes and failure without them

| Component | Change and reason | Without it |
|---|---|---|
| `flinc-agent/flinc_agent/` | Complete installable agent, persona/MCP entry points, source discovery and workflow guidance. | A clone contains no installable Agent integration. |
| `notebook.py`, `tools.py` | Path-specific execution, status, duplicate guard, kernel selection, shutdown, validated Repeat selection. | The agent lacks a complete reliable tool path for Audit and Repeat. |
| `persona.py` MCP endpoint resolution | Resolve this Jupyter process's published MCP endpoint while preserving chat identity headers. | With a dynamically assigned MCP port, the chat may connect to port zero and expose no notebook tools, even though direct MCP tests pass. |
| `browser_patch/` | HTTP-compatible UUID generation, path-bound commands, kernel readiness checks, new asset names. | Browser initialization can fail; commands time out or race kernel startup; cached broken code can remain active. |
| `handler.py`, `repeat-handler.py`, `kernel_process.py` | Forward interrupts to the real kernel, preserve archiving, and return child exit codes. | Interrupts can kill the session/capture or miss the replay kernel; failures can be hidden. |
| `kernel_bootstrap.py` and launcher startup flags | Exercise traceback formatting during Audit and use in-memory history. | Repeat may lack error-formatting dependencies or encounter a read-only history database. |
| `install_kernels.py`, `install.sh` | Generate correct local kernel commands without destroying a project or modifying repository templates. | Agent setup can register duplicate wrappers or erase captures on reinstall. |
| `setup.py` and config template | Apply version-checked integration and allow archive shutdown time. | Cloned code is not registered in Jupyter, or capture finalization can be terminated early. |

The bootstrap is Python/IPython-specific. It builds and discards a caught
exception's formatted traceback so Sciunit captures lazy formatting imports;
it does not change notebook source or pre-load all workload dependencies.
The current startup injection uses IPython `exec_lines`; deployments with custom
startup configuration need compatibility validation.

The branch's preexisting `audit-sciunit.py` environment policy is retained;
Sciunit core was not edited. The IMERG-specific notebook and Dask ECS repairs
are excluded from this Agent integration. Their earlier validation record is
kept outside the repository and is not proof of the reduced-scope workflow.

## What to commit

Commit the changed FLINC launcher/installer files, new bootstrap/process helper,
the complete `flinc-agent/` directory, this guide, README changes, and `.gitignore`.
Keep the existing repository structure. Do not commit generated installed
kernelspec paths, credentials, logs, captures, datasets, caches, or backups.
The existing Repeat template remains portable; setup generates installed paths.

Preserve Sciunit captures separately if you need to replay existing executions
after deployment. Cloning source does not restore a capture or authenticate a user.

## Checks

```bash
python -m pip install './flinc-agent[test]'
pytest -q flinc-agent/tests
```

Tests cover notebook targeting/guards, safe shutdown, committed-capture selection,
wrapper exits and signals, explicit mode configuration, and browser patching.
The live validation uses actual MCP tools and a real browser to run a small
generic notebook through Audit and Repeat while checking unchanged source and
matching outputs.

A subsequent natural-language Flinc Agent chat ran the unchanged IMERG/Dask
notebook through Audit and Repeat using its existing AWS environment. Audit
completed seven code cells and committed `e1`. The first Repeat attempt failed
because an AWS worker's container-image pull timed out. The agent diagnosed the
failure, cleaned up, and retried `e1` once without source or library edits. The
retry completed seven code cells, matched all 14 output files by SHA-256, and
committed the Repeat record `e3`. All 15 test AWS tasks were stopped and all test
kernels shut down. This test also exposed and verified the persona's dynamic
MCP-port fix. See `flinc-agent/tests/imerg-natural-language-result.json`.
The regression suite now has 17 passing tests. AWS is a dependency of that
validation notebook, not a dependency of the generic Agent installation.

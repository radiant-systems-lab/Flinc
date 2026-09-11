# Codex ACP and authentication for Flinc Agent

This guide explains the agent backend used by the current Flinc Agent, how to
install it, and how to authenticate after cloning the repository. Follow
[FLINC_AGENT_SETUP.md](FLINC_AGENT_SETUP.md) for the complete Jupyter and
Sciunit setup. Run the commands below as the operating-system user that runs
Jupyter, with its Python environment activated.

## How the components fit together

```text
Your natural-language request in the JupyterLab Flinc Agent chat
    -> Jupyter AI and its ACP client
    -> codex-acp adapter
    -> Codex agent
    -> FLINC/Jupyter tools through MCP
    -> notebook Audit and Repeat kernels, backed by Sciunit/CDE
```

| Component | Responsibility |
| --- | --- |
| Jupyter AI | Provides the chat interface and persona integration. |
| ACP client | Connects Jupyter AI to an agent using Agent Client Protocol. |
| `codex-acp` | Starts the Codex App Server and translates requests, responses, and agent events between Codex and the ACP client. |
| Codex | Interprets the request, plans actions, invokes tools, and reports results. |
| Flinc Agent | Supplies FLINC-specific instructions and notebook workflow tools. |
| Jupyter MCP tools | Let the agent inspect and operate the notebook and its kernels. |
| Sciunit/CDE | Performs the underlying capture and replay work. |

ACP connects the chat client to the agent. MCP connects the agent to tools.
Neither protocol replaces Sciunit or executes an Audit by itself.

The current Flinc persona inherits from `CodexAcpPersona`; it is specifically
integrated with Codex. Generic notebook support does not mean that arbitrary
model providers or agent backends can be substituted without integration work.

## What the Python installation includes

From the repository root:

```bash
python -m pip install ./flinc-agent
```

This installs the Flinc Agent Python package and the declared JupyterLab,
Jupyter AI, ACP client, MCP, and notebook dependencies. See
[pyproject.toml](flinc-agent/pyproject.toml) for the actual version constraints.

It does not install Node.js/npm, authenticate Codex, or build the native
Sciunit/CDE environment. Notebook-specific libraries, data, and service
credentials must also be supplied by the deployment.

## Install and verify Codex ACP

Use a supported Node.js/npm installation available to the Jupyter user. The
following commands pin the adapter to the version used in our validation and
the standalone Codex CLI to the version observed in the validation environment:

```bash
node --version
npm --version
npm install -g @agentclientprotocol/codex-acp@1.11.0 @openai/codex@0.154.0
command -v codex-acp
command -v codex
codex-acp --version
codex --version
```

Use a writable npm installation/prefix belonging to the intended user, or have
the environment administrator provision these executables. Both commands must
be on the Jupyter server process's `PATH`, not just an unrelated terminal's.

The adapter package also declares a compatible `@openai/codex` dependency.
That dependency does not necessarily expose a standalone `codex` command on
your shell's `PATH`; the explicit CLI installation above supplies the command
required by Flinc setup and the login examples.

By default, the adapter can use its bundled Codex dependency. It supports
`CODEX_PATH` when a deployment intentionally selects another executable.
Do not assume the standalone CLI and the adapter's bundled CLI have identical
versions. Pinning these two top-level packages also does not lock every
transitive npm dependency or reproduce the native Sciunit environment.

## Choose an authentication method

There is no separate Flinc account to create. "Agent login" means authenticating
Codex for the model service it uses. Choose one of the following methods.

### ChatGPT account login

On a machine with a usable browser login flow:

```bash
codex login
codex login status
```

Complete the browser sign-in. Access and usage limits depend on the account
and workspace's Codex entitlement. Signing into the ChatGPT website alone
does not establish a CLI login on a different server.

For a remote or headless Jupyter server:

```bash
codex login --device-auth
codex login status
```

Open the displayed URL in your own browser and enter the one-time code. Device
code login must be enabled in the account's security settings or by the
workspace administrator. Follow the official authentication guide if that
method is unavailable in your deployment.

### OpenAI API key login

If your deployment already supplies an API key through `OPENAI_API_KEY`, run:

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
codex login status
```

Supply the key through your deployment's secret management mechanism. The
example passes it through standard input rather than including a literal key
in command history. API-key usage is billed to the OpenAI Platform account;
it does not use included ChatGPT subscription credits.

Authentication methods, device login, credential storage, and billing behavior
are described in the [official Codex authentication documentation](https://learn.chatgpt.com/docs/auth).

## Use the same user and credential environment as Jupyter

Codex caches authentication in its configured credential store. File-based
storage normally uses `~/.codex/auth.json`, or the directory selected by
`CODEX_HOME`; an operating-system credential store may be used instead.

For example, logging in as `root` does not automatically authenticate Jupyter
running as `jovyan`. Login and the agent process must have access to the same
intended credential store. A Jupyter terminal is a useful place to run
`codex login status` because it normally uses the Jupyter server's user.

If your deployment overrides `HOME`, `CODEX_HOME`, or its credential storage
configuration, keep that configuration consistent between login and Jupyter.
For disposable containers, use the deployment's private credential persistence
mechanism or log in again when the environment is recreated.

Do not commit authentication caches, API keys, or other credentials to this
repository or bake them into a shared image. The GitHub branch contains code
and documentation, not the credentials from the working environment.

| Login or credential | What it authorizes |
| --- | --- |
| `gh auth login` | GitHub operations such as fetching private repositories or pushing commits. |
| `codex login` | Codex model access for the Flinc Agent backend. |
| Jupyter login/token | Access to the Jupyter server. |
| Notebook service credentials | The notebook's own external services, such as a data API or cloud account. |

These are separate authentication contexts. Successful GitHub login does not
authenticate Codex or the notebook's external services.

## Finish setup after cloning

With compatible Sciunit/CDE already installed and the Jupyter server stopped,
run from the cloned repository in the Jupyter Python environment:

```bash
python -m pip install ./flinc-agent
codex login status
jupyter kernelspec list
flinc-agent-setup --flinc-root "$PWD" --kernel python3 --check
flinc-agent-setup --flinc-root "$PWD" --kernel python3
```

Replace `python3` with the original Python kernelspec name you intend to use.
The check validates setup prerequisites; it is not an end-to-end model login,
network, or notebook execution test.

Start Jupyter through your normal deployment process, reload the browser, and
create a fresh **flinc-agent** chat. If the chat client presents an authentication
choice, select the method configured for your deployment. Jupyter manages the
adapter subprocess; you do not need to keep `codex-acp` running in a terminal.

Try a request such as:

> Run Audit and then Repeat on my-notebook.ipynb. Keep every source cell
> unchanged, confirm the committed execution ID, and report both results.

Successful login enables model access. Successful end-to-end execution also
requires working browser tools, kernels, Sciunit/CDE, and the notebook's inputs
and dependencies. The supported environment remains Linux, Python/IPython,
JupyterLab 4, and shared accessible local paths as detailed in the setup guide.

## Troubleshooting

| Symptom | Check or next step |
| --- | --- |
| `codex-acp: command not found` | Install the adapter and ensure the npm executable directory is on Jupyter's `PATH`. |
| `codex: command not found` | Install the standalone CLI and verify it from the Jupyter user's environment. |
| Login works in SSH but the agent requests login | Compare the OS user, credential store, and `CODEX_HOME` used by SSH and Jupyter. |
| Browser login cannot return to a remote server | Use `codex login --device-auth` if allowed by the account/workspace. |
| Authentication or account-access error | Check `codex login status`, account entitlement, and administrator restrictions. |
| API quota or billing error | Check the API account's billing and limits; GitHub login will not resolve this. |
| Chat responds but cannot operate a notebook | Check Jupyter MCP/browser integration, reload the browser, and restart Jupyter after installing updated code. |
| Audit or Repeat fails after tools start working | Inspect the actual kernel/Sciunit error and notebook dependencies; model login does not install them. |
| Actions are denied by an agent permission mode | Review the deployment's configured permissions. Authentication and action permissions are separate; setup does not automatically enable full access. |

For a shared support report, include versions and redacted errors. Do not paste
authentication files or unredacted logs containing tokens.

## Implementation references

- [Flinc persona](flinc-agent/flinc_agent/persona.py): Codex ACP integration,
  FLINC instructions, permission-mode configuration, and Jupyter MCP endpoint.
- [Flinc setup](flinc-agent/flinc_agent/setup.py): prerequisite checks and setup.
- [Flinc setup guide](FLINC_AGENT_SETUP.md): compatibility, installation,
  validation results, and limitations.
- The installed `@agentclientprotocol/codex-acp` package's `README.md` describes
  its bundled Codex dependency, authentication options, and `CODEX_PATH`.
- [Official Codex authentication documentation](https://learn.chatgpt.com/docs/auth).

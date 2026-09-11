"""Codex-backed Jupyter AI persona for FLINC and Sciunit workflows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from collections.abc import Mapping

from jupyter_ai_acp_client.acp_personas.codex import CodexAcpPersona
from jupyter_ai_persona_manager import PersonaDefaults
from traitlets import Unicode
from jupyter_ai_persona_manager import McpServerHttp
from jupyter_core.paths import jupyter_runtime_dir

from .prompt import FLINC_AGENT_SYSTEM_PROMPT


def build_codex_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an ACP environment with persistent FLINC developer instructions."""
    process_environment = dict(os.environ if environment is None else environment)
    raw_config = process_environment.get("CODEX_CONFIG", "").strip()

    if raw_config:
        try:
            config = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValueError("CODEX_CONFIG must contain a valid JSON object") from exc
        if not isinstance(config, dict):
            raise ValueError("CODEX_CONFIG must contain a JSON object")
    else:
        config = {}

    existing_instructions = config.get("developer_instructions")
    instruction_parts = []
    if isinstance(existing_instructions, str) and existing_instructions.strip():
        instruction_parts.append(existing_instructions.strip())
    instruction_parts.append(FLINC_AGENT_SYSTEM_PROMPT)
    config["developer_instructions"] = "\n\n".join(instruction_parts)

    process_environment["CODEX_CONFIG"] = json.dumps(
        config,
        separators=(",", ":"),
    )
    return process_environment


class FlincAgentPersona(CodexAcpPersona):
    """Source-grounded FLINC agent powered by the authenticated Codex CLI."""

    NOTEBOOK_EDITING_GUIDANCE = CodexAcpPersona.NOTEBOOK_EDITING_GUIDANCE
    initial_agent_mode = Unicode(
        "", config=True,
        help="Explicit ACP mode for new FLINC sessions. Empty preserves the adapter default.",
    )

    def get_mcp_settings(self):
        """Use this Jupyter process's actual MCP endpoint, including dynamic ports."""
        settings = super().get_mcp_settings()
        runtime = Path(jupyter_runtime_dir()) / f'jpserver-mcp-{os.getpid()}.json'
        port = self.config.get('MCPExtensionApp', {}).get('mcp_port', 3001)
        expected = f'http://localhost:{port}/mcp'
        if settings is None or not runtime.is_file():
            return settings
        info = json.loads(runtime.read_text())
        if info.get('pid') != os.getpid() or not info.get('url'):
            return settings
        # Preserve identity headers and all unrelated/user-supplied servers.
        return settings.model_copy(update={'mcp_servers': [
            server.model_copy(update={'url': info['url']})
            if isinstance(server, McpServerHttp) and server.url == expected
            else server for server in settings.mcp_servers
        ]})

    async def _init_agent_subprocess(self, env=None):
        """Start Codex ACP with FLINC policy at developer-instruction priority."""
        environment = build_codex_environment(env)
        if self.initial_agent_mode:
            if self.initial_agent_mode not in {"read-only", "agent", "agent-full-access"}:
                raise ValueError("Unsupported FLINC initial_agent_mode")
            environment["INITIAL_AGENT_MODE"] = self.initial_agent_mode
        return await super()._init_agent_subprocess(
            env=environment,
        )

    @property
    def defaults(self) -> PersonaDefaults:
        parent_defaults = super().defaults
        return PersonaDefaults(
            name="flinc-agent",
            avatar_path=parent_defaults.avatar_path,
            description="Installs, operates, and diagnoses FLINC and Sciunit in Jupyter.",
            system_prompt="unused",
        )

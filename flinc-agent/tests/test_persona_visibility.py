from importlib.metadata import PathDistribution
from pathlib import Path

from flinc_agent.persona_visibility import restrict_to_nb_agent


def make_distribution(tmp_path: Path, name: str, entry_points: str) -> PathDistribution:
    metadata = tmp_path / f"{name}-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n")
    (metadata / "entry_points.txt").write_text(entry_points)
    return PathDistribution(metadata)


def test_restrict_to_nb_agent_hides_other_personas_and_preserves_runtime(tmp_path):
    agent = make_distribution(
        tmp_path,
        "flinc-agent",
        "[jupyter_ai.personas]\n"
        "flinc-agent = flinc_agent.persona:FlincAgentPersona\n",
    )
    acp = make_distribution(
        tmp_path,
        "jupyter-ai-acp-client",
        "[jupyter_ai.personas]\n"
        "codex-acp = jupyter_ai_acp_client.acp_personas.codex:CodexAcpPersona\n"
        "copilot-acp = jupyter_ai_acp_client.acp_personas.copilot:CopilotAcpPersona\n"
        "\n[console_scripts]\nacp-runtime = package:main\n",
    )
    backup = tmp_path / "backup"

    removed = restrict_to_nb_agent(backup, [agent, acp])

    assert removed == [
        "jupyter-ai-acp-client:codex-acp",
        "jupyter-ai-acp-client:copilot-acp",
    ]
    assert "flinc-agent" in (Path(agent._path) / "entry_points.txt").read_text()
    acp_metadata = (Path(acp._path) / "entry_points.txt").read_text()
    assert "jupyter_ai.personas" not in acp_metadata
    assert "acp-runtime = package:main" in acp_metadata
    assert (backup / "jupyter-ai-acp-client-entry_points.txt").is_file()


def test_restrict_to_nb_agent_is_repeatable(tmp_path):
    acp = make_distribution(
        tmp_path,
        "jupyter-ai-acp-client",
        "[jupyter_ai.personas]\ncodex-acp = package:Codex\n",
    )
    backup = tmp_path / "backup"

    assert restrict_to_nb_agent(backup, [acp]) == [
        "jupyter-ai-acp-client:codex-acp"
    ]
    assert restrict_to_nb_agent(backup, [acp]) == []

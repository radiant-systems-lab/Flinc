"""Control which installed Jupyter AI personas are exposed in chat."""

from __future__ import annotations

from configparser import ConfigParser
from importlib.metadata import Distribution, distributions
from pathlib import Path
import re
import shutil


PERSONA_ENTRY_POINT_GROUP = "jupyter_ai.personas"
NB_AGENT_ENTRY_POINT_NAME = "flinc-agent"
NB_AGENT_ENTRY_POINT_VALUE = "flinc_agent.persona:FlincAgentPersona"
NB_AGENT_PERSONA_ID = "jupyter-ai-personas::flinc_agent::FlincAgentPersona"


def restrict_to_nb_agent(
    backup_dir: Path,
    installed_distributions: list[Distribution] | None = None,
) -> list[str]:
    """Remove non-NB-Agent persona entry points while preserving their packages."""
    installed = (
        list(distributions())
        if installed_distributions is None
        else installed_distributions
    )
    removed: list[str] = []

    for distribution in installed:
        metadata_path = getattr(distribution, "_path", None)
        if metadata_path is None:
            continue
        entry_points_path = Path(metadata_path) / "entry_points.txt"
        if not entry_points_path.is_file():
            continue

        parser = ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(entry_points_path, encoding="utf-8")
        if not parser.has_section(PERSONA_ENTRY_POINT_GROUP):
            continue

        names_to_remove = [
            name
            for name, value in parser.items(PERSONA_ENTRY_POINT_GROUP)
            if not (
                name == NB_AGENT_ENTRY_POINT_NAME
                and value.strip() == NB_AGENT_ENTRY_POINT_VALUE
            )
        ]
        if not names_to_remove:
            continue

        distribution_name = distribution.metadata.get("Name", "unknown-distribution")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", distribution_name)
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry_points_path, backup_dir / f"{safe_name}-entry_points.txt")

        for name in names_to_remove:
            parser.remove_option(PERSONA_ENTRY_POINT_GROUP, name)
            removed.append(f"{distribution_name}:{name}")
        if not parser.items(PERSONA_ENTRY_POINT_GROUP):
            parser.remove_section(PERSONA_ENTRY_POINT_GROUP)

        with entry_points_path.open("w", encoding="utf-8", newline="\n") as stream:
            parser.write(stream)

    return sorted(removed)

"""Configuration shared by flinc-agent services."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_FLINC_REPOSITORY = "https://github.com/radiant-systems-lab/Flinc.git"
DEFAULT_FLINC_REVISION = "main"
DEFAULT_KERNEL_NAME = "python3"

SOURCE_SUFFIXES = {".c", ".h", ".json", ".md", ".py", ".rst", ".sh", ".txt"}
IGNORED_SOURCE_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "tests",
}

STALE_RUNTIME_ENVIRONMENT_VARIABLES = (
    "AWS_ACCESS_KEY_ID",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_EC2_METADATA_DISABLED",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SECURITY_TOKEN",
    "AWS_SESSION_TOKEN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "ECS_AGENT_URI",
    "ECS_CONTAINER_METADATA_URI",
    "ECS_CONTAINER_METADATA_URI_V4",
    "HOSTNAME",
    "JPY_PARENT_PID",
    "JUPYTER_TOKEN",
    "SESSION_ID",
    "SESSION_MODE",
    "SESSION_OWNER_ID",
)

SECRET_ENVIRONMENT_VARIABLES = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SECURITY_TOKEN",
    "AWS_SESSION_TOKEN",
    "JUPYTER_TOKEN",
}


def agent_cache_dir() -> Path:
    """Return the user-specific cache directory used for managed sources."""
    configured = os.environ.get("FLINC_AGENT_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "flinc-agent"

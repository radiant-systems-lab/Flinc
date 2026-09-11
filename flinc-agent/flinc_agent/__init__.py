"""flinc-agent package."""

from .timeouts import configure_jupyter_command_timeout
from .version import __version__

configure_jupyter_command_timeout()

__all__ = ["__version__"]

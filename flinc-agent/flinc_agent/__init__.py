"""flinc-agent package."""

from .timeouts import configure_jupyter_command_timeout
from .version import __version__

configure_jupyter_command_timeout()

from .notebook_compat import configure_notebook_read_errors

configure_notebook_read_errors()

__all__ = ["__version__"]

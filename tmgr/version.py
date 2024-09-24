"""Version information."""

import platform
from tmgr import __version__


def get_version():
    """Return package-name __version__ python python_version."""
    return (f'stmgr {__version__} '
            f'python {platform.python_version()}')
import os
from importlib import metadata

__version__ = os.environ.get("PKGBOT_VERSION", "").lstrip("v")

if not __version__:
    try:
        __version__ = metadata.version("gitlab-pkgbot")
    except metadata.PackageNotFoundError:
        # Running from a source checkout without an installed distribution.
        __version__ = "0.0.0"

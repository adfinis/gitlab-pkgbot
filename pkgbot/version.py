import os

# Allow the build/release pipeline to override the version from the release
# tag (see .github/workflows/release.yml). Falls back to the literal below so
# that local builds and editable installs keep working.
__version__ = os.environ.get("PKGBOT_VERSION", "").lstrip("v") or "1.1.9"

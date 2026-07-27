"""linejudge — the independent line judge for coding agents.

Runs an agent on a goal, then independently verifies the result.
The agent's own claim of success is never consulted.
"""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    # Single source of truth is pyproject.toml -- a hardcoded copy here drifts,
    # and a version string that lies is a poor look for this particular tool.
    __version__ = _version("linejudge")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0.0.0+source"

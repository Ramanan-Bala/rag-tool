"""The universal ``AGENTS.md`` writer.

Any agent that loads ``AGENTS.md`` (the emerging cross-tool standard) will pick
up the rules block written here even if it does not have a dedicated plugin.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import AgentPlugin


def _user_config_root() -> Path:
    """Return the per-user config base, honouring ``XDG_CONFIG_HOME``."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser()
    return Path.home() / ".config"


class UniversalAgent(AgentPlugin):
    """Writes ``AGENTS.md`` at user (``~/.config/repo-rag/``) and project scope."""

    name = "universal"
    display = "Universal AGENTS.md"

    def detect(self) -> bool:  # always available
        return True

    def user_rules_path(self) -> Path | None:
        return _user_config_root() / "repo-rag" / "AGENTS.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "AGENTS.md"

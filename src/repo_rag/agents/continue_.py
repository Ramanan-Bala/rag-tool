"""Continue.dev plugin.

Continue stores both ``systemMessage`` (rules) and ``mcpServers`` (MCP) in the
same ``~/.continue/config.json``. We append the rules into a dedicated
``systemMessage`` key when no other rules file is present, but the canonical
universal :class:`UniversalAgent` plus the project ``AGENTS.md`` already cover
the policy text for Continue, so the file we touch here only manages MCP.
"""

from __future__ import annotations

from pathlib import Path

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    mcp_servers_json_snippet,
    upsert_json_mcp_entry,
)


class ContinueAgent(AgentPlugin):
    name = "continue"
    display = "Continue.dev"

    def _config_dir(self) -> Path:
        return Path.home() / ".continue"

    def _config_path(self) -> Path:
        return self._config_dir() / "config.json"

    def detect(self) -> bool:
        return self._config_dir().exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "AGENTS.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "AGENTS.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(self._config_path(), parent_key="mcpServers")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._config_path(),
            config_snippet=mcp_servers_json_snippet(),
        )

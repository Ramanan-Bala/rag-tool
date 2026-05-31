"""MiniMax Agent / MiniMax Code plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    upsert_json_mcp_entry,
)

MINIMAX_MCP_ENTRY: dict[str, Any] = {
    "command": "rag",
    "args": ["mcp-server"],
    "enabled": True,
    "configured": True,
}


class MinimaxAgent(AgentPlugin):
    name = "minimax"
    display = "MiniMax Agent"

    def _config_dir(self) -> Path:
        return Path.home() / ".minimax"

    def _mcp_path(self) -> Path:
        return self._config_dir() / "mcp" / "mcp.json"

    def detect(self) -> bool:
        return self._config_dir().exists()

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
        return upsert_json_mcp_entry(self._mcp_path(), entry=MINIMAX_MCP_ENTRY)

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._mcp_path(),
            config_snippet=(
                "{\n"
                '  "mcpServers": {\n'
                '    "repo-rag": {\n'
                '      "command": "rag",\n'
                '      "args": ["mcp-server"],\n'
                '      "enabled": true,\n'
                '      "configured": true\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
        )

"""Zed editor plugin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    mcp_servers_json_snippet,
    upsert_json_mcp_entry,
)


def _zed_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Zed"
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Zed"
    return Path.home() / ".config" / "zed"


class ZedAgent(AgentPlugin):
    name = "zed"
    display = "Zed"

    def detect(self) -> bool:
        return _zed_config_dir().exists()

    def user_rules_path(self) -> Path | None:
        return _zed_config_dir() / ".rules"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / ".rules"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        return upsert_json_mcp_entry(
            _zed_config_dir() / "settings.json",
            parent_key="context_servers",
        )

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=_zed_config_dir() / "settings.json",
            config_snippet=mcp_servers_json_snippet(),
            notes=["Zed uses the `context_servers` key for MCP integrations."],
        )

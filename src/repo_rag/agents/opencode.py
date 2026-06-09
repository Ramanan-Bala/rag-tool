"""OpenCode agent plugin (CLI + Desktop).

Covers both OpenCode CLI (terminal) and OpenCode Desktop (native app) in a
single plugin. ``rag agents setup --target opencode`` writes the rules block
into ``CLAUDE.md`` and patches the MCP config in ``opencode.json``.

OpenCode stores MCP servers under an ``mcp`` key with a ``type``/``command``
array format that differs from the standard ``mcpServers`` pattern, so the
plugin implements custom JSON merge logic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
)

_OPENCODE_MCP_ENTRY = {"type": "local", "command": ["rag", "mcp-server"]}


def _opencode_config_dir() -> Path:
    """Return the OpenCode config directory (XDG-compliant)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "opencode"


def _opencode_config_path() -> Path:
    """Return the primary OpenCode config file path."""
    return _opencode_config_dir() / "opencode.json"


def _opencode_legacy_config_path() -> Path:
    """Return the legacy (pre-XDG) OpenCode config file path."""
    return Path.home() / ".opencode.json"


def _opencode_mcp_snippet() -> str:
    """Return the OpenCode-format MCP snippet for manual setup."""
    return json.dumps({"mcp": {"repo-rag": _OPENCODE_MCP_ENTRY}}, indent=2)


class OpenCodeAgent(AgentPlugin):
    name = "opencode"
    display = "OpenCode"

    def _config_dir(self) -> Path:
        return _opencode_config_dir()

    def _config_path(self) -> Path:
        return _opencode_config_path()

    def detect(self) -> bool:
        if self._config_dir().exists():
            return True
        legacy = _opencode_legacy_config_path()
        return legacy.exists()

    def user_rules_path(self) -> Path | None:
        return self._config_dir() / "CLAUDE.md"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "CLAUDE.md"

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope != "user":
            return None
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        data: dict
        if path.exists() and path.read_text(encoding="utf-8").strip():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return InstallResult(
                    path=path,
                    written=False,
                    skipped_reason=f"invalid JSON: {exc}",
                )
            if not isinstance(data, dict):
                return InstallResult(
                    path=path,
                    written=False,
                    skipped_reason="not a JSON object",
                )
        else:
            data = {}

        mcp_servers = data.setdefault("mcp", {})
        if not isinstance(mcp_servers, dict):
            return InstallResult(
                path=path,
                written=False,
                skipped_reason="mcp is not a JSON object",
            )

        before = json.dumps(mcp_servers.get("repo-rag"), sort_keys=True)
        mcp_servers["repo-rag"] = dict(_OPENCODE_MCP_ENTRY)
        after = json.dumps(mcp_servers["repo-rag"], sort_keys=True)

        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return InstallResult(path=path, written=before != after, detail="mcp")

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        return MCPHint(
            config_path=self._config_path(),
            config_snippet=_opencode_mcp_snippet(),
            notes=[
                "OpenCode uses a 'mcp' key with 'type'/'command' format.",
                "Install: curl -fsSL https://opencode.ai/install | bash",
            ],
        )

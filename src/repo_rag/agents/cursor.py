"""Cursor plugin.

Cursor reads project rules from ``<repo>/.cursor/rules/*.mdc`` and an MCP
config from ``<repo>/.cursor/mcp.json`` (project) or ``~/.cursor/mcp.json``
(user). The ``.mdc`` format is Markdown with a YAML frontmatter; we emit a
single self-contained file the user can tweak later.
"""

from __future__ import annotations

from pathlib import Path

from . import _rules_text
from .base import (
    AgentPlugin,
    InstallResult,
    MCPHint,
    Scope,
    mcp_servers_json_snippet,
    upsert_json_mcp_entry,
)

_CURSOR_FRONTMATTER = """\
---
description: repo-rag code search policy (use repo_rag_search before Grep/Glob)
alwaysApply: true
---
"""


class CursorAgent(AgentPlugin):
    name = "cursor"
    display = "Cursor"

    def detect(self) -> bool:
        return (Path.home() / ".cursor").exists()

    def user_rules_path(self) -> Path | None:
        return Path.home() / ".cursor" / "rules" / "repo-rag.mdc"

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / ".cursor" / "rules" / "repo-rag.mdc"

    def install_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult:
        path = self._resolve_rules_path(scope, repo_root)
        if path is None:
            return InstallResult(path=None, skipped_reason="no rules path for cursor")
        path.parent.mkdir(parents=True, exist_ok=True)
        body = _CURSOR_FRONTMATTER + "\n" + _rules_text.md_block()
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if existing == body:
            return InstallResult(path=path, written=False, detail="already up to date")
        path.write_text(body, encoding="utf-8")
        return InstallResult(path=path, written=True)

    def uninstall_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> bool:
        path = self._resolve_rules_path(scope, repo_root)
        if path is None or not path.exists():
            return False
        try:
            path.unlink()
        except OSError:
            return False
        return True

    def install_mcp(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult | None:
        if scope == "project":
            if repo_root is None:
                return None
            path = repo_root / ".cursor" / "mcp.json"
        else:
            path = Path.home() / ".cursor" / "mcp.json"
        return upsert_json_mcp_entry(path)

    def mcp_hint(self, *, scope: Scope = "user", repo_root: Path | None = None) -> MCPHint:
        if scope == "project" and repo_root is not None:
            target = repo_root / ".cursor" / "mcp.json"
        else:
            target = Path.home() / ".cursor" / "mcp.json"
        return MCPHint(config_path=target, config_snippet=mcp_servers_json_snippet())

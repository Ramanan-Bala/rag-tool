"""MiniMax Agent / MiniMax Code plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import _rules_text
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
    "env": {},
    "enabled": True,
    "configured": True,
    "description": (
        "Local RAG indexer - search code with hybrid keyword + vector search. "
        "Tools: repo_rag_search, repo_rag_get_context, repo_rag_remember, "
        "repo_rag_forget, repo_rag_status"
    ),
}

MINIMAX_BUILTIN_MARKER = "<!-- mavis:builtin-agent-md-stub v2 -->"

MINIMAX_RULES_BODY = """\
## Code Search Policy (repo-rag)

This guidance applies whenever you read, modify, or reason about code,
symbols, files, or configuration in a repository indexed by `repo-rag`.

### 1. Recommended first step

For non-trivial code questions or multi-step coding tasks, call one of these
MCP tools before any other search or file-read tool:

  - `mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'`
  - `mavis mcp call repo-rag repo_rag_get_context '{"task": "<task description>"}'`
  - `mavis mcp call repo-rag repo_rag_status '{}'`

Treat the chunks returned by repo-rag as the primary evidence and cite
`path:start_line-end_line` when describing code you found via repo-rag.

### 2. Avoid these tools as the first code-search action

In a repo-rag indexed repository, prefer repo-rag search over:

  - Grep, ripgrep, `rg`
  - Glob and file-pattern searches
  - LS on source directories for exploration
  - Reading a source file you have not first located via repo-rag
  - Shell-based search commands (`Select-String`, `findstr`, `grep`, `ag`, `ack`, `fd`)

If you reach for Grep, Glob, or a Read on an unknown path, pause and call
`mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'` first.

### 3. Reasonable exceptions

You may use Grep, Glob, LS, or Read directly when one of these applies. State
which one in your reply so the user can audit:

  a. The repo-rag MCP server is unavailable or unresponsive in this session.
  b. `mavis mcp call repo-rag repo_rag_status '{}'` reports the current repo is
     not indexed.
  c. `mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'`
     returned zero results (and you actually ran the call).
  d. You are verifying or expanding a specific line range that repo-rag has
     already surfaced (`verifying repo-rag hit at <path>:<lines>`).
  e. You are enumerating files by pure name pattern with no semantic intent
     (for example, "list all `*.csproj` files"). Glob is fine here.
  f. The user explicitly identified the file by exact path.

Outside of (a)-(f), prefer to route through repo-rag.

### 4. Capture findings

When you discover a durable fact (an architectural decision, gotcha,
invariant, naming convention, performance trap, or anything a future session
should know), call
`mavis mcp call repo-rag repo_rag_remember '{"note": "<note>"}'`
before ending the session so the knowledge survives across chats.

If a remembered fact needs removal, call
`mavis mcp call repo-rag repo_rag_forget '{"id": <id>}'`.

### 5. Recovery when the index is stale

If the current branch has changed since the last index, or search results
look outdated, suggest running:

  `rag index --changed --sequential --window-size 10 --pace-sec 0`

(or installing the git hooks via `rag hooks install`) and then continue using
repo-rag for follow-up queries.

### 6. Compliance notes

Skipping repo-rag when none of the section 3 exceptions apply is out of
policy. If you notice yourself about to issue Grep, Glob, or Read for code
in an indexed repo without a section 3 justification, cancel the call and
switch to repo-rag search instead.
"""


def _minimax_rules_block() -> str:
    return f"{_rules_text.MD_BEGIN}\n{MINIMAX_RULES_BODY.rstrip()}\n{_rules_text.MD_END}\n"


class MinimaxAgent(AgentPlugin):
    name = "minimax"
    display = "MiniMax Code"

    def _config_dir(self) -> Path:
        return Path.home() / ".minimax"

    def _mcp_path(self) -> Path:
        return self._config_dir() / "mcp" / "mcp.json"

    def _rules_paths(self) -> list[Path]:
        return [
            self._config_dir() / "agents" / "coder" / "agent.md",
            self._config_dir() / "agents" / "mavis" / "agent.md",
        ]

    def _rules_display_path(self) -> Path:
        return self._config_dir() / "agents" / "*" / "agent.md"

    def detect(self) -> bool:
        return self._mcp_path().exists() or any(self._config_dir().glob("agents/*/agent.md"))

    def user_rules_display_path(self) -> str | Path | None:
        return self._rules_display_path()

    def project_rules_path(self, repo_root: Path) -> Path | None:
        return repo_root / "AGENTS.md"

    def rules_block(self) -> str:
        return _minimax_rules_block()

    def _upsert_rules_before_builtin_marker(self, existing: str) -> str:
        without_block, _ = _rules_text.remove_md_block(existing)
        block = self.rules_block()
        if MINIMAX_BUILTIN_MARKER not in without_block:
            return _rules_text.upsert_md_block(without_block, block=block)
        head, _, tail = without_block.partition(MINIMAX_BUILTIN_MARKER)
        return (
            head.rstrip() + "\n\n" + block + "\n" + MINIMAX_BUILTIN_MARKER + tail
        ).rstrip() + "\n"

    def install_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> InstallResult:
        if scope != "user":
            return super().install_rules(scope=scope, repo_root=repo_root)
        if not self._config_dir().exists():
            return InstallResult(
                path=self._rules_display_path(),
                skipped_reason="MiniMax config directory not found",
            )
        written = False
        for path in self._rules_paths():
            path.parent.mkdir(parents=True, exist_ok=True)
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            new_content = self._upsert_rules_before_builtin_marker(existing)
            if new_content != existing:
                path.write_text(new_content, encoding="utf-8")
                written = True
        return InstallResult(
            path=self._rules_display_path(),
            written=written,
            detail="2 agent files" if written else "already up to date",
        )

    def uninstall_rules(
        self,
        *,
        scope: Scope,
        repo_root: Path | None = None,
    ) -> bool:
        if scope != "user":
            return super().uninstall_rules(scope=scope, repo_root=repo_root)
        removed_any = False
        for path in self._rules_paths():
            if not path.exists():
                continue
            existing = path.read_text(encoding="utf-8")
            new_content, removed = _rules_text.remove_md_block(existing)
            if removed:
                path.write_text(new_content, encoding="utf-8")
                removed_any = True
        return removed_any

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
            config_snippet=json.dumps({"mcpServers": {"repo-rag": MINIMAX_MCP_ENTRY}}, indent=2)
            + "\n",
        )

# Claude (CLI + Desktop)

Covers both **Claude Code** (Anthropic's terminal-and-IDE agent) and
**Claude Desktop** (native macOS / Windows / Linux app). One plugin handles
both — `rag agents setup --target claude` writes the rules block into
`CLAUDE.md` and patches MCP configs for both environments.

## Auto setup

```bash
rag agents setup --target claude
```

This single command:
- Inserts the policy block into `~/.claude/CLAUDE.md` (user scope) and
  `<repo>/CLAUDE.md` (project scope).
- Adds the `repo-rag` MCP entry to `~/.claude.json` (Claude Code CLI).
- Adds the MCP entry to the platform-specific desktop config so Claude
  Desktop also picks it up.

The old target names `claude_code` and `claude_desktop` still work as
aliases for backward compatibility.

## Manual setup

### Claude Code CLI

```bash
claude mcp add repo-rag rag mcp-server
```

Or edit `~/.claude.json`:

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "rag",
      "args": ["mcp-server"]
    }
  }
}
```

### Claude Desktop (native app)

Edit the platform-specific config:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "rag",
      "args": ["mcp-server"]
    }
  }
}
```

Restart Claude Desktop after saving.

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.claude/CLAUDE.md` | Markdown (marker block) |
| Project rules | `<repo>/CLAUDE.md` | Markdown (marker block) |
| MCP config (CLI) | `~/.claude.json` | JSON (`mcpServers.repo-rag`) |
| MCP config (Desktop) | platform-specific JSON | JSON (`mcpServers.repo-rag`) |

## Notes

- Claude Code auto-reloads `CLAUDE.md` when the file changes.
- If you use the `claude mcp add` CLI you do not need to edit `.claude.json`
  by hand; the command writes the same entry.
- The MCP tools' `readOnlyHint=true` annotation lets Claude Code auto-approve
  `repo_rag_search`, `repo_rag_get_context`, and `repo_rag_status`.
- GUI apps (Claude Desktop) do not inherit your shell's PATH. If `rag` is in
  a virtualenv, use the absolute path in `command`
  (`/Users/you/.local/bin/rag`).

## Uninstall

```bash
rag agents uninstall --target claude
```

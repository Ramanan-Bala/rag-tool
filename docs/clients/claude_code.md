# Claude Code

Claude Code (Anthropic's terminal-and-IDE agent) reads project guidance from
`CLAUDE.md` files. MCP servers live in `~/.claude.json`.

## Auto setup

```bash
rag agents setup --target claude_code
```

## Manual setup

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

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.claude/CLAUDE.md` | Markdown (marker block) |
| Project rules | `<repo>/CLAUDE.md` | Markdown (marker block) |
| MCP config | `~/.claude.json` | JSON (`mcpServers.repo-rag`) |

## Notes

- Claude Code auto-reloads `CLAUDE.md` when the file changes.
- If you use the `claude mcp add` CLI you do not need to edit `.claude.json`
  by hand; the command writes the same entry.
- The MCP tools' `readOnlyHint=true` annotation lets Claude Code auto-approve
  `repo_rag_search`, `repo_rag_get_context`, and `repo_rag_status`.

## Uninstall

```bash
rag agents uninstall --target claude_code
```

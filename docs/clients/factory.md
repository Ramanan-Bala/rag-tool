# Factory Droid

Factory Droid is an MCP-aware AI coding agent that reads its rules from
`~/.factory/AGENTS.md` (user scope) and the repo's `AGENTS.md` (project
scope), and its MCP servers from `~/.factory/mcp.json`.

## Auto setup

```bash
rag agents setup --target factory
```

This:

- Inserts the `<!-- repo-rag:begin -->` ... `<!-- repo-rag:end -->` block
  into `~/.factory/AGENTS.md` and `<repo>/AGENTS.md`.
- Adds the `repo-rag` entry to `~/.factory/mcp.json` under `mcpServers`.

## Manual setup

```bash
droid mcp add repo-rag "rag mcp-server"
```

Or edit `~/.factory/mcp.json`:

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
| User rules | `~/.factory/AGENTS.md` | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.factory/mcp.json` | JSON (`mcpServers.repo-rag`) |

## Uninstall

```bash
rag agents uninstall --target factory
```

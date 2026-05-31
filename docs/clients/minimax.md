# MiniMax Agent

MiniMax Agent / MiniMax Code stores MCP servers in
`~/.minimax/mcp/mcp.json`. repo-rag writes the shared project rules block to
the repo's `AGENTS.md`.

## Auto setup

```bash
rag agents setup --target minimax
```

This:

- Inserts the `<!-- repo-rag:begin -->` ... `<!-- repo-rag:end -->` block
  into `<repo>/AGENTS.md`.
- Adds the `repo-rag` entry to `~/.minimax/mcp/mcp.json` under `mcpServers`.

## Manual setup

Edit `~/.minimax/mcp/mcp.json`:

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "rag",
      "args": ["mcp-server"],
      "enabled": true,
      "configured": true
    }
  }
}
```

## Files touched

| Scope | Path | Format |
|---|---|---|
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.minimax/mcp/mcp.json` | JSON (`mcpServers.repo-rag`) |

## Uninstall

```bash
rag agents uninstall --target minimax
```

# Google Antigravity

Antigravity (Google's agentic IDE) reads `AGENTS.md` rules and lists MCP
servers in `~/.antigravity/mcp.json`.

## Auto setup

```bash
rag agents setup --target antigravity
```

## Manual setup

Edit `~/.antigravity/mcp.json`:

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
| User rules | `~/.antigravity/AGENTS.md` | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.antigravity/mcp.json` | JSON (`mcpServers.repo-rag`) |

## Uninstall

```bash
rag agents uninstall --target antigravity
```

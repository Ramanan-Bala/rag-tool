# Gemini CLI

Google's Gemini CLI reads rules from `GEMINI.md` and stores MCP servers in
`~/.gemini/settings.json` under `mcpServers`.

## Auto setup

```bash
rag agents setup --target gemini
```

## Manual setup

Edit `~/.gemini/settings.json`:

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
| User rules | `~/.gemini/GEMINI.md` | Markdown (marker block) |
| Project rules | `<repo>/GEMINI.md` | Markdown (marker block) |
| MCP config | `~/.gemini/settings.json` | JSON (`mcpServers.repo-rag`) |

## Uninstall

```bash
rag agents uninstall --target gemini
```

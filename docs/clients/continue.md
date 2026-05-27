# Continue.dev

Continue.dev keeps everything in a single `~/.continue/config.json`: model
settings, prompt context, slash commands, and MCP servers under `mcpServers`.

## Auto setup

```bash
rag agents setup --target continue
```

## Manual setup

Edit `~/.continue/config.json`:

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
| User rules | `~/.continue/AGENTS.md` (we still write it for completeness) | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.continue/config.json` | JSON (`mcpServers.repo-rag`) |

## Notes

- Continue caches the MCP server list at startup; reload the extension after
  editing the config.
- If you already have a `systemMessage` or `customCommands` set in Continue,
  they are preserved.

## Uninstall

```bash
rag agents uninstall --target continue
```

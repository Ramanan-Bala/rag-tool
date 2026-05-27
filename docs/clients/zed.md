# Zed

Zed reads project rules from `.rules` files and registers MCP servers in
`settings.json` under the `context_servers` key.

## Auto setup

```bash
rag agents setup --target zed
```

## Manual setup

Edit `settings.json`:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Zed/settings.json` |
| Linux | `~/.config/zed/settings.json` |
| Windows | `%APPDATA%\Zed\settings.json` |

```json
{
  "context_servers": {
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
| User rules | `<zed-config>/.rules` | Markdown (marker block) |
| Project rules | `<repo>/.rules` | Markdown (marker block) |
| MCP config | `<zed-config>/settings.json` | JSON (`context_servers.repo-rag`) |

## Notes

- Zed names its MCP integration key `context_servers`, not `mcpServers`.
  The plugin writes the correct key for you.

## Uninstall

```bash
rag agents uninstall --target zed
```

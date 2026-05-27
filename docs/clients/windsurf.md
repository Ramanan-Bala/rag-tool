# Windsurf

Windsurf (the Codeium editor) reads global rules from
`~/.codeium/windsurf/global_rules.md` and project rules from
`<repo>/.windsurfrules`. MCP servers go in
`~/.codeium/windsurf/mcp_config.json`.

## Auto setup

```bash
rag agents setup --target windsurf
```

## Manual setup

Edit `~/.codeium/windsurf/mcp_config.json`:

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
| User rules | `~/.codeium/windsurf/global_rules.md` | Markdown (marker block) |
| Project rules | `<repo>/.windsurfrules` | Markdown (marker block) |
| MCP config | `~/.codeium/windsurf/mcp_config.json` | JSON (`mcpServers.repo-rag`) |

## Notes

- `.windsurfrules` is a top-level file in the project; commit it if you want
  every contributor to use repo-rag.
- Windsurf evaluates rules per workspace; reopen the workspace after install.

## Uninstall

```bash
rag agents uninstall --target windsurf
```

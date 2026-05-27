# Claude Desktop

Claude Desktop has no rules file; only an MCP config. Pair this plugin with
the `universal` plugin (`AGENTS.md`) if you also want the policy text loaded.

## Auto setup

```bash
rag agents setup --target claude_desktop
```

## Manual setup

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
| Rules | (none) | - |
| MCP config | platform-specific JSON | JSON (`mcpServers.repo-rag`) |

## Notes

- GUI apps do not inherit your shell's PATH. If `rag` is in a virtualenv,
  use the absolute path in `command` (`/Users/you/.local/bin/rag`).
- Alternatively run the Docker image:

  ```json
  {
    "mcpServers": {
      "repo-rag": {
        "command": "docker",
        "args": [
          "run", "-i", "--rm",
          "-v", "/Users/you/.repo-rag:/data/.repo-rag",
          "ghcr.io/ramanan-bala/repo-rag:latest"
        ]
      }
    }
  }
  ```

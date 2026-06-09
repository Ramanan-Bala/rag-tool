# OpenCode (CLI + Desktop)

Covers both **OpenCode CLI** (terminal agent) and **OpenCode Desktop**
(native app from SST/Anomaly). One plugin handles both — `rag agents setup
--target opencode` writes the rules block into `CLAUDE.md` and patches the
MCP config in `opencode.json`.

## Auto setup

```bash
rag agents setup --target opencode
```

This single command:
- Inserts the policy block into `~/.config/opencode/CLAUDE.md` (user scope)
  and `<repo>/CLAUDE.md` (project scope).
- Adds the `repo-rag` MCP entry to `~/.config/opencode/opencode.json`.

OpenCode shares a single config file for both CLI and Desktop, so no
separate desktop side-effect write is needed.

## Manual setup

Edit `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "repo-rag": {
      "type": "local",
      "command": ["rag", "mcp-server"]
    }
  }
}
```

> **Note:** OpenCode's MCP format uses `type`/`command` (array) instead of
> the standard `mcpServers`/`command`+`args` pattern. The `rag agents setup`
> command writes the correct format automatically.

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.config/opencode/CLAUDE.md` | Markdown (marker block) |
| Project rules | `<repo>/CLAUDE.md` | Markdown (marker block) |
| MCP config | `~/.config/opencode/opencode.json` | JSON (`mcp.repo-rag`) |

## Install

```bash
# Via the install script
curl -fsSL https://opencode.ai/install | bash

# Via npm
npm i -g opencode-ai

# Via Homebrew (macOS)
brew install sst/tap/opencode
```

## Notes

- OpenCode reads `CLAUDE.md` files in its config directory and at the repo
  root for custom instructions.
- The legacy config path `~/.opencode.json` is also detected but the plugin
  writes to the XDG-compliant `~/.config/opencode/opencode.json`.
- GUI apps (OpenCode Desktop) do not inherit your shell's PATH. If `rag` is
  in a virtualenv, use the absolute path in `command`
  (`/Users/you/.local/bin/rag`).

## Uninstall

```bash
rag agents uninstall --target opencode
```

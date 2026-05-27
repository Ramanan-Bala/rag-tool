# Cline

Cline is a VS Code extension. It reads project rules from `AGENTS.md` at
the workspace root and registers MCP servers through VS Code settings, which
repo-rag does not automate.

## Auto setup

```bash
rag agents setup --target cline           # writes <repo>/AGENTS.md
```

## Manual MCP setup

1. Open VS Code.
2. Open the Cline sidebar.
3. Click "MCP Servers" -> "Add server".
4. Enter:

   - Command: `rag`
   - Args: `mcp-server`

(Or paste the JSON snippet from `rag agents print-mcp --target cline` into
Cline's MCP settings JSON.)

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | (none, Cline reads project `AGENTS.md`) | - |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | VS Code settings | manual |

## Uninstall

```bash
rag agents uninstall --target cline
```

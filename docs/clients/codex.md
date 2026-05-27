# OpenAI Codex CLI

The Codex CLI (`codex`) reads `AGENTS.md` from the user (`~/.codex/`) and the
repo, and stores MCP servers in `~/.codex/config.toml` under
`[mcp_servers.<name>]` tables.

## Auto setup

```bash
rag agents setup --target codex
```

## Manual setup

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.repo-rag]
command = "rag"
args = ["mcp-server"]
```

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.codex/AGENTS.md` | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.codex/config.toml` | TOML (`mcp_servers.repo-rag`) |

## Notes

- repo-rag's writer parses the TOML file with `tomllib`, edits only the
  `[mcp_servers.repo-rag]` entry, and re-serialises with `tomli-w` so other
  tables stay intact.
- The TOML grammar requires the entry name be quoted if it contains a hyphen:
  `[mcp_servers."repo-rag"]`. The writer always emits this form.

## Uninstall

```bash
rag agents uninstall --target codex
```

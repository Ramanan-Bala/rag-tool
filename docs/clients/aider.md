# Aider

Aider's native rules file is `CONVENTIONS.md` (loaded with `--read CONVENTIONS.md`).
MCP support is still evolving in Aider; this plugin writes a marker-tagged
YAML reference block into `~/.aider.conf.yml` that you can move once your
Aider build supports it.

## Auto setup

```bash
rag agents setup --target aider
```

## Manual setup

`~/.aider.conf.yml` (or `--read` on the command line):

```yaml
# >>> repo-rag >>>
# repo-rag MCP server entry (kept here as a reference; move into the
# correct key for your Aider build if your version supports MCP).
# mcp-servers:
#   repo-rag:
#     command: rag
#     args: [mcp-server]
# <<< repo-rag <<<
```

Add `CONVENTIONS.md` to the repo root and start Aider with:

```bash
aider --read CONVENTIONS.md
```

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.aider/CONVENTIONS.md` | Markdown (marker block) |
| Project rules | `<repo>/CONVENTIONS.md` | Markdown (marker block) |
| MCP reference | `~/.aider.conf.yml` | YAML (commented marker block) |

## Notes

- Because Aider does not yet read MCP servers from the YAML config in a
  standardised way, the YAML block is informational only. Watch the Aider
  changelog for first-class MCP support.

## Uninstall

```bash
rag agents uninstall --target aider
```

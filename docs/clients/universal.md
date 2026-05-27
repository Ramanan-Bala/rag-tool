# Universal (AGENTS.md)

The `universal` plugin writes the policy block into the cross-tool
`AGENTS.md` standard. Any future agent that loads `AGENTS.md` will pick it
up automatically.

## Auto setup

```bash
rag agents setup --target universal
```

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.config/repo-rag/AGENTS.md` (honours `$XDG_CONFIG_HOME`) | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | (none - the universal plugin only handles rules) | - |

## When to use it

- You want the policy in `AGENTS.md` even when no specific agent is detected.
- A new MCP-aware tool ships that reads `AGENTS.md` but does not yet have a
  dedicated plugin in repo-rag.

## Notes

- `rag agents setup --all` always includes the universal plugin in addition
  to every detected one.
- Project `AGENTS.md` lives at the repo root; consider committing it so
  every contributor and CI agent picks up the policy.

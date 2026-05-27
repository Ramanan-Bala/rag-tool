# Cursor

Cursor reads project rules from `.mdc` files under `.cursor/rules/` and the
MCP config from `.cursor/mcp.json`. The `.mdc` format is Markdown with a YAML
frontmatter (`alwaysApply: true` makes the rule load for every conversation).

## Auto setup

```bash
rag agents setup --target cursor              # both scopes
rag agents setup --target cursor --scope project
```

## Manual setup

Create `<repo>/.cursor/rules/repo-rag.mdc`:

```markdown
---
description: repo-rag code search policy (use repo_rag_search before Grep/Glob)
alwaysApply: true
---
<!-- repo-rag:begin -->
...
<!-- repo-rag:end -->
```

Add `<repo>/.cursor/mcp.json`:

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
| User rules | `~/.cursor/rules/repo-rag.mdc` | `.mdc` (frontmatter + Markdown) |
| Project rules | `<repo>/.cursor/rules/repo-rag.mdc` | `.mdc` (frontmatter + Markdown) |
| User MCP | `~/.cursor/mcp.json` | JSON (`mcpServers.repo-rag`) |
| Project MCP | `<repo>/.cursor/mcp.json` | JSON (`mcpServers.repo-rag`) |

## Notes

- Cursor reloads rules automatically on save.
- Because Cursor's `.mdc` file is a single repo-rag-owned document (not a
  marker block inside a user-owned file), `rag agents uninstall --target cursor`
  deletes it entirely.

## Uninstall

```bash
rag agents uninstall --target cursor
```

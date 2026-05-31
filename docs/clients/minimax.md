# MiniMax Code

MiniMax Agent / MiniMax Code stores MCP servers in
`~/.minimax/mcp/mcp.json`. MiniMax loads user instructions from
agent-specific `agent.md` files under `~/.minimax/agents/`.

## Auto setup

```bash
rag agents setup --target minimax
```

This:

- Inserts the `<!-- repo-rag:begin -->` ... `<!-- repo-rag:end -->` block
  into `~/.minimax/agents/coder/agent.md`,
  `~/.minimax/agents/mavis/agent.md`, and `<repo>/AGENTS.md`.
- Adds the `repo-rag` entry to `~/.minimax/mcp/mcp.json` under `mcpServers`.

Use `--scope user` to write only the MiniMax user rules files, and
`--skip-mcp` when you only want rules installation.

## Manual setup

Edit `~/.minimax/mcp/mcp.json`:

```json
{
  "mcpServers": {
    "repo-rag": {
      "command": "rag",
      "args": ["mcp-server"],
      "env": {},
      "enabled": true,
      "configured": true,
      "description": "Local RAG indexer - search code with hybrid keyword + vector search. Tools: repo_rag_search, repo_rag_get_context, repo_rag_remember, repo_rag_forget, repo_rag_status"
    }
  }
}
```

MiniMax rule snippets use its CLI MCP invocation form, for example:

```bash
mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'
```

## Files touched

| Scope | Path | Format |
|---|---|---|
| User rules | `~/.minimax/agents/coder/agent.md` | Markdown (marker block) |
| User rules | `~/.minimax/agents/mavis/agent.md` | Markdown (marker block) |
| Project rules | `<repo>/AGENTS.md` | Markdown (marker block) |
| MCP config | `~/.minimax/mcp/mcp.json` | JSON (`mcpServers.repo-rag`) |

## Uninstall

```bash
rag agents uninstall --target minimax
```

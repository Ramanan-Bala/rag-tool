<!-- repo-rag:begin -->
## Code Search Policy (repo-rag)

This guidance applies whenever you read, modify, or reason about code,
symbols, files, or configuration in a repository indexed by `repo-rag`.

### 1. Recommended first step

For non-trivial code questions or multi-step coding tasks, call one of these
MCP tools before any other search or file-read tool:

  - `mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'`
  - `mavis mcp call repo-rag repo_rag_get_context '{"task": "<task description>"}'`
  - `mavis mcp call repo-rag repo_rag_status '{}'`

Treat the chunks returned by repo-rag as the primary evidence and cite
`path:start_line-end_line` when describing code you found via repo-rag.

### 2. Avoid these tools as the first code-search action

In a repo-rag indexed repository, prefer repo-rag search over:

  - Grep, ripgrep, `rg`
  - Glob and file-pattern searches
  - LS on source directories for exploration
  - Reading a source file you have not first located via repo-rag
  - Shell-based search commands (`Select-String`, `findstr`, `grep`, `ag`, `ack`, `fd`)

If you reach for Grep, Glob, or a Read on an unknown path, pause and call
`mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'` first.

### 3. Reasonable exceptions

You may use Grep, Glob, LS, or Read directly when one of these applies. State
which one in your reply so the user can audit:

  a. The repo-rag MCP server is unavailable or unresponsive in this session.
  b. `mavis mcp call repo-rag repo_rag_status '{}'` reports the current repo is
     not indexed.
  c. `mavis mcp call repo-rag repo_rag_search '{"query": "<your query>"}'`
     returned zero results (and you actually ran the call).
  d. You are verifying or expanding a specific line range that repo-rag has
     already surfaced (`verifying repo-rag hit at <path>:<lines>`).
  e. You are enumerating files by pure name pattern with no semantic intent
     (for example, "list all `*.csproj` files"). Glob is fine here.
  f. The user explicitly identified the file by exact path.

Outside of (a)-(f), prefer to route through repo-rag.

### 4. Capture findings

When you discover a durable fact (an architectural decision, gotcha,
invariant, naming convention, performance trap, or anything a future session
should know), call
`mavis mcp call repo-rag repo_rag_remember '{"note": "<note>"}'`
before ending the session so the knowledge survives across chats.

If a remembered fact needs removal, call
`mavis mcp call repo-rag repo_rag_forget '{"id": <id>}'`.

### 5. Recovery when the index is stale

If the current branch has changed since the last index, or search results
look outdated, suggest running:

  `rag index --changed --sequential --window-size 10 --pace-sec 0`

(or installing the git hooks via `rag hooks install`) and then continue using
repo-rag for follow-up queries.

### 6. Compliance notes

Skipping repo-rag when none of the section 3 exceptions apply is out of
policy. If you notice yourself about to issue Grep, Glob, or Read for code
in an indexed repo without a section 3 justification, cancel the call and
switch to repo-rag search instead.
<!-- repo-rag:end -->

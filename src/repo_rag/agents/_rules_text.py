"""Single source of truth for the repo-rag code search policy block.

The wording is intentionally collaborative: it nudges agents to route code
questions through ``repo_rag_search`` first, but stops short of strict
"mandatory / prohibited / enforcement" language so MCP clients with built-in
content filters do not reject the rules file.
"""

from __future__ import annotations

MD_BEGIN = "<!-- repo-rag:begin -->"
MD_END = "<!-- repo-rag:end -->"

HASH_BEGIN = "# >>> repo-rag >>>"
HASH_END = "# <<< repo-rag <<<"

SLASH_BEGIN = "// >>> repo-rag >>>"
SLASH_END = "// <<< repo-rag <<<"


_BODY = """\
## Code Search Policy (repo-rag)

This guidance applies whenever you read, modify, or reason about code,
symbols, files, or configuration in a repository indexed by `repo-rag`.

### 1. Recommended first step

For non-trivial code questions or multi-step coding tasks, call one of these
MCP tools before any other search or file-read tool:

  - `repo_rag_search`           - for queries / "where is X" / "how does X work"
  - `repo_rag_get_context`      - at the start of multi-step tasks
  - `repo_rag_status`           - to confirm the repo is indexed

Treat the chunks returned by repo-rag as the primary evidence and cite
`path:start_line-end_line` when describing code you found via repo-rag.

### 2. Avoid these tools as the first code-search action

In a repo-rag indexed repository, prefer `repo_rag_search` over:

  - Grep, ripgrep, `rg`
  - Glob and file-pattern searches
  - LS on source directories for exploration
  - Reading a source file you have not first located via repo-rag
  - Shell-based search commands (`Select-String`, `findstr`, `grep`, `ag`, `ack`, `fd`)

If you reach for Grep, Glob, or a Read on an unknown path, pause and run
`repo_rag_search` first.

### 3. Reasonable exceptions

You may use Grep, Glob, LS, or Read directly when one of these applies. State
which one in your reply so the user can audit:

  a. The repo-rag MCP server is unavailable or unresponsive in this session.
  b. `repo_rag_status` reports the current repo is not indexed.
  c. `repo_rag_search` for the relevant query returned zero results (and you
     actually ran the call).
  d. You are verifying or expanding a specific line range that repo-rag has
     already surfaced (`verifying repo-rag hit at <path>:<lines>`).
  e. You are enumerating files by pure name pattern with no semantic intent
     (for example, "list all `*.csproj` files"). Glob is fine here.
  f. The user explicitly identified the file by exact path.

Outside of (a)-(f), prefer to route through repo-rag.

### 4. Capture findings

When you discover a durable fact (an architectural decision, gotcha,
invariant, naming convention, performance trap, or anything a future session
should know), call `repo_rag_remember` before ending the session so the
knowledge survives across chats.

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
switch to `repo_rag_search` instead.
"""


def rules_markdown() -> str:
    """Return the policy body for Markdown rules files (no markers)."""
    return _BODY


def md_block() -> str:
    """Return the policy body wrapped in Markdown markers."""
    return f"{MD_BEGIN}\n{_BODY.rstrip()}\n{MD_END}\n"


def upsert_md_block(existing: str, *, block: str | None = None) -> str:
    """Insert or replace the marker-tagged Markdown block inside ``existing``."""
    block = block or md_block()
    if MD_BEGIN in existing and MD_END in existing:
        head, _, rest = existing.partition(MD_BEGIN)
        _, _, tail = rest.partition(MD_END)
        return (head + block + tail.lstrip("\n")).rstrip() + "\n"
    if existing.strip():
        return existing.rstrip() + "\n\n" + block
    return block


def remove_md_block(existing: str) -> tuple[str, bool]:
    """Strip the marker-tagged Markdown block. Returns ``(new_text, removed)``."""
    if MD_BEGIN not in existing or MD_END not in existing:
        return existing, False
    head, _, rest = existing.partition(MD_BEGIN)
    _, _, tail = rest.partition(MD_END)
    new_content = (head + tail.lstrip("\n")).rstrip() + "\n"
    return new_content, True

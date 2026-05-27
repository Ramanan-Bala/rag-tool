from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .config import GlobalConfig
from .search import SearchHit
from .store.sqlite import SqliteStore


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_context_pack(
    task: str,
    hits: list[SearchHit],
    sqlite: SqliteStore,
    cfg: GlobalConfig,
    repo_root: Path,
    max_tokens: int | None = None,
) -> str:
    budget = max_tokens or cfg.retrieval.max_context_tokens
    lines: list[str] = []
    lines.append("# Context pack")
    lines.append("")
    lines.append(
        f"_Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}Z "
        f"for repo `{repo_root.name}`._"
    )
    lines.append("")
    lines.append("## Task")
    lines.append("")
    lines.append(task.strip())
    lines.append("")

    notes = sqlite.search_notes(task, limit=8)
    if notes:
        lines.append("## Remembered notes")
        lines.append("")
        for n in notes:
            tag_str = f"  _[tags: {n['tags']}]_" if n["tags"] else ""
            lines.append(f"- ({n['id']}) {n['note']}{tag_str}")
        lines.append("")

    if hits:
        files_seen: list[str] = []
        for h in hits:
            if h.path not in files_seen:
                files_seen.append(h.path)
        lines.append("## Top relevant files")
        lines.append("")
        for p in files_seen[:10]:
            lines.append(f"- `{p}`")
        lines.append("")
        lines.append("## Relevant chunks")
        lines.append("")
        used_tokens = sum(_approx_tokens(line) for line in lines)
        for h in hits:
            header = (
                f"### `{h.path}` lines {h.start_line}-{h.end_line} "
                f"(score={h.score:.3f}, via={'+'.join(h.sources)})"
            )
            fence_lang = h.language if h.language and h.language != "text" else ""
            block = "\n".join(
                [
                    "",
                    header,
                    "",
                    f"```{fence_lang}",
                    h.content.rstrip(),
                    "```",
                    "",
                ]
            )
            block_tokens = _approx_tokens(block)
            if used_tokens + block_tokens > budget:
                lines.append(f"_(truncated at {budget} tokens; {len(hits)} hits considered)_")
                break
            lines.append(block)
            used_tokens += block_tokens
    else:
        lines.append("_No matching chunks found. The repo may be unindexed; run `rag rebuild`._")
        lines.append("")

    lines.append("")
    lines.append("## Suggested investigation order")
    lines.append("")
    if hits:
        for i, h in enumerate(hits[:5], 1):
            lines.append(f"{i}. Open `{h.path}` lines {h.start_line}-{h.end_line}")
    else:
        lines.append("1. Run `rag rebuild` to index the repo, then retry.")
    return "\n".join(lines)

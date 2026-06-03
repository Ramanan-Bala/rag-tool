from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .fileutils import CODE_LANGS, detect_language


@dataclass
class Chunk:
    path: str
    language: str
    start_line: int
    end_line: int
    content: str


_CODE_BOUNDARY = re.compile(
    r"^(?:\s*(?:def|class|function|fn|public|private|protected|internal|"
    r"static|async|export|module|namespace|interface|impl|struct|enum|trait|type|@)\b)",
    re.MULTILINE,
)
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)

# Map repo-rag language names to tree-sitter grammar names.
_TS_LANG = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "csharp": "c_sharp",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "kotlin": "kotlin",
    "ruby": "ruby",
    "php": "php",
    "c": "c",
    "cpp": "cpp",
    "swift": "swift",
    "scala": "scala",
    "shell": "bash",
    "sql": "sql",
}
_DEF_NODE_HINTS = (
    "function",
    "class",
    "method",
    "struct",
    "interface",
    "enum",
    "impl_item",
    "trait",
    "mod_item",
    "module",
    "namespace",
    "decorated",
    "type_declaration",
    "constructor",
    "export",
)


def _is_def_node(node_type: str) -> bool:
    return any(hint in node_type for hint in _DEF_NODE_HINTS)


def _tree_sitter_segments(text: str, path: Path, lang: str) -> list[tuple[int, str]] | None:
    """Segment code at top-level definition boundaries using tree-sitter.

    Returns None if tree-sitter (or the grammar) is unavailable so callers can
    fall back to the regex segmentation.
    """
    ts_name = _TS_LANG.get(lang)
    if ts_name == "typescript" and path.suffix.lower() == ".tsx":
        ts_name = "tsx"
    if not ts_name:
        return None
    try:
        from tree_sitter_language_pack import get_parser
    except Exception:
        return None
    try:
        parser = get_parser(ts_name)
        data = text.encode("utf-8", errors="replace")
        root = parser.parse(data).root_node
    except Exception:
        return None

    points = {0}
    for child in root.children:
        if _is_def_node(child.type) and child.start_byte > 0:
            points.add(child.start_byte)
    if len(points) <= 1:
        return None

    ordered = sorted(points)
    ordered.append(len(data))
    segments: list[tuple[int, str]] = []
    for i in range(len(ordered) - 1):
        start, end = ordered[i], ordered[i + 1]
        seg = data[start:end].decode("utf-8", errors="replace")
        if seg.strip():
            segments.append((data[:start].count(b"\n"), seg))
    return segments or None


def _approx_tokens_to_chars(tokens: int) -> int:
    return tokens * 4


def _split_with_budget(text: str, max_chars: int, overlap_chars: int) -> list[tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    safe_overlap = min(overlap_chars, max(0, max_chars // 2))
    chunks: list[tuple[int, int, str]] = []
    buf: list[str] = []
    buf_size = 0
    start_idx = 0
    i = 0
    added_since_flush = False
    while i < len(lines):
        line = lines[i]
        if buf_size + len(line) > max_chars and buf and added_since_flush:
            content = "".join(buf)
            chunks.append((start_idx + 1, start_idx + len(buf), content))
            overlap_lines: list[str] = []
            overlap_size = 0
            j = len(buf) - 1
            while j >= 0 and overlap_size + len(buf[j]) <= safe_overlap:
                overlap_lines.insert(0, buf[j])
                overlap_size += len(buf[j])
                j -= 1
            start_idx = start_idx + len(buf) - len(overlap_lines)
            buf = overlap_lines.copy()
            buf_size = overlap_size
            added_since_flush = False
            continue
        buf.append(line)
        buf_size += len(line)
        i += 1
        added_since_flush = True
    if buf:
        content = "".join(buf)
        chunks.append((start_idx + 1, start_idx + len(buf), content))
    return chunks


def chunk_text(
    path: Path,
    rel_path: str,
    text: str,
    code_tokens: int,
    prose_tokens: int,
    overlap_tokens: int,
    use_tree_sitter: bool = True,
) -> list[Chunk]:
    lang = detect_language(path)
    is_code = lang in CODE_LANGS
    target_tokens = code_tokens if is_code else prose_tokens
    max_chars = _approx_tokens_to_chars(target_tokens)
    overlap_chars = _approx_tokens_to_chars(overlap_tokens)

    segments: list[tuple[int, str]] = []
    ts_segments = (
        _tree_sitter_segments(text, path, lang) if (is_code and use_tree_sitter) else None
    )
    if is_code and ts_segments is not None:
        segments = ts_segments
    elif is_code:
        last = 0
        last_line = 0
        for m in _CODE_BOUNDARY.finditer(text):
            if m.start() == 0:
                continue
            seg = text[last : m.start()]
            if seg.strip():
                segments.append((last_line, seg))
            last_line += seg.count("\n")
            last = m.start()
        if last < len(text):
            seg = text[last:]
            if seg.strip():
                segments.append((last_line, seg))
    elif lang == "markdown":
        last = 0
        last_line = 0
        for m in _MARKDOWN_HEADING.finditer(text):
            if m.start() == 0:
                continue
            seg = text[last : m.start()]
            if seg.strip():
                segments.append((last_line, seg))
            last_line += seg.count("\n")
            last = m.start()
        if last < len(text):
            segments.append((last_line, text[last:]))
    else:
        segments.append((0, text))

    out: list[Chunk] = []
    for base_line, seg in segments:
        for start, end, content in _split_with_budget(seg, max_chars, overlap_chars):
            out.append(
                Chunk(
                    path=rel_path,
                    language=lang,
                    start_line=base_line + start,
                    end_line=base_line + end,
                    content=content,
                )
            )
    if not out and text.strip():
        out.append(
            Chunk(
                path=rel_path,
                language=lang,
                start_line=1,
                end_line=max(1, text.count("\n") + 1),
                content=text,
            )
        )
    return out

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
) -> list[Chunk]:
    lang = detect_language(path)
    is_code = lang in CODE_LANGS
    target_tokens = code_tokens if is_code else prose_tokens
    max_chars = _approx_tokens_to_chars(target_tokens)
    overlap_chars = _approx_tokens_to_chars(overlap_tokens)

    segments: list[tuple[int, str]] = []
    if is_code:
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

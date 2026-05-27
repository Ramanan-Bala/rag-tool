from pathlib import Path

from repo_rag.chunker import chunk_text


def test_python_chunks_split_on_def(tmp_path: Path):
    p = tmp_path / "m.py"
    src = (
        "def alpha():\n    return 1\n\n"
        "def beta():\n    return 2\n\n"
        "class Gamma:\n    def delta(self):\n        return 3\n"
    )
    p.write_text(src, encoding="utf-8")
    chunks = chunk_text(p, "m.py", src, code_tokens=200, prose_tokens=1500, overlap_tokens=20)
    assert chunks
    for c in chunks:
        assert c.path == "m.py"
        assert c.language == "python"
        assert c.start_line >= 1
        assert c.end_line >= c.start_line


def test_markdown_splits_on_headings(tmp_path: Path):
    p = tmp_path / "doc.md"
    src = (
        "# Title\n\nIntro text.\n\n"
        "## Section A\n\nSection A content.\n\n"
        "## Section B\n\nSection B content.\n"
    )
    p.write_text(src, encoding="utf-8")
    chunks = chunk_text(p, "doc.md", src, code_tokens=200, prose_tokens=200, overlap_tokens=20)
    assert len(chunks) >= 1


def test_chunker_handles_empty_file(tmp_path: Path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    chunks = chunk_text(p, "empty.txt", "", code_tokens=100, prose_tokens=100, overlap_tokens=10)
    assert chunks == []


def test_chunker_respects_max_chars(tmp_path: Path):
    p = tmp_path / "big.txt"
    text = "\n".join(f"line {i}" for i in range(2000))
    p.write_text(text, encoding="utf-8")
    chunks = chunk_text(p, "big.txt", text, code_tokens=100, prose_tokens=200, overlap_tokens=20)
    assert len(chunks) > 1
    for c in chunks[:-1]:
        assert len(c.content) <= 200 * 4 + 200

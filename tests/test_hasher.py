from repo_rag.hasher import chunk_id, hash_file, hash_text, short_hash


def test_hash_text_deterministic():
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("hello") != hash_text("world")


def test_short_hash_length():
    assert len(short_hash("foo")) == 12
    assert len(short_hash("foo", 16)) == 16


def test_chunk_id_changes_with_content():
    a = chunk_id("r", "src/x.py", 1, 10, "alpha")
    b = chunk_id("r", "src/x.py", 1, 10, "beta")
    assert a != b


def test_chunk_id_stable_for_same_input():
    a = chunk_id("r", "src/x.py", 1, 10, "alpha")
    b = chunk_id("r", "src/x.py", 1, 10, "alpha")
    assert a == b


def test_hash_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world", encoding="utf-8")
    assert hash_file(p) == hash_text("hello world")

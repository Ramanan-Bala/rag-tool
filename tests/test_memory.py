from pathlib import Path

from repo_rag.memory import forget, infer_tags, list_notes, remember
from repo_rag.store.sqlite import SqliteStore


def test_infer_tags_explicit_hashtags():
    tags = infer_tags("Make sure to handle #redis #ttl edges")
    assert "redis" in tags.split(",")
    assert "ttl" in tags.split(",")


def test_infer_tags_keyword_inference():
    tags = infer_tags("We use Redis TTL for sessions, not the database")
    parts = tags.split(",")
    assert "redis" in parts
    assert "session" in parts
    assert "database" in parts


def test_remember_and_forget(tmp_path: Path):
    db = SqliteStore(tmp_path / "m.db")
    note_id = remember(db, "Redis TTL is source of truth for session expiry")
    assert isinstance(note_id, int)
    rows = list_notes(db)
    assert len(rows) == 1
    assert rows[0]["id"] == note_id
    assert forget(db, note_id) is True
    assert list_notes(db) == []
    db.close()


def test_search_notes(tmp_path: Path):
    db = SqliteStore(tmp_path / "m.db")
    remember(db, "Use Redis TTL for sessions")
    remember(db, "Postgres is the source of truth for invoices")
    hits = db.search_notes("redis", limit=5)
    assert hits
    assert "Redis" in hits[0]["note"]
    db.close()

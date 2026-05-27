from pathlib import Path

from repo_rag.registry import load_registry, lookup, register_repo, remove_repo


def test_register_and_lookup(tmp_path: Path, isolated_index_root: Path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    repo_id = register_repo(repo)
    assert repo_id == "myrepo"
    assert lookup(repo) == "myrepo"
    reg = load_registry()
    assert reg[str(repo.resolve())] == "myrepo"


def test_register_collision_appends_hash(tmp_path: Path, isolated_index_root: Path):
    a = tmp_path / "a" / "myrepo"
    b = tmp_path / "b" / "myrepo"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    id_a = register_repo(a)
    id_b = register_repo(b)
    assert id_a == "myrepo"
    assert id_b != "myrepo"
    assert id_b.startswith("myrepo-")


def test_register_idempotent(tmp_path: Path, isolated_index_root: Path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    assert register_repo(repo) == register_repo(repo)


def test_remove(tmp_path: Path, isolated_index_root: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    register_repo(repo)
    assert remove_repo(repo) == "r"
    assert lookup(repo) is None

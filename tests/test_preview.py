from pathlib import Path

from repo_rag.config import GlobalConfig
from repo_rag.preview import build_index_preview
from repo_rag.registry import register_repo


def test_preview_lists_files_and_chunk_counts(fake_repo: Path, isolated_index_root: Path):
    repo_id = register_repo(fake_repo)
    cfg = GlobalConfig()

    preview = build_index_preview(fake_repo, repo_id, cfg, include_cache_counts=False)

    assert preview.repo_root == fake_repo.resolve()
    assert preview.repo_id == "myrepo"
    assert preview.total_files == 2
    assert preview.total_chunks >= 2
    assert preview.cache_available is False
    assert [item.path for item in preview.files] == ["README.md", "src/main.py"]
    assert all(item.embed_chunks == item.chunks for item in preview.files)


def test_preview_honors_per_repo_exclude_globs(fake_repo: Path, isolated_index_root: Path):
    repo_id = register_repo(fake_repo)
    cfg = GlobalConfig(exclude_globs=[*GlobalConfig().exclude_globs, "README.md"])

    preview = build_index_preview(fake_repo, repo_id, cfg, include_cache_counts=False)

    assert [item.path for item in preview.files] == ["src/main.py"]

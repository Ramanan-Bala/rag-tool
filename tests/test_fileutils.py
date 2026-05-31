from __future__ import annotations

from pathlib import Path

from repo_rag.fileutils import iter_repo_files


def _listed(repo: Path) -> list[str]:
    return sorted(
        path.relative_to(repo).as_posix()
        for path in iter_repo_files(
            repo,
            include_globs=["**/*.js", "**/*.py", "**/*.txt"],
            exclude_globs=[],
            max_file_bytes=100_000,
        )
    )


def test_iter_repo_files_honors_gitignore_files_in_nested_directories(tmp_path: Path):
    repo = tmp_path / "bizcore"
    (repo / "frontend" / "dist").mkdir(parents=True)
    (repo / "backend" / "__pycache__").mkdir(parents=True)

    (repo / ".gitignore").write_text("root-ignored.txt\n", encoding="utf-8")
    (repo / "frontend" / ".gitignore").write_text("dist/\nlocal.txt\n", encoding="utf-8")
    (repo / "backend" / ".gitignore").write_text("__pycache__/\nlocal.txt\n", encoding="utf-8")

    (repo / "root-ignored.txt").write_text("skip\n", encoding="utf-8")
    (repo / "root-kept.txt").write_text("keep\n", encoding="utf-8")
    (repo / "frontend" / "app.js").write_text("console.log('keep')\n", encoding="utf-8")
    (repo / "frontend" / "dist" / "bundle.js").write_text("skip\n", encoding="utf-8")
    (repo / "frontend" / "local.txt").write_text("skip\n", encoding="utf-8")
    (repo / "backend" / "app.py").write_text("print('keep')\n", encoding="utf-8")
    (repo / "backend" / "__pycache__" / "app.py").write_text("skip\n", encoding="utf-8")
    (repo / "backend" / "local.txt").write_text("skip\n", encoding="utf-8")

    assert _listed(repo) == [
        "backend/app.py",
        "frontend/app.js",
        "root-kept.txt",
    ]

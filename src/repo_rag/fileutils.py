from __future__ import annotations

import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pathspec

EXTENSION_TO_LANG = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".swift": "swift",
    ".m": "objc",
    ".mm": "objc",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".vue": "vue",
    ".svelte": "svelte",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".ini": "ini",
    ".cfg": "ini",
}

CODE_LANGS = {
    "python",
    "javascript",
    "typescript",
    "csharp",
    "go",
    "rust",
    "java",
    "kotlin",
    "ruby",
    "php",
    "c",
    "cpp",
    "swift",
    "objc",
    "scala",
    "shell",
    "powershell",
    "sql",
    "vue",
    "svelte",
}

PROSE_LANGS = {"markdown", "rst", "text", "html"}


def detect_language(path: Path) -> str:
    name = path.name.lower()
    if name == "dockerfile" or name.endswith(".dockerfile"):
        return "dockerfile"
    return EXTENSION_TO_LANG.get(path.suffix.lower(), "text")


_TEXT_BYTES = (
    frozenset({7, 8, 9, 10, 12, 13, 27})
    | frozenset(range(0x20, 0x7F))
    | frozenset({0x85})
    | frozenset(range(0xA0, 0x100))
)


def is_binary(path: Path, peek: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(peek)
    except OSError:
        return True
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    nontext = sum(b not in _TEXT_BYTES for b in chunk)
    return nontext / len(chunk) > 0.30


@dataclass(frozen=True)
class GitignoreMatcher:
    specs: tuple[tuple[str, pathspec.PathSpec], ...]

    def match_file(self, rel_path: str) -> bool:
        for base, spec in self.specs:
            if base:
                prefix = f"{base}/"
                if not rel_path.startswith(prefix):
                    continue
                scoped_path = rel_path[len(prefix) :]
            else:
                scoped_path = rel_path
            if spec.match_file(scoped_path):
                return True
        return False


def load_gitignore(repo_root: Path) -> GitignoreMatcher:
    specs: list[tuple[str, pathspec.PathSpec]] = []
    for gi in sorted(repo_root.rglob(".gitignore")):
        try:
            patterns = gi.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        try:
            base = gi.parent.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if base == ".":
            base = ""
        specs.append((base, pathspec.PathSpec.from_lines("gitwildmatch", patterns)))
    return GitignoreMatcher(tuple(specs))


def make_pathspec(globs: Iterable[str]) -> pathspec.PathSpec:
    return pathspec.PathSpec.from_lines("gitwildmatch", list(globs))


def iter_repo_files(
    repo_root: Path,
    include_globs: list[str],
    exclude_globs: list[str],
    max_file_bytes: int,
    extra_ignored: set[Path] | None = None,
) -> Iterator[Path]:
    gitignore = load_gitignore(repo_root)
    include_spec = make_pathspec(include_globs)
    exclude_spec = make_pathspec(exclude_globs)
    extra = extra_ignored or set()

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path in extra:
            continue
        try:
            rel = path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if exclude_spec.match_file(rel) or gitignore.match_file(rel):
            continue
        if not include_spec.match_file(rel):
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        if is_binary(path):
            continue
        yield path


def _run_git(repo_root: Path, args: list[str], timeout: float = 15.0) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _resolve_ref(repo_root: Path, ref: str) -> str | None:
    out = _run_git(repo_root, ["rev-parse", "--verify", "--quiet", ref])
    if out is None:
        return None
    out = out.strip()
    return out or None


def _diff_files(repo_root: Path, since: str, until: str = "HEAD") -> list[Path] | None:
    out = _run_git(
        repo_root,
        ["diff", "--name-only", "--no-renames", f"{since}..{until}"],
    )
    if out is None:
        return None
    files: list[Path] = []
    for line in out.splitlines():
        line = line.strip().strip('"')
        if line:
            files.append(repo_root / line)
    return files


def _porcelain_files(repo_root: Path) -> list[Path] | None:
    out = _run_git(repo_root, ["status", "--porcelain"])
    if out is None:
        return None
    files: list[Path] = []
    for line in out.splitlines():
        if not line:
            continue
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        path_part = path_part.strip().strip('"')
        if path_part:
            files.append(repo_root / path_part)
    return files


def changed_files_via_git(
    repo_root: Path,
    since_commit: str | None = None,
) -> list[Path] | None:
    """Return paths considered "changed" relative to the last indexed state.

    If `since_commit` is provided AND resolves to a commit in this repo, return
    the union of:
      - files changed between `since_commit` and HEAD (`git diff name-only`)
      - currently uncommitted modifications (`git status --porcelain`)

    Otherwise fall back to `git status --porcelain` only. Returns None on
    git failure (caller should treat as "unknown - re-index everything").
    """
    paths: list[Path] = []
    seen = set()

    if since_commit and _resolve_ref(repo_root, since_commit):
        head = _resolve_ref(repo_root, "HEAD")
        if head and head != since_commit:
            diff = _diff_files(repo_root, since_commit, "HEAD")
            if diff is not None:
                for p in diff:
                    if p not in seen:
                        seen.add(p)
                        paths.append(p)

    porcelain = _porcelain_files(repo_root)
    if porcelain is None and not paths:
        return None
    if porcelain:
        for p in porcelain:
            if p not in seen:
                seen.add(p)
                paths.append(p)
    return paths

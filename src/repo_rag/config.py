from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

import tomli_w
from pydantic import BaseModel, Field

from .paths import global_config_path, repo_index_dir

DEFAULT_INCLUDE_GLOBS = [
    "src/**",
    "app/**",
    "lib/**",
    "packages/**",
    "services/**",
    "docs/**",
    "README.md",
    "package.json",
    "pyproject.toml",
    "tsconfig.json",
    "Dockerfile",
    "docker-compose.yml",
    "*.py",
    "*.ts",
    "*.tsx",
    "*.js",
    "*.jsx",
    "*.cs",
    "*.go",
    "*.rs",
    "*.java",
    "*.kt",
    "*.rb",
    "*.php",
    "*.swift",
    "*.scala",
    "*.md",
    "*.rst",
    "*.toml",
    "*.yaml",
    "*.yml",
    "*.json",
]

DEFAULT_EXCLUDE_GLOBS = [
    ".git/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "coverage/**",
    ".next/**",
    ".turbo/**",
    "vendor/**",
    "__pycache__/**",
    ".venv/**",
    "venv/**",
    "env/**",
    ".env/**",
    "virtualenv/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".tox/**",
    ".idea/**",
    ".vscode/**",
    "**/site-packages/**",
    "**/*.dist-info/**",
    "**/*.egg-info/**",
    "pythoncore-*/**",
    "python-*/**",
    "Python*/**",
    "*.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    ".rag/**",
    ".repo-rag/**",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.bin",
    "*.dat",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.webp",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.7z",
]


class EmbeddingConfig(BaseModel):
    provider: Literal["fastembed", "sentence_transformers", "ollama", "openai"] = "fastembed"
    model: str = "BAAI/bge-small-en-v1.5"
    dim: int = 384
    base_url: str | None = None
    api_key_env: str = "RAG_EMBEDDING_API_KEY"
    batch_size: int = 32


class ChunkingConfig(BaseModel):
    code_chunk_tokens: int = 500
    prose_chunk_tokens: int = 1500
    overlap_tokens: int = 150
    max_file_bytes: int = 1_000_000


class RetrievalConfig(BaseModel):
    top_k: int = 20
    vector_weight: float = 0.6
    keyword_weight: float = 0.4
    recency_boost: float = 0.05
    max_context_tokens: int = 6000


class GlobalConfig(BaseModel):
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    include_globs: list[str] = Field(default_factory=lambda: DEFAULT_INCLUDE_GLOBS.copy())
    exclude_globs: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDE_GLOBS.copy())


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _apply_env_overrides(cfg: GlobalConfig) -> GlobalConfig:
    e = cfg.embedding.model_copy()
    if v := os.environ.get("RAG_EMBEDDING_PROVIDER"):
        e.provider = v  # type: ignore[assignment]
    if v := os.environ.get("RAG_EMBEDDING_MODEL"):
        e.model = v
    if v := os.environ.get("RAG_EMBEDDING_DIM"):
        e.dim = int(v)
    if v := os.environ.get("RAG_EMBEDDING_BASE_URL"):
        e.base_url = v
    if v := os.environ.get("RAG_EMBEDDING_API_KEY_ENV"):
        e.api_key_env = v
    cfg = cfg.model_copy()
    cfg.embedding = e
    return cfg


def load_global_config() -> GlobalConfig:
    data = _read_toml(global_config_path())
    cfg = GlobalConfig.model_validate(data) if data else GlobalConfig()
    return _apply_env_overrides(cfg)


def save_global_config(cfg: GlobalConfig) -> None:
    path = global_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(cfg.model_dump(), f)


def load_repo_config(repo_id: str) -> GlobalConfig:
    base = load_global_config()
    repo_cfg_path = repo_index_dir(repo_id) / "config.toml"
    overrides = _read_toml(repo_cfg_path)
    if not overrides:
        return base
    merged = base.model_dump()
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k].update(v)
        else:
            merged[k] = v
    return _apply_env_overrides(GlobalConfig.model_validate(merged))

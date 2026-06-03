from __future__ import annotations

import tomllib
from importlib.util import find_spec
from pathlib import Path


def _pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def test_tree_sitter_is_installed_by_default():
    project = _pyproject()["project"]
    dependencies = "\n".join(project["dependencies"])
    extras = project.get("optional-dependencies", {})

    assert "tree-sitter>=" in dependencies
    assert "tree-sitter-language-pack>=" in dependencies
    assert "treesitter" not in extras


def test_tree_sitter_modules_are_available_from_default_install():
    assert find_spec("tree_sitter") is not None
    assert find_spec("tree_sitter_language_pack") is not None

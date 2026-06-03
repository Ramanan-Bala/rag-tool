from repo_rag.fileutils import languages_for_content


def test_languages_for_content_code():
    langs = languages_for_content("code")
    assert langs is not None
    assert "python" in langs
    assert "markdown" not in langs


def test_languages_for_content_docs():
    langs = languages_for_content("docs")
    assert langs is not None
    assert "markdown" in langs
    assert "python" not in langs


def test_languages_for_content_config():
    langs = languages_for_content("config")
    assert langs is not None
    assert "yaml" in langs and "toml" in langs
    assert "python" not in langs


def test_languages_for_content_all_is_none():
    assert languages_for_content("all") is None
    assert languages_for_content("") is None
    assert languages_for_content("unknown") is None

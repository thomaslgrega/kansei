import pytest

from kansei import llm
from kansei.config import Settings


def test_settings_load_without_an_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://localhost/kansei")
    assert settings.openai_api_key is None


def test_openai_client_names_the_missing_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "openai_api_key", None)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.openai_client()

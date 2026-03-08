"""Basic app construction smoke test."""

import pytest

from infinity_film_studio.app import create_app


def test_app_constructs(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    app = create_app()
    assert "ai_client" in app
    assert "prompts" in app
    controllers = app.get("controllers")
    assert controllers
    assert {"script", "video", "storyboard"}.issubset(set(controllers.keys()))


def test_app_requires_openai_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="No OpenAI API key configured"):
        create_app()

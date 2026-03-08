"""Checks strict OpenAI-only provider wiring."""

from infinity_film_studio.app import create_app


def test_create_app_ignores_legacy_fallback_provider_env(monkeypatch):
    tracked = [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY_FALLBACK",
        "OPENAI_BASE_URL_FALLBACK",
        "OPENAI_MODEL_FALLBACK",
        "OPENAI_API_KEY_FALLBACK_1",
        "OPENAI_BASE_URL_FALLBACK_1",
        "OPENAI_MODEL_FALLBACK_1",
        "OPENAI_DEFAULT_CHAT_MODEL",
    ]
    for name in tracked:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-primary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY_FALLBACK_1", "sk-hc-secondary")
    monkeypatch.setenv("OPENAI_BASE_URL_FALLBACK_1", "https://ai.hackclub.com/proxy/v1")

    app = create_app()
    providers = getattr(app["ai_client"], "_providers")

    assert len(providers) == 1
    assert providers[0].api_key == "sk-openai-primary"
    assert providers[0].base_url == "https://api.openai.com/v1"

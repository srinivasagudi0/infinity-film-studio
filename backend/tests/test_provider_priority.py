"""Provider-priority tests for Hack Club -> OpenAI -> Offline behavior."""

from infinity_film_studio.app import create_app


def test_hackclub_is_prioritized_before_openai(monkeypatch):
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

    # Intentionally configure OpenAI in primary slot and Hack Club in fallback slot.
    # App wiring should reorder to Hack Club first.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-primary")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY_FALLBACK_1", "sk-hc-secondary")
    monkeypatch.setenv("OPENAI_BASE_URL_FALLBACK_1", "https://ai.hackclub.com/proxy/v1")

    app = create_app()
    providers = getattr(app["ai_client"], "_providers")

    assert len(providers) >= 2
    assert providers[0].api_key.startswith("sk-hc-")
    assert providers[1].api_key.startswith("sk-")
    assert not providers[1].api_key.startswith("sk-hc-")


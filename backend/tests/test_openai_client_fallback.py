"""Tests for ordered API fallback in OpenAIClient."""

from infinity_film_studio.ai import openai_client as openai_client_module
from infinity_film_studio.ai.openai_client import OpenAIClient


class _FakeCompletions:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def create(self, messages, model: str, **_kwargs):
        if self._api_key == "bad-key":
            raise RuntimeError("primary key failed")
        return {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "model": model,
            "messages": messages,
        }


class _FakeEmbeddings:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def create(self, input, model: str, **_kwargs):
        if self._api_key == "bad-key":
            raise RuntimeError("primary key failed")
        inputs = input if isinstance(input, list) else [input]
        return {
            "data": [{"embedding": [1.0, 0.0], "index": idx} for idx, _ in enumerate(inputs)],
            "model": model,
        }


class _FakeChat:
    def __init__(self, api_key: str):
        self.completions = _FakeCompletions(api_key)


class _FakeOpenAI:
    def __init__(self, api_key: str, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = _FakeChat(api_key)
        self.embeddings = _FakeEmbeddings(api_key)


def test_chat_uses_fallback_provider_and_model_override(monkeypatch):
    monkeypatch.setattr(openai_client_module, "OpenAI", _FakeOpenAI)

    client = OpenAIClient(
        api_key="bad-key",
        base_url="https://api.openai.com/v1",
        fallback_configs=[
            {
                "api_key": "hackclub-key",
                "base_url": "https://ai.hackclub.com/proxy/v1",
                "chat_model_override": "google/gemini-3-flash-preview",
            }
        ],
    )

    response = client.chat(
        messages=[{"role": "user", "content": "hello"}],
        model="gpt-4.1-mini",
    )

    assert response["model"] == "google/gemini-3-flash-preview"
    assert client.api_key == "hackclub-key"
    assert client.base_url == "https://ai.hackclub.com/proxy/v1"

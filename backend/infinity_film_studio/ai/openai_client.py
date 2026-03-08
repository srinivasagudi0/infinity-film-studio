"""Strict OpenAI client wrapper for live requests only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None

DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass(frozen=True)
class _Provider:
    """Provider configuration for a single OpenAI-compatible endpoint."""

    api_key: str
    base_url: str | None = None
    chat_model_override: str | None = None


class OpenAIClient:
    """Thin wrapper around a single OpenAI client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
    ):
        cleaned_api_key = self._clean(api_key)
        if not cleaned_api_key:
            raise RuntimeError("Missing OpenAI API key. Set `OPENAI_API_KEY` in the environment or Streamlit secrets.")

        cleaned_base_url = self._clean(base_url)
        provider = _Provider(api_key=cleaned_api_key, base_url=cleaned_base_url)
        self._providers = [provider]
        self.api_key = provider.api_key
        self.base_url = provider.base_url
        self.default_chat_model = self._clean(default_chat_model) or DEFAULT_CHAT_MODEL
        self.default_embedding_model = (
            self._clean(default_embedding_model) or DEFAULT_EMBEDDING_MODEL
        )
        self._clients: dict[tuple[str, str | None], OpenAI] = {}

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _get_live_client(self, provider: _Provider) -> OpenAI:
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK not installed. Run `pip install openai`.")
        client_key = (provider.api_key, provider.base_url)
        client = self._clients.get(client_key)
        if not client:
            client = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
            self._clients[client_key] = client
        return client

    @property
    def client(self) -> OpenAI:
        return self._get_live_client(self._providers[0])

    def chat(self, messages: list[dict[str, str]], model: str | None = None, **kwargs) -> Any:
        """Call the OpenAI chat endpoint."""
        provider = self._providers[0]
        chosen_model = provider.chat_model_override or model or self.default_chat_model
        return self.client.chat.completions.create(messages=messages, model=chosen_model, **kwargs)

    def embeddings(self, inputs, model: str | None = None, **kwargs) -> Any:
        """Call the OpenAI embeddings endpoint."""
        chosen_model = model or self.default_embedding_model
        return self.client.embeddings.create(input=inputs, model=chosen_model, **kwargs)

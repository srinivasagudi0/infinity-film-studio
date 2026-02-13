"""Central OpenAI client wrapper with demo fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None

DEFAULT_CHAT_MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class _DemoChat:
    """Lightweight demo stub that mimics `chat.completions.create`."""

    def __init__(self, message: str):
        self.completions = _DemoCompletions(message)


class _DemoCompletions:
    """Imitates the `create(...)` callable under `chat.completions`."""

    def __init__(self, message: str):
        self._message = message

    def create(self, *_args, **_kwargs):
        return {
            "choices": [{"message": {"role": "assistant", "content": self._message}}],
            "model": "demo-fallback",
        }


class _DemoEmbeddings:
    """Demo stub for embeddings."""

    def __init__(self, vector_len: int = 8):
        self._vector_len = vector_len

    def create(self, input, model: str, **_kwargs):
        # Produce deterministic zero vectors per input item.
        inputs = input if isinstance(input, list) else [input]
        return {
            "data": [
                {"embedding": [0.0] * self._vector_len, "index": idx}
                for idx, _ in enumerate(inputs)
            ],
            "model": model,
        }


class _DemoClient:
    """Aggregates demo endpoints to resemble the OpenAI client."""

    def __init__(self, message: str):
        self.chat = _DemoChat(message)
        self.embeddings = _DemoEmbeddings()


@dataclass(frozen=True)
class _Provider:
    """Provider configuration for a single OpenAI-compatible endpoint."""

    api_key: str
    base_url: str | None = None
    chat_model_override: str | None = None


class OpenAIClient:
    """Thin wrapper around OpenAI-compatible providers with demo mode."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        fallback_configs: Sequence[Dict[str, str | None]] | None = None,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
    ):
        self._providers = self._build_providers(api_key, base_url, fallback_configs)
        self.api_key = self._providers[0].api_key if self._providers else None
        self.base_url = self._providers[0].base_url if self._providers else base_url
        self.default_chat_model = self._clean(default_chat_model) or DEFAULT_CHAT_MODEL
        self.default_embedding_model = (
            self._clean(default_embedding_model) or DEFAULT_EMBEDDING_MODEL
        )
        self._clients: Dict[tuple[str, str | None], OpenAI] = {}
        self._demo_client: Optional[_DemoClient] = None

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _build_providers(
        self,
        api_key: str | None,
        base_url: str | None,
        fallback_configs: Sequence[Dict[str, str | None]] | None,
    ) -> List[_Provider]:
        providers: list[_Provider] = []
        seen: set[tuple[str, str | None, str | None]] = set()

        primary_key = self._clean(api_key)
        if primary_key:
            primary_base = self._clean(base_url)
            provider = _Provider(api_key=primary_key, base_url=primary_base)
            providers.append(provider)
            seen.add((provider.api_key, provider.base_url, provider.chat_model_override))

        for cfg in fallback_configs or []:
            fallback_key = self._clean(cfg.get("api_key"))
            if not fallback_key:
                continue
            fallback_base = self._clean(cfg.get("base_url"))
            fallback_model = self._clean(cfg.get("chat_model_override"))
            provider = _Provider(
                api_key=fallback_key,
                base_url=fallback_base,
                chat_model_override=fallback_model,
            )
            marker = (provider.api_key, provider.base_url, provider.chat_model_override)
            if marker in seen:
                continue
            providers.append(provider)
            seen.add(marker)

        return providers

    def _get_demo_client(self) -> _DemoClient:
        if not self._demo_client:
            self._demo_client = _DemoClient("AI unavailable: set OPENAI_API_KEY for live responses.")
        return self._demo_client

    def _get_live_client(self, provider: _Provider) -> OpenAI:
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK not installed. Run `pip install openai`.")
        client_key = (provider.api_key, provider.base_url)
        client = self._clients.get(client_key)
        if not client:
            client = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
            self._clients[client_key] = client
        return client

    def _promote_provider(self, idx: int) -> None:
        if idx <= 0:
            return
        provider = self._providers.pop(idx)
        self._providers.insert(0, provider)
        self.api_key = self._providers[0].api_key
        self.base_url = self._providers[0].base_url

    def _call_with_fallback(self, call: Callable[[Any, _Provider], Any]) -> Any:
        if not self._providers:
            return call(self._get_demo_client(), _Provider(api_key="", base_url=None))

        last_error: Exception | None = None
        for idx, provider in enumerate(self._providers):
            try:
                client = self._get_live_client(provider)
                response = call(client, provider)
                self._promote_provider(idx)
                return response
            except Exception as exc:  # pragma: no cover - runtime path
                last_error = exc
                continue

        if last_error:
            raise last_error
        return call(self._get_demo_client(), _Provider(api_key="", base_url=None))

    @property
    def client(self) -> OpenAI | _DemoClient:
        if not self._providers:
            return self._get_demo_client()
        return self._get_live_client(self._providers[0])

    def chat(self, messages: List[Dict[str, str]], model: str | None = None, **kwargs) -> Any:
        """Call provider chat endpoint with ordered API-key fallback."""

        def _chat_call(client: Any, provider: _Provider) -> Any:
            chosen_model = provider.chat_model_override or model or self.default_chat_model
            return client.chat.completions.create(messages=messages, model=chosen_model, **kwargs)

        return self._call_with_fallback(_chat_call)

    def embeddings(self, inputs, model: str | None = None, **kwargs) -> Any:
        """Call provider embeddings endpoint with ordered API-key fallback."""

        def _embedding_call(client: Any, _provider: _Provider) -> Any:
            chosen_model = model or self.default_embedding_model
            return client.embeddings.create(input=inputs, model=chosen_model, **kwargs)

        return self._call_with_fallback(_embedding_call)


# EOF end of file

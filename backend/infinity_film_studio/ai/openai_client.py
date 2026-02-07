"""Central OpenAI client wrapper with demo fallbacks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None


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


class OpenAIClient:
    """Thin wrapper around the OpenAI Python SDK with demo mode."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client: Optional[OpenAI | _DemoClient] = None

    @property
    def client(self) -> OpenAI | _DemoClient:
        if not self._client:
            if self.api_key:
                if OpenAI is None:
                    raise RuntimeError("OpenAI SDK not installed. Run `pip install openai`.")
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                # Demo mode: deterministic stub to keep app usable without creds.
                self._client = _DemoClient(
                    "AI unavailable: set OPENAI_API_KEY for live responses."
                )
        return self._client

    def chat(self, messages: List[Dict[str, str]], model: str = "gpt-4.1-mini", **kwargs) -> Any:
        """Call OpenAI chat/completions with provided messages or demo fallback."""
        return self.client.chat.completions.create(messages=messages, model=model, **kwargs)

    def embeddings(self, inputs, model: str = "text-embedding-3-small", **kwargs) -> Any:
        """Call OpenAI embeddings endpoint or return demo zero vectors."""
        return self.client.embeddings.create(input=inputs, model=model, **kwargs)


# EOF end of file

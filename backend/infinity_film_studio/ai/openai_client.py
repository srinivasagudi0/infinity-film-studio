"""Central OpenAI client wrapper."""

from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None


class OpenAIClient:
    """Thin wrapper around the OpenAI Python SDK."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if not self._client:
            if OpenAI is None:
                raise RuntimeError("OpenAI SDK not installed. Run `pip install openai`.")
            if not self.api_key:
                raise RuntimeError("OpenAI API key is missing; set OPENAI_API_KEY.")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(self, messages: List[Dict[str, str]], model: str = "gpt-4.1-mini", **kwargs) -> Any:
        """Call OpenAI chat/completions with provided messages."""
        return self.client.chat.completions.create(messages=messages, model=model, **kwargs)

    def embeddings(self, inputs, model: str = "text-embedding-3-small", **kwargs) -> Any:
        """Call OpenAI embeddings endpoint."""
        return self.client.embeddings.create(input=inputs, model=model, **kwargs)


# EOF end of file
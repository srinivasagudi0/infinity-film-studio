"""Backend dependency wiring.

This returns a simple dictionary with the shared runtime objects.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency at runtime
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Support both package imports and direct script execution (e.g., `streamlit run`).
try:  # pragma: no cover - exercised in runtime environments
    from .ai.openai_client import OpenAIClient
except ImportError:  # pragma: no cover
    import sys

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from infinity_film_studio.ai.openai_client import OpenAIClient

# Ensure local `.env` values are available when running via Streamlit/CLI.
if load_dotenv is not None:  # pragma: no branch
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


DEFAULT_CHAT_MODEL = "gpt-4.1-mini"


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _required_openai_api_key() -> str:
    api_key = _read_env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key configured. Set `OPENAI_API_KEY` in the environment or Streamlit secrets."
        )
    return api_key


def create_app() -> dict[str, Any]:
    """Create the backend dependency container."""
    default_chat_model = _read_env("OPENAI_DEFAULT_CHAT_MODEL") or DEFAULT_CHAT_MODEL
    api_key = _required_openai_api_key()
    base_url = _read_env("OPENAI_BASE_URL")

    return {
        "ai_client": OpenAIClient(
            api_key=api_key,
            base_url=base_url,
            default_chat_model=default_chat_model,
        ),
        "prompts": {},
        "controllers": {
            "script": {},
            "video": {},
            "storyboard": {},
        },
    }

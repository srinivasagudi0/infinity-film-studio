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


DEFAULT_HACKCLUB_BASE = "https://ai.hackclub.com/proxy/v1"
DEFAULT_CHAT_MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"
DEFAULT_OPENAI_FALLBACK_MODEL = "gpt-4.1-mini"


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _is_hackclub(api_key: str | None, base_url: str | None) -> bool:
    return bool(
        (api_key and api_key.startswith("sk-hc-"))
        or (base_url and "hackclub.com" in base_url.lower())
    )


def _is_openai(api_key: str | None, base_url: str | None) -> bool:
    if _is_hackclub(api_key, base_url):
        return False
    if base_url:
        return "openai.com" in base_url.lower()
    return bool(api_key and api_key.startswith("sk-"))


def _resolve_base_url(api_key: str | None, base_url: str | None) -> str | None:
    if base_url:
        return base_url
    if api_key and api_key.startswith("sk-hc-"):
        return DEFAULT_HACKCLUB_BASE
    return None


def _build_provider_chain(
    default_chat_model: str,
    default_openai_fallback_model: str,
) -> list[dict[str, str | None]]:
    providers: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    def add_provider(
        api_key: str | None,
        base_url: str | None,
        chat_model_override: str | None = None,
    ) -> None:
        if not api_key:
            return

        resolved_base_url = _resolve_base_url(api_key, base_url)
        resolved_model = chat_model_override
        if not resolved_model and _is_openai(api_key, resolved_base_url):
            model_lower = default_chat_model.lower()
            if model_lower.startswith("google/") or "gemini" in model_lower:
                resolved_model = default_openai_fallback_model

        provider = {
            "api_key": api_key,
            "base_url": resolved_base_url,
            "chat_model_override": resolved_model,
        }
        marker = (
            provider["api_key"] or "",
            provider["base_url"],
            provider["chat_model_override"],
        )
        if marker in seen:
            return
        providers.append(provider)
        seen.add(marker)

    add_provider(
        _read_env("OPENAI_API_KEY"),
        _read_env("OPENAI_BASE_URL"),
    )
    add_provider(
        _read_env("OPENAI_API_KEY_FALLBACK"),
        _read_env("OPENAI_BASE_URL_FALLBACK"),
        _read_env("OPENAI_MODEL_FALLBACK"),
    )

    prefix = "OPENAI_API_KEY_FALLBACK_"
    indexed_slots = sorted(
        int(name[len(prefix) :])
        for name in os.environ
        if name.startswith(prefix) and name[len(prefix) :].isdigit()
    )
    for slot in indexed_slots:
        idx = str(slot)
        add_provider(
            _read_env(f"{prefix}{idx}"),
            _read_env(f"OPENAI_BASE_URL_FALLBACK_{idx}"),
            _read_env(f"OPENAI_MODEL_FALLBACK_{idx}"),
        )

    hackclub: list[dict[str, str | None]] = []
    openai: list[dict[str, str | None]] = []
    other: list[dict[str, str | None]] = []
    for provider in providers:
        api_key = provider["api_key"]
        base_url = provider["base_url"]
        if _is_hackclub(api_key, base_url):
            hackclub.append(provider)
        elif _is_openai(api_key, base_url):
            openai.append(provider)
        else:
            other.append(provider)
    return hackclub + openai + other


def create_app() -> dict[str, Any]:
    """Create the backend dependency container."""
    default_chat_model = _read_env("OPENAI_DEFAULT_CHAT_MODEL") or DEFAULT_CHAT_MODEL
    default_openai_fallback_model = (
        _read_env("OPENAI_FALLBACK_OPENAI_MODEL") or DEFAULT_OPENAI_FALLBACK_MODEL
    )
    provider_chain = _build_provider_chain(
        default_chat_model=default_chat_model,
        default_openai_fallback_model=default_openai_fallback_model,
    )

    primary = provider_chain[0] if provider_chain else {}
    fallback_configs = provider_chain[1:] if len(provider_chain) > 1 else []

    return {
        "ai_client": OpenAIClient(
            api_key=primary.get("api_key"),
            base_url=primary.get("base_url"),
            fallback_configs=fallback_configs,
            default_chat_model=default_chat_model,
        ),
        "prompts": {},
        "controllers": {
            "script": {},
            "video": {},
            "storyboard": {},
        },
    }

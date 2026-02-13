"""Backend application factory.

This repo currently uses a lightweight "service container" style factory that
returns a dictionary of dependencies/controllers. The FastAPI web layer can be
added on top of this without changing core wiring.
"""

from __future__ import annotations

import os
from typing import Any, Dict

# Support both package imports and direct script execution (e.g., `streamlit run`).
try:  # pragma: no cover - exercised in runtime environments
    from .ai.openai_client import OpenAIClient
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from infinity_film_studio.ai.openai_client import OpenAIClient


def create_app() -> Dict[str, Any]:
    """Create the backend dependency container."""

    def _read_env(name: str) -> str | None:
        value = os.getenv(name)
        if value is None:
            return None
        value = value.strip()
        return value or None

    def _collect_fallback_configs() -> list[dict[str, str | None]]:
        configs: list[dict[str, str | None]] = []

        # Backwards-compatible single fallback slot.
        legacy_key = _read_env("OPENAI_API_KEY_FALLBACK")
        if legacy_key:
            configs.append(
                {
                    "api_key": legacy_key,
                    "base_url": _read_env("OPENAI_BASE_URL_FALLBACK"),
                    "chat_model_override": _read_env("OPENAI_MODEL_FALLBACK"),
                }
            )

        # Ordered fallback chain: OPENAI_API_KEY_FALLBACK_1, _2, ...
        prefix = "OPENAI_API_KEY_FALLBACK_"
        indexed_names = sorted(
            (
                name
                for name in os.environ
                if name.startswith(prefix) and name[len(prefix) :].isdigit()
            ),
            key=lambda name: int(name[len(prefix) :]),
        )
        for name in indexed_names:
            idx = name[len(prefix) :]
            key_value = _read_env(name)
            if not key_value:
                continue
            configs.append(
                {
                    "api_key": key_value,
                    "base_url": _read_env(f"OPENAI_BASE_URL_FALLBACK_{idx}"),
                    "chat_model_override": _read_env(f"OPENAI_MODEL_FALLBACK_{idx}"),
                }
            )

        return configs

    api_key = _read_env("OPENAI_API_KEY")
    base_url = _read_env("OPENAI_BASE_URL")
    fallback_configs = _collect_fallback_configs()

    return {
        "ai_client": OpenAIClient(
            api_key=api_key,
            base_url=base_url,
            fallback_configs=fallback_configs,
        ),
        "prompts": {},
        "controllers": {
            "script": {},
            "video": {},
            "storyboard": {},
        },
    }

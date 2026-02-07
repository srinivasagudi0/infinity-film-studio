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

    api_key = os.getenv("OPENAI_API_KEY") or None
    base_url = os.getenv("OPENAI_BASE_URL") or None

    return {
        "ai_client": OpenAIClient(api_key=api_key, base_url=base_url),
        "prompts": {},
        "controllers": {
            "script": {},
            "video": {},
            "storyboard": {},
        },
    }

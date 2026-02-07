"""Lightweight Streamlit demo that works with or without an OpenAI key."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Ensure backend package is importable when running `streamlit run streamlit_app.py`.
ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from infinity_film_studio.app import create_app  # noqa: E402


def _extract_content(resp: Any) -> str:
    """Handle both demo dict responses and SDK objects."""
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        try:
            return resp.choices[0].message["content"]  # type: ignore[attr-defined]
        except Exception:
            return str(resp)


def main() -> None:
    st.set_page_config(page_title="Infinity Film Studio Demo", page_icon="🎬", layout="centered")
    st.title("Infinity Film Studio – Demo")

    app = create_app()
    ai_client = app["ai_client"]

    demo_mode = getattr(ai_client, "api_key", None) in (None, "")
    if demo_mode:
        st.info("Running in demo mode (no OPENAI_API_KEY provided). Responses are stubbed.")
    else:
        st.success("Live mode: OPENAI_API_KEY detected.")

    prompt = st.text_area(
        "Script idea or scene context",
        "A tense corridor chase in a neon-lit city.",
        height=120,
    )

    if st.button("Generate suggestion", type="primary"):
        with st.spinner("Thinking..."):
            resp = ai_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4.1-mini",
            )
        st.subheader("Suggestion")
        st.write(_extract_content(resp))

    st.divider()
    st.caption(
        "Tip: set OPENAI_API_KEY in your environment to switch from demo fallbacks to live model outputs."
    )


if __name__ == "__main__":
    main()

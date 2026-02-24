"""Main Streamlit UI for Infinity Film Studio.

Two runtime modes are supported:
- Live mode calls the configured API provider chain.
- Demo mode returns deterministic offline output.
"""

from __future__ import annotations

import html
import csv
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence

import streamlit as st

try:  # pragma: no cover - optional dependency at runtime
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Ensure backend package is importable when running `streamlit run streamlit_app.py`.
ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if load_dotenv is not None:  # pragma: no branch
    load_dotenv(ROOT / ".env", override=False)

SECRET_ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_DEFAULT_CHAT_MODEL",
    "OPENAI_API_KEY_FALLBACK",
    "OPENAI_BASE_URL_FALLBACK",
    "OPENAI_MODEL_FALLBACK",
    "OPENAI_FALLBACK_OPENAI_MODEL",
)


def _hydrate_env_from_streamlit_secrets() -> None:
    """Load OpenAI config from Streamlit Secrets into env when not already set."""
    try:
        secrets_obj = st.secrets
    except Exception:
        return

    try:
        secrets = secrets_obj.to_dict()  # type: ignore[attr-defined]
    except Exception:
        try:
            secrets = dict(secrets_obj)
        except Exception:
            return

    openai_block = secrets.get("openai")
    if isinstance(openai_block, dict):
        mapping = {
            "api_key": "OPENAI_API_KEY",
            "base_url": "OPENAI_BASE_URL",
            "default_chat_model": "OPENAI_DEFAULT_CHAT_MODEL",
            "fallback_openai_model": "OPENAI_FALLBACK_OPENAI_MODEL",
        }
        for secret_key, env_key in mapping.items():
            value = openai_block.get(secret_key)
            if isinstance(value, str) and value.strip() and not os.getenv(env_key):
                os.environ[env_key] = value.strip()

    for key in SECRET_ENV_KEYS:
        value = secrets.get(key)
        if isinstance(value, str) and value.strip() and not os.getenv(key):
            os.environ[key] = value.strip()

    # Allow indexed fallback keys in secrets without enumerating every slot.
    for key, value in secrets.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            continue
        if key.startswith(
            ("OPENAI_API_KEY_FALLBACK_", "OPENAI_BASE_URL_FALLBACK_", "OPENAI_MODEL_FALLBACK_")
        ) and not os.getenv(key):
            os.environ[key] = value.strip()


_hydrate_env_from_streamlit_secrets()

from infinity_film_studio.app import create_app  # noqa: E402

GENRES = ["Sci-Fi", "Thriller", "Drama", "Mystery", "Action", "Comedy"]
TONES = ["Hopeful", "Dark", "Bittersweet", "Urgent", "Whimsical"]
CAMERA_STYLES = [
    "Handheld energy",
    "Steady cinematic",
    "Slow dolly",
    "Wide tableau",
    "Tight intimate closeups",
]
PALETTES = [
    "Neon cyan + amber",
    "Muted earth + steel",
    "Cold blue + white",
    "Warm tungsten + shadow",
    "High contrast monochrome",
]
ISSUE_FLAGS = [
    "Dialogue muddy",
    "Too slow in middle",
    "Looks flat",
    "Confusing geography",
    "Weak ending impact",
]
FOCUS_AREAS = [
    "Character emotion",
    "World-building",
    "Action choreography",
    "Mystery tension",
    "Dialogue rhythm",
]
CONCEPT_SEEDS = [
    "A rescue pilot returns to a city that no longer remembers her.",
    "An aging stunt coordinator trains a teenage genius in secret.",
    "A floating market hides a blackmail ring run by retired actors.",
    "Three siblings race one night to recover a missing reel of film.",
    "A climate lab intern discovers weather can be scored like music.",
]
STYLE_PRESETS = [
    {
        "name": "Neon Pursuit",
        "genre": "Sci-Fi",
        "tone": "Urgent",
        "camera_style": "Steady cinematic",
        "palette": "Neon cyan + amber",
        "energy": 74,
        "pace": 66,
        "focus": "Action choreography",
        "tagline": "Electric city tension with precision camera language.",
    },
    {
        "name": "Quiet Fracture",
        "genre": "Drama",
        "tone": "Bittersweet",
        "camera_style": "Tight intimate closeups",
        "palette": "Muted earth + steel",
        "energy": 52,
        "pace": 41,
        "focus": "Character emotion",
        "tagline": "Controlled emotion and close-frame vulnerability.",
    },
    {
        "name": "Stormline Protocol",
        "genre": "Thriller",
        "tone": "Dark",
        "camera_style": "Handheld energy",
        "palette": "Cold blue + white",
        "energy": 81,
        "pace": 72,
        "focus": "Mystery tension",
        "tagline": "High-pressure movement with escalating uncertainty.",
    },
    {
        "name": "Golden Rebuild",
        "genre": "Action",
        "tone": "Hopeful",
        "camera_style": "Slow dolly",
        "palette": "Warm tungsten + shadow",
        "energy": 67,
        "pace": 58,
        "focus": "World-building",
        "tagline": "Forward momentum with warm cinematic lift.",
    },
]

DEFAULT_CHAT_MODEL = os.getenv(
    "OPENAI_DEFAULT_CHAT_MODEL",
    "google/gemini-2.5-flash-lite-preview-09-2025",
)


@st.cache_resource
def _get_ai_client() -> Any:
    app = create_app()
    return app["ai_client"]


def _extract_content(resp: Any) -> str:
    """Handle both demo dict responses and SDK objects."""
    def _normalize(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text") or item.get("content")
                    if isinstance(text_value, str):
                        parts.append(text_value)
                else:
                    text_value = getattr(item, "text", None) or getattr(item, "content", None)
                    if isinstance(text_value, str):
                        parts.append(text_value)
            if parts:
                return "\n".join(parts).strip()
        return str(content)

    try:
        return _normalize(resp["choices"][0]["message"]["content"])
    except Exception:
        pass

    try:
        return _normalize(resp.choices[0].message.content)  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        message = resp.choices[0].message  # type: ignore[attr-defined]
        if isinstance(message, dict):
            return _normalize(message.get("content", ""))
    except Exception:
        pass

    return str(resp)


def _seed_for(*parts: str) -> int:
    key = "|".join(parts).strip().lower()
    return abs(hash(key)) % (2**31)


def _short_seed(seed: str) -> str:
    words = seed.replace(".", "").split()
    return " ".join(words[:4]) + "..."


def _provider_name(api_key: str | None, base_url: str | None) -> str:
    base = (base_url or "").lower()
    if (api_key and api_key.startswith("sk-hc-")) or ("hackclub.com" in base):
        return "Hack Club"
    if "openai.com" in base or (api_key and api_key.startswith("sk-")):
        return "OpenAI"
    return "Custom"


def _provider_chain_text(ai_client: Any) -> str:
    providers = getattr(ai_client, "_providers", None) or []
    if not providers:
        return "Offline"
    names = [_provider_name(getattr(p, "api_key", None), getattr(p, "base_url", None)) for p in providers]
    return " -> ".join(names + ["Offline"])


def _rerun() -> None:
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def _init_state() -> None:
    defaults = {
        "ifs_project_title": "Neon Corridor",
        "ifs_genre": GENRES[0],
        "ifs_tone": TONES[3],
        "ifs_camera_style": CAMERA_STYLES[1],
        "ifs_palette": PALETTES[0],
        "ifs_focus": FOCUS_AREAS[0],
        "ifs_energy": 68,
        "ifs_pace": 57,
        "ifs_concept_idx": 0,
        "ifs_model": DEFAULT_CHAT_MODEL,
        "ifs_temperature": 0.72,
        "ifs_frame_count": 6,
        "ifs_script_prompt": CONCEPT_SEEDS[0],
        "ifs_story_prompt": "The protagonist commits to the plan while alarms start rising.",
        "ifs_edit_objective": "narrative clarity and emotional punch",
        "ifs_rough_cut_notes": "",
        "ifs_rough_cut_question": "Where does pacing drop and what should I cut first?",
        "ifs_clip_duration_guess_seconds": 90,
        "ifs_cut_segment_seconds": 20,
        "ifs_script_output": "",
        "ifs_storyboard_output": "",
        "ifs_edit_output": "",
        "ifs_rough_cut_output": "",
        "ifs_rough_cut_timeline_rows": [],
        "ifs_rough_cut_timeline_csv": "",
        "ifs_rough_cut_timeline_json": "",
        "ifs_rough_cut_metadata": {},
        "ifs_deck_output": "",
        "ifs_history": [],
        "ifs_preset": STYLE_PRESETS[0]["name"],
        "ifs_status_line": "Ready.",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        .stApp {
            font-family: 'Manrope', 'Segoe UI', sans-serif;
            color: #eef4ff;
            background:
                radial-gradient(circle at 12% 18%, rgba(42, 201, 182, 0.24), transparent 40%),
                radial-gradient(circle at 88% 10%, rgba(255, 127, 84, 0.18), transparent 30%),
                radial-gradient(circle at 60% 65%, rgba(118, 106, 255, 0.14), transparent 36%),
                linear-gradient(150deg, #060f24 0%, #0a1733 46%, #111f45 100%);
            background-size: 170% 170%;
            animation: ifs-bg-shift 22s ease infinite;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.22;
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
            background-size: 26px 26px;
            mask-image: radial-gradient(circle at 50% 12%, black 38%, transparent 92%);
            z-index: 0;
        }

        header[data-testid="stHeader"] {
            display: none;
        }

        [data-testid="stToolbar"] {
            display: none;
        }

        [data-testid="stAppViewContainer"] {
            margin-top: 0;
        }

        @keyframes ifs-bg-shift {
            0% { background-position: 0% 20%; }
            50% { background-position: 100% 80%; }
            100% { background-position: 0% 20%; }
        }

        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, rgba(7, 19, 45, 0.98) 0%, rgba(10, 26, 60, 0.98) 100%);
            border-right: 1px solid rgba(171, 196, 255, 0.24);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 0.35rem;
            padding-bottom: 2.6rem;
        }

        .hero-card,
        .brief-card,
        .status-card {
            border-radius: 20px;
            border: 1px solid rgba(151, 178, 241, 0.28);
            background:
                linear-gradient(145deg, rgba(16, 34, 72, 0.86), rgba(8, 18, 40, 0.92)),
                radial-gradient(circle at 90% 8%, rgba(255, 153, 110, 0.2), transparent 35%);
            box-shadow:
                0 16px 40px rgba(3, 8, 22, 0.45),
                inset 0 1px 0 rgba(255, 255, 255, 0.09);
        }

        .hero-card {
            padding: 1.2rem 1.25rem;
            margin-bottom: 0.65rem;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.3fr 0.9fr;
            gap: 0.9rem;
            align-items: stretch;
        }

        .hero-stack {
            display: flex;
            flex-direction: column;
            gap: 0.68rem;
        }

        .hero-title {
            margin: 0.38rem 0 0;
            font-family: 'Space Grotesk', 'Manrope', sans-serif;
            font-size: 1.7rem;
            line-height: 1.1;
            color: #f5f9ff;
        }

        .hero-sub {
            margin: 0.65rem 0 0;
            color: rgba(226, 237, 255, 0.9);
            font-size: 1rem;
        }

        .hero-meta {
            margin-top: 0.75rem;
            color: rgba(215, 229, 255, 0.8);
            font-size: 0.86rem;
            letter-spacing: 0.015em;
        }

        .mode-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 0.2rem 0.7rem;
            font-size: 0.78rem;
            letter-spacing: 0.03em;
            border: 1px solid rgba(188, 211, 255, 0.38);
            background: rgba(140, 167, 227, 0.2);
            color: #ebf2ff;
        }

        .mode-pill.live {
            border-color: rgba(89, 233, 201, 0.72);
            background: rgba(44, 201, 171, 0.25);
            color: #dcfff4;
        }

        .mode-pill.demo {
            border-color: rgba(255, 179, 131, 0.68);
            background: rgba(255, 134, 94, 0.2);
            color: #ffe9df;
        }

        .brief-card {
            padding: 1rem 1.1rem;
            min-height: 160px;
            margin-bottom: 0.65rem;
        }

        .callsheet-card {
            border-radius: 18px;
            border: 1px solid rgba(164, 188, 245, 0.24);
            background:
                linear-gradient(150deg, rgba(11, 23, 49, 0.82), rgba(8, 16, 34, 0.92)),
                radial-gradient(circle at 20% 10%, rgba(47, 204, 183, 0.14), transparent 36%);
            padding: 0.9rem 0.95rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
        }

        .callsheet-kicker {
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: rgba(174, 201, 255, 0.78);
            font-size: 0.72rem;
            margin: 0;
        }

        .callsheet-title {
            margin: 0.22rem 0 0;
            font-family: 'Space Grotesk', 'Manrope', sans-serif;
            font-size: 1rem;
            color: #f6faff;
        }

        .callsheet-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.45rem 0.7rem;
            margin-top: 0.68rem;
        }

        .callsheet-cell {
            border-radius: 12px;
            border: 1px solid rgba(154, 181, 241, 0.16);
            background: rgba(8, 17, 37, 0.48);
            padding: 0.5rem 0.6rem;
        }

        .callsheet-cell span {
            display: block;
            color: rgba(184, 206, 252, 0.74);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }

        .callsheet-cell strong {
            color: #f0f6ff;
            font-size: 0.85rem;
            line-height: 1.3;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 0.15rem;
        }

        .chip {
            border-radius: 999px;
            border: 1px solid rgba(167, 192, 245, 0.2);
            background: rgba(11, 24, 51, 0.56);
            color: rgba(230, 239, 255, 0.9);
            padding: 0.28rem 0.58rem;
            font-size: 0.78rem;
        }

        .brief-card h4 {
            margin: 0;
            font-family: 'Space Grotesk', 'Manrope', sans-serif;
            color: #f5f9ff;
        }

        .brief-card p {
            margin: 0.5rem 0 0;
            color: rgba(223, 234, 255, 0.86);
            line-height: 1.5;
        }

        .status-card {
            padding: 0.68rem 0.9rem;
            margin-top: 0.6rem;
            color: rgba(226, 238, 255, 0.92);
            font-size: 0.92rem;
        }

        [data-testid="stMetricValue"] {
            color: #f9fbff;
            font-weight: 800;
            letter-spacing: -0.01em;
        }

        [data-testid="stMetricLabel"] {
            color: rgba(219, 233, 255, 0.78);
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.45rem;
            margin-top: 0.3rem;
        }

        [data-testid="stTabs"] [role="tab"] {
            border-radius: 999px;
            border: 1px solid rgba(168, 191, 245, 0.25);
            background: rgba(128, 157, 224, 0.14);
            color: #ebf2ff;
            padding: 0.46rem 0.92rem;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            background: rgba(46, 201, 180, 0.23);
            border-color: rgba(98, 236, 207, 0.66);
            color: #f0fffb;
        }

        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-baseweb="select"] > div {
            background: rgba(7, 20, 45, 0.88);
            color: #eff5ff;
            border-color: rgba(165, 190, 246, 0.28);
        }

        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stTextInput"] input:focus {
            border-color: rgba(103, 223, 200, 0.88);
            box-shadow: 0 0 0 1px rgba(103, 223, 200, 0.24);
        }

        [data-testid="stSidebar"] .stMarkdown p {
            color: rgba(221, 235, 255, 0.9);
        }

        .sidebar-note {
            border-radius: 14px;
            border: 1px solid rgba(156, 183, 241, 0.22);
            background: rgba(9, 21, 48, 0.56);
            padding: 0.7rem 0.8rem;
            margin: 0.15rem 0 0.7rem;
            color: rgba(222, 235, 255, 0.92);
            font-size: 0.84rem;
            line-height: 1.45;
        }

        .sidebar-note code {
            color: #f6fbff;
            background: rgba(122, 155, 235, 0.12);
            border-radius: 6px;
            padding: 0.07rem 0.28rem;
        }

        .sidebar-section-title {
            margin: 0.35rem 0 0.25rem;
            font-family: 'Space Grotesk', 'Manrope', sans-serif;
            color: #f4f9ff;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
        }

        [data-testid="stSidebar"] .stButton > button,
        .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(167, 191, 248, 0.3);
            background: linear-gradient(145deg, rgba(33, 52, 92, 0.85), rgba(16, 30, 62, 0.92));
            color: #edf3ff;
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(111, 229, 207, 0.7);
            box-shadow: 0 8px 18px rgba(7, 15, 35, 0.35);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(145deg, rgba(255, 95, 103, 0.95), rgba(255, 74, 106, 0.95));
            border-color: rgba(255, 144, 163, 0.62);
            color: #fff8fb;
        }

        .seed-grid {
            margin: 0.25rem 0 0.35rem;
        }

        .cue-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.55rem;
            margin: 0.65rem 0 0.45rem;
        }

        .cue-card {
            border-radius: 14px;
            border: 1px solid rgba(156, 183, 241, 0.18);
            background:
                linear-gradient(160deg, rgba(12, 24, 51, 0.8), rgba(8, 18, 38, 0.9));
            padding: 0.68rem 0.78rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }

        .cue-kicker {
            color: rgba(178, 202, 252, 0.74);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.68rem;
            margin: 0;
        }

        .cue-value {
            color: #f4f9ff;
            margin-top: 0.24rem;
            font-weight: 700;
            line-height: 1.28;
        }

        .export-row {
            border-top: 1px solid rgba(158, 183, 238, 0.24);
            margin-top: 0.55rem;
            padding-top: 0.55rem;
        }

        .history-item {
            border-radius: 14px;
            border: 1px solid rgba(162, 187, 244, 0.24);
            background: rgba(8, 19, 42, 0.75);
            padding: 0.76rem 0.88rem;
            margin-bottom: 0.6rem;
        }

        .history-item h5 {
            margin: 0;
            color: #f5f8ff;
            font-size: 0.95rem;
        }

        .history-item p {
            margin: 0.3rem 0 0;
            color: rgba(214, 228, 255, 0.82);
            font-size: 0.84rem;
        }

        .mini-label {
            color: rgba(207, 223, 255, 0.75);
            font-size: 0.82rem;
            margin-top: -0.15rem;
            margin-bottom: 0.12rem;
        }

        @media (max-width: 980px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }

            .cue-strip {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 640px) {
            .cue-strip {
                grid-template-columns: 1fr;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .stApp {
                animation: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _preset_by_name(name: str) -> dict[str, Any]:
    for preset in STYLE_PRESETS:
        if preset["name"] == name:
            return preset
    return STYLE_PRESETS[0]


def _apply_preset(name: str) -> None:
    preset = _preset_by_name(name)
    st.session_state["ifs_genre"] = preset["genre"]
    st.session_state["ifs_tone"] = preset["tone"]
    st.session_state["ifs_camera_style"] = preset["camera_style"]
    st.session_state["ifs_palette"] = preset["palette"]
    st.session_state["ifs_energy"] = preset["energy"]
    st.session_state["ifs_pace"] = preset["pace"]
    st.session_state["ifs_focus"] = preset["focus"]
    st.session_state["ifs_status_line"] = f"Applied preset: {preset['name']}"


def _randomize_profile() -> None:
    rng = random.Random()
    st.session_state["ifs_genre"] = rng.choice(GENRES)
    st.session_state["ifs_tone"] = rng.choice(TONES)
    st.session_state["ifs_camera_style"] = rng.choice(CAMERA_STYLES)
    st.session_state["ifs_palette"] = rng.choice(PALETTES)
    st.session_state["ifs_focus"] = rng.choice(FOCUS_AREAS)
    st.session_state["ifs_energy"] = rng.randint(35, 90)
    st.session_state["ifs_pace"] = rng.randint(30, 85)
    st.session_state["ifs_status_line"] = "Profile randomized for a fresh direction."


def _rotate_value(values: Sequence[str], current: str) -> str:
    if current not in values:
        return values[0]
    idx = values.index(current)
    return values[(idx + 1) % len(values)]


def _save_history(kind: str, title: str, content: str) -> None:
    item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "title": title,
        "content": content,
    }
    history = st.session_state["ifs_history"]
    history.insert(0, item)
    del history[14:]


def _build_director_brief() -> str:
    concept = CONCEPT_SEEDS[st.session_state["ifs_concept_idx"]]
    return (
        f"Project '{st.session_state['ifs_project_title']}' follows this premise: {concept} "
        f"The style profile is {st.session_state['ifs_tone'].lower()} {st.session_state['ifs_genre'].lower()} "
        f"with {st.session_state['ifs_camera_style'].lower()} framing and {st.session_state['ifs_palette'].lower()} palette. "
        f"Focus area is {st.session_state['ifs_focus'].lower()}, with energy {st.session_state['ifs_energy']}/100 "
        f"and pace {st.session_state['ifs_pace']}/100."
    )


def _compute_scores() -> dict[str, int]:
    energy = int(st.session_state["ifs_energy"])
    pace = int(st.session_state["ifs_pace"])
    balance = max(0, 100 - abs(energy - pace))

    creative_score = min(99, int(energy * 0.52 + pace * 0.31 + balance * 0.17))
    tension = min(99, int(energy * 0.64 + pace * 0.28 + 8))
    clarity = min(99, int(balance * 0.58 + pace * 0.28 + 15))
    visual = min(99, int(energy * 0.35 + 45))
    cohesion = min(99, int(balance * 0.72 + 22))

    return {
        "creative": creative_score,
        "tension": tension,
        "clarity": clarity,
        "visual": visual,
        "cohesion": cohesion,
    }


def _progress(label: str, value: int) -> None:
    st.markdown(f"<p class='mini-label'>{html.escape(label)}: {value}%</p>", unsafe_allow_html=True)
    try:
        st.progress(value / 100.0, text=f"{value}%")
    except TypeError:
        st.progress(value / 100.0)


def _format_timestamp(seconds: float | int | None) -> str:
    if seconds is None:
        return "--:--"
    total = max(0, int(round(float(seconds))))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_timestamp_range(start: float | int, end: float | int) -> str:
    return f"{_format_timestamp(start)}-{_format_timestamp(end)}"


def _format_bytes(num_bytes: int | None) -> str:
    if not num_bytes:
        return "0 B"
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024.0
    return f"{int(num_bytes)} B"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_rate(rate: str | None) -> float | None:
    if not rate:
        return None
    text = str(rate).strip()
    if not text or text in {"0/0", "N/A"}:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        numerator = _safe_float(left)
        denominator = _safe_float(right)
        if numerator is None or denominator in (None, 0.0):
            return None
        return numerator / denominator
    return _safe_float(text)


@st.cache_data(show_spinner=False)
def _probe_video_metadata(file_name: str, video_bytes: bytes) -> dict[str, Any]:
    """Best-effort ffprobe metadata extraction for rough-cut uploads."""
    meta: dict[str, Any] = {
        "file_name": file_name or "rough-cut",
        "file_size_bytes": len(video_bytes or b""),
        "duration_seconds": None,
        "width": None,
        "height": None,
        "fps": None,
        "video_codec": None,
        "audio_codec": None,
        "bitrate_kbps": None,
        "probe_status": "unavailable",
    }
    if not video_bytes:
        return meta

    suffix = Path(file_name or "clip.mp4").suffix or ".mp4"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(video_bytes)
            temp_path = Path(tmp.name)

        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-print_format",
                "json",
                str(temp_path),
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            meta["probe_status"] = "ffprobe_failed"
            return meta

        payload = json.loads(proc.stdout or "{}")
        streams = payload.get("streams") or []
        format_block = payload.get("format") or {}
        video_stream = next(
            (s for s in streams if str(s.get("codec_type", "")).lower() == "video"),
            None,
        )
        audio_stream = next(
            (s for s in streams if str(s.get("codec_type", "")).lower() == "audio"),
            None,
        )

        duration = _safe_float(format_block.get("duration"))
        if duration is None and video_stream:
            duration = _safe_float(video_stream.get("duration"))
        if duration is None and audio_stream:
            duration = _safe_float(audio_stream.get("duration"))

        bitrate = _safe_float(format_block.get("bit_rate"))
        if bitrate is None and video_stream:
            bitrate = _safe_float(video_stream.get("bit_rate"))

        meta.update(
            {
                "duration_seconds": duration,
                "width": video_stream.get("width") if video_stream else None,
                "height": video_stream.get("height") if video_stream else None,
                "fps": _parse_rate((video_stream or {}).get("avg_frame_rate")),
                "video_codec": (video_stream or {}).get("codec_name"),
                "audio_codec": (audio_stream or {}).get("codec_name"),
                "bitrate_kbps": int(round(bitrate / 1000.0)) if bitrate else None,
                "probe_status": "ok",
            }
        )
        return meta
    except FileNotFoundError:
        meta["probe_status"] = "ffprobe_not_installed"
        return meta
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        meta["probe_status"] = "ffprobe_failed"
        return meta
    except Exception:
        meta["probe_status"] = "ffprobe_failed"
        return meta
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


def _normalize_clip_duration_seconds(
    metadata: dict[str, Any],
    fallback_seconds: int,
) -> int:
    detected = _safe_float(metadata.get("duration_seconds"))
    if detected and detected > 0:
        return max(4, int(round(detected)))
    return max(4, int(fallback_seconds))


def _build_cut_segments(duration_seconds: int, segment_seconds: int) -> list[dict[str, int]]:
    duration = max(4, int(duration_seconds))
    segment = max(5, int(segment_seconds))

    if duration <= segment:
        return [{"start": 0, "end": duration, "length": duration}]

    segments: list[dict[str, int]] = []
    cursor = 0
    while cursor < duration:
        end = min(duration, cursor + segment)
        segments.append({"start": cursor, "end": end, "length": max(1, end - cursor)})
        cursor = end

    if len(segments) > 1 and segments[-1]["length"] < max(3, segment // 3):
        segments[-2]["end"] = segments[-1]["end"]
        segments[-2]["length"] = segments[-2]["end"] - segments[-2]["start"]
        segments.pop()

    return segments


def _clip_note_snippets(notes: str) -> list[str]:
    snippets: list[str] = []
    for line in notes.replace("\r", "\n").split("\n"):
        cleaned = " ".join(line.strip().split())
        if not cleaned:
            continue
        snippets.append(cleaned[:140])
    return snippets


def _rough_cut_rows_to_csv(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return ""
    fieldnames = [
        "timestamp",
        "priority",
        "focus",
        "issue",
        "observation",
        "action",
        "confidence",
    ]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return out.getvalue()


def _rough_cut_table_markdown(rows: Sequence[dict[str, Any]]) -> str:
    lines = [
        "| Time | Priority | Focus | Issue | Observation | Recommended Cut |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {timestamp} | {priority} | {focus} | {issue} | {observation} | {action} |".format(
                timestamp=str(row.get("timestamp", "")).replace("|", "/"),
                priority=str(row.get("priority", "")).replace("|", "/"),
                focus=str(row.get("focus", "")).replace("|", "/"),
                issue=str(row.get("issue", "")).replace("|", "/"),
                observation=str(row.get("observation", "")).replace("|", "/"),
                action=str(row.get("action", "")).replace("|", "/"),
            )
        )
    return "\n".join(lines)


def _rough_cut_rows_summary(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return "No rough-cut timeline flags."

    priority_counts: dict[str, int] = {}
    issue_counts: dict[str, int] = {}
    for row in rows:
        priority = str(row.get("priority", "Unknown"))
        issue = str(row.get("issue", "General"))
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        issue_counts[issue] = issue_counts.get(issue, 0) + 1

    prio_text = ", ".join(
        f"{name}: {priority_counts.get(name, 0)}" for name in ["High", "Medium", "Low"] if priority_counts.get(name)
    ) or "No priorities"
    issue_text = ", ".join(
        f"{name} ({count})" for name, count in sorted(issue_counts.items(), key=lambda item: (-item[1], item[0]))[:4]
    ) or "No issue clusters"
    first_times = ", ".join(str(row.get("timestamp", "")) for row in rows[:5])
    return f"Priorities -> {prio_text}. Top issue clusters -> {issue_text}. First flagged windows -> {first_times}."


def _fallback_rough_cut_rows(
    *,
    project: str,
    objective: str,
    pacing: str,
    issues: Sequence[str],
    tone: str,
    focus: str,
    energy: int,
    pace: int,
    duration_seconds: int,
    segment_seconds: int,
    notes: str,
    file_name: str,
) -> list[dict[str, Any]]:
    rng = random.Random(
        _seed_for(
            project,
            objective,
            pacing,
            tone,
            focus,
            str(energy),
            str(pace),
            str(duration_seconds),
            str(segment_seconds),
            ",".join(sorted(issues)),
            file_name,
            notes[:240],
        )
    )

    segments = _build_cut_segments(duration_seconds, segment_seconds)
    note_snippets = _clip_note_snippets(notes)
    issue_cycle = list(issues) or [
        "Too slow in middle",
        "Confusing geography",
        "Weak ending impact",
        "Looks flat",
    ]
    focus_cycle = [
        focus,
        "Screen direction",
        "Performance emphasis",
        "Cut motivation",
        "Rhythm continuity",
        "Shot geography",
    ]
    priority_labels = ["Low", "Medium", "High"]

    observation_stems = [
        "energy drops after the setup beat and the cut holds a fraction too long",
        "viewer orientation gets weaker because shot order withholds a reset wide",
        "performance reaction lands late, reducing emotional carry into the next beat",
        "visual information repeats without new story value",
        "audio momentum implies escalation, but picture rhythm stays flat",
        "the cut point lands before the intention reads on screen",
    ]
    action_stems = [
        "trim 8-16 frames and cut on movement initiation",
        "insert or move an orienting wide before the peak beat",
        "hold the reaction 10-14 frames longer, then hard cut to consequence",
        "replace the transition with a straight cut and front-load the next beat",
        "use an L-cut from the next line to pull momentum forward",
        "remove one redundant angle and keep the strongest eyeline match",
    ]

    rows: list[dict[str, Any]] = []
    for idx, segment in enumerate(segments):
        start = segment["start"]
        end = segment["end"]
        issue = issue_cycle[idx % len(issue_cycle)]
        focus_label = focus_cycle[idx % len(focus_cycle)]

        intensity = 0
        if issue in {"Too slow in middle", "Confusing geography", "Weak ending impact"}:
            intensity += 1
        if pacing == "Fast" and segment["length"] >= max(12, segment_seconds):
            intensity += 1
        if idx == len(segments) - 1 and "Weak ending impact" in issue_cycle:
            intensity += 1
        if 35 <= pace <= 55 and idx == len(segments) // 2:
            intensity += 1
        intensity = min(2, intensity + (1 if rng.random() > 0.72 else 0))
        priority = priority_labels[intensity]

        observation = rng.choice(observation_stems)
        action = rng.choice(action_stems)

        if note_snippets:
            source_note = note_snippets[idx % len(note_snippets)]
            observation = f"{observation}; transcript/notes cue: \"{source_note}\""

        rows.append(
            {
                "timestamp": _format_timestamp_range(start, end),
                "priority": priority,
                "focus": focus_label,
                "issue": issue,
                "observation": observation,
                "action": action,
                "confidence": f"{0.58 + (idx % 4) * 0.08:.2f}",
                "start_seconds": start,
                "end_seconds": end,
            }
        )

    return rows


def _fallback_rough_cut_review(
    *,
    project: str,
    objective: str,
    pacing: str,
    runtime_target: int,
    tone: str,
    focus: str,
    energy: int,
    pace: int,
    issues: Sequence[str],
    metadata: dict[str, Any],
    rows: Sequence[dict[str, Any]],
    review_question: str,
) -> str:
    duration_seconds = _normalize_clip_duration_seconds(metadata, 90)
    width = metadata.get("width")
    height = metadata.get("height")
    fps = metadata.get("fps")
    res_text = f"{width}x{height}" if width and height else "Unknown"
    fps_text = f"{fps:.2f}" if isinstance(fps, (float, int)) else "Unknown"
    flagged_high = [row["timestamp"] for row in rows if row.get("priority") == "High"]
    repeated_issues: dict[str, int] = {}
    for row in rows:
        label = str(row.get("issue", "General"))
        repeated_issues[label] = repeated_issues.get(label, 0) + 1
    top_issues = sorted(repeated_issues.items(), key=lambda item: (-item[1], item[0]))[:3]
    issue_summary = ", ".join(f"{name} ({count})" for name, count in top_issues) or "none"

    lines = [
        "### Rough Cut Snapshot",
        f"- Project: {project}",
        f"- Clip file: {metadata.get('file_name', 'rough-cut')}",
        f"- Clip length: {_format_timestamp(duration_seconds)}",
        f"- Resolution / FPS: {res_text} / {fps_text}",
        f"- Tone + focus target: {tone} / {focus}",
        f"- Edit objective: {objective}",
        f"- Review question: {review_question or 'General pacing and clarity pass'}",
        f"- Runtime target context: {runtime_target} min ({pacing.lower()} pacing profile)",
        "",
        "### Timestamped Cut Notes",
        _rough_cut_table_markdown(rows),
        "",
        "### Pattern Diagnosis",
        f"- Most repeated issues: {issue_summary}.",
        f"- Highest-priority zones: {', '.join(flagged_high) if flagged_high else 'No high-priority zones flagged in this pass.'}",
        f"- Rhythm profile suggests {'compression' if pace >= 60 else 'selective expansion'} around the midpoint to protect {objective.lower()}.",
        f"- Energy/Pace balance ({energy}/{pace}) supports {'hard cuts and movement-based transitions' if energy >= 65 else 'clean reaction holds and motivated dissolves'} as the default strategy.",
        "",
        "### First Pass Fix Order",
        "1. Resolve all High priority timestamp flags before color or polish passes.",
        "2. Rebuild geography around the first confusion point using one orienting shot or clearer eyeline progression.",
        "3. Tighten dead air inside repeated setup beats, then re-check emotional readability.",
        "4. Rewatch without audio once to validate visual continuity and story comprehension.",
        "5. Rewatch audio-only to catch dialogue clarity dips and L-cut opportunities.",
    ]
    return "\n".join(lines)


def _fallback_script_pack(
    project: str,
    concept: str,
    genre: str,
    tone: str,
    energy: int,
    pace: int,
    focus: str,
) -> str:
    rng = random.Random(_seed_for(project, concept, genre, tone, str(energy), str(pace), focus))
    pivots = [
        "a leaked recording",
        "a missing memory shard",
        "an impossible production deadline",
        "a false ally in the control room",
        "a public broadcast that cannot be stopped",
    ]
    costs = ["trust", "time", "credibility", "the backup plan", "the final safe route"]
    pivot = rng.choice(pivots)
    cost = rng.choice(costs)

    logline = (
        f"A {tone.lower()} {genre.lower()} film where the core team must turn '{concept}' "
        f"into a successful mission before dawn, while {pivot} threatens to derail everything."
    )

    beats = [
        "Opening image: establish world state and emotional weather in one frame.",
        "Setup: define objective, urgency, and personal stakes.",
        "Catalyst: a disruption forces immediate commitment.",
        f"Debate: strategy splits when {pivot} surfaces.",
        "Break into action: the bold plan moves into execution.",
        f"Midpoint: partial win reframes the mission and costs {cost}.",
        "All is lost: the central strategy fails in public view.",
        "Finale: rebuild from truth, take the final risk, and resolve the arc.",
    ]

    excerpt = textwrap.dedent(
        f"""
        INT. IMPROVISED STUDIO FLOOR - NIGHT

        The room is lit by emergency strips and old monitor glow.

        LEAD CREATOR
        We have one shot. If this sequence fails, the whole project dies here.

        PRODUCER
        Then we stop waiting for perfect and start executing.

        The feed stutters, then stabilizes. Everyone locks in.

        LEAD CREATOR
        Rolling. No second takes.

        A silent beat. Then the first alarm starts.

        Focus target: {focus}. Tone target: {tone}.
        Energy target: {energy}/100. Pace target: {pace}/100.
        """
    ).strip()

    notes = [
        f"Open with a high-intensity visual to match energy {energy}/100.",
        f"Cut rhythm should feel {'urgent' if pace >= 60 else 'measured'} for pace {pace}/100.",
        f"Make '{focus}' explicit in at least two story beats.",
        "Reserve one line of quiet dialogue right before the final push.",
    ]

    result = ["### Logline", logline, "", "### 8-Beat Outline"]
    result.extend([f"{idx}. {beat}" for idx, beat in enumerate(beats, 1)])
    result.extend(["", "### Scene Excerpt", f"```text\n{excerpt}\n```", "", "### Director Notes"])
    result.extend([f"- {note}" for note in notes])
    return "\n".join(result)


def _fallback_storyboard(
    scene: str,
    style: str,
    palette: str,
    frame_count: int,
    tone: str,
    focus: str,
) -> str:
    core_scene = scene.strip() or "A high-pressure decision moment"
    camera_patterns = [
        "Wide establish",
        "Medium push-in",
        "Over-shoulder",
        "Tight closeup",
        "Lateral move",
        "Locked-off resolution",
    ]
    sound_patterns = [
        "Low atmospheric hum",
        "Pulse percussion enters",
        "Room tone drops, one sharp hit",
        "Breathing and cloth movement",
        "Rising synth bed",
        "Silence before final cue",
    ]

    lines = [
        "### Shot Grid",
        "| Frame | Camera | Visual | Sound |",
        "|---|---|---|---|",
    ]
    for idx in range(frame_count):
        camera = f"{camera_patterns[idx % len(camera_patterns)]} ({style.lower()})"
        visual = (
            f"{core_scene}. Frame {idx + 1} escalates {tone.lower()} tone with "
            f"{palette.lower()} accents and focus on {focus.lower()}."
        )
        sound = sound_patterns[idx % len(sound_patterns)]
        lines.append(f"| {idx + 1} | {camera} | {visual} | {sound} |")

    lines.extend(
        [
            "",
            "### Continuity Guardrails",
            "- Keep eye-line direction consistent from frame 2 through frame 5.",
            "- Hold one color accent as the emotional anchor across the sequence.",
            "- Reserve the cleanest composition for the final consequence frame.",
        ]
    )
    return "\n".join(lines)


def _fallback_edit_notes(
    pacing: str,
    objective: str,
    issues: Sequence[str],
    energy: int,
    pace: int,
    focus: str,
) -> str:
    notes = [
        f"1. Structure pass: optimize first 45 seconds for {objective.lower()}.",
        f"2. Rhythm pass: pacing profile is {pacing.lower()} with energy {energy}/100 and pace {pace}/100.",
        "3. Front-load one premium visual in the first 10 seconds.",
        f"4. Preserve {focus.lower()} beats by trimming non-essential transitions.",
    ]

    if "Dialogue muddy" in issues:
        notes.append("5. Clean dialogue with denoise and mild 2-3kHz presence lift.")
    if "Too slow in middle" in issues:
        notes.append("6. Trim midpoint by 15-20% and replace one dissolve with a hard cut.")
    if "Looks flat" in issues:
        notes.append("7. Add contrast curve and selective saturation for subject separation.")
    if "Confusing geography" in issues:
        notes.append("8. Insert one orienting wide shot before conflict peak.")
    if "Weak ending impact" in issues:
        notes.append("9. Add a 1.5 second silence pocket before final impact beat.")

    notes.extend(
        [
            "",
            "### Priority",
            "- High: objective clarity and geographical orientation",
            "- Medium: midpoint rhythm consistency",
            "- Finish: emotional hold after the final image",
        ]
    )
    return "\n".join(notes)


def _fallback_deck(
    project: str,
    brief: str,
    script: str,
    storyboard: str,
    edit: str,
    rough_cut: str = "",
    rough_cut_rows: Sequence[dict[str, Any]] | None = None,
) -> str:
    has_script = "ready" if script else "pending"
    has_story = "ready" if storyboard else "pending"
    has_edit = "ready" if edit else "pending"
    has_rough_cut = "ready" if rough_cut else "pending"
    rough_cut_summary = _rough_cut_rows_summary(rough_cut_rows or [])

    return "\n".join(
        [
            "### Director Deck",
            f"- Project: {project}",
            f"- Script Pack: {has_script}",
            f"- Storyboard: {has_story}",
            f"- Edit Notes: {has_edit}",
            f"- Rough Cut Review: {has_rough_cut}",
            "",
            "### Creative Thesis",
            brief,
            "",
            "### Rough Cut Signal",
            rough_cut_summary,
            "",
            "### Next 3 Moves",
            "1. Lock the emotional objective for each major beat.",
            "2. Validate visual continuity from storyboard frame 1 to final consequence frame.",
            "3. Use edit notes and rough-cut timestamps to tighten the midpoint and sharpen final impact.",
        ]
    )


def _generate_text(
    ai_client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    fallback: Callable[[], str],
    temperature: float,
) -> tuple[str, str]:
    """Return (content, status) where status is live/demo/fallback."""
    demo_mode = getattr(ai_client, "api_key", None) in (None, "")
    if demo_mode:
        return fallback(), "demo"

    try:
        resp = ai_client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return _extract_content(resp), "live"
    except Exception:
        return fallback(), "fallback"


def _sidebar_controls() -> None:
    st.sidebar.markdown("## Director Controls")
    st.sidebar.caption("Tune style, pacing, and generation behavior.")
    st.sidebar.markdown(
        """
        <div class="sidebar-note">
          API credentials are not entered in this UI. Add <code>OPENAI_API_KEY</code> (and optional fallback keys)
          in Streamlit Secrets or your local <code>.env</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='sidebar-section-title'>Look & Tone</div>", unsafe_allow_html=True)

    preset_names = [preset["name"] for preset in STYLE_PRESETS]
    st.sidebar.selectbox("Style preset", preset_names, key="ifs_preset")

    preset_cols = st.sidebar.columns(2)
    if preset_cols[0].button("Apply", key="apply_preset", use_container_width=True):
        _apply_preset(st.session_state["ifs_preset"])
        _rerun()
    if preset_cols[1].button("Random", key="random_profile", use_container_width=True):
        _randomize_profile()
        _rerun()

    if st.sidebar.button("Shuffle Concept", use_container_width=True):
        st.session_state["ifs_concept_idx"] = (st.session_state["ifs_concept_idx"] + 1) % len(
            CONCEPT_SEEDS
        )
        st.session_state["ifs_script_prompt"] = CONCEPT_SEEDS[st.session_state["ifs_concept_idx"]]
        st.session_state["ifs_status_line"] = "Concept seed shuffled."
        _rerun()

    st.sidebar.markdown("<div class='sidebar-section-title'>Project Profile</div>", unsafe_allow_html=True)
    st.sidebar.text_input("Project title", key="ifs_project_title")
    st.sidebar.selectbox("Genre", GENRES, key="ifs_genre")
    st.sidebar.selectbox("Tone", TONES, key="ifs_tone")
    st.sidebar.selectbox("Camera style", CAMERA_STYLES, key="ifs_camera_style")
    st.sidebar.selectbox("Palette", PALETTES, key="ifs_palette")
    st.sidebar.selectbox("Focus area", FOCUS_AREAS, key="ifs_focus")
    st.sidebar.slider("Energy", 0, 100, key="ifs_energy")
    st.sidebar.slider("Pace", 0, 100, key="ifs_pace")
    st.sidebar.slider("Creativity", 0.1, 1.2, key="ifs_temperature")
    st.sidebar.markdown("<div class='sidebar-section-title'>Model Routing</div>", unsafe_allow_html=True)
    st.sidebar.text_input("Model", key="ifs_model")

    st.sidebar.markdown("---")
    active_preset = _preset_by_name(st.session_state["ifs_preset"])
    st.sidebar.caption(f"Preset tagline: {active_preset['tagline']}")


def _top_section(demo_mode: bool, ai_client: Any) -> None:
    mode_class = "demo" if demo_mode else "live"
    mode_text = "Demo Mode" if demo_mode else "Live AI Mode"

    concept = CONCEPT_SEEDS[st.session_state["ifs_concept_idx"]]
    brief = _build_director_brief()
    scores = _compute_scores()
    now_label = datetime.now().strftime("%a, %b %d • %I:%M %p").replace(" 0", " ")
    provider_chain = _provider_chain_text(ai_client)
    project = st.session_state["ifs_project_title"]
    look_chips = [
        f"{st.session_state['ifs_genre']} / {st.session_state['ifs_tone']}",
        st.session_state["ifs_camera_style"],
        st.session_state["ifs_palette"],
        f"Focus: {st.session_state['ifs_focus']}",
    ]

    left, right = st.columns([1.4, 1.0], gap="large")
    with left:
        chip_html = "".join(f"<span class='chip'>{html.escape(chip)}</span>" for chip in look_chips)
        st.markdown(
            f"""
            <div class="hero-card">
              <div class="hero-grid">
                <div class="hero-stack">
                  <div>
                    <span class="mode-pill {mode_class}">{mode_text}</span>
                    <h2 class="hero-title">Infinity Film Studio Director Console</h2>
                    <p class="hero-sub">A working creative desk for scripts, shot design, edit notes, and kickoff-ready decks.</p>
                    <p class="hero-meta">Session clock: {html.escape(now_label)} • Provider route: {html.escape(provider_chain)}</p>
                  </div>
                  <div class="chip-row">{chip_html}</div>
                </div>
                <div class="callsheet-card">
                  <p class="callsheet-kicker">Today’s Call Sheet</p>
                  <p class="callsheet-title">{html.escape(project)}</p>
                  <div class="callsheet-grid">
                    <div class="callsheet-cell">
                      <span>Energy / Pace</span>
                      <strong>{st.session_state['ifs_energy']}/100 • {st.session_state['ifs_pace']}/100</strong>
                    </div>
                    <div class="callsheet-cell">
                      <span>Frames</span>
                      <strong>{int(st.session_state['ifs_frame_count'])} planned storyboard frames</strong>
                    </div>
                    <div class="callsheet-cell">
                      <span>Concept Seed</span>
                      <strong>{html.escape(_short_seed(concept))}</strong>
                    </div>
                    <div class="callsheet-cell">
                      <span>Model</span>
                      <strong>{html.escape((st.session_state['ifs_model'] or DEFAULT_CHAT_MODEL)[:38])}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f"""
            <div class="brief-card">
              <h4>Live Director Brief</h4>
              <p>{html.escape(brief)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f"**Project:** `{st.session_state['ifs_project_title']}`")
    st.markdown(f"**Provider order:** `{provider_chain}`")
    st.markdown(f"**Active concept:** {concept}")

    st.markdown(
        f"""
        <div class="cue-strip">
          <div class="cue-card"><p class="cue-kicker">Genre</p><div class="cue-value">{html.escape(st.session_state['ifs_genre'])}</div></div>
          <div class="cue-card"><p class="cue-kicker">Tone</p><div class="cue-value">{html.escape(st.session_state['ifs_tone'])}</div></div>
          <div class="cue-card"><p class="cue-kicker">Camera Language</p><div class="cue-value">{html.escape(st.session_state['ifs_camera_style'])}</div></div>
          <div class="cue-card"><p class="cue-kicker">Palette</p><div class="cue-value">{html.escape(st.session_state['ifs_palette'])}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Creative", f"{scores['creative']}")
    metric_cols[1].metric("Tension", f"{scores['tension']}")
    metric_cols[2].metric("Clarity", f"{scores['clarity']}")
    metric_cols[3].metric("Visual", f"{scores['visual']}")
    metric_cols[4].metric("Cohesion", f"{scores['cohesion']}")

    prog_a, prog_b, prog_c = st.columns(3)
    with prog_a:
        _progress("Energy", st.session_state["ifs_energy"])
    with prog_b:
        _progress("Pace", st.session_state["ifs_pace"])
    with prog_c:
        _progress("Profile Balance", max(0, 100 - abs(st.session_state["ifs_energy"] - st.session_state["ifs_pace"])))

    action_cols = st.columns(4)
    if action_cols[0].button("Boost Energy", key="boost_energy", use_container_width=True):
        st.session_state["ifs_energy"] = min(100, st.session_state["ifs_energy"] + 6)
        st.session_state["ifs_status_line"] = "Energy boosted by +6."
        _rerun()

    if action_cols[1].button("Soften Pace", key="soften_pace", use_container_width=True):
        st.session_state["ifs_pace"] = max(0, st.session_state["ifs_pace"] - 6)
        st.session_state["ifs_status_line"] = "Pace reduced by -6 for controlled cadence."
        _rerun()

    if action_cols[2].button("Remix Tone", key="remix_tone_top", use_container_width=True):
        st.session_state["ifs_tone"] = _rotate_value(TONES, st.session_state["ifs_tone"])
        st.session_state["ifs_status_line"] = f"Tone remixed to {st.session_state['ifs_tone']}."
        _rerun()

    if action_cols[3].button("Sync Concept", key="sync_concept", use_container_width=True):
        st.session_state["ifs_script_prompt"] = concept
        st.session_state["ifs_story_prompt"] = concept
        st.session_state["ifs_status_line"] = "Concept synced into script and storyboard prompts."
        _rerun()

    st.markdown(
        f"""
        <div class="status-card">
          Status: {html.escape(st.session_state['ifs_status_line'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _script_tab(ai_client: Any, concept: str) -> None:
    st.subheader("Script Copilot")
    st.caption("Generate logline, beat map, excerpt, and direction notes.")

    seed_cols = st.columns(len(CONCEPT_SEEDS))
    for idx, seed in enumerate(CONCEPT_SEEDS):
        if seed_cols[idx].button(_short_seed(seed), key=f"script_seed_{idx}", use_container_width=True):
            st.session_state["ifs_concept_idx"] = idx
            st.session_state["ifs_script_prompt"] = seed
            st.session_state["ifs_status_line"] = "Loaded new concept into script prompt."
            _rerun()

    st.text_area("Scene premise", key="ifs_script_prompt", height=120)

    controls = st.columns(3)
    generate = controls[0].button("Generate Script Pack", type="primary", use_container_width=True)
    if controls[1].button("Push to Storyboard", key="push_story", use_container_width=True):
        st.session_state["ifs_story_prompt"] = st.session_state["ifs_script_prompt"]
        st.session_state["ifs_status_line"] = "Script premise pushed to storyboard tab."
        _rerun()
    if controls[2].button("Clear Script Output", key="clear_script", use_container_width=True):
        st.session_state["ifs_script_output"] = ""
        st.session_state["ifs_status_line"] = "Script output cleared."
        _rerun()

    if generate:
        project = st.session_state["ifs_project_title"]
        genre = st.session_state["ifs_genre"]
        tone = st.session_state["ifs_tone"]
        focus = st.session_state["ifs_focus"]
        energy = st.session_state["ifs_energy"]
        pace = st.session_state["ifs_pace"]
        model = st.session_state["ifs_model"].strip() or DEFAULT_CHAT_MODEL
        premise = st.session_state["ifs_script_prompt"]
        temperature = float(st.session_state["ifs_temperature"])

        system_prompt = (
            "You are a film development copilot. Provide concise but high-impact outputs "
            "for directors and producers. Return markdown with clear section headings."
        )
        user_prompt = textwrap.dedent(
            f"""
            Project title: {project}
            Genre: {genre}
            Tone: {tone}
            Focus area: {focus}
            Energy: {energy}/100
            Pace: {pace}/100
            Premise: {premise}

            Produce:
            1) Logline (1 paragraph)
            2) 8-beat outline (numbered)
            3) Scene excerpt (~180 words)
            4) Director notes (4 bullets)
            """
        ).strip()

        fallback = lambda: _fallback_script_pack(project, premise, genre, tone, energy, pace, focus)

        with st.spinner("Generating script pack..."):
            content, status = _generate_text(
                ai_client,
                model,
                system_prompt,
                user_prompt,
                fallback,
                temperature,
            )

        if status == "fallback":
            st.info("Live model call failed, so an offline fallback was generated.")

        st.session_state["ifs_script_output"] = content
        st.session_state["ifs_status_line"] = f"Script pack generated ({status})."
        _save_history("Script", f"{project} script pack", content)

    if st.session_state["ifs_script_output"]:
        st.markdown(st.session_state["ifs_script_output"])
        st.markdown("<div class='export-row'></div>", unsafe_allow_html=True)
        st.download_button(
            "Download Script Pack",
            data=st.session_state["ifs_script_output"],
            file_name="script_pack.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_script",
        )


def _storyboard_tab(ai_client: Any) -> None:
    st.subheader("Storyboard Engine")
    st.caption("Convert a moment into a shot-by-shot visual plan.")

    st.text_area("Moment to storyboard", key="ifs_story_prompt", height=110)
    st.slider("Frames", 4, 12, key="ifs_frame_count")

    col_a, col_b, col_c = st.columns(3)
    if col_a.button("Use Script Premise", key="use_script_premise", use_container_width=True):
        st.session_state["ifs_story_prompt"] = st.session_state["ifs_script_prompt"]
        st.session_state["ifs_status_line"] = "Storyboard prompt loaded from script premise."
        _rerun()
    focus_override = col_b.selectbox("Shot Focus", FOCUS_AREAS, index=FOCUS_AREAS.index(st.session_state["ifs_focus"]))
    generate = col_c.button("Generate Shot Grid", type="primary", use_container_width=True)

    if generate:
        project = st.session_state["ifs_project_title"]
        tone = st.session_state["ifs_tone"]
        style = st.session_state["ifs_camera_style"]
        palette = st.session_state["ifs_palette"]
        frame_count = int(st.session_state["ifs_frame_count"])
        model = st.session_state["ifs_model"].strip() or DEFAULT_CHAT_MODEL
        scene = st.session_state["ifs_story_prompt"]
        temperature = float(st.session_state["ifs_temperature"])

        system_prompt = (
            "You are a storyboard supervisor. Return practical, production-ready frame plans. "
            "Use markdown table format and include continuity guardrails."
        )
        user_prompt = textwrap.dedent(
            f"""
            Project title: {project}
            Tone: {tone}
            Camera style: {style}
            Palette: {palette}
            Focus area: {focus_override}
            Scene moment: {scene}
            Frame count: {frame_count}

            Output:
            - Markdown table with columns: Frame, Camera, Visual, Sound
            - Then 3 continuity guardrails as bullets
            """
        ).strip()

        fallback = lambda: _fallback_storyboard(scene, style, palette, frame_count, tone, focus_override)

        with st.spinner("Generating storyboard..."):
            content, status = _generate_text(
                ai_client,
                model,
                system_prompt,
                user_prompt,
                fallback,
                temperature,
            )

        if status == "fallback":
            st.info("Live model call failed, so an offline fallback was generated.")

        st.session_state["ifs_storyboard_output"] = content
        st.session_state["ifs_status_line"] = f"Storyboard generated ({status})."
        _save_history("Storyboard", f"{project} shot grid", content)

    if st.session_state["ifs_storyboard_output"]:
        st.markdown(st.session_state["ifs_storyboard_output"])
        st.markdown("<div class='export-row'></div>", unsafe_allow_html=True)
        st.download_button(
            "Download Storyboard",
            data=st.session_state["ifs_storyboard_output"],
            file_name="storyboard.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_story",
        )


def _edit_tab(ai_client: Any) -> None:
    st.subheader("Edit Review")
    st.caption("Generate standard edit notes or upload a rough cut for timestamped review.")

    settings_col, rough_cut_col = st.columns([1.05, 1.15], gap="large")

    with settings_col:
        pacing = st.selectbox("Pacing profile", ["Fast", "Balanced", "Slow burn"], index=1)
        runtime_target = st.slider("Target runtime (minutes)", 3, 40, 12)
        st.text_input("Primary objective", key="ifs_edit_objective")
        issues = st.multiselect("Current issues", ISSUE_FLAGS, default=["Too slow in middle"])

    clip_bytes = b""
    clip_name = ""
    clip_type = ""
    clip_meta: dict[str, Any] = {}

    with rough_cut_col:
        st.markdown("#### Rough Cut Analyzer")
        st.caption("Upload a clip and generate timestamped cut notes you can act on immediately.")
        uploaded_video = st.file_uploader(
            "Upload rough cut (mp4/mov/webm/mkv)",
            type=["mp4", "mov", "m4v", "webm", "mkv", "avi"],
            key="ifs_rough_cut_file",
            help="The app uses local metadata probing when available and builds a timestamped review.",
        )
        st.text_area(
            "Transcript / shot notes (optional)",
            key="ifs_rough_cut_notes",
            height=120,
            help="Paste transcript, shot notes, or editor observations to improve cut recommendations.",
        )
        st.text_input(
            "Review question (optional)",
            key="ifs_rough_cut_question",
            help="Example: Where does pacing drop, and what should I trim first?",
        )
        cut_cfg_a, cut_cfg_b = st.columns(2)
        cut_cfg_a.number_input(
            "Clip duration fallback (sec)",
            min_value=4,
            max_value=7200,
            step=1,
            key="ifs_clip_duration_guess_seconds",
            help="Used when ffprobe metadata is unavailable.",
        )
        cut_cfg_b.slider(
            "Segment size (sec)",
            min_value=5,
            max_value=90,
            key="ifs_cut_segment_seconds",
            help="Smaller segments produce more granular timestamp notes.",
        )

        if uploaded_video is not None:
            clip_bytes = uploaded_video.getvalue()
            clip_name = uploaded_video.name
            clip_type = uploaded_video.type or ""
            clip_meta = _probe_video_metadata(clip_name, clip_bytes)

            detected_duration = _safe_float(clip_meta.get("duration_seconds"))
            clip_len_label = (
                _format_timestamp(detected_duration)
                if detected_duration and detected_duration > 0
                else _format_timestamp(st.session_state["ifs_clip_duration_guess_seconds"])
            )
            res_label = (
                f"{clip_meta.get('width')}x{clip_meta.get('height')}"
                if clip_meta.get("width") and clip_meta.get("height")
                else "Unknown"
            )

            meta_cols = st.columns(4)
            meta_cols[0].metric("Clip Length", clip_len_label)
            meta_cols[1].metric("File Size", _format_bytes(len(clip_bytes)))
            meta_cols[2].metric("Resolution", res_label)
            meta_cols[3].metric(
                "FPS",
                f"{clip_meta['fps']:.2f}" if isinstance(clip_meta.get("fps"), (int, float)) else "Unknown",
            )

            if clip_meta.get("probe_status") == "ffprobe_not_installed":
                st.info("`ffprobe` is not installed locally. Using manual duration fallback for timeline segmentation.")
            elif clip_meta.get("probe_status") == "ffprobe_failed":
                st.info("Video metadata probe failed. Timestamp analysis will use the fallback duration you set.")

            with st.expander("Preview uploaded rough cut", expanded=False):
                st.video(clip_bytes)
                st.caption(
                    f"File: {clip_name} • MIME: {clip_type or 'unknown'} • Probe: {clip_meta.get('probe_status', 'unknown')}"
                )

    controls = st.columns(3)
    generate = controls[0].button("Generate Edit Notes", use_container_width=True)
    analyze_cut = controls[1].button("Analyze Rough Cut", type="primary", use_container_width=True)
    if controls[2].button("Clear Edit Output", key="clear_edit", use_container_width=True):
        st.session_state["ifs_edit_output"] = ""
        st.session_state["ifs_rough_cut_output"] = ""
        st.session_state["ifs_rough_cut_timeline_rows"] = []
        st.session_state["ifs_rough_cut_timeline_csv"] = ""
        st.session_state["ifs_rough_cut_timeline_json"] = ""
        st.session_state["ifs_rough_cut_metadata"] = {}
        st.session_state["ifs_status_line"] = "Edit output cleared."
        _rerun()

    if generate:
        project = st.session_state["ifs_project_title"]
        tone = st.session_state["ifs_tone"]
        focus = st.session_state["ifs_focus"]
        objective = st.session_state["ifs_edit_objective"]
        energy = st.session_state["ifs_energy"]
        pace = st.session_state["ifs_pace"]
        model = st.session_state["ifs_model"].strip() or DEFAULT_CHAT_MODEL
        temperature = float(st.session_state["ifs_temperature"])

        system_prompt = (
            "You are a senior film editor. Provide concise, high-leverage feedback that is immediately "
            "actionable in an editing suite."
        )
        user_prompt = textwrap.dedent(
            f"""
            Project title: {project}
            Tone: {tone}
            Pacing profile: {pacing}
            Runtime target: {runtime_target} minutes
            Objective: {objective}
            Focus area: {focus}
            Energy: {energy}/100
            Pace: {pace}/100
            Issues: {', '.join(issues) if issues else 'none'}

            Output:
            - Prioritized numbered edit notes
            - End with a short Priority section (High/Medium/Finish)
            """
        ).strip()

        fallback = lambda: _fallback_edit_notes(pacing, objective, issues, energy, pace, focus)

        with st.spinner("Generating edit notes..."):
            content, status = _generate_text(
                ai_client,
                model,
                system_prompt,
                user_prompt,
                fallback,
                temperature,
            )

        if status == "fallback":
            st.info("Live model call failed, so an offline fallback was generated.")

        st.session_state["ifs_edit_output"] = content
        st.session_state["ifs_status_line"] = f"Edit notes generated ({status})."
        _save_history("Edit", f"{project} edit notes", content)

    if analyze_cut:
        project = st.session_state["ifs_project_title"]
        tone = st.session_state["ifs_tone"]
        focus = st.session_state["ifs_focus"]
        objective = st.session_state["ifs_edit_objective"]
        energy = int(st.session_state["ifs_energy"])
        pace = int(st.session_state["ifs_pace"])
        model = st.session_state["ifs_model"].strip() or DEFAULT_CHAT_MODEL
        temperature = float(st.session_state["ifs_temperature"])
        cut_notes = st.session_state["ifs_rough_cut_notes"]
        review_question = st.session_state["ifs_rough_cut_question"].strip()
        segment_seconds = int(st.session_state["ifs_cut_segment_seconds"])
        fallback_duration_seconds = int(st.session_state["ifs_clip_duration_guess_seconds"])

        if not clip_bytes and not cut_notes.strip():
            st.warning("Upload a rough cut or paste transcript/shot notes to run timestamped analysis.")
        else:
            if not clip_meta:
                clip_meta = {
                    "file_name": clip_name or "rough-cut",
                    "file_size_bytes": len(clip_bytes),
                    "duration_seconds": None,
                    "width": None,
                    "height": None,
                    "fps": None,
                    "video_codec": None,
                    "audio_codec": None,
                    "bitrate_kbps": None,
                    "probe_status": "not_probed",
                }
            clip_meta["file_name"] = clip_name or clip_meta.get("file_name") or "rough-cut"
            clip_meta["file_size_bytes"] = len(clip_bytes)

            duration_seconds = _normalize_clip_duration_seconds(clip_meta, fallback_duration_seconds)
            rows = _fallback_rough_cut_rows(
                project=project,
                objective=objective,
                pacing=pacing,
                issues=issues,
                tone=tone,
                focus=focus,
                energy=energy,
                pace=pace,
                duration_seconds=duration_seconds,
                segment_seconds=segment_seconds,
                notes=cut_notes,
                file_name=clip_name or "rough-cut",
            )
            fallback_content = _fallback_rough_cut_review(
                project=project,
                objective=objective,
                pacing=pacing,
                runtime_target=runtime_target,
                tone=tone,
                focus=focus,
                energy=energy,
                pace=pace,
                issues=issues,
                metadata=clip_meta,
                rows=rows,
                review_question=review_question,
            )

            segment_preview = ", ".join(row["timestamp"] for row in rows[:8])
            transcript_excerpt = cut_notes.strip()[:3000] if cut_notes.strip() else "No transcript/notes provided."
            metadata_summary = {
                "file_name": clip_meta.get("file_name") or "rough-cut",
                "file_size_bytes": clip_meta.get("file_size_bytes"),
                "probe_status": clip_meta.get("probe_status"),
                "duration_seconds": clip_meta.get("duration_seconds") or duration_seconds,
                "width": clip_meta.get("width"),
                "height": clip_meta.get("height"),
                "fps": clip_meta.get("fps"),
                "video_codec": clip_meta.get("video_codec"),
                "audio_codec": clip_meta.get("audio_codec"),
                "bitrate_kbps": clip_meta.get("bitrate_kbps"),
            }

            system_prompt = (
                "You are a senior film editor reviewing a rough cut. Produce timestamped, production-ready notes "
                "that improve pacing, clarity, geography, and emotional impact. Return markdown only."
            )
            user_prompt = textwrap.dedent(
                f"""
                Project title: {project}
                Tone: {tone}
                Pacing profile: {pacing}
                Runtime target: {runtime_target} minutes
                Objective: {objective}
                Focus area: {focus}
                Energy: {energy}/100
                Pace: {pace}/100
                Current issues: {', '.join(issues) if issues else 'none'}
                Review question: {review_question or 'General rough-cut pass'}

                Clip metadata (JSON):
                {json.dumps(metadata_summary, indent=2)}

                Timeline segments under review:
                {segment_preview}

                Transcript / shot notes (may be partial):
                {transcript_excerpt}

                Required output format:
                1) "Rough Cut Snapshot" bullets
                2) "Timestamped Cut Notes" markdown table with columns:
                   Time | Priority | Focus | Issue | Observation | Recommended Cut
                3) "Pattern Diagnosis" bullets
                4) "First Pass Fix Order" numbered list

                Keep recommendations concrete (frame trims, cut timing, inserts, L-cuts/J-cuts, reaction holds).
                """
            ).strip()

            with st.spinner("Analyzing rough cut timeline..."):
                content, status = _generate_text(
                    ai_client,
                    model,
                    system_prompt,
                    user_prompt,
                    lambda: fallback_content,
                    temperature,
                )

            if status == "fallback":
                st.info("Live model call failed, so a local timestamped rough-cut review was generated.")

            st.session_state["ifs_rough_cut_output"] = content
            st.session_state["ifs_rough_cut_timeline_rows"] = rows
            st.session_state["ifs_rough_cut_timeline_csv"] = _rough_cut_rows_to_csv(rows)
            st.session_state["ifs_rough_cut_timeline_json"] = json.dumps(rows, indent=2)
            st.session_state["ifs_rough_cut_metadata"] = metadata_summary
            st.session_state["ifs_status_line"] = f"Rough cut analysis generated ({status})."
            _save_history("Rough Cut", f"{project} timestamped review", content)

    if st.session_state["ifs_rough_cut_timeline_rows"]:
        st.markdown("#### Timeline Flags")
        st.caption("Structured timestamped notes generated for the rough-cut pass (downloadable as CSV/JSON).")
        rows = st.session_state["ifs_rough_cut_timeline_rows"]
        count_high = sum(1 for row in rows if row.get("priority") == "High")
        count_medium = sum(1 for row in rows if row.get("priority") == "Medium")
        count_low = sum(1 for row in rows if row.get("priority") == "Low")
        sum_cols = st.columns(4)
        sum_cols[0].metric("Flags", str(len(rows)))
        sum_cols[1].metric("High", str(count_high))
        sum_cols[2].metric("Medium", str(count_medium))
        sum_cols[3].metric("Low", str(count_low))
        st.caption(_rough_cut_rows_summary(rows))
        display_rows = [
            {
                "Time": row.get("timestamp", ""),
                "Priority": row.get("priority", ""),
                "Focus": row.get("focus", ""),
                "Issue": row.get("issue", ""),
                "Observation": row.get("observation", ""),
                "Recommended Cut": row.get("action", ""),
            }
            for row in rows
        ]
        try:
            st.dataframe(display_rows, use_container_width=True, hide_index=True)
        except Exception:
            st.json(display_rows, expanded=False)

    if st.session_state["ifs_edit_output"]:
        st.markdown("#### Edit Notes")
        st.markdown(st.session_state["ifs_edit_output"])
        st.download_button(
            "Download Edit Notes",
            data=st.session_state["ifs_edit_output"],
            file_name="edit_notes.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_edit",
        )
        st.markdown("<div class='export-row'></div>", unsafe_allow_html=True)

    if st.session_state["ifs_rough_cut_output"]:
        st.markdown("#### Rough Cut Analysis")
        st.markdown(st.session_state["ifs_rough_cut_output"])
        export_cols = st.columns(3)
        export_cols[0].download_button(
            "Download Rough Cut Review",
            data=st.session_state["ifs_rough_cut_output"],
            file_name="rough_cut_review.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_rough_cut_review",
        )
        if st.session_state["ifs_rough_cut_timeline_csv"]:
            export_cols[1].download_button(
                "Download Timeline CSV",
                data=st.session_state["ifs_rough_cut_timeline_csv"],
                file_name="rough_cut_timeline.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_cut_csv",
            )
        if st.session_state["ifs_rough_cut_timeline_json"]:
            export_cols[2].download_button(
                "Download Timeline JSON",
                data=st.session_state["ifs_rough_cut_timeline_json"],
                file_name="rough_cut_timeline.json",
                mime="application/json",
                use_container_width=True,
                key="dl_cut_json",
            )
        st.markdown("<div class='export-row'></div>", unsafe_allow_html=True)


def _deck_tab(ai_client: Any) -> None:
    st.subheader("Director Deck")
    st.caption("Synthesize script, storyboard, and edit strategy into one production brief.")

    col_a, col_b = st.columns(2)
    generate = col_a.button("Generate Director Deck", type="primary", use_container_width=True)
    if col_b.button("Clear Deck", key="clear_deck", use_container_width=True):
        st.session_state["ifs_deck_output"] = ""
        st.session_state["ifs_status_line"] = "Director deck cleared."
        _rerun()

    if generate:
        project = st.session_state["ifs_project_title"]
        model = st.session_state["ifs_model"].strip() or DEFAULT_CHAT_MODEL
        temperature = float(st.session_state["ifs_temperature"])
        brief = _build_director_brief()

        script_content = st.session_state["ifs_script_output"]
        storyboard_content = st.session_state["ifs_storyboard_output"]
        edit_content = st.session_state["ifs_edit_output"]
        rough_cut_content = st.session_state.get("ifs_rough_cut_output", "")
        rough_cut_rows = st.session_state.get("ifs_rough_cut_timeline_rows", [])
        rough_cut_meta = st.session_state.get("ifs_rough_cut_metadata", {})
        rough_cut_summary = _rough_cut_rows_summary(rough_cut_rows)

        system_prompt = (
            "You are an executive creative producer. Build a concise production deck summary "
            "for a director and team kickoff meeting."
        )
        user_prompt = textwrap.dedent(
            f"""
            Project: {project}
            Director brief: {brief}

            Script pack:
            {script_content[:2200] if script_content else 'No script pack yet.'}

            Storyboard:
            {storyboard_content[:2200] if storyboard_content else 'No storyboard yet.'}

            Edit notes:
            {edit_content[:2200] if edit_content else 'No edit notes yet.'}

            Rough cut review:
            {rough_cut_content[:2800] if rough_cut_content else 'No rough cut review yet.'}

            Rough cut timeline summary:
            {rough_cut_summary}

            Rough cut metadata (JSON):
            {json.dumps(rough_cut_meta, indent=2) if rough_cut_meta else 'No metadata yet.'}

            Create markdown with sections:
            - Executive Summary
            - What Is Locked
            - What Needs Decisions
            - Production Risks
            - Next 5 Actions
            """
        ).strip()

        fallback = lambda: _fallback_deck(
            project,
            brief,
            script_content,
            storyboard_content,
            edit_content,
            rough_cut_content,
            rough_cut_rows,
        )

        with st.spinner("Generating director deck..."):
            content, status = _generate_text(
                ai_client,
                model,
                system_prompt,
                user_prompt,
                fallback,
                temperature,
            )

        if status == "fallback":
            st.info("Live model call failed, so an offline fallback was generated.")

        st.session_state["ifs_deck_output"] = content
        st.session_state["ifs_status_line"] = f"Director deck generated ({status})."
        _save_history("Deck", f"{project} director deck", content)

    if st.session_state["ifs_deck_output"]:
        st.markdown(st.session_state["ifs_deck_output"])
        st.markdown("<div class='export-row'></div>", unsafe_allow_html=True)
        st.download_button(
            "Download Director Deck",
            data=st.session_state["ifs_deck_output"],
            file_name="director_deck.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_deck",
        )


def _history_tab() -> None:
    st.subheader("Recent Generations")
    st.caption("Latest outputs from this session. You can restore prompts directly.")

    history = st.session_state["ifs_history"]
    if not history:
        st.info("No generations yet. Create a script pack, shot grid, edit notes, or deck first.")
        return

    for index, item in enumerate(history):
        preview = item["content"][:280].replace("\n", " ").strip()
        st.markdown(
            f"""
            <div class="history-item">
              <h5>[{html.escape(item['kind'])}] {html.escape(item['title'])}</h5>
              <p>{html.escape(item['time'])}</p>
              <p>{html.escape(preview)}...</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        btn_a, btn_b, btn_c = st.columns(3)
        if btn_a.button("Use As Script", key=f"hist_script_{index}", use_container_width=True):
            st.session_state["ifs_script_prompt"] = item["content"][:700]
            st.session_state["ifs_status_line"] = "History item loaded into script premise."
            _rerun()
        if btn_b.button("Use As Storyboard", key=f"hist_story_{index}", use_container_width=True):
            st.session_state["ifs_story_prompt"] = item["content"][:700]
            st.session_state["ifs_status_line"] = "History item loaded into storyboard prompt."
            _rerun()
        if btn_c.button("Remove", key=f"hist_remove_{index}", use_container_width=True):
            st.session_state["ifs_history"].pop(index)
            st.session_state["ifs_status_line"] = "History item removed."
            _rerun()


def main() -> None:
    st.set_page_config(
        page_title="Infinity Film Studio Director Console",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_state()
    _inject_styles()

    ai_client = _get_ai_client()
    demo_mode = getattr(ai_client, "api_key", None) in (None, "")

    # Render top controls first so their state updates happen before sidebar
    # widgets with the same keys are instantiated in this run.
    _top_section(demo_mode, ai_client)
    _sidebar_controls()

    concept = CONCEPT_SEEDS[st.session_state["ifs_concept_idx"]]

    tab_script, tab_storyboard, tab_edit, tab_deck, tab_history = st.tabs(
        ["Script Copilot", "Storyboard", "Edit Review", "Director Deck", "History"]
    )

    with tab_script:
        _script_tab(ai_client, concept)

    with tab_storyboard:
        _storyboard_tab(ai_client)

    with tab_edit:
        _edit_tab(ai_client)

    with tab_deck:
        _deck_tab(ai_client)

    with tab_history:
        _history_tab()


if __name__ == "__main__":
    main()

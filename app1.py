"""Offline-first Streamlit app with optional live OpenAI mode.

Defaults to local deterministic generation with zero external dependencies.
Users can enable live generation by setting an API key in the sidebar.
"""

from __future__ import annotations

import html
import random
import textwrap
from datetime import datetime
from typing import Any, Sequence

import streamlit as st


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


def seed_for(*parts: str) -> int:
    text = "|".join(parts).strip().lower()
    return abs(hash(text)) % (2**31)


def _extract_content(resp: Any) -> str:
    """Normalize OpenAI SDK responses and dict fallbacks to plain text."""

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


def _load_openai_client(api_key: str, base_url: str):
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        return None, f"OpenAI SDK import failed: {exc}"

    try:
        client = OpenAI(api_key=api_key, base_url=(base_url or None))
        return client, ""
    except Exception as exc:
        return None, f"OpenAI client init failed: {exc}"


def _call_live(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> tuple[str, str]:
    """Returns (content, error_message)."""
    client, error = _load_openai_client(api_key=api_key, base_url=base_url)
    if error:
        return "", error

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return _extract_content(resp), ""
    except Exception as exc:
        return "", f"Live generation failed: {exc}"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@500;700&display=swap');

        header[data-testid="stHeader"] {
            display: none;
        }

        [data-testid="stToolbar"] {
            display: none;
        }

        .stApp {
            font-family: 'Manrope', 'Segoe UI', sans-serif;
            background:
                radial-gradient(circle at 10% 18%, rgba(48, 211, 190, 0.22), transparent 40%),
                radial-gradient(circle at 88% 10%, rgba(255, 118, 89, 0.17), transparent 32%),
                linear-gradient(154deg, #081229 0%, #0d1c3d 48%, #12224d 100%);
            color: #ebf2ff;
        }

        .block-container {
            max-width: 1220px;
            padding-top: 0.45rem;
            padding-bottom: 2.5rem;
        }

        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, rgba(7, 19, 45, 0.98), rgba(11, 29, 64, 0.98));
            border-right: 1px solid rgba(170, 197, 255, 0.23);
        }

        .hero-card {
            border-radius: 20px;
            padding: 1.15rem 1.25rem;
            border: 1px solid rgba(149, 178, 241, 0.28);
            background:
                radial-gradient(circle at 92% 10%, rgba(255, 146, 111, 0.2), transparent 35%),
                linear-gradient(145deg, rgba(17, 36, 73, 0.84), rgba(8, 19, 44, 0.92));
            box-shadow:
                0 16px 36px rgba(3, 9, 22, 0.44),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            margin-bottom: 0.75rem;
        }

        .hero-card h2 {
            margin: 0.48rem 0 0;
            font-family: 'Sora', 'Manrope', sans-serif;
            font-size: 1.68rem;
            line-height: 1.1;
            color: #f5f9ff;
        }

        .hero-card p {
            margin: 0.55rem 0 0;
            color: rgba(225, 236, 255, 0.88);
        }

        .mode-pill {
            display: inline-block;
            padding: 0.2rem 0.66rem;
            border-radius: 999px;
            font-size: 0.78rem;
            border: 1px solid rgba(189, 212, 255, 0.38);
            color: #ecf4ff;
            background: rgba(126, 155, 220, 0.2);
        }

        .mode-pill.live {
            border-color: rgba(88, 232, 201, 0.68);
            background: rgba(50, 205, 176, 0.24);
            color: #ddfff4;
        }

        .mode-pill.offline {
            border-color: rgba(255, 184, 130, 0.62);
            background: rgba(255, 129, 95, 0.2);
            color: #ffeade;
        }

        .status-line {
            margin-top: 0.55rem;
            border: 1px solid rgba(151, 178, 241, 0.24);
            border-radius: 14px;
            padding: 0.54rem 0.72rem;
            color: rgba(223, 236, 255, 0.9);
            background: rgba(8, 20, 44, 0.62);
        }

        [data-testid="stMetricValue"] {
            color: #f9fbff;
            font-weight: 800;
            letter-spacing: -0.01em;
        }

        [data-testid="stMetricLabel"] {
            color: rgba(215, 230, 255, 0.8);
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.44rem;
        }

        [data-testid="stTabs"] [role="tab"] {
            border-radius: 999px;
            border: 1px solid rgba(169, 192, 247, 0.24);
            background: rgba(128, 157, 224, 0.14);
            color: #eaf2ff;
            padding: 0.44rem 0.9rem;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            border-color: rgba(100, 236, 207, 0.64);
            background: rgba(45, 200, 178, 0.22);
            color: #f0fffb;
        }

        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-baseweb="select"] > div {
            background: rgba(7, 20, 45, 0.88);
            color: #f1f6ff;
            border-color: rgba(164, 189, 246, 0.28);
        }

        [data-testid="stSidebar"] .stButton > button,
        .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(168, 191, 248, 0.3);
            background: linear-gradient(145deg, rgba(33, 52, 92, 0.84), rgba(16, 30, 62, 0.92));
            color: #edf3ff;
            transition: transform 160ms ease, border-color 160ms ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(110, 229, 206, 0.72);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(145deg, rgba(255, 96, 104, 0.95), rgba(255, 74, 106, 0.95));
            border-color: rgba(255, 146, 164, 0.62);
            color: #fff8fb;
        }

        .history-card {
            border-radius: 14px;
            border: 1px solid rgba(162, 187, 244, 0.22);
            background: rgba(8, 20, 43, 0.74);
            padding: 0.72rem 0.82rem;
            margin-bottom: 0.58rem;
        }

        .history-card h5 {
            margin: 0;
            color: #f5f9ff;
            font-size: 0.94rem;
        }

        .history-card p {
            margin: 0.28rem 0 0;
            color: rgba(214, 228, 255, 0.82);
            font-size: 0.84rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    defaults = {
        "ifs1_project_title": "Neon Corridor",
        "ifs1_genre": GENRES[0],
        "ifs1_tone": TONES[3],
        "ifs1_camera_style": CAMERA_STYLES[1],
        "ifs1_palette": PALETTES[0],
        "ifs1_energy": 68,
        "ifs1_pace": 57,
        "ifs1_live_enabled": False,
        "ifs1_api_key": "",
        "ifs1_base_url": "",
        "ifs1_model": "gpt-4.1-mini",
        "ifs1_temperature": 0.7,
        "ifs1_script_output": "",
        "ifs1_storyboard_output": "",
        "ifs1_edit_output": "",
        "ifs1_history": [],
        "ifs1_status": "Ready.",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _save_history(kind: str, source: str, content: str) -> None:
    item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "source": source,
        "content": content,
    }
    history = st.session_state["ifs1_history"]
    history.insert(0, item)
    del history[12:]


def _make_logline(genre: str, tone: str, protagonist: str, setting: str, goal: str, obstacle: str) -> str:
    return (
        f"A {tone.lower()} {genre.lower()} short film where {protagonist} must {goal} in "
        f"{setting}, but {obstacle} threatens to break the mission."
    )


def _make_beats(logline: str) -> list[str]:
    rng = random.Random(seed_for(logline))
    pivots = [
        "a leaked recording",
        "a failed rehearsal",
        "an impossible deadline",
        "an anonymous message",
        "a missing memory shard",
        "a locked archive",
    ]
    costs = ["trust", "time", "reputation", "the team dynamic", "their backup plan"]
    reveal = rng.choice(pivots)
    cost = rng.choice(costs)
    return [
        "Opening image: show the world and emotional weather in one striking visual.",
        "Setup: establish what the protagonist wants and why now.",
        "Catalyst: a disruption forces a decision.",
        f"Debate: the team hesitates after {reveal}.",
        "Break into action: the plan starts moving fast.",
        f"Midpoint: a partial win raises stakes and costs {cost}.",
        "All is lost: the core strategy collapses.",
        "Finale: rebuild from truth, execute a riskier final move, and resolve the arc.",
    ]


def _make_scene_excerpt(protagonist: str, goal: str, tone: str, energy: int, pace: int) -> str:
    return textwrap.dedent(
        f"""
        INT. MAKESHIFT CONTROL ROOM - NIGHT

        {protagonist.upper()} stares at the monitor wall. A timer bleeds red in the corner.

        {protagonist.upper()}
        If we miss this window, we lose the whole city.

        PARTNER
        Then we do not miss.

        {protagonist.upper()} exhales, steadies their hands, and keys in the final override.

        The room hums. Then silence.

        PARTNER (softly)
        Did we just... {goal}?

        {protagonist.upper()} does not answer. The first alarm begins to ring.

        Tone target: {tone}. Energy: {energy}/100. Pace: {pace}/100.
        """
    ).strip()


def _offline_script_pack(
    genre: str,
    tone: str,
    protagonist: str,
    setting: str,
    goal: str,
    obstacle: str,
    energy: int,
    pace: int,
) -> str:
    logline = _make_logline(genre, tone, protagonist, setting, goal, obstacle)
    beats = _make_beats(logline)
    scene = _make_scene_excerpt(protagonist, goal, tone, energy, pace)

    lines = ["### Logline", logline, "", "### 8-Beat Outline"]
    lines.extend([f"{idx}. {beat}" for idx, beat in enumerate(beats, 1)])
    lines.extend(["", "### Scene Excerpt", f"```text\n{scene}\n```"])
    return "\n".join(lines)


def _offline_storyboard(scene: str, style: str, palette: str, frame_count: int) -> str:
    base = scene.strip() or "The key dramatic moment"
    camera_templates = [
        "Wide establish",
        "Medium push-in",
        "Over-shoulder",
        "Close-up",
        "Tracking shot",
        "Locked final composition",
    ]
    sound_templates = [
        "Low atmosphere, distant mechanical hum.",
        "Pulse percussion starts under room tone.",
        "Sharp transient cue then ambient ducking.",
        "Breathing detail and cloth movement.",
        "Rising tonal swell with warning beeps.",
        "Silence before one signature final sound.",
    ]

    rows = [
        "### Shot Grid",
        "| Frame | Camera | Visual | Sound |",
        "|---|---|---|---|",
    ]

    for idx in range(frame_count):
        camera = f"{camera_templates[idx % len(camera_templates)]} ({style.lower()})"
        visual = f"{base}. Decision tension is staged with {palette.lower()} accents."
        sound = sound_templates[idx % len(sound_templates)]
        rows.append(f"| {idx + 1} | {camera} | {visual} | {sound} |")

    rows.extend(
        [
            "",
            "### Continuity Guardrails",
            "- Keep eye-line direction consistent from frame 2 onward.",
            "- Use one repeating color accent to anchor tone.",
            "- Reserve the clearest composition for the final consequence frame.",
        ]
    )
    return "\n".join(rows)


def _offline_edit_notes(pacing: str, objective: str, issues: Sequence[str], energy: int, pace: int) -> str:
    notes = [
        f"1. Pacing preset: {pacing}. Prioritize {objective.lower()} in the first 45 seconds.",
        f"2. Rhythm target: energy {energy}/100, pace {pace}/100.",
        "3. Front-load the strongest visual by moving it into the first 10 seconds.",
        "4. Use L-cuts to keep momentum through exposition lines.",
    ]
    if "Dialogue muddy" in issues:
        notes.append("5. Denoise dialogue and add a 2-3 kHz presence boost for clarity.")
    if "Too slow in middle" in issues:
        notes.append("6. Trim 15-20% from the midpoint beat and replace one transition with a hard cut.")
    if "Looks flat" in issues:
        notes.append("7. Add contrast curve and separate subject/background with selective saturation.")
    if "Confusing geography" in issues:
        notes.append("8. Insert one orienting wide shot before the conflict peak.")
    if "Weak ending impact" in issues:
        notes.append("9. Add a 1-2 second hold after the impact moment.")
    return "\n".join(notes)


def _sidebar() -> None:
    st.sidebar.markdown("## Runtime Mode")
    st.sidebar.checkbox("Enable Live API", key="ifs1_live_enabled")
    st.sidebar.text_input("API Key", type="password", key="ifs1_api_key")
    st.sidebar.text_input("Base URL (optional)", key="ifs1_base_url")
    st.sidebar.text_input("Model", key="ifs1_model")
    st.sidebar.slider("Creativity", 0.1, 1.2, key="ifs1_temperature")

    if st.sidebar.button("Test API Connection", use_container_width=True):
        if not st.session_state["ifs1_live_enabled"]:
            st.session_state["ifs1_status"] = "Live API is disabled. Turn it on to test."
        elif not st.session_state["ifs1_api_key"].strip():
            st.session_state["ifs1_status"] = "API key is empty. Add a key to test live mode."
        else:
            content, error = _call_live(
                api_key=st.session_state["ifs1_api_key"].strip(),
                base_url=st.session_state["ifs1_base_url"].strip(),
                model=st.session_state["ifs1_model"].strip() or "gpt-4.1-mini",
                system_prompt="You are a concise assistant.",
                user_prompt="Reply with: connection ok",
                temperature=0.2,
            )
            if error:
                st.session_state["ifs1_status"] = f"API test failed. {error}"
            else:
                st.session_state["ifs1_status"] = f"API connected. Response: {content[:80]}"

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Project Controls")
    st.sidebar.text_input("Project title", key="ifs1_project_title")
    st.sidebar.selectbox("Genre", GENRES, key="ifs1_genre")
    st.sidebar.selectbox("Tone", TONES, key="ifs1_tone")
    st.sidebar.selectbox("Camera style", CAMERA_STYLES, key="ifs1_camera_style")
    st.sidebar.selectbox("Palette", PALETTES, key="ifs1_palette")
    st.sidebar.slider("Energy", 0, 100, key="ifs1_energy")
    st.sidebar.slider("Pace", 0, 100, key="ifs1_pace")


def _top() -> None:
    live_mode = bool(st.session_state["ifs1_live_enabled"] and st.session_state["ifs1_api_key"].strip())
    mode_label = "Live API Mode" if live_mode else "Offline Mode"
    mode_class = "live" if live_mode else "offline"

    st.markdown(
        f"""
        <div class="hero-card">
          <span class="mode-pill {mode_class}">{mode_label}</span>
          <h2>Infinity Film Studio - Offline First Console</h2>
          <p>Runs fully offline by default. Add an API key in the sidebar to switch to live generation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    energy = int(st.session_state["ifs1_energy"])
    pace = int(st.session_state["ifs1_pace"])
    balance = max(0, 100 - abs(energy - pace))
    creative = min(99, int((energy * 0.55) + (pace * 0.3) + (balance * 0.15)))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Creative", f"{creative}")
    c2.metric("Energy", f"{energy}%")
    c3.metric("Pace", f"{pace}%")
    c4.metric("Balance", f"{balance}%")

    st.markdown(
        f"""
        <div class="status-line">
          Status: {html.escape(st.session_state['ifs1_status'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _script_tab() -> None:
    st.subheader("Script Lab")

    with st.form("ifs1_script_form"):
        col1, col2 = st.columns(2)
        protagonist = col1.text_input("Protagonist", value="A rookie location sound engineer")
        setting = col2.text_input("Setting", value="a storm-hit floating megacity")
        goal = col1.text_input("Goal", value="transmit one clean signal before sunrise")
        obstacle = col2.text_input("Main obstacle", value="a corrupted control grid and a traitor on comms")
        submitted = st.form_submit_button("Generate Script Pack", type="primary", use_container_width=True)

    if submitted:
        genre = st.session_state["ifs1_genre"]
        tone = st.session_state["ifs1_tone"]
        energy = int(st.session_state["ifs1_energy"])
        pace = int(st.session_state["ifs1_pace"])

        offline_output = _offline_script_pack(
            genre=genre,
            tone=tone,
            protagonist=protagonist,
            setting=setting,
            goal=goal,
            obstacle=obstacle,
            energy=energy,
            pace=pace,
        )

        source = "offline"
        content = offline_output

        if st.session_state["ifs1_live_enabled"] and st.session_state["ifs1_api_key"].strip():
            system_prompt = "You are a film development copilot. Return clear markdown sections."
            user_prompt = textwrap.dedent(
                f"""
                Project: {st.session_state['ifs1_project_title']}
                Genre: {genre}
                Tone: {tone}
                Energy: {energy}/100
                Pace: {pace}/100
                Protagonist: {protagonist}
                Setting: {setting}
                Goal: {goal}
                Obstacle: {obstacle}

                Produce:
                1) Logline
                2) 8-beat outline
                3) Scene excerpt (~160 words)
                4) 4 director notes
                """
            ).strip()
            live_content, error = _call_live(
                api_key=st.session_state["ifs1_api_key"].strip(),
                base_url=st.session_state["ifs1_base_url"].strip(),
                model=st.session_state["ifs1_model"].strip() or "gpt-4.1-mini",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(st.session_state["ifs1_temperature"]),
            )
            if error:
                st.warning(f"Live call failed. Using offline output. {error}")
            elif live_content.strip():
                content = live_content
                source = "live"

        st.session_state["ifs1_script_output"] = content
        st.session_state["ifs1_status"] = f"Script pack generated ({source})."
        _save_history("Script", source, content)

    if st.session_state["ifs1_script_output"]:
        st.markdown(st.session_state["ifs1_script_output"])
        st.download_button(
            "Download Script Pack",
            data=st.session_state["ifs1_script_output"],
            file_name="app1_script_pack.md",
            mime="text/markdown",
            use_container_width=True,
            key="ifs1_dl_script",
        )


def _storyboard_tab() -> None:
    st.subheader("Storyboard Builder")

    default_scene = "A high-stakes decision under pressure."
    if st.session_state["ifs1_script_output"]:
        default_scene = st.session_state["ifs1_script_output"][:180]

    with st.form("ifs1_story_form"):
        scene = st.text_area("Scene moment to board", value=default_scene, height=100)
        frame_count = st.slider("Frames", 4, 12, 6)
        submitted = st.form_submit_button("Generate Storyboard", type="primary", use_container_width=True)

    if submitted:
        style = st.session_state["ifs1_camera_style"]
        palette = st.session_state["ifs1_palette"]

        offline_output = _offline_storyboard(scene=scene, style=style, palette=palette, frame_count=frame_count)
        source = "offline"
        content = offline_output

        if st.session_state["ifs1_live_enabled"] and st.session_state["ifs1_api_key"].strip():
            system_prompt = "You are a storyboard supervisor. Return practical markdown shot plans."
            user_prompt = textwrap.dedent(
                f"""
                Project: {st.session_state['ifs1_project_title']}
                Tone: {st.session_state['ifs1_tone']}
                Camera style: {style}
                Palette: {palette}
                Scene: {scene}
                Frames: {frame_count}

                Output:
                - Markdown table with columns Frame, Camera, Visual, Sound
                - Then 3 continuity guardrails
                """
            ).strip()
            live_content, error = _call_live(
                api_key=st.session_state["ifs1_api_key"].strip(),
                base_url=st.session_state["ifs1_base_url"].strip(),
                model=st.session_state["ifs1_model"].strip() or "gpt-4.1-mini",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(st.session_state["ifs1_temperature"]),
            )
            if error:
                st.warning(f"Live call failed. Using offline output. {error}")
            elif live_content.strip():
                content = live_content
                source = "live"

        st.session_state["ifs1_storyboard_output"] = content
        st.session_state["ifs1_status"] = f"Storyboard generated ({source})."
        _save_history("Storyboard", source, content)

    if st.session_state["ifs1_storyboard_output"]:
        st.markdown(st.session_state["ifs1_storyboard_output"])
        st.download_button(
            "Download Storyboard",
            data=st.session_state["ifs1_storyboard_output"],
            file_name="app1_storyboard.md",
            mime="text/markdown",
            use_container_width=True,
            key="ifs1_dl_story",
        )


def _edit_tab() -> None:
    st.subheader("Edit Notes")

    with st.form("ifs1_edit_form"):
        pacing = st.selectbox("Pacing", ["Fast", "Balanced", "Slow burn"], index=1)
        objective = st.text_input("Primary objective", value="narrative clarity and emotional punch")
        issues = st.multiselect("Current issues", ISSUE_FLAGS, default=["Too slow in middle"])
        submitted = st.form_submit_button("Generate Edit Notes", type="primary", use_container_width=True)

    if submitted:
        energy = int(st.session_state["ifs1_energy"])
        pace = int(st.session_state["ifs1_pace"])

        offline_output = _offline_edit_notes(
            pacing=pacing,
            objective=objective,
            issues=issues,
            energy=energy,
            pace=pace,
        )
        source = "offline"
        content = offline_output

        if st.session_state["ifs1_live_enabled"] and st.session_state["ifs1_api_key"].strip():
            system_prompt = "You are a senior film editor. Return concise high-leverage notes in markdown."
            user_prompt = textwrap.dedent(
                f"""
                Project: {st.session_state['ifs1_project_title']}
                Tone: {st.session_state['ifs1_tone']}
                Pacing: {pacing}
                Objective: {objective}
                Energy: {energy}/100
                Pace: {pace}/100
                Issues: {', '.join(issues) if issues else 'none'}

                Output:
                - Numbered edit recommendations
                - A short final Priority section
                """
            ).strip()
            live_content, error = _call_live(
                api_key=st.session_state["ifs1_api_key"].strip(),
                base_url=st.session_state["ifs1_base_url"].strip(),
                model=st.session_state["ifs1_model"].strip() or "gpt-4.1-mini",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(st.session_state["ifs1_temperature"]),
            )
            if error:
                st.warning(f"Live call failed. Using offline output. {error}")
            elif live_content.strip():
                content = live_content
                source = "live"

        st.session_state["ifs1_edit_output"] = content
        st.session_state["ifs1_status"] = f"Edit notes generated ({source})."
        _save_history("Edit", source, content)

    if st.session_state["ifs1_edit_output"]:
        st.markdown(st.session_state["ifs1_edit_output"])
        st.download_button(
            "Download Edit Notes",
            data=st.session_state["ifs1_edit_output"],
            file_name="app1_edit_notes.md",
            mime="text/markdown",
            use_container_width=True,
            key="ifs1_dl_edit",
        )


def _history_tab() -> None:
    st.subheader("Recent Outputs")

    history = st.session_state["ifs1_history"]
    if not history:
        st.info("No generations yet.")
        return

    for item in history:
        preview = item["content"][:220].replace("\n", " ").strip()
        st.markdown(
            f"""
            <div class="history-card">
              <h5>[{html.escape(item['kind'])}] source: {html.escape(item['source'])}</h5>
              <p>{html.escape(item['time'])}</p>
              <p>{html.escape(preview)}...</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(page_title="Infinity Film Studio Offline+Live Demo", page_icon="🎬", layout="wide")
    _init_state()
    _inject_styles()

    _top()
    _sidebar()

    tab_script, tab_storyboard, tab_edit, tab_history = st.tabs(["Script", "Storyboard", "Edit", "History"])
    with tab_script:
        _script_tab()
    with tab_storyboard:
        _storyboard_tab()
    with tab_edit:
        _edit_tab()
    with tab_history:
        _history_tab()


if __name__ == "__main__":
    main()

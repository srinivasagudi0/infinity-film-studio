"""Standalone offline Streamlit demo for Infinity Film Studio.

This app intentionally avoids backend and API imports so it always works
without OPENAI_API_KEY or external services.
"""

from __future__ import annotations

import random
import textwrap

import streamlit as st


GENRES = [
    "Sci-Fi",
    "Thriller",
    "Drama",
    "Mystery",
    "Action",
    "Comedy",
]

TONES = [
    "Hopeful",
    "Dark",
    "Bittersweet",
    "Urgent",
    "Whimsical",
]

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


def seed_for(*parts: str) -> int:
    text = "|".join(parts).strip().lower()
    return abs(hash(text)) % (2**31)


def make_logline(
    genre: str,
    tone: str,
    protagonist: str,
    setting: str,
    goal: str,
    obstacle: str,
) -> str:
    return (
        f"A {tone.lower()} {genre.lower()} short film where {protagonist} must {goal} in "
        f"{setting}, but {obstacle} threatens to break the mission."
    )


def make_beats(logline: str) -> list[str]:
    rng = random.Random(seed_for(logline))
    pivots = [
        "a leaked recording",
        "a failed rehearsal",
        "an impossible deadline",
        "an anonymous message",
        "a missing memory shard",
        "a locked archive",
    ]
    costs = [
        "trust",
        "time",
        "reputation",
        "the team dynamic",
        "their backup plan",
    ]
    reveal = rng.choice(pivots)
    cost = rng.choice(costs)
    return [
        "Opening image: Show the world and emotional weather in one striking visual.",
        "Setup: Establish what the protagonist wants and why now.",
        "Catalyst: A disruption forces a decision.",
        f"Debate: The team hesitates after {reveal}.",
        "Break into action: The plan starts moving fast.",
        f"Midpoint: A partial win raises stakes and costs {cost}.",
        "All is lost: The core strategy collapses.",
        "Finale: Rebuild from truth, execute a riskier final move, and resolve the arc.",
    ]


def make_scene_excerpt(protagonist: str, goal: str, tone: str) -> str:
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

        Tone target: {tone}.
        """
    ).strip()


def make_storyboard(scene: str, style: str, palette: str) -> list[dict[str, str]]:
    base = scene.strip() or "The key dramatic moment"
    return [
        {
            "shot": "Frame 1 - Establish",
            "camera": f"Wide shot, {style.lower()}",
            "visual": f"{base} begins in a layered environment with clear foreground depth.",
            "sound": "Low atmosphere, distant mechanical hum.",
        },
        {
            "shot": "Frame 2 - Intent",
            "camera": "Medium push-in",
            "visual": "Protagonist commits to action; eyes locked on objective.",
            "sound": "Heartbeat-like percussion enters.",
        },
        {
            "shot": "Frame 3 - Complication",
            "camera": "Over-shoulder, slight tilt",
            "visual": "Unexpected obstacle appears and blocks the clean path.",
            "sound": "Sharp transient cue, then room tone drops.",
        },
        {
            "shot": "Frame 4 - Pivot",
            "camera": "Closeup on hands / controls",
            "visual": f"Decision point framed with {palette.lower()} lighting accents.",
            "sound": "Breath, cloth rustle, one emphasized click.",
        },
        {
            "shot": "Frame 5 - Consequence",
            "camera": "Fast lateral move",
            "visual": "System responds; environment shifts visibly in the background.",
            "sound": "Rising tonal swell, warning beeps.",
        },
        {
            "shot": "Frame 6 - Resolve",
            "camera": "Locked-off final composition",
            "visual": "Aftermath image that reflects emotional outcome.",
            "sound": "Silence, then one signature final sound.",
        },
    ]


def make_edit_notes(pacing: str, objective: str, issue_flags: list[str]) -> list[str]:
    notes = [
        f"Pacing preset: {pacing}. Prioritize {objective.lower()} in first 45 seconds.",
        "Front-load the strongest visual by moving it into the first 10 seconds.",
        "Use L-cuts to keep momentum through exposition lines.",
    ]
    if "Dialogue muddy" in issue_flags:
        notes.append("Denoise dialogue and add a 2-3 kHz presence boost for clarity.")
    if "Too slow in middle" in issue_flags:
        notes.append("Trim 15-20% from the midpoint beat and replace one transition with a hard cut.")
    if "Looks flat" in issue_flags:
        notes.append("Add contrast curve and separate subject/background with selective saturation.")
    if "Confusing geography" in issue_flags:
        notes.append("Insert one orienting wide shot before the conflict peak.")
    notes.append("End on a 1-2 second hold after the final impact moment.")
    return notes


def script_tab() -> None:
    st.subheader("Script Lab (Offline)")
    genre = st.selectbox("Genre", GENRES, index=0)
    tone = st.selectbox("Tone", TONES, index=3)
    protagonist = st.text_input("Protagonist", value="A rookie location sound engineer")
    setting = st.text_input("Setting", value="a storm-hit floating megacity")
    goal = st.text_input("Goal", value="transmit one clean signal before sunrise")
    obstacle = st.text_input("Main obstacle", value="a corrupted control grid and a traitor on comms")

    if st.button("Generate Script Pack", type="primary"):
        logline = make_logline(genre, tone, protagonist, setting, goal, obstacle)
        beats = make_beats(logline)
        scene = make_scene_excerpt(protagonist, goal, tone)

        st.markdown("### Logline")
        st.write(logline)
        st.markdown("### 8-Beat Outline")
        for index, beat in enumerate(beats, 1):
            st.write(f"{index}. {beat}")
        st.markdown("### Scene Excerpt")
        st.code(scene, language="markdown")

        st.session_state["ifs_logline"] = logline
        st.session_state["ifs_scene"] = scene


def storyboard_tab() -> None:
    st.subheader("Storyboard Builder (Offline)")
    scene = st.text_area(
        "Scene moment to board",
        value=st.session_state.get("ifs_logline", "A high-stakes decision under pressure."),
        height=80,
    )
    style = st.selectbox("Camera style", CAMERA_STYLES, index=0)
    palette = st.selectbox("Palette", PALETTES, index=0)

    if st.button("Generate Storyboard", type="primary"):
        frames = make_storyboard(scene, style, palette)
        for frame in frames:
            st.markdown(f"### {frame['shot']}")
            st.write(f"Camera: {frame['camera']}")
            st.write(f"Visual: {frame['visual']}")
            st.write(f"Sound: {frame['sound']}")


def edit_tab() -> None:
    st.subheader("Edit Notes (Offline)")
    pacing = st.selectbox("Pacing", ["Fast", "Balanced", "Slow burn"], index=1)
    objective = st.text_input("Primary objective", value="narrative clarity and emotional punch")
    issues = st.multiselect(
        "Current issues",
        ["Dialogue muddy", "Too slow in middle", "Looks flat", "Confusing geography"],
        default=["Too slow in middle"],
    )

    if st.button("Generate Edit Notes", type="primary"):
        notes = make_edit_notes(pacing, objective, issues)
        for index, note in enumerate(notes, 1):
            st.write(f"{index}. {note}")


def main() -> None:
    st.set_page_config(page_title="Infinity Film Studio Offline Demo", layout="wide")
    st.title("Infinity Film Studio - Offline Demo")
    st.caption("Runs without API keys, backend services, or internet access.")

    tab1, tab2, tab3 = st.tabs(["Script", "Storyboard", "Edit"])
    with tab1:
        script_tab()
    with tab2:
        storyboard_tab()
    with tab3:
        edit_tab()


if __name__ == "__main__":
    main()

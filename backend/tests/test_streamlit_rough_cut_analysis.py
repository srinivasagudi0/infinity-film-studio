"""Rough-cut analysis helper tests for the Streamlit app."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app import (
    _build_cut_segments,
    _fallback_rough_cut_rows,
    _rough_cut_rows_summary,
    _rough_cut_rows_to_csv,
)


def test_build_cut_segments_merges_tiny_tail():
    rows = _build_cut_segments(duration_seconds=61, segment_seconds=20)
    assert rows[0] == {"start": 0, "end": 20, "length": 20}
    assert rows[-1]["end"] == 61
    assert all(item["end"] > item["start"] for item in rows)


def test_rough_cut_rows_and_exports():
    rows = _fallback_rough_cut_rows(
        project="Neon Corridor",
        objective="narrative clarity",
        pacing="Balanced",
        issues=["Too slow in middle", "Confusing geography"],
        tone="Urgent",
        focus="Character emotion",
        energy=70,
        pace=58,
        duration_seconds=72,
        segment_seconds=18,
        notes="Cut feels slow at midpoint.\nNeed better geography before peak.",
        file_name="rough_cut_v1.mp4",
    )

    assert rows
    assert rows[0]["timestamp"].count(":") >= 1
    assert {"priority", "issue", "action"}.issubset(rows[0].keys())

    csv_text = _rough_cut_rows_to_csv(rows)
    assert "timestamp,priority,focus,issue,observation,action,confidence" in csv_text

    summary = _rough_cut_rows_summary(rows)
    assert "Priorities ->" in summary
    assert "Top issue clusters ->" in summary

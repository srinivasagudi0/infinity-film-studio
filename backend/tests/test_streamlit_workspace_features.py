"""Workspace persistence/export helper tests for the Streamlit app."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app import (  # noqa: E402
    _compare_workspace_snapshots,
    _list_workspace_stores,
    _read_workspace_store,
    _save_workspace_version,
    _shot_list_csv,
    _workspace_export_payloads,
)


def _sample_snapshot(version_label: str, deck_suffix: str = ""):
    return {
        "saved_at": "2026-02-24T17:00:00",
        "project_title": "Neon Corridor",
        "settings": {
            "ifs_project_title": "Neon Corridor",
            "ifs_genre": "Sci-Fi",
            "ifs_tone": "Urgent",
            "ifs_camera_style": "Steady cinematic",
            "ifs_palette": "Neon cyan + amber",
            "ifs_energy": 70,
            "ifs_pace": 58,
            "ifs_script_prompt": "A rescue pilot returns to a city that no longer remembers her.",
            "ifs_story_prompt": "A tense confrontation in a transit hub.",
            "ifs_edit_objective": "narrative clarity and emotional punch",
        },
        "outputs": {
            "ifs_script_output": "### Logline\nA sci-fi thriller.\n\n### 8-Beat Outline\n1. Setup\n",
            "ifs_storyboard_output": (
                "### Shot Grid\n"
                "| Frame | Camera | Visual | Sound |\n"
                "|---|---|---|---|\n"
                "| 1 | Wide establish | Hub exterior | Low hum |\n"
                "| 2 | Medium push-in | Pilot steps in | Pulse rises |\n"
            ),
            "ifs_edit_output": "1. Tighten the opening by 12 frames.\n",
            "ifs_rough_cut_output": "### Rough Cut Snapshot\n- Clip length: 01:20\n",
            "ifs_deck_output": f"### Director Deck\n- Version: {version_label}{deck_suffix}\n",
            "ifs_rough_cut_timeline_rows": [
                {
                    "timestamp": "00:00-00:20",
                    "priority": "High",
                    "focus": "Character emotion",
                    "issue": "Too slow in middle",
                    "observation": "Hold runs long.",
                    "action": "Trim 10 frames.",
                    "confidence": "0.72",
                }
            ],
            "ifs_rough_cut_timeline_csv": "",
            "ifs_rough_cut_timeline_json": "",
            "ifs_rough_cut_metadata": {"file_name": "cut_v1.mp4", "duration_seconds": 80},
        },
        "history": [],
        "summary": {
            "has_script": True,
            "has_storyboard": True,
            "has_edit": True,
            "has_rough_cut": True,
            "has_deck": True,
            "rough_cut_flags": 1,
        },
    }


def test_workspace_save_list_read_and_compare(tmp_path, monkeypatch):
    monkeypatch.setenv("IFS_WORKSPACE_ROOT", str(tmp_path))

    snap_v1 = _sample_snapshot("v1")
    snap_v2 = _sample_snapshot("v2", deck_suffix=" updated")
    snap_v2["outputs"]["ifs_edit_output"] = "1. Tighten opening.\n2. Add orienting wide.\n"

    first = _save_workspace_version("Neon Corridor", "initial", snap_v1)
    second = _save_workspace_version("Neon Corridor", "after notes", snap_v2)

    assert first["project_id"] == second["project_id"]
    assert first["version_id"] == "v001"
    assert second["version_id"] == "v002"

    stores = _list_workspace_stores()
    assert len(stores) == 1
    assert stores[0]["version_count"] == 2

    store = _read_workspace_store(first["project_id"])
    assert store is not None
    assert len(store["versions"]) == 2

    summary, diff_map = _compare_workspace_snapshots(
        store["versions"][0]["snapshot"],
        store["versions"][1]["snapshot"],
        "v001",
        "v002",
    )
    assert "Version Compare" in summary
    assert diff_map
    assert "Director Deck" in diff_map or "Edit Notes" in diff_map


def test_workspace_exports_include_pdf_bundle_fountain_and_csv():
    snapshot = _sample_snapshot("v3")
    payloads = _workspace_export_payloads(snapshot)

    assert {"bundle_md", "fountain", "shot_csv", "deck_pdf", "project_json"}.issubset(payloads.keys())

    bundle_name, bundle_data, bundle_mime = payloads["bundle_md"]
    assert bundle_name.endswith(".md")
    assert bundle_mime == "text/markdown"
    assert "# Neon Corridor Workspace Bundle" in bundle_data

    fountain_name, fountain_data, _ = payloads["fountain"]
    assert fountain_name.endswith(".fountain")
    assert "Title: Neon Corridor" in fountain_data

    shot_name, shot_data, shot_mime = payloads["shot_csv"]
    assert shot_name.endswith(".csv")
    assert shot_mime == "text/csv"
    assert "shot_number,frame,camera,visual,sound" in shot_data

    pdf_name, pdf_data, pdf_mime = payloads["deck_pdf"]
    assert pdf_name.endswith(".pdf")
    assert pdf_mime == "application/pdf"
    assert isinstance(pdf_data, (bytes, bytearray))
    assert bytes(pdf_data).startswith(b"%PDF")

    raw_csv = _shot_list_csv(snapshot["outputs"]["ifs_storyboard_output"])
    assert "Wide establish" in raw_csv

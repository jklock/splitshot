"""Tests for v1→v2 project migration roundtrip."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from splitshot.domain.models import (
    Project,
    ProjectStage,
    VideoAsset,
    project_from_dict,
    project_to_dict,
)
from splitshot.persistence.projects import load_project, save_project


def test_legacy_load_produces_valid_v2_save():
    """A legacy v1 project dict should load, migrate, and re-save as valid v2."""
    v1_data = {
        "id": "migtest",
        "name": "Migration Test",
        "schema_version": 1,
        "primary_video": {
            "path": "/fake/media/run.mp4",
            "duration_ms": 15000,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "audio_sample_rate": 48000,
            "rotation": 0,
            "is_still_image": False,
        },
        "secondary_video": None,
        "merge_sources": [
            {
                "id": "ms1",
                "asset": {
                    "path": "/fake/media/added.mp4",
                    "duration_ms": 12000,
                    "width": 1920,
                    "height": 1080,
                    "fps": 30.0,
                    "audio_sample_rate": 48000,
                    "rotation": 0,
                    "is_still_image": False,
                },
                "angle_role": "follow",
                "sync_offset_ms": 0,
                "placement": {},
                "trim_derivative": {},
            }
        ],
        "scoring": {
            "enabled": True,
            "ruleset": "uspsa_minor",
            "stage_number": 1,
            "competitor_name": "Test Shooter",
            "practiscore_source_path": "",
            "practiscore_source_name": "",
            "penalties": 0.0,
            "point_map": {},
            "penalty_counts": {},
            "hit_factor": None,
            "imported_stage": {
                "source_name": "test_match.csv",
                "source_path": "",
                "match_type": "uspsa",
                "competitor_name": "Test Shooter",
                "stage_number": 1,
                "stage_name": "Bay 1",
                "division": "Open",
                "classification": "GM",
            },
        },
        "analysis": {
            "shots": [],
            "events": [],
            "waveform_primary": [],
            "waveform_secondary": [],
        },
        "overlay": {},
        "popups": [],
        "popup_template": {},
        "merge": {"layout": "side_by_side", "pip_size": "35%"},
        "export": {"quality": "high", "preset": "source"},
        "ui_state": {"active_tool": "project"},
    }

    p = project_from_dict(v1_data)

    # Migration assertions
    assert p.schema_version == 2
    assert len(p.stages) == 1
    assert p.active_stage_id == p.stages[0].id

    stage = p.stages[0]
    assert stage.primary_media.path == "/fake/media/run.mp4"
    assert len(stage.added_media) == 1
    assert stage.added_media[0].asset.path == "/fake/media/added.mp4"
    assert stage.label == "Bay 1"
    assert stage.order_index == 1
    assert stage.imported_stage_number == 1
    assert stage.imported_stage_name == "Bay 1"
    assert stage.scoring.enabled is True
    assert stage.scoring.competitor_name == "Test Shooter"
    assert stage.merge.layout.value == "side_by_side"

    # Re-save and re-load
    d = project_to_dict(p)
    assert d["schema_version"] == 2
    assert len(d["stages"]) == 1

    p2 = project_from_dict(d)
    assert len(p2.stages) == 1
    assert p2.stages[0].label == "Bay 1"
    assert p2.stages[0].primary_media.path == "/fake/media/run.mp4"

    # Verify legacy fields are still populated for backward compat
    assert p2.primary_video.path == "/fake/media/run.mp4"
    assert len(p2.merge_sources) == 1
    assert p2.scoring.competitor_name == "Test Shooter"


def test_v1_without_imported_stage_uses_fallback_label():
    v1_data = {
        "id": "nostage",
        "name": "No Stage Info",
        "schema_version": 1,
        "primary_video": {
            "path": "/fake/video.mp4",
            "duration_ms": 5000,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
        },
        "merge_sources": [],
        "scoring": {"enabled": True, "ruleset": "uspsa_minor"},
        "analysis": {"shots": []},
        "overlay": {},
        "merge": {},
        "export": {},
        "ui_state": {},
    }
    p = project_from_dict(v1_data)
    assert len(p.stages) == 1
    assert p.stages[0].label == "Stage 1"
    assert p.stages[0].order_index == 1


def test_v2_project_saved_and_loaded_roundtrip():
    """Save a v2 project to disk and reload it, verifying stages and queue persist."""
    p = Project()
    s1 = ProjectStage(
        id="s1",
        label="Stage 1",
        order_index=1,
        primary_media=VideoAsset(
            path="/tmp/test.mp4", duration_ms=5000, width=1920, height=1080, fps=30.0
        ),
    )
    s2 = ProjectStage(id="s2", label="Stage 2", order_index=2)
    p.stages = [s1, s2]
    p.active_stage_id = "s1"
    p.schema_version = 2
    p.practiscore_source_file = "match.csv"

    with TemporaryDirectory() as tmpdir:
        proj_dir = Path(tmpdir) / "test-project.splitshot"
        save_project(p, proj_dir)
        assert (proj_dir / "project.json").exists()

        loaded = load_project(str(proj_dir))
        assert len(loaded.stages) == 2
        assert loaded.stages[0].label == "Stage 1"
        assert loaded.stages[1].label == "Stage 2"
        assert loaded.active_stage_id == "s1"
        assert loaded.schema_version == 2
        assert Path(loaded.practiscore_source_file) == (proj_dir / "match.csv").resolve()

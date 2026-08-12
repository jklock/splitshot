"""Tests for the v107 multi-stage project model, migration, and queue operations."""

from __future__ import annotations

from splitshot.domain.models import (
    Project,
    ProjectStage,
    QueueEntry,
    QueueStatus,
    CombinedExportSettings,
    CombinedExportMode,
    OutputProfile,
    QueueSettings,
    VideoAsset,
    project_to_dict,
    project_from_dict,
    stage_to_dict,
    _stage_from_dict,
    output_profile_from_dict,
    output_profile_to_dict,
)


def test_project_has_stages_and_queue_fields():
    p = Project()
    assert p.stages == []
    assert p.active_stage_id == ""
    assert p.queue == []
    assert p.schema_version == 1
    assert isinstance(p.combined_export_settings, CombinedExportSettings)
    assert isinstance(p.queue_settings, QueueSettings)
    assert p.queue_settings.fade_in_s == 0.5
    assert p.queue_settings.fade_out_s == 0.5


def test_project_stage_defaults():
    s = ProjectStage()
    assert s.id
    assert s.label == ""
    assert s.order_index == 1
    assert isinstance(s.primary_media, VideoAsset)
    assert s.added_media == []
    assert s.queue_status == QueueStatus.NOT_QUEUED


def test_active_stage_returns_first_when_no_explicit_id():
    p = Project()
    s1 = ProjectStage(id="s1", label="Stage 1", order_index=1)
    s2 = ProjectStage(id="s2", label="Stage 2", order_index=2)
    p.stages = [s1, s2]
    assert p.active_stage is not None
    assert p.active_stage.id == "s1"


def test_active_stage_returns_explicit_id():
    p = Project()
    s1 = ProjectStage(id="s1", label="Stage 1", order_index=1)
    s2 = ProjectStage(id="s2", label="Stage 2", order_index=2)
    p.stages = [s1, s2]
    p.active_stage_id = "s2"
    assert p.active_stage is not None
    assert p.active_stage.id == "s2"


def test_active_stage_returns_none_for_empty_stages():
    p = Project()
    assert p.active_stage is None


def test_v1_migration_creates_single_stage():
    old_data = {
        "id": "test123",
        "name": "Test Match",
        "schema_version": 1,
        "primary_video": {
            "path": "media/run1.mp4",
            "duration_ms": 10000,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
        },
        "scoring": {"enabled": True, "stage_number": 3, "ruleset": "uspsa_minor"},
        "analysis": {"shots": []},
        "overlay": {},
        "merge": {},
        "export": {},
        "merge_sources": [],
        "ui_state": {},
    }
    p = project_from_dict(old_data)
    assert len(p.stages) == 1
    assert p.schema_version == 2
    assert p.stages[0].primary_media.path == "media/run1.mp4"
    assert p.stages[0].scoring.stage_number == 3
    assert p.active_stage_id == p.stages[0].id


def test_v2_roundtrip_preserves_stages_and_queue():
    # Create a v2 project with stages and a queue entry
    p = Project()
    s1 = ProjectStage(
        id="s1",
        label="Bay 1",
        order_index=1,
        primary_media=VideoAsset(
            path="media/s1.mp4", duration_ms=5000, width=1920, height=1080, fps=30.0
        ),
    )
    s2 = ProjectStage(id="s2", label="Bay 2", order_index=2)
    p.stages = [s1, s2]
    p.active_stage_id = "s1"
    p.schema_version = 2
    entry = QueueEntry(stage_id="s1", status=QueueStatus.QUEUED)
    p.queue = [entry]
    p.combined_export_settings.separator_enabled = True
    p.combined_export_settings.separator_duration_s = 0.75

    d = project_to_dict(p)
    assert d["schema_version"] == 2
    assert len(d["stages"]) == 2
    assert d["stages"][0]["label"] == "Bay 1"
    assert d["stages"][0]["primary_media"]["path"] == "media/s1.mp4"
    assert d["active_stage_id"] == "s1"
    assert len(d["queue"]) == 1
    assert d["queue"][0]["status"] == "queued"

    p2 = project_from_dict(d)
    assert len(p2.stages) == 2
    assert p2.stages[0].label == "Bay 1"
    assert p2.stages[0].primary_media.path == "media/s1.mp4"
    assert p2.active_stage_id == "s1"
    assert len(p2.queue) == 1
    assert p2.queue[0].status == QueueStatus.QUEUED


def test_v2_roundtrip_active_stage_fallback():
    """V2 roundtrip preserves stages from the data; empty is empty."""
    d = project_to_dict(Project())
    p = project_from_dict(d)
    assert p.schema_version == 2
    # Empty v2 project has no stages (nothing to migrate); that's valid.
    assert p.active_stage_id == ""


def test_queue_entry_references_stage_id():
    entry = QueueEntry(stage_id="stage-abc", status=QueueStatus.QUEUED)
    assert entry.stage_id == "stage-abc"
    assert entry.status == QueueStatus.QUEUED
    assert entry.id  # auto-generated
    assert entry.error_message == ""


def test_combined_export_settings_defaults():
    s = CombinedExportSettings()
    assert s.mode == CombinedExportMode.PLAIN_STITCH
    assert s.separator_enabled is False
    assert s.separator_duration_s == 0.5
    assert s.separator_text == ""
    assert s.separator_image_path == ""


def test_stage_to_dict_and_back():
    s = ProjectStage(
        id="abc",
        label="Bay 3 — Standards",
        order_index=3,
        imported_stage_number=3,
        imported_stage_name="Standards",
        primary_media=VideoAsset(
            path="/tmp/test.mp4", duration_ms=8000, width=1920, height=1080, fps=29.97
        ),
        queue_status=QueueStatus.QUEUED,
        presentation_overridden=True,
    )
    d = stage_to_dict(s)
    assert d["id"] == "abc"
    assert d["label"] == "Bay 3 — Standards"
    assert d["order_index"] == 3
    assert d["primary_media"]["path"] == "/tmp/test.mp4"
    assert d["queue_status"] == "queued"
    assert d["presentation_overridden"] is True

    s2 = _stage_from_dict(d)
    assert s2.id == "abc"
    assert s2.label == "Bay 3 — Standards"
    assert s2.order_index == 3
    assert s2.primary_media.path == "/tmp/test.mp4"
    assert s2.queue_status == QueueStatus.QUEUED
    assert s2.presentation_overridden is True


def test_review_comparison_context_round_trips_for_export() -> None:
    project = Project()
    project.scoring.comparison_competitors = [
        {
            "name": "Other Shooter",
            "place": 2,
            "division": "Carry Optics",
            "classification": "Sharpshooter",
        }
    ]

    restored = project_from_dict(project_to_dict(project))

    assert restored.scoring.comparison_competitors == project.scoring.comparison_competitors


def test_legacy_with_merge_sources_migrates_correctly():
    old_data = {
        "id": "test123",
        "name": "Test Match",
        "schema_version": 1,
        "primary_video": {
            "path": "media/primary.mp4",
            "duration_ms": 10000,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
        },
        "merge_sources": [
            {
                "id": "ms1",
                "asset": {
                    "path": "media/added1.mp4",
                    "duration_ms": 8000,
                    "width": 1920,
                    "height": 1080,
                    "fps": 30.0,
                },
                "angle_role": "follow",
            }
        ],
        "scoring": {"enabled": True},
        "analysis": {"shots": []},
        "overlay": {},
        "merge": {},
        "export": {},
        "ui_state": {},
    }
    p = project_from_dict(old_data)
    assert len(p.stages) == 1
    assert len(p.stages[0].added_media) == 1
    assert p.stages[0].added_media[0].asset.path == "media/added1.mp4"


def test_queue_status_enum_values():
    assert QueueStatus.NOT_QUEUED.value == "not_queued"
    assert QueueStatus.QUEUED.value == "queued"
    assert QueueStatus.PROCESSING.value == "processing"
    assert QueueStatus.COMPLETE.value == "complete"
    assert QueueStatus.FAILED.value == "failed"
    assert QueueStatus.STALE.value == "stale"


def test_combined_export_mode_enum_values():
    assert CombinedExportMode.PLAIN_STITCH.value == "plain_stitch"
    assert CombinedExportMode.SEPARATOR.value == "separator"


def test_project_serializes_combined_export_settings():
    p = Project()
    p.combined_export_settings.mode = CombinedExportMode.SEPARATOR
    p.combined_export_settings.separator_enabled = True
    p.combined_export_settings.separator_duration_s = 1.0
    p.combined_export_settings.separator_text = "Next Stage"

    d = project_to_dict(p)
    ces = d["combined_export_settings"]
    assert ces["mode"] == "separator"
    assert ces["separator_enabled"] is True
    assert ces["separator_duration_s"] == 1.0
    assert ces["separator_text"] == "Next Stage"


def test_project_round_trips_queue_fade_settings():
    project = Project()
    project.queue_settings.fade_in_s = 0.75
    project.queue_settings.fade_out_s = 1.25

    restored = project_from_dict(project_to_dict(project))

    assert restored.queue_settings.fade_in_s == 0.75
    assert restored.queue_settings.fade_out_s == 1.25


def test_queue_settings_migrate_invalid_values_to_defaults():
    project = Project()
    project.schema_version = 2
    payload = project_to_dict(project)
    payload["queue_settings"] = {"fade_in_s": "bad", "fade_out_s": -1}

    restored = project_from_dict(payload)

    assert restored.queue_settings.fade_in_s == 0.5
    assert restored.queue_settings.fade_out_s == 0.5


def test_output_profile_validates_persistent_export_settings():
    profile = OutputProfile(
        profile_name="Vertical",
        export_settings={
            "quality": "medium",
            "aspect_ratio": "9:16",
            "video_codec": "h264",
            "video_bitrate_mbps": 12,
            "output_path": "/ignored/output.mp4",
            "last_log": "ignored",
        },
    )

    restored = output_profile_from_dict(output_profile_to_dict(profile))

    assert restored.export_settings["quality"] == "medium"
    assert restored.export_settings["aspect_ratio"] == "9:16"
    assert restored.export_settings["video_bitrate_mbps"] == 12
    assert "output_path" not in restored.export_settings
    assert "last_log" not in restored.export_settings


def test_schema_version_bumped_on_save():
    p = Project(schema_version=1)
    d = project_to_dict(p)
    assert d["schema_version"] == 2

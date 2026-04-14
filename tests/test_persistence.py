from __future__ import annotations

from pathlib import Path

from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    ExportPreset,
    ImportedStageScore,
    MergeLayout,
    OverlayPosition,
    MergeSource,
    Project,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    ShotSource,
    VideoAsset,
    project_from_dict,
    project_to_dict,
)
from splitshot.persistence.projects import load_project, save_project


def test_project_round_trip_preserves_feature_state(tmp_path: Path) -> None:
    project = Project(name="Round Trip")
    project.description = "Project details and merge media should persist."
    project.primary_video = VideoAsset(path="/tmp/input.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    project.merge_sources = [
        MergeSource(
            asset=VideoAsset(
                path="/tmp/merge-image.png",
                duration_ms=0,
                width=320,
                height=180,
                fps=30.0,
                is_still_image=True,
            )
        )
    ]
    project.secondary_video = project.merge_sources[0].asset
    project.analysis.beep_time_ms_primary = 400
    project.analysis.waveform_primary = [0.1, 0.2, 0.3]
    project.analysis.shots = [
        ShotEvent(
            time_ms=800,
            source=ShotSource.MANUAL,
            confidence=1.0,
            score=ScoreMark(letter=ScoreLetter.C, x_norm=0.2, y_norm=0.8),
        )
    ]
    project.scoring.enabled = True
    project.scoring.match_type = "idpa"
    project.scoring.stage_number = 2
    project.scoring.competitor_name = "John Klockenkemper"
    project.scoring.competitor_place = 4
    project.scoring.penalties = 10
    project.scoring.penalty_counts = {"procedural_errors": 2}
    project.scoring.imported_stage = ImportedStageScore(
        source_name="IDPA.csv",
        source_path="/tmp/IDPA.csv",
        match_type="idpa",
        competitor_name="John Klockenkemper",
        competitor_place=4,
        stage_number=2,
        stage_name="Stage 2",
        division="CO",
        classification="UN",
        raw_seconds=29.83,
        aggregate_points=5.0,
        final_time=39.83,
        score_counts={"Points Down": 5.0},
    )
    project.overlay.position = OverlayPosition.TOP
    project.overlay.style_type = "rounded"
    project.overlay.spacing = 6
    project.overlay.margin = 4
    project.overlay.max_visible_shots = 8
    project.overlay.shot_quadrant = "top_right"
    project.overlay.shot_direction = "down"
    project.overlay.custom_x = 0.2
    project.overlay.custom_y = 0.3
    project.overlay.bubble_width = 120
    project.overlay.bubble_height = 52
    project.overlay.font_family = "Verdana"
    project.overlay.font_size = 18
    project.overlay.font_bold = False
    project.overlay.font_italic = True
    project.overlay.show_timer = False
    project.overlay.show_score = False
    project.overlay.custom_box_enabled = True
    project.overlay.custom_box_mode = "imported_summary"
    project.overlay.custom_box_text = "Stage review"
    project.overlay.custom_box_quadrant = "middle_middle"
    project.overlay.custom_box_x = 0.5
    project.overlay.custom_box_y = 0.6
    project.merge.enabled = True
    project.merge.layout = MergeLayout.PIP
    project.merge.pip_size_percent = 50
    project.merge.pip_x = 0.2
    project.merge.pip_y = 0.8
    project.export.output_path = "/tmp/export.mp4"
    project.export.preset = ExportPreset.CUSTOM
    project.export.aspect_ratio = AspectRatio.PORTRAIT
    project.export.target_width = 1080
    project.export.target_height = 1920
    project.export.frame_rate = ExportFrameRate.FPS_60
    project.export.video_bitrate_mbps = 20.0
    project.export.last_log = "Encoder command: ffmpeg"

    bundle = save_project(project, tmp_path / "round-trip.ssproj")
    loaded = load_project(bundle)

    assert loaded.name == project.name
    assert loaded.description == project.description
    assert loaded.primary_video.path == project.primary_video.path
    assert len(loaded.merge_sources) == 1
    assert loaded.merge_sources[0].asset.path == "/tmp/merge-image.png"
    assert loaded.merge_sources[0].asset.is_still_image is True
    assert loaded.secondary_video is not None
    assert loaded.secondary_video.path == "/tmp/merge-image.png"
    assert loaded.analysis.beep_time_ms_primary == 400
    assert loaded.analysis.waveform_primary == [0.1, 0.2, 0.3]
    assert len(loaded.analysis.shots) == 1
    assert loaded.analysis.shots[0].score is not None
    assert loaded.analysis.shots[0].score.letter == ScoreLetter.C
    assert loaded.scoring.enabled is True
    assert loaded.scoring.match_type == "idpa"
    assert loaded.scoring.stage_number == 2
    assert loaded.scoring.competitor_name == "John Klockenkemper"
    assert loaded.scoring.competitor_place == 4
    assert loaded.scoring.penalties == 10
    assert loaded.scoring.penalty_counts["procedural_errors"] == 2
    assert loaded.scoring.imported_stage is not None
    assert loaded.scoring.imported_stage.source_name == "IDPA.csv"
    assert loaded.scoring.imported_stage.stage_number == 2
    assert loaded.scoring.imported_stage.aggregate_points == 5.0
    assert loaded.scoring.imported_stage.final_time == 39.83
    assert loaded.overlay.position == OverlayPosition.TOP
    assert loaded.overlay.style_type == "rounded"
    assert loaded.overlay.spacing == 6
    assert loaded.overlay.margin == 4
    assert loaded.overlay.max_visible_shots == 8
    assert loaded.overlay.shot_quadrant == "top_right"
    assert loaded.overlay.shot_direction == "down"
    assert loaded.overlay.custom_x == 0.2
    assert loaded.overlay.custom_y == 0.3
    assert loaded.overlay.bubble_width == 120
    assert loaded.overlay.bubble_height == 52
    assert loaded.overlay.font_family == "Verdana"
    assert loaded.overlay.font_size == 18
    assert loaded.overlay.font_bold is False
    assert loaded.overlay.font_italic is True
    assert loaded.overlay.show_timer is False
    assert loaded.overlay.show_score is False
    assert loaded.overlay.custom_box_enabled is True
    assert loaded.overlay.custom_box_mode == "imported_summary"
    assert loaded.overlay.custom_box_text == "Stage review"
    assert loaded.overlay.custom_box_quadrant == "middle_middle"
    assert loaded.overlay.custom_box_x == 0.5
    assert loaded.overlay.custom_box_y == 0.6
    assert loaded.merge.enabled is True
    assert loaded.merge.layout == MergeLayout.PIP
    assert loaded.merge.pip_size_percent == 50
    assert loaded.merge.pip_x == 0.2
    assert loaded.merge.pip_y == 0.8
    assert loaded.export.output_path == "/tmp/export.mp4"
    assert loaded.export.preset == ExportPreset.CUSTOM
    assert loaded.export.aspect_ratio == AspectRatio.PORTRAIT
    assert loaded.export.target_width == 1080
    assert loaded.export.target_height == 1920
    assert loaded.export.frame_rate == ExportFrameRate.FPS_60
    assert loaded.export.video_bitrate_mbps == 20.0
    assert loaded.export.last_log == "Encoder command: ffmpeg"


def test_project_from_dict_infers_still_image_merge_sources() -> None:
    project = Project(name="Legacy Merge")
    project.primary_video = VideoAsset(path="/tmp/input.mp4", duration_ms=2000, width=640, height=360, fps=30.0)

    legacy = project_to_dict(project)
    legacy["secondary_video"] = {
        "path": "/tmp/merge-image.png",
        "duration_ms": 0,
        "width": 320,
        "height": 180,
        "fps": 30.0,
        "audio_sample_rate": 22050,
        "rotation": 0,
    }

    loaded = project_from_dict(legacy)

    assert loaded.secondary_video is not None
    assert loaded.secondary_video.is_still_image is True
    assert len(loaded.merge_sources) == 1
    assert loaded.merge_sources[0].asset.path == "/tmp/merge-image.png"
    assert loaded.merge_sources[0].asset.is_still_image is True


def test_save_project_bundles_browser_session_media_into_project_bundle(tmp_path: Path) -> None:
    session_dir = tmp_path / "splitshot-browser-session"
    session_dir.mkdir()
    primary_path = session_dir / "1234567890abcdef1234567890abcdef_primary.mp4"
    merge_path = session_dir / "fedcba0987654321fedcba0987654321_merge.mp4"
    primary_path.write_bytes(b"primary-video")
    merge_path.write_bytes(b"merge-video")

    project = Project(name="Bundled Browser Media")
    project.primary_video = VideoAsset(path=str(primary_path), duration_ms=2000, width=640, height=360, fps=30.0)
    merge_asset = VideoAsset(path=str(merge_path), duration_ms=1800, width=320, height=180, fps=30.0)
    project.merge_sources = [MergeSource(asset=merge_asset)]
    project.secondary_video = merge_asset

    bundle = save_project(project, tmp_path / "bundled.ssproj")
    loaded = load_project(bundle)

    assert project.primary_video.path == str(primary_path)
    assert project.merge_sources[0].asset.path == str(merge_path)
    assert loaded.primary_video.path != str(primary_path)
    assert loaded.merge_sources[0].asset.path != str(merge_path)
    assert Path(loaded.primary_video.path).parent == bundle / "media"
    assert Path(loaded.merge_sources[0].asset.path).parent == bundle / "media"
    assert Path(loaded.primary_video.path).read_bytes() == b"primary-video"
    assert Path(loaded.merge_sources[0].asset.path).read_bytes() == b"merge-video"
    assert loaded.secondary_video is not None
    assert loaded.secondary_video.path == loaded.merge_sources[0].asset.path

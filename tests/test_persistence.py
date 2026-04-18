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


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "example_data"


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
            ),
            pip_size_percent=42,
            sync_offset_ms=135,
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
            score=ScoreMark(letter=ScoreLetter.C, x_norm=0.2, y_norm=0.8, penalty_counts={"procedural_errors": 1}),
        )
    ]
    selected_shot_id = project.analysis.shots[0].id
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
    project.overlay.timer_x = 0.15
    project.overlay.timer_y = 0.1
    project.overlay.draw_x = 0.82
    project.overlay.draw_y = 0.12
    project.overlay.score_x = 0.8
    project.overlay.score_y = 0.2
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
    project.ui_state.selected_shot_id = selected_shot_id
    project.ui_state.timeline_zoom = 12.5
    project.ui_state.timeline_offset_ms = 275
    project.ui_state.active_tool = "timing"
    project.ui_state.waveform_mode = "add"
    project.ui_state.waveform_expanded = True
    project.ui_state.timing_expanded = False
    project.ui_state.layout_locked = False
    project.ui_state.rail_width = 68
    project.ui_state.inspector_width = 520
    project.ui_state.waveform_height = 288
    project.ui_state.scoring_shot_expansion = {selected_shot_id: True}
    project.ui_state.waveform_shot_amplitudes = {selected_shot_id: 1.75}
    project.ui_state.timing_edit_shot_ids = [selected_shot_id]

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
    assert loaded.analysis.shots[0].score.penalty_counts == {"procedural_errors": 1}
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
    assert loaded.overlay.timer_x == 0.15
    assert loaded.overlay.timer_y == 0.1
    assert loaded.overlay.draw_x == 0.82
    assert loaded.overlay.draw_y == 0.12
    assert loaded.overlay.score_x == 0.8
    assert loaded.overlay.score_y == 0.2
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
    assert loaded.overlay.custom_box_quadrant == "custom"
    assert loaded.overlay.custom_box_x == 0.5
    assert loaded.overlay.custom_box_y == 0.6
    assert loaded.merge.enabled is True
    assert loaded.merge.layout == MergeLayout.PIP
    assert loaded.merge.pip_size_percent == 50
    assert loaded.merge.pip_x == 0.2
    assert loaded.merge.pip_y == 0.8
    assert loaded.merge_sources[0].pip_size_percent == 42
    assert loaded.merge_sources[0].sync_offset_ms == 135
    assert loaded.analysis.sync_offset_ms == 135
    assert loaded.export.output_path == "/tmp/export.mp4"
    assert loaded.export.preset == ExportPreset.CUSTOM
    assert loaded.export.aspect_ratio == AspectRatio.PORTRAIT
    assert loaded.export.target_width == 1080
    assert loaded.export.target_height == 1920
    assert loaded.export.frame_rate == ExportFrameRate.FPS_60
    assert loaded.export.video_bitrate_mbps == 20.0
    assert loaded.export.last_log == "Encoder command: ffmpeg"
    assert loaded.ui_state.selected_shot_id == selected_shot_id
    assert loaded.ui_state.timeline_zoom == 12.5
    assert loaded.ui_state.timeline_offset_ms == 275
    assert loaded.ui_state.active_tool == "timing"
    assert loaded.ui_state.waveform_mode == "add"
    assert loaded.ui_state.waveform_expanded is True
    assert loaded.ui_state.timing_expanded is False
    assert loaded.ui_state.layout_locked is False
    assert loaded.ui_state.rail_width == 68
    assert loaded.ui_state.inspector_width == 520
    assert loaded.ui_state.waveform_height == 288
    assert loaded.ui_state.scoring_shot_expansion == {selected_shot_id: True}
    assert loaded.ui_state.waveform_shot_amplitudes == {selected_shot_id: 1.75}
    assert loaded.ui_state.timing_edit_shot_ids == [selected_shot_id]


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
    legacy["analysis"]["sync_offset_ms"] = 87

    loaded = project_from_dict(legacy)

    assert loaded.secondary_video is not None
    assert loaded.secondary_video.is_still_image is True
    assert len(loaded.merge_sources) == 1
    assert loaded.merge_sources[0].asset.path == "/tmp/merge-image.png"
    assert loaded.merge_sources[0].asset.is_still_image is True
    assert loaded.merge_sources[0].pip_size_percent == loaded.merge.pip_size_percent
    assert loaded.merge_sources[0].sync_offset_ms == 87
    assert loaded.analysis.sync_offset_ms == 87


def test_project_round_trip_drops_combo_score_color_keys(tmp_path: Path) -> None:
    project = Project(name="Score Colors")
    project.overlay.scoring_colors["A|procedural_errors"] = "#112233"
    project.overlay.scoring_colors["PE"] = "#445566"

    bundle = save_project(project, tmp_path / "score-colors.ssproj")
    loaded = load_project(bundle)

    assert "A|procedural_errors" not in project_to_dict(project)["overlay"]["scoring_colors"]
    assert "A|procedural_errors" not in loaded.overlay.scoring_colors
    assert loaded.overlay.scoring_colors["PE"] == "#445566"


def test_save_project_moves_browser_session_media_into_project_input_folder(tmp_path: Path) -> None:
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

    assert Path(project.primary_video.path).parent == bundle / "Input"
    assert Path(project.merge_sources[0].asset.path).parent == bundle / "Input"
    assert loaded.primary_video.path != str(primary_path)
    assert loaded.merge_sources[0].asset.path != str(merge_path)
    assert Path(loaded.primary_video.path).parent == bundle / "Input"
    assert Path(loaded.merge_sources[0].asset.path).parent == bundle / "Input"
    assert Path(loaded.primary_video.path).name == "primary.mp4"
    assert Path(loaded.merge_sources[0].asset.path).name == "merge.mp4"
    assert Path(loaded.primary_video.path).read_bytes() == b"primary-video"
    assert Path(loaded.merge_sources[0].asset.path).read_bytes() == b"merge-video"
    assert loaded.secondary_video is not None
    assert loaded.secondary_video.path == loaded.merge_sources[0].asset.path


def test_save_project_copies_practiscore_text_reports_into_csv_folder(tmp_path: Path) -> None:
    project = Project(name="PractiScore Report")
    report_path = EXAMPLES_DIR / "USPSA" / "report.txt"
    project.scoring.practiscore_source_path = str(report_path)
    project.scoring.practiscore_source_name = "report.txt"

    bundle = save_project(project, tmp_path / "practiscore-project")
    loaded = load_project(bundle)

    assert Path(project.scoring.practiscore_source_path).parent == bundle / "CSV"
    assert Path(project.scoring.practiscore_source_path).name == "report.txt"
    assert Path(loaded.scoring.practiscore_source_path).parent == bundle / "CSV"
    assert Path(loaded.scoring.practiscore_source_path).read_text() == report_path.read_text()

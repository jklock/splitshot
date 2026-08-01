from __future__ import annotations

import re
from pathlib import Path

from splitshot.domain.models import (
    OverlayTextBox,
    ProjectStage,
    QueueEntry,
    QueueStatus,
    VideoAsset,
    project_from_dict,
    project_to_dict,
)
from splitshot.ui.controller import ProjectController


def test_applying_saved_export_profile_restores_settings_and_stales_queue(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "profile.ssproj"
    controller.project_path.mkdir()
    stage = ProjectStage(label="Stage 1")
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id
    controller.project.export.video_bitrate_mbps = 18.0
    profile = controller.create_output_profile("Match Export")
    controller.project.queue = [QueueEntry(stage_id=stage.id, status=QueueStatus.QUEUED)]
    stage.queue_status = QueueStatus.QUEUED

    controller.project.export.video_bitrate_mbps = 7.0
    controller.apply_output_profile(profile["output_id"])

    assert controller.project.export.video_bitrate_mbps == 18.0
    assert controller.project.queue[0].status == QueueStatus.STALE
    assert stage.queue_status == QueueStatus.STALE


def test_trimmed_derivative_filename_uses_stage_time_date_and_collision_suffix(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "trim.ssproj"
    controller.project_path.mkdir()
    stage = ProjectStage(label="Stage", order_index=2, imported_stage_number=7)
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id

    first = Path(controller._trimmed_derivative_path(tmp_path / "source.mp4"))
    assert re.fullmatch(
        r"Trim_Stage7_\d{2}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.mp4",
        first.name,
    )
    first.touch()
    second = Path(controller._trimmed_derivative_path(tmp_path / "source.mp4"))
    assert second.stem == f"{first.stem}_2"


def test_intro_outro_media_overlays_and_queue_choices_round_trip() -> None:
    controller = ProjectController()
    controller.project.intro_clip.asset = VideoAsset(path="IntroOutro/intro.mp4", duration_ms=5000)
    controller.project.intro_clip.overlay.text_boxes = [
        OverlayTextBox(
            source="match_summary",
            summary_metric_ids=["match_result", "stage_count"],
            text_color="#ffcc00",
        )
    ]
    controller.project.intro_clip.fade_in_s = 0.7
    controller.project.intro_clip.fade_out_s = 0.9
    controller.project.outro_clip.fade_in_s = 1.1
    controller.project.outro_clip.fade_out_s = 1.3
    controller.project.queue_settings.include_intro = True
    controller.project.queue_settings.include_outro = False

    restored = project_from_dict(project_to_dict(controller.project))

    assert restored.intro_clip.asset.path == "IntroOutro/intro.mp4"
    assert restored.intro_clip.overlay.text_boxes[0].source == "match_summary"
    assert restored.intro_clip.overlay.text_boxes[0].summary_metric_ids == [
        "match_result",
        "stage_count",
    ]
    assert restored.intro_clip.overlay.text_boxes[0].text_color == "#ffcc00"
    assert restored.intro_clip.fade_in_s == 0.7
    assert restored.intro_clip.fade_out_s == 0.9
    assert restored.outro_clip.fade_in_s == 1.1
    assert restored.outro_clip.fade_out_s == 1.3
    assert restored.queue_settings.include_intro is True
    assert restored.queue_settings.include_outro is False


def test_match_results_overlay_uses_final_spreadsheet_match_values() -> None:
    controller = ProjectController()
    source = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"
    controller.import_practiscore_file(str(source), source_name="IDPA.csv")
    controller.set_practiscore_context(
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )

    text = controller._match_summary_overlay_text(
        [
            "score_time",
            "raw_time",
            "points_down",
            "penalties",
            "division_placement",
            "class_placement",
            "overall_placement",
        ]
    )

    assert text.splitlines() == [
        "Final 83.01",
        "Points Down 11",
        "Penalties 2",
        "Division CO",
        "Class UN",
        "Overall 4",
    ]
    assert controller._match_summary_overlay_text(
        ["match_result", "shot_points", "penalties", "overall_place"]
    ).splitlines() == [
        "Final 83.01",
        "Points Down 11",
        "Penalties 2",
        "Overall 4",
    ]


def test_intro_outro_clip_fades_drive_video_and_audio_filters(
    tmp_path: Path, monkeypatch
) -> None:
    controller = ProjectController()
    controller.project.intro_clip.fade_in_s = 0.7
    controller.project.intro_clip.fade_out_s = 0.9
    controller.project.outro_clip.fade_in_s = 1.1
    controller.project.outro_clip.fade_out_s = 1.3
    source = tmp_path / "boundary.mp4"
    reference = tmp_path / "reference.mp4"
    captured: list[list[str]] = []

    def fake_probe(path: Path) -> dict[str, object]:
        if path == source:
            return {
                "format": {"duration": "10.0"},
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
            }
        return {
            "format": {"duration": "20.0"},
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "sample_rate": "48000",
                    "channel_layout": "stereo",
                },
            ],
        }

    monkeypatch.setattr("splitshot.ui.controller.run_ffprobe_json", fake_probe)
    monkeypatch.setattr(
        "splitshot.ui.controller.run_ffmpeg",
        lambda command, **_kwargs: captured.append(command),
    )
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    controller._prepare_queue_boundary_clip(source, reference, tmp_path, "intro")
    controller._prepare_queue_boundary_clip(source, reference, tmp_path, "outro")

    intro_video = captured[0][captured[0].index("-vf") + 1]
    intro_audio = captured[0][captured[0].index("-af") + 1]
    outro_video = captured[1][captured[1].index("-vf") + 1]
    outro_audio = captured[1][captured[1].index("-af") + 1]
    assert "fade=t=in:st=0:d=0.700" in intro_video
    assert "fade=t=out:st=9.100:d=0.900" in intro_video
    assert "afade=t=in:st=0:d=0.700" in intro_audio
    assert "afade=t=out:st=9.100:d=0.900" in intro_audio
    assert "fade=t=in:st=0:d=1.100" in outro_video
    assert "fade=t=out:st=8.700:d=1.300" in outro_video
    assert "afade=t=in:st=0:d=1.100" in outro_audio
    assert "afade=t=out:st=8.700:d=1.300" in outro_audio


def test_intro_outro_clip_fades_migrate_to_safe_defaults() -> None:
    payload = project_to_dict(ProjectController().project)
    payload["intro_clip"].pop("fade_in_s")
    payload["intro_clip"].pop("fade_out_s")
    payload["outro_clip"]["fade_in_s"] = "bad"
    payload["outro_clip"]["fade_out_s"] = -1

    restored = project_from_dict(payload)

    assert restored.intro_clip.fade_in_s == 0.5
    assert restored.intro_clip.fade_out_s == 0.5
    assert restored.outro_clip.fade_in_s == 0.5
    assert restored.outro_clip.fade_out_s == 0.5


def test_intro_overlay_uses_export_overlay_renderer_with_match_text(
    tmp_path: Path, monkeypatch
) -> None:
    controller = ProjectController()
    controller.project.stages = [ProjectStage(label="Stage 1")]
    controller.project.active_stage_id = controller.project.stages[0].id
    controller.project.intro_clip.asset = VideoAsset(
        path=str(tmp_path / "intro.mp4"), duration_ms=1000, width=640, height=360
    )
    controller.project.intro_clip.overlay.text_boxes = [
        OverlayTextBox(source="match_summary", summary_metric_ids=["stage_count"])
    ]
    captured = {}

    def fake_export(project, output_path, **_kwargs) -> None:
        captured["project"] = project
        Path(output_path).touch()

    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export)
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    rendered = controller._render_queue_boundary_overlay(
        "intro", tmp_path / "intro.mp4", tmp_path
    )

    boundary_project = captured["project"]
    assert boundary_project.primary_video.path == str(tmp_path / "intro.mp4")
    assert boundary_project.stages == []
    assert boundary_project.overlay.text_boxes[0].source == "manual"
    assert boundary_project.overlay.text_boxes[0].text == "Stages 1"
    assert rendered.is_file()


def test_combined_queue_includes_only_enabled_boundary_media(
    tmp_path: Path, monkeypatch
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "match.ssproj"
    controller.project_path.mkdir()
    controller.project.output_root = str(controller.project_path / "Output")
    primary = controller.project_path / "stage.mp4"
    intro = controller.project_path / "intro.mp4"
    outro = controller.project_path / "outro.mp4"
    for path in (primary, intro, outro):
        path.touch()
    stage = ProjectStage(
        label="Stage 1",
        order_index=1,
        primary_media=VideoAsset(path=str(primary), duration_ms=1000),
    )
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id
    controller._sync_active_stage_to_project()
    controller.project.queue = [QueueEntry(stage_id=stage.id, status=QueueStatus.QUEUED)]
    controller.project.intro_clip.asset = VideoAsset(path=str(intro), duration_ms=1000)
    controller.project.outro_clip.asset = VideoAsset(path=str(outro), duration_ms=1000)
    controller.project.queue_settings.include_intro = True
    controller.project.queue_settings.include_outro = False
    rendered_boundaries: list[str] = []
    concatenated: list[str] = []
    fade_args: list[tuple[float | None, float | None]] = []

    def fake_export(_project, output_path, progress_callback=None, **_kwargs) -> None:
        Path(output_path).touch()
        if progress_callback:
            progress_callback(1.0)

    def fake_boundary(kind, _source, output_dir, **_kwargs) -> Path:
        rendered_boundaries.append(kind)
        path = output_dir / f"{kind}-overlay.mp4"
        path.touch()
        return path

    def fake_prepare(_source, _reference, output_dir, kind, **_kwargs) -> Path:
        path = output_dir / f"{kind}-prepared.mp4"
        path.touch()
        return path

    def fake_concat(paths, output_dir) -> Path:
        concatenated.extend(path.name for path in paths)
        combined = output_dir / "combined.mp4"
        combined.touch()
        return combined

    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export)
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)
    monkeypatch.setattr(controller, "_render_queue_boundary_overlay", fake_boundary)
    monkeypatch.setattr(controller, "_prepare_queue_boundary_clip", fake_prepare)
    monkeypatch.setattr(controller, "_concat_outputs", fake_concat)
    monkeypatch.setattr(
        controller,
        "_apply_queue_fades_to_file",
        lambda _path, *, fade_in_s=None, fade_out_s=None, **_kwargs: fade_args.append(
            (fade_in_s, fade_out_s)
        ),
    )

    controller.process_queue("combined")

    assert rendered_boundaries == ["intro"]
    assert concatenated[0] == "intro-prepared.mp4"
    assert concatenated[1].endswith("1-stage-1.mp4")
    assert fade_args == [(0.0, None)]

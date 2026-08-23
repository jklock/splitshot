from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from splitshot.domain.models import (
    ImportedStageScore,
    OverlayTextBox,
    ProjectStage,
    QueueEntry,
    QueueStatus,
    ShotEvent,
    VideoAsset,
    project_from_dict,
    project_to_dict,
)
from splitshot.media.ffmpeg import run_ffmpeg, run_ffprobe_json
from splitshot.ui.controller import ProjectController


def test_global_settings_primary_preserves_stage_owned_data_and_round_trips(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "global-settings.ssproj"
    controller.project_path.mkdir()
    source = ProjectStage(label="Stage 1", primary_media=VideoAsset(path="one.mp4"))
    target = ProjectStage(label="Stage 2", primary_media=VideoAsset(path="two.mp4"))
    source.overlay.font_size = 42
    source.merge.pip_x = 0.25
    source.export.video_bitrate_mbps = 22.0
    source.analysis.shots = [ShotEvent(time_ms=777)]
    source.scoring.competitor_name = "Source Shooter"
    source.scoring.imported_stage = ImportedStageScore(
        match_type="idpa", stage_number=1, raw_seconds=7.36, final_time=7.36
    )
    target.analysis.shots = [ShotEvent(time_ms=1234)]
    target.scoring.competitor_name = "Target Shooter"
    target.scoring.stage_number = 2
    target.scoring.imported_stage = ImportedStageScore(
        match_type="idpa", stage_number=2, raw_seconds=28.89, final_time=30.89
    )
    controller.project.stages = [source, target]
    controller.project.active_stage_id = source.id
    controller._sync_active_stage_to_project()
    controller.project.analysis.shots = [ShotEvent(time_ms=9999)]
    controller.project.scoring.competitor_name = "Stale Project Shooter"
    controller.project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa", stage_number=1, raw_seconds=99.99, final_time=99.99
    )
    controller.project.queue = [QueueEntry(stage_id=target.id, status=QueueStatus.QUEUED)]
    target.queue_status = QueueStatus.QUEUED

    controller.set_global_settings_primary(source.id)

    assert controller.project.global_settings_stage_id == source.id
    assert [shot.time_ms for shot in source.analysis.shots] == [777]
    assert source.scoring.competitor_name == "Source Shooter"
    assert source.scoring.imported_stage.final_time == 7.36
    assert target.overlay.font_size == 42
    assert target.merge.pip_x == 0.25
    assert target.export.video_bitrate_mbps == 22.0
    assert [shot.time_ms for shot in target.analysis.shots] == [1234]
    assert target.scoring.competitor_name == "Target Shooter"
    assert target.scoring.stage_number == 2
    assert target.scoring.imported_stage.final_time == 30.89

    restored = project_from_dict(project_to_dict(controller.project))
    assert restored.global_settings_stage_id == source.id
    assert restored.stages[1].ignore_global_settings is False


def test_ignore_global_settings_uses_effective_defaults_without_changing_stage_data(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "ignore-global.ssproj"
    controller.project_path.mkdir()
    source = ProjectStage(label="Stage 1", primary_media=VideoAsset(path="one.mp4"))
    target = ProjectStage(label="Stage 2", primary_media=VideoAsset(path="two.mp4"))
    source.overlay.font_size = 64
    target.overlay.font_size = 64
    target.analysis.shots = [ShotEvent(time_ms=2345)]
    target.scoring.stage_number = 2
    controller.project.stages = [source, target]
    controller.project.active_stage_id = target.id
    controller.project.global_settings_stage_id = source.id

    controller.ignore_global_settings(target.id)

    assert target.ignore_global_settings is True
    assert target.overlay.font_size != 64
    assert [shot.time_ms for shot in target.analysis.shots] == [2345]
    assert target.scoring.stage_number == 2
    assert controller.project.primary_video.path == "two.mp4"


def test_queue_renders_immutable_stage_views_with_distinct_analysis_and_scoring(
    monkeypatch, tmp_path: Path
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "immutable-render.ssproj"
    controller.project_path.mkdir()
    first = ProjectStage(label="Stage 1", primary_media=VideoAsset(path="one.mp4"))
    second = ProjectStage(label="Stage 2", primary_media=VideoAsset(path="two.mp4"))
    first.analysis.shots = [ShotEvent(time_ms=1000)]
    second.analysis.shots = [ShotEvent(time_ms=2000), ShotEvent(time_ms=3000)]
    first.scoring.stage_number = 1
    second.scoring.stage_number = 2
    controller.project.stages = [first, second]
    controller.project.active_stage_id = first.id
    controller.project.primary_video = first.primary_media
    controller.project.analysis = first.analysis
    controller.project.scoring = first.scoring
    for stage in (first, second):
        controller.project.queue.append(QueueEntry(stage_id=stage.id, status=QueueStatus.QUEUED))
        stage.queue_status = QueueStatus.QUEUED

    rendered: list[tuple[str, int, int]] = []

    def fake_export(project, output_path, **_kwargs):
        rendered.append(
            (
                Path(project.primary_video.path).name,
                len(project.analysis.shots),
                project.scoring.stage_number,
            )
        )
        Path(output_path).write_bytes(b"rendered")

    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export)
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    controller.process_queue("individual")

    assert rendered == [("one.mp4", 1, 1), ("two.mp4", 2, 2)]
    assert controller.project.active_stage_id == first.id
    assert controller.project.primary_video.path == "one.mp4"
    assert len(controller.project.analysis.shots) == 1


def test_queued_snapshot_remains_render_source_until_stage_is_marked_stale(
    monkeypatch, tmp_path: Path
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "snapshot-render.ssproj"
    controller.project_path.mkdir()
    stage = ProjectStage(label="Stage 1", primary_media=VideoAsset(path="queued.mp4"))
    stage.analysis.shots = [ShotEvent(time_ms=1000)]
    stage.scoring.stage_number = 1
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id
    controller._sync_active_stage_to_project()
    controller.add_stage_to_queue(stage.id)
    stage.primary_media = VideoAsset(path="uncommitted-live-change.mp4")
    stage.analysis.shots = [ShotEvent(time_ms=9000), ShotEvent(time_ms=9500)]
    rendered: list[tuple[str, list[int]]] = []

    def fake_export(project, output_path, **_kwargs):
        rendered.append(
            (Path(project.primary_video.path).name, [shot.time_ms for shot in project.analysis.shots])
        )
        Path(output_path).write_bytes(b"rendered")

    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export)
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    controller.process_queue("individual")

    assert rendered == [("queued.mp4", [1000])]


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
        "Division CO - 2/12",
        "Class UN - 1/7",
        "Overall 4/26",
    ]
    assert controller._match_summary_overlay_text(
        ["match_result", "shot_points", "penalties", "overall_place"]
    ).splitlines() == [
        "Final 83.01",
        "Points Down 11",
        "Penalties 2",
        "Overall 4/26",
    ]


def test_intro_outro_clip_fades_drive_video_and_audio_filters(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(
        "splitshot.ui.controller.probe_video",
        lambda path: VideoAsset(path=str(path), duration_ms=1000, width=640, height=360),
    )
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    rendered = controller._render_queue_boundary_overlay("intro", tmp_path / "intro.mp4", tmp_path)

    boundary_project = captured["project"]
    assert boundary_project.primary_video.path == str(tmp_path / "intro.mp4")
    assert boundary_project.stages == []
    assert boundary_project.overlay.text_boxes[0].source == "manual"
    assert boundary_project.overlay.text_boxes[0].text == "Stages 1"
    assert rendered.is_file()


def test_combined_queue_includes_only_enabled_boundary_media(tmp_path: Path, monkeypatch) -> None:
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
    boundary_steps: list[tuple[str, bool | None]] = []
    concatenated: list[str] = []
    fade_args: list[tuple[float | None, float | None]] = []

    def fake_export(_project, output_path, progress_callback=None, **_kwargs) -> None:
        Path(output_path).touch()
        if progress_callback:
            progress_callback(1.0)

    def fake_boundary(kind, _source, output_dir, **_kwargs) -> Path:
        rendered_boundaries.append(kind)
        boundary_steps.append(("overlay", None))
        path = output_dir / f"{kind}-overlay.mp4"
        path.touch()
        return path

    def fake_prepare(_source, _reference, output_dir, kind, **kwargs) -> Path:
        boundary_steps.append(("prepare", kwargs.get("apply_fades", True)))
        path = output_dir / f"{kind}-prepared.mp4"
        path.touch()
        return path

    def fake_concat(paths, output_dir, **_kwargs) -> Path:
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
    assert boundary_steps == [
        ("prepare", False),
        ("overlay", None),
        ("prepare", True),
    ]
    assert concatenated[0] == "intro-prepared.mp4"
    assert concatenated[1].endswith("1-stage-1.mp4")
    assert fade_args == [(0.0, None)]


def test_combined_output_uses_dated_name_in_output_directory(tmp_path: Path, monkeypatch) -> None:
    controller = ProjectController()
    controller.project.name = "08/16/2026 IDPA @ WSRC"
    output_date = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")

    def fake_concat(_results, _output_dir, output_path: Path, **_kwargs) -> Path:
        assert output_path.parent == tmp_path
        output_path.touch()
        return output_path

    monkeypatch.setattr(controller, "_plain_concat", fake_concat)
    monkeypatch.setattr(controller, "_validate_rendered_output", lambda _path: None)

    combined_path = controller._concat_outputs([tmp_path / "stage.mp4"], tmp_path)

    assert combined_path == tmp_path / f"Combined-{output_date}.mp4"
    assert combined_path.is_file()


def test_plain_concat_normalizes_mixed_frame_rate_timelines(tmp_path: Path) -> None:
    controller = ProjectController()
    clips: list[Path] = []
    for frame_rate in (30, 60):
        clip = tmp_path / f"clip-{frame_rate}.mp4"
        run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s=320x180:r={frame_rate}:d=0.6",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:sample_rate=48000:duration=0.6",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(clip),
            ]
        )
        clips.append(clip)

    combined = tmp_path / "Combined-2026-08-23.mp4"
    controller._plain_concat(clips, tmp_path, combined)

    metadata = run_ffprobe_json(combined)
    video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
    assert 1.1 <= float(video["duration"]) <= 1.4
    assert 1.1 <= float(audio["duration"]) <= 1.4
    assert abs(float(video["duration"]) - float(audio["duration"])) < 0.1

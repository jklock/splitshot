from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.domain.models import AspectRatio, ExportFrameRate, MergeLayout, MergeSource, OverlayPosition, Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.export.pipeline import _is_expected_decoder_pipe_shutdown, export_project
from splitshot.export.presets import apply_export_preset, export_presets_for_api
from splitshot.media.probe import probe_video
from splitshot.overlay.render import OverlayRenderer
from splitshot.scoring.logic import apply_scoring_preset


def _ffprobe_json(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _frame_rgb(path: Path, timestamp: float) -> np.ndarray:
    metadata = _ffprobe_json(path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(height, width, 3)


def test_export_writes_mp4_with_requested_crop(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory()
    project = Project(name="Export Test")
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.waveform_primary = analysis.waveform
    project.analysis.shots = analysis.shots
    project.overlay.position = OverlayPosition.TOP
    project.export.aspect_ratio = AspectRatio.SQUARE
    project.export.crop_center_x = 0.5
    project.export.crop_center_y = 0.5

    output_path = tmp_path / "export.mp4"
    export_project(project, output_path)

    assert output_path.exists()
    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == int(video_stream["height"])
    assert output_path.stat().st_size > 0
    frame = _frame_rgb(output_path, 0.9)
    assert int(frame.sum()) > 0


def test_export_project_initializes_qt_gui_application_for_headless_runs(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    video_path = synthetic_video_factory()
    project = Project(name="Headless Export Test")
    project.primary_video = probe_video(video_path)

    called = False

    def fake_ensure_qt_gui_application():
        nonlocal called
        called = True
        return None

    monkeypatch.setattr("splitshot.export.pipeline._ensure_qt_gui_application", fake_ensure_qt_gui_application)

    output_path = tmp_path / "headless-export.mp4"
    export_project(project, output_path)

    assert called is True
    assert output_path.exists()


@pytest.mark.parametrize("suffix", [".mov", ".m4v", ".mkv"])
def test_export_supports_common_output_containers(
    synthetic_video_factory,
    tmp_path: Path,
    suffix: str,
) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name=f"Container Export {suffix}")
    project.primary_video = probe_video(video_path)
    project.export.target_width = 160
    project.export.target_height = 90
    project.export.video_bitrate_mbps = 1
    project.export.ffmpeg_preset = "ultrafast"

    output_path = tmp_path / f"container-export{suffix}"
    export_project(project, output_path)

    assert output_path.exists()
    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == 160
    assert int(video_stream["height"]) == 90


def test_export_rejects_unsupported_output_container(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory()
    project = Project(name="Unsupported Container Export")
    project.primary_video = probe_video(video_path)

    with pytest.raises(ValueError, match="Unsupported export format"):
        export_project(project, tmp_path / "export.webm")


def test_export_burns_overlay_badges_into_output_video(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name="Overlay Export Test")
    project.primary_video = probe_video(video_path)
    project.overlay.position = OverlayPosition.TOP
    project.overlay.style_type = "square"
    project.overlay.spacing = 8
    project.overlay.margin = 8
    project.overlay.timer_badge.background_color = "#ff0000"
    project.overlay.timer_badge.text_color = "#ffffff"
    project.overlay.timer_badge.opacity = 1.0
    project.export.target_width = 160
    project.export.target_height = 90
    project.export.video_bitrate_mbps = 1
    project.export.ffmpeg_preset = "ultrafast"

    output_path = tmp_path / "overlay-export.mp4"
    export_project(project, output_path)

    frame = _frame_rgb(output_path, 0.1)
    top_band = frame[:36, :130]
    red_dominant_pixels = (
        (top_band[:, :, 0] > 120)
        & (top_band[:, :, 0] > top_band[:, :, 1] + 40)
        & (top_band[:, :, 0] > top_band[:, :, 2] + 40)
    )
    assert int(red_dominant_pixels.sum()) > 20


def test_overlay_renderer_embeds_score_inside_shot_badge(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name="Scored Overlay")
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.shots = analysis.shots
    project.scoring.enabled = True
    project.overlay.show_score = False
    project.overlay.max_visible_shots = 4
    project.overlay.scoring_colors["C"] = "#00ff00"
    project.analysis.shots[0].score = ScoreMark(letter=ScoreLetter.C)

    badges, score_marks = OverlayRenderer().build_badges(project, project.analysis.shots[0].time_ms + 50)

    assert score_marks == []
    assert any(badge.text.startswith("Shot 1 ") and badge.text.endswith("s C") and badge.text_color == "#00ff00" for badge in badges)


def test_overlay_renderer_shows_draw_only_before_first_shot(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name="Draw Overlay")
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.shots = analysis.shots
    project.overlay.show_timer = False
    project.overlay.show_shots = True
    project.overlay.show_draw = True
    project.overlay.show_score = False

    before_first = OverlayRenderer().build_badges(project, project.analysis.shots[0].time_ms - 1)[0]
    after_first = OverlayRenderer().build_badges(project, project.analysis.shots[0].time_ms + 50)[0]

    assert any(badge.text.startswith("Draw ") for badge in before_first)
    assert not any(badge.text.startswith("Draw ") for badge in after_first)
    assert any("Shot 1" in badge.text and badge.text.endswith("s") for badge in after_first)


def test_overlay_renderer_keeps_final_shot_visible_and_uses_final_label() -> None:
    project = Project(name="Final Overlay")
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.DOWN_0)),
        ShotEvent(time_ms=1600, score=ScoreMark(letter=ScoreLetter.DOWN_1)),
        ShotEvent(time_ms=2100, score=ScoreMark(letter=ScoreLetter.DOWN_3)),
    ]
    apply_scoring_preset(project, "idpa_time_plus")
    project.overlay.show_draw = False
    project.overlay.show_score = True

    badges, _score_marks = OverlayRenderer().build_badges(project, 2400)

    assert any(badge.text.startswith("Shot 3 ") for badge in badges)
    assert any(badge.text.startswith("Final ") for badge in badges)


def test_overlay_renderer_uses_custom_quadrant_coordinates() -> None:
    project = Project(name="Custom Overlay Position")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.shot_quadrant = "custom"
    project.overlay.custom_x = 0.5
    project.overlay.custom_y = 0.5
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.timer_badge.background_color = "#ff0000"
    project.overlay.timer_badge.text_color = "#ffffff"
    project.overlay.timer_badge.opacity = 1.0

    image = QImage(160, 90, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 100, 160, 90)
    painter.end()

    center_red = 0
    corner_red = 0
    for y in range(30, 62):
        for x in range(34, 126):
            color = image.pixelColor(x, y)
            if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                center_red += 1
    for y in range(0, 24):
        for x in range(0, 70):
            color = image.pixelColor(x, y)
            if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                corner_red += 1

    assert center_red > 20
    assert center_red > corner_red


def test_overlay_renderer_defaults_empty_custom_quadrant_coordinates_to_center() -> None:
    project = Project(name="Default Custom Overlay Position")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.shot_quadrant = "custom"
    project.overlay.custom_x = None
    project.overlay.custom_y = None
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.timer_badge.background_color = "#ff0000"
    project.overlay.timer_badge.text_color = "#ffffff"
    project.overlay.timer_badge.opacity = 1.0

    image = QImage(160, 90, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 100, 160, 90)
    painter.end()

    center_red = 0
    corner_red = 0
    for y in range(30, 62):
        for x in range(34, 126):
            color = image.pixelColor(x, y)
            if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                center_red += 1
    for y in range(0, 24):
        for x in range(0, 70):
            color = image.pixelColor(x, y)
            if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                corner_red += 1

    assert center_red > 20
    assert center_red > corner_red


def test_merge_export_writes_combined_canvas(synthetic_video_factory, tmp_path: Path) -> None:
    primary_path = synthetic_video_factory(name="primary", resolution=(640, 360), beep_ms=400)
    secondary_path = synthetic_video_factory(name="secondary", resolution=(640, 360), beep_ms=650)
    project = Project(name="Merge Export")
    project.primary_video = probe_video(primary_path)
    project.secondary_video = probe_video(secondary_path)
    primary_analysis = analyze_video_audio(primary_path, threshold=0.35)
    secondary_analysis = analyze_video_audio(secondary_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = primary_analysis.beep_time_ms
    project.analysis.beep_time_ms_secondary = secondary_analysis.beep_time_ms
    project.analysis.waveform_primary = primary_analysis.waveform
    project.analysis.waveform_secondary = secondary_analysis.waveform
    project.analysis.shots = primary_analysis.shots
    project.analysis.sync_offset_ms = compute_sync_offset(
        primary_analysis.beep_time_ms,
        secondary_analysis.beep_time_ms,
    )
    project.merge.enabled = True
    project.merge.layout = MergeLayout.SIDE_BY_SIDE
    project.overlay.position = OverlayPosition.TOP

    output_path = tmp_path / "merge-export.mp4"
    export_project(project, output_path)

    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) > 640
    assert int(video_stream["height"]) == 360


def test_merge_export_supports_many_sources_and_still_images(synthetic_video_factory, tmp_path: Path) -> None:
    primary_path = synthetic_video_factory(name="primary", resolution=(640, 360), beep_ms=400)
    secondary_path = synthetic_video_factory(name="secondary", resolution=(640, 360), beep_ms=650)
    tertiary_path = synthetic_video_factory(name="tertiary", resolution=(640, 360), beep_ms=900)
    image_path = tmp_path / "merge-image.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#00aa55:s=320x180",
            "-frames:v",
            "1",
            str(image_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    project = Project(name="Grid Merge Export")
    project.primary_video = probe_video(primary_path)
    project.merge_sources = [
        MergeSource(asset=probe_video(secondary_path)),
        MergeSource(asset=probe_video(image_path)),
        MergeSource(asset=probe_video(tertiary_path)),
    ]
    project.secondary_video = project.merge_sources[0].asset
    project.merge.enabled = True

    output_path = tmp_path / "grid-merge-export.mp4"
    export_project(project, output_path)

    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == 1280
    assert int(video_stream["height"]) == 720
    assert project.export.last_error is None


def test_export_presets_map_to_explicit_encoding_variables() -> None:
    project = Project()

    apply_export_preset(project, "universal_vertical")

    assert project.export.aspect_ratio == AspectRatio.PORTRAIT
    assert project.export.target_width == 1080
    assert project.export.target_height == 1920
    assert project.export.video_bitrate_mbps == 20.0
    assert project.export.audio_sample_rate == 48000
    assert project.export.audio_bitrate_kbps == 320
    preset_ids = {preset["id"] for preset in export_presets_for_api()}
    assert {"universal_vertical", "short_form_vertical", "youtube_long_1080p", "youtube_long_4k"} <= preset_ids


def test_export_accepts_expected_decoder_broken_pipe_after_successful_encode() -> None:
    log_lines = [
        "decoder: [out#0/rawvideo @ 0x1] Error writing trailer: Broken pipe",
        "decoder: Conversion failed!",
        "encoder: frame=  942 fps= 66 q=-1.0 Lsize=   93069KiB",
    ]

    assert _is_expected_decoder_pipe_shutdown(1, 0, log_lines)
    assert not _is_expected_decoder_pipe_shutdown(1, 1, log_lines)


def test_export_uses_target_dimensions_and_stores_ffmpeg_log(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory(resolution=(640, 360))
    project = Project(name="Preset Export Test")
    project.primary_video = probe_video(video_path)
    project.overlay.position = OverlayPosition.TOP
    project.export.aspect_ratio = AspectRatio.PORTRAIT
    project.export.target_width = 180
    project.export.target_height = 320
    project.export.frame_rate = ExportFrameRate.FPS_30
    project.export.video_bitrate_mbps = 1.5
    project.export.two_pass = True

    output_path = tmp_path / "vertical-export.mp4"
    export_project(project, output_path)

    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == 180
    assert int(video_stream["height"]) == 320
    assert "Encoder pass 1 command:" in project.export.last_log
    assert "Encoder pass 2 command:" in project.export.last_log
    assert "libx264" in project.export.last_log
    assert project.export.last_error is None

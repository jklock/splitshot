from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    ImportedStageScore,
    MergeLayout,
    MergeSource,
    OverlayPosition,
    OverlayTextBox,
    Project,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    TimingEvent,
    VideoAsset,
)
from splitshot.export.pipeline import (
    _encoder_command,
    _is_expected_decoder_pipe_shutdown,
    _merged_duration_ms,
    _normalized_output_fades,
    _prune_expected_decoder_pipe_shutdown_lines,
    export_project,
)
from splitshot.export.presets import apply_export_preset, export_presets_for_api
from splitshot.media.probe import probe_video
from splitshot.overlay.font_policy import (
    WINDOWS_MONO_FONT_FAMILIES,
    WINDOWS_SANS_FONT_FAMILIES,
    WINDOWS_SERIF_FONT_FAMILIES,
    default_overlay_font_family,
    resolve_overlay_font_family,
)
from splitshot.overlay.render import (
    OverlayRenderer,
    _auto_badge_size,
    _combined_rect,
    _overlay_qfont,
    _standard_badge_texts,
)
from splitshot.scoring.logic import apply_scoring_preset
from splitshot.timeline.model import draw_time_ms
from splitshot.ui.controller import ProjectController

ROOT = Path(__file__).resolve().parents[2]
E2E_VIDEO = ROOT / "tests" / "fixtures" / "media" / "e2e-stage.mp4"


def test_output_fades_scale_to_short_clip_and_emit_video_audio_filters(tmp_path: Path) -> None:
    assert _normalized_output_fades(0.5, 0.5, 0.6) == pytest.approx((0.3, 0.3))
    project = Project()
    project.primary_video.path = "source.mp4"

    command = _encoder_command(
        project,
        1920,
        1080,
        30.0,
        tmp_path / "output.mp4",
        fade_in_s=0.5,
        fade_out_s=0.5,
        duration_s=10.0,
        fade_audio=True,
    )

    assert command[command.index("-vf") + 1] == (
        "fade=t=in:st=0:d=0.500:color=black,fade=t=out:st=9.500:d=0.500:color=black"
    )
    assert command[command.index("-af") + 1] == (
        "volume=1.000,afade=t=in:st=0:d=0.500,afade=t=out:st=9.500:d=0.500,alimiter=limit=0.95"
    )
    assert command[command.index("-threads") + 1] == "4"


def test_encoder_applies_configured_output_audio_level_and_limiter(tmp_path: Path) -> None:
    project = Project()
    project.primary_video.path = "source.mp4"
    project.export.audio_output_level_percent = 225

    command = _encoder_command(
        project,
        1920,
        1080,
        30.0,
        tmp_path / "output.mp4",
        duration_s=10.0,
    )

    assert command[command.index("-af") + 1] == "volume=2.250,alimiter=limit=0.95"


def test_encoder_omits_audio_filter_for_silent_source(tmp_path: Path) -> None:
    project = Project()
    project.primary_video.path = "silent-source.mp4"

    command = _encoder_command(
        project,
        1920,
        1080,
        30.0,
        tmp_path / "output.mp4",
        has_audio=False,
    )

    assert "-af" not in command
    assert "-an" in command


def test_encoder_supports_muted_output_level(tmp_path: Path) -> None:
    project = Project()
    project.primary_video.path = "source.mp4"
    project.export.audio_output_level_percent = 0

    command = _encoder_command(
        project,
        1920,
        1080,
        30.0,
        tmp_path / "output.mp4",
    )

    assert command[command.index("-af") + 1] == "volume=0.000,alimiter=limit=0.95"


def test_export_with_audio_fade_enabled_handles_silent_video(
    synthetic_video_factory, tmp_path: Path
) -> None:
    source_with_audio = synthetic_video_factory(
        name="silent-fade",
        duration_ms=700,
        beep_ms=200,
        shot_times_ms=[400],
        resolution=(160, 90),
    )
    silent_source = source_with_audio.with_name("silent-fade-video-only.mp4")
    project = Project(name="Silent Fade")
    project.primary_video = probe_video(silent_source)
    project.export.target_width = 160
    project.export.target_height = 90

    output = export_project(
        project,
        tmp_path / "silent-fade-output.mp4",
        fade_in_s=0.2,
        fade_out_s=0.2,
        fade_audio=True,
    )

    streams = _ffprobe_json(output)["streams"]
    assert any(stream["codec_type"] == "video" for stream in streams)
    assert not any(stream["codec_type"] == "audio" for stream in streams)


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


def _ci_artifact_export_target(tmp_path: Path, name: str) -> Path:
    if os.environ.get("CI"):
        target = ROOT / "artifacts" / f"{name}-{platform.system().lower()}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    return tmp_path / f"{name}.mp4"


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

    monkeypatch.setattr(
        "splitshot.export.pipeline._ensure_qt_gui_application", fake_ensure_qt_gui_application
    )

    output_path = tmp_path / "headless-export.mp4"
    export_project(project, output_path)

    assert called is True
    assert output_path.exists()


def test_overlay_qfont_uses_known_fallback_stacks() -> None:
    courier_font = _overlay_qfont("Courier New", 18, bold=True, italic=False)
    helvetica_font = _overlay_qfont("Helvetica Neue", 14, bold=False, italic=True)
    custom_font = _overlay_qfont("Missing Family", 16, bold=False, italic=False)

    assert courier_font.pixelSize() == 18
    assert courier_font.bold() is True
    assert courier_font.italic() is False
    assert courier_font.families()
    assert courier_font.families()[0] in {
        *WINDOWS_MONO_FONT_FAMILIES,
        "Menlo",
        "Monaco",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Noto Sans Mono",
    }
    assert "Monospace" not in courier_font.families()

    assert helvetica_font.pixelSize() == 14
    assert helvetica_font.italic() is True
    assert helvetica_font.families()
    resolved_families = set(helvetica_font.families())
    primary_family = helvetica_font.families()[0]
    if sys.platform.startswith("win"):
        assert helvetica_font.families()[: len(WINDOWS_SANS_FONT_FAMILIES)] == list(
            WINDOWS_SANS_FONT_FAMILIES
        )
        assert "Helvetica Neue" not in resolved_families
    elif sys.platform == "darwin":
        assert primary_family in {"Helvetica Neue", "Helvetica", "Arial"}
    else:
        assert primary_family in {"DejaVu Sans", "Liberation Sans", "Arial", "Noto Sans"}

    assert custom_font.families()
    assert "Sans Serif" not in custom_font.families()


def test_overlay_font_policy_uses_windows_ui_defaults() -> None:
    assert default_overlay_font_family("win32") == "Segoe UI"
    assert resolve_overlay_font_family("Helvetica Neue", "win32") == "Segoe UI"
    assert default_overlay_font_family("darwin") == "Helvetica Neue"
    assert WINDOWS_SANS_FONT_FAMILIES[0] == "Segoe UI"
    assert WINDOWS_MONO_FONT_FAMILIES[0] == "Consolas"
    assert WINDOWS_SERIF_FONT_FAMILIES[0] == "Georgia"


def test_overlay_renderer_score_marks_use_overlay_qfont(
    monkeypatch, synthetic_video_factory
) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name="Score Mark Font")
    project.primary_video = probe_video(video_path)

    captured: list[tuple[str, int, bool, bool]] = []

    def fake_overlay_qfont(font_family: str, font_size: int, bold: bool, italic: bool):
        captured.append((font_family, font_size, bold, italic))
        return _overlay_qfont(font_family, font_size, bold, italic)

    monkeypatch.setattr("splitshot.overlay.render._overlay_qfont", fake_overlay_qfont)

    renderer = OverlayRenderer()
    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    try:
        renderer._paint_scores(painter, project, [("A", 0.5, 0.5, 1.0)], 320, 180)
    finally:
        painter.end()

    assert captured == [(default_overlay_font_family(), 28, True, False)]


def test_overlay_renderer_uses_text_box_typography(monkeypatch) -> None:
    project = Project(name="Text Box Style")
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.text_boxes = [
        OverlayTextBox(
            source="manual",
            text="Match title",
            style_type="rounded",
            font_family="Courier New",
            font_size=22,
            font_bold=False,
            font_italic=True,
        )
    ]
    captured: list[tuple[str, int, bool, bool]] = []

    def fake_overlay_qfont(font_family: str, font_size: int, bold: bool, italic: bool):
        captured.append((font_family, font_size, bold, italic))
        return _overlay_qfont(font_family, font_size, bold, italic)

    monkeypatch.setattr("splitshot.overlay.render._overlay_qfont", fake_overlay_qfont)
    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 0, 320, 180)
    painter.end()

    assert ("Courier New", 22, False, True) in captured


def test_overlay_renderer_auto_sizes_text_box_with_its_own_typography() -> None:
    project = Project(name="Auto-sized Text Box")
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.font_size = 14
    project.overlay.text_boxes = [
        OverlayTextBox(
            source="manual",
            text="WIDE INTRO TITLE\nSECOND LINE",
            quadrant="middle_middle",
            background_color="#ff0000",
            text_color="#ffffff",
            font_family="Arial",
            font_size=52,
            font_bold=True,
            width=0,
            height=0,
        )
    ]

    image = QImage(640, 360, QImage.Format.Format_ARGB32)
    image.fill(QColor("#101010"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 0, 640, 360)
    painter.end()

    red_pixels = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if (color := image.pixelColor(x, y)).red() > 150
        and color.red() > color.green() * 1.5
        and color.red() > color.blue() * 1.5
    ]
    assert red_pixels
    box_width = max(x for x, _y in red_pixels) - min(x for x, _y in red_pixels) + 1
    box_height = max(y for _x, y in red_pixels) - min(y for _x, y in red_pixels) + 1
    assert box_width > 400
    assert box_height >= 110


@pytest.mark.parametrize("kind", ["intro", "outro"])
def test_encoded_intro_outro_frame_auto_sizes_text_box(
    kind: str,
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    source = synthetic_video_factory(
        name=f"{kind}-text-box-source",
        duration_ms=400,
        beep_ms=100,
        shot_times_ms=[250],
        resolution=(640, 360),
    )
    controller = ProjectController()
    clip = getattr(controller.project, f"{kind}_clip")
    clip.asset = probe_video(source)
    clip.overlay.show_timer = False
    clip.overlay.show_draw = False
    clip.overlay.show_shots = False
    clip.overlay.show_score = False
    clip.overlay.font_size = 14
    clip.overlay.text_boxes = [
        OverlayTextBox(
            source="manual",
            text=f"WIDE {kind.upper()} TITLE\nSECOND LINE",
            quadrant="middle_middle",
            background_color="#ff0000",
            text_color="#ffffff",
            font_family="Arial",
            font_size=52,
            font_bold=True,
            width=0,
            height=0,
        )
    ]
    controller.project.export.target_width = 640
    controller.project.export.target_height = 360
    controller.project.export.video_bitrate_mbps = 1
    controller.project.export.ffmpeg_preset = "ultrafast"

    output = controller._render_queue_boundary_overlay(kind, source, tmp_path)
    frame = _frame_rgb(output, 0.1)
    red_mask = (
        (frame[:, :, 0] > 140)
        & (frame[:, :, 0] > frame[:, :, 1] * 1.5)
        & (frame[:, :, 0] > frame[:, :, 2] * 1.5)
    )
    ys, xs = np.where(red_mask)

    assert xs.size > 0
    assert int(xs.max() - xs.min() + 1) > 350
    assert int(ys.max() - ys.min() + 1) >= 105


def test_intro_font_size_is_painted_after_boundary_matches_final_dimensions(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    source = synthetic_video_factory(
        name="square-intro-font-source",
        duration_ms=400,
        beep_ms=100,
        shot_times_ms=[250],
        resolution=(640, 640),
    )
    reference = synthetic_video_factory(
        name="landscape-stage-reference",
        duration_ms=400,
        beep_ms=100,
        shot_times_ms=[250],
        resolution=(320, 180),
    )
    controller = ProjectController()
    controller.project.export.target_width = 320
    controller.project.export.target_height = 180
    controller.project.export.video_bitrate_mbps = 1
    controller.project.export.ffmpeg_preset = "ultrafast"
    clip = controller.project.intro_clip
    clip.asset = probe_video(source)
    clip.fade_in_s = 0
    clip.fade_out_s = 0
    clip.overlay.show_timer = False
    clip.overlay.show_draw = False
    clip.overlay.show_shots = False
    clip.overlay.show_score = False
    clip.overlay.text_boxes = [
        OverlayTextBox(
            source="manual",
            text="INTRO",
            quadrant="middle_middle",
            background_color="#ff0000",
            text_color="#ffffff",
            font_family="Arial",
            font_size=40,
            font_bold=True,
            width=0,
            height=0,
        )
    ]

    normalized = controller._prepare_queue_boundary_clip(
        source,
        reference,
        tmp_path,
        "intro",
        apply_fades=False,
    )
    overlay = controller._render_queue_boundary_overlay("intro", normalized, tmp_path)
    output = controller._prepare_queue_boundary_clip(
        overlay,
        reference,
        tmp_path,
        "intro",
    )
    frame = _frame_rgb(output, 0.2)
    red_mask = (
        (frame[:, :, 0] > 140)
        & (frame[:, :, 0] > frame[:, :, 1] * 1.5)
        & (frame[:, :, 0] > frame[:, :, 2] * 1.5)
    )
    ys, xs = np.where(red_mask)

    assert xs.size > 0
    assert int(ys.max() - ys.min() + 1) >= 42


def test_e2e_fixture_contains_detectable_shots() -> None:
    analysis = analyze_video_audio(E2E_VIDEO, threshold=0.35)

    assert analysis.beep_time_ms is not None
    assert len(analysis.shots) > 0


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


def test_export_rejects_unsupported_output_container(
    synthetic_video_factory, tmp_path: Path
) -> None:
    video_path = synthetic_video_factory()
    project = Project(name="Unsupported Container Export")
    project.primary_video = probe_video(video_path)

    with pytest.raises(ValueError, match="Unsupported export format"):
        export_project(project, tmp_path / "export.webm")


def test_export_burns_overlay_badges_into_output_video(
    synthetic_video_factory, tmp_path: Path
) -> None:
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
    red_dominant_pixels = (
        (frame[:, :, 0] > 120)
        & (frame[:, :, 0] > frame[:, :, 1] + 40)
        & (frame[:, :, 0] > frame[:, :, 2] + 40)
    )
    assert int(red_dominant_pixels.sum()) > 20


def test_export_generates_e2e_ci_proof_mp4(tmp_path: Path) -> None:
    assert E2E_VIDEO.exists(), f"Missing E2E test fixture at {E2E_VIDEO}"

    project = Project(name="E2E CI Export Proof")
    project.primary_video = probe_video(E2E_VIDEO)
    project.primary_video.duration_ms = min(int(project.primary_video.duration_ms or 4000), 4000)
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.custom_box_enabled = True
    project.overlay.custom_box_text = "CI export proof"
    project.overlay.custom_box_width = 220
    project.overlay.custom_box_height = 56
    project.merge.enabled = True
    project.merge.layout = MergeLayout.PIP
    secondary = probe_video(E2E_VIDEO)
    secondary.duration_ms = project.primary_video.duration_ms
    project.merge_sources = [
        MergeSource(
            asset=secondary,
            pip_size_percent=28,
            pip_x=1.0,
            pip_y=1.0,
            opacity=0.8,
            sync_offset_ms=0,
        )
    ]
    project.secondary_video = secondary
    project.export.target_width = 640
    project.export.target_height = 360
    project.export.video_bitrate_mbps = 3
    project.export.ffmpeg_preset = "ultrafast"

    output_path = _ci_artifact_export_target(tmp_path, "clip1-export-proof")
    export_project(project, output_path)

    assert output_path.exists()
    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == 640
    assert int(video_stream["height"]) == 360
    assert output_path.stat().st_size > 0


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
    project.overlay.scoring_colors["PE"] = "#112233"
    project.overlay.current_shot_badge.background_color = "#f97316"
    project.overlay.current_shot_badge.text_color = "#000000"
    project.overlay.shot_badge.background_color = "#f97316"
    project.overlay.shot_badge.text_color = "#000000"
    project.analysis.shots[0].score = ScoreMark(
        letter=ScoreLetter.C, penalty_counts={"procedural_errors": 1}
    )

    badges, score_marks = OverlayRenderer().build_badges(
        project, project.analysis.shots[0].time_ms + 50
    )

    scored_badge = next(badge for badge in badges if badge.text.startswith("Shot 1 "))

    assert score_marks == []
    assert scored_badge.background_color is None
    assert scored_badge.style.background_color == "#f97316"
    assert scored_badge.text_color == "#000000"
    assert "  C" in scored_badge.text
    assert "PE x1" in scored_badge.text
    assert scored_badge.text_runs is not None
    assert ("C", "#00ff00") in scored_badge.text_runs
    assert ("PE", "#112233") in scored_badge.text_runs


def test_overlay_renderer_paint_handles_scored_badge_runs_without_crashing(
    synthetic_video_factory,
) -> None:
    video_path = synthetic_video_factory(resolution=(320, 180))
    project = Project(name="Scored Paint")
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.shots = analysis.shots
    project.scoring.enabled = True
    project.overlay.show_score = False
    project.overlay.show_shots = True
    project.analysis.shots[0].score = ScoreMark(
        letter=ScoreLetter.C, penalty_counts={"procedural_errors": 1}
    )

    image = QImage(320, 180, QImage.Format_ARGB32)
    image.fill(QColor("black"))
    painter = QPainter(image)
    try:
        OverlayRenderer().paint(painter, project, project.analysis.shots[0].time_ms + 50, 320, 180)
    finally:
        painter.end()

    assert not image.isNull()


def test_overlay_renderer_formats_timer_and_draw_like_browser_preview() -> None:
    project = Project(name="Overlay Formatting")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100)]
    project.overlay.show_timer = True
    project.overlay.show_draw = True
    project.overlay.show_shots = False
    project.overlay.show_score = False

    badges, _score_marks = OverlayRenderer().build_badges(project, 600)
    texts = {badge.text for badge in badges}

    assert "Timer 0.50" in texts
    assert "Draw 1.00" in texts


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
    project.scoring.enabled = False

    before_first = OverlayRenderer().build_badges(project, project.analysis.shots[0].time_ms - 1)[0]
    after_first = OverlayRenderer().build_badges(project, project.analysis.shots[0].time_ms + 50)[0]
    expected_shot_badge = f"Shot 1 Draw {draw_time_ms(project) / 1000.0:.2f}s"

    assert any(badge.text.startswith("Draw ") for badge in before_first)
    assert not any(badge.text.startswith("Draw ") for badge in after_first)
    assert any(badge.text == expected_shot_badge for badge in after_first)


def test_overlay_renderer_reveals_shot_badges_on_frame_boundaries() -> None:
    project = Project(name="Frame Safe Overlay")
    project.primary_video = VideoAsset(
        path="/tmp/frame-safe.mp4", duration_ms=1000, width=640, height=360, fps=10.0
    )
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [ShotEvent(time_ms=150)]
    project.overlay.show_timer = False
    project.overlay.show_draw = True
    project.overlay.show_shots = True
    project.overlay.show_score = False

    before_boundary, _score_marks = OverlayRenderer().build_badges(project, 199)
    on_boundary, _score_marks = OverlayRenderer().build_badges(project, 200)

    assert any(badge.text.startswith("Draw ") for badge in before_boundary)
    assert not any(badge.text.startswith("Shot 1 ") for badge in before_boundary)
    assert not any(badge.text.startswith("Draw ") for badge in on_boundary)
    assert any(badge.text.startswith("Shot 1 ") for badge in on_boundary)


def test_overlay_renderer_folds_reload_intervals_into_the_following_shot_badge() -> None:
    project = Project(name="Timing Event Overlay")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=250),
        ShotEvent(time_ms=480),
        ShotEvent(time_ms=720),
    ]
    project.analysis.events = [
        TimingEvent(
            kind="reload",
            label="Reload",
            after_shot_id=project.analysis.shots[0].id,
            before_shot_id=project.analysis.shots[1].id,
        )
    ]
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = True
    project.overlay.show_score = False
    project.scoring.enabled = False

    badges, _score_marks = OverlayRenderer().build_badges(project, 500)
    texts = [badge.text for badge in badges]

    assert "Shot 1 Draw 0.15s" in texts
    assert "Reload" not in texts
    assert "Shot 2 Reload 0.23s" in texts


def test_overlay_auto_badge_size_uses_longest_project_badge_text_with_fixed_padding() -> None:
    class FakeMetrics:
        def horizontalAdvance(self, text: str) -> int:
            return len(text) * 8

        def height(self) -> int:
            return 18

    project = Project(name="Auto Bubble")
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [ShotEvent(time_ms=index * 100) for index in range(1, 100)]
    project.analysis.events = [
        TimingEvent(
            kind="reload",
            label="Reload",
            after_shot_id=project.analysis.shots[97].id,
            before_shot_id=project.analysis.shots[98].id,
        )
    ]
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = True
    project.overlay.show_score = False
    project.overlay.font_size = 18
    project.scoring.enabled = False

    texts = _standard_badge_texts(project)

    assert "Shot 99 Reload 0.10s" in texts
    assert _auto_badge_size(texts, FakeMetrics()) == (len("Shot 99 Reload 0.10s") * 8 + 20, 28)


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


def test_overlay_renderer_shows_imported_summary_custom_box_only_after_final_shot() -> None:
    project = Project(name="Imported Summary Overlay")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100)]
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.custom_box_enabled = True
    project.overlay.custom_box_mode = "imported_summary"
    project.overlay.custom_box_quadrant = "middle_middle"
    project.overlay.custom_box_background_color = "#ff0000"
    project.overlay.custom_box_text_color = "#ffffff"
    project.overlay.custom_box_opacity = 1.0
    project.scoring.imported_stage = ImportedStageScore(
        match_type="uspsa",
        raw_seconds=23.24,
        aggregate_points=101.0,
        total_points=101.0,
        hit_factor=4.3460,
    )

    before = QImage(220, 120, QImage.Format.Format_ARGB32)
    before.fill(QColor("#000000"))
    before_painter = QPainter(before)
    OverlayRenderer().paint(before_painter, project, 1099, 220, 120)
    before_painter.end()

    after = QImage(220, 120, QImage.Format.Format_ARGB32)
    after.fill(QColor("#000000"))
    after_painter = QPainter(after)
    OverlayRenderer().paint(after_painter, project, 1200, 220, 120)
    after_painter.end()

    before_red = 0
    after_red = 0
    for y in range(120):
        for x in range(220):
            before_color = before.pixelColor(x, y)
            after_color = after.pixelColor(x, y)
            if (
                before_color.red() > 120
                and before_color.red() > before_color.green() + 40
                and before_color.red() > before_color.blue() + 40
            ):
                before_red += 1
            if (
                after_color.red() > 120
                and after_color.red() > after_color.green() + 40
                and after_color.red() > after_color.blue() + 40
            ):
                after_red += 1

    assert before_red == 0
    assert after_red > 20


def test_overlay_renderer_respects_fixed_custom_box_dimensions() -> None:
    project = Project(name="Fixed Custom Box Dimensions")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.custom_box_enabled = True
    project.overlay.custom_box_mode = "manual"
    project.overlay.custom_box_text = "This is a very long custom review line"
    project.overlay.custom_box_quadrant = "top_left"
    project.overlay.custom_box_background_color = "#ff0000"
    project.overlay.custom_box_text_color = "#ffffff"
    project.overlay.custom_box_opacity = 1.0
    project.overlay.custom_box_width = 120
    project.overlay.custom_box_height = 40
    project.overlay.style_type = "square"

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 0, 320, 180)
    painter.end()

    red_pixels: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                red_pixels.append((x, y))

    assert red_pixels
    min_x = min(x for x, _y in red_pixels)
    max_x = max(x for x, _y in red_pixels)
    min_y = min(y for _x, y in red_pixels)
    max_y = max(y for _x, y in red_pixels)

    assert 116 <= (max_x - min_x + 1) <= 122
    assert 36 <= (max_y - min_y + 1) <= 42


def test_overlay_renderer_can_anchor_imported_summary_above_final_box() -> None:
    project = Project(name="Summary Above Final")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.DOWN_0))]
    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.enabled = True
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = True
    project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            source="imported_summary",
            text="Geometry\nRaw 13.05\nPD 4\nFinal 17.05",
            quadrant="above_final",
            background_color="#ff7b22",
            text_color="#ffffff",
            opacity=1.0,
        )
    ]
    project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa",
        raw_seconds=13.05,
        final_time=17.05,
        score_counts={"PD": 4},
    )

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 1200, 320, 180)
    painter.end()

    orange_pixels: list[tuple[int, int]] = []
    green_pixels: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.red() > 180 and color.green() > 70 and color.blue() < 80:
                orange_pixels.append((x, y))
            if (
                color.green() > 90
                and color.green() > color.red() + 20
                and color.green() > color.blue() + 20
            ):
                green_pixels.append((x, y))

    assert orange_pixels
    assert green_pixels

    orange_center_x = (min(x for x, _y in orange_pixels) + max(x for x, _y in orange_pixels)) / 2
    green_center_x = (min(x for x, _y in green_pixels) + max(x for x, _y in green_pixels)) / 2
    orange_bottom = max(y for _x, y in orange_pixels)
    green_top = min(y for _x, y in green_pixels)

    assert abs(orange_center_x - green_center_x) <= 3
    assert orange_bottom < green_top


def test_overlay_renderer_prefers_final_score_anchor_over_badge_stack_for_imported_summary() -> (
    None
):
    project = Project(name="Imported Summary Above Final Score")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=900, score=ScoreMark(letter=ScoreLetter.DOWN_0)),
        ShotEvent(time_ms=1200, score=ScoreMark(letter=ScoreLetter.DOWN_0)),
    ]
    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.enabled = True
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = True
    project.overlay.show_score = True
    project.overlay.score_x = 0.78
    project.overlay.score_y = 0.22
    project.overlay.shot_badge.background_color = "#1d8f3a"
    project.overlay.shot_badge.text_color = "#ffffff"
    project.overlay.current_shot_badge.background_color = "#1d8f3a"
    project.overlay.current_shot_badge.text_color = "#ffffff"
    project.overlay.hit_factor_badge.background_color = "#1d4dff"
    project.overlay.hit_factor_badge.text_color = "#ffffff"
    project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            source="imported_summary",
            quadrant="above_final",
            background_color="#ff7b22",
            text_color="#ffffff",
            opacity=1.0,
            width=180,
            height=54,
        )
    ]
    project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa",
        raw_seconds=13.05,
        final_time=17.05,
        score_counts={"PD": 4},
    )

    class AnchorSpyOverlayRenderer(OverlayRenderer):
        def __init__(self) -> None:
            super().__init__()
            self.stack_anchor_rect = None
            self.final_score_rect = None
            self.summary_anchor_rect = None

        def _paint_badges(self, painter, badges, project, width, height, **kwargs):
            rects = super()._paint_badges(painter, badges, project, width, height, **kwargs)
            quadrant = kwargs.get("quadrant")
            if quadrant is None and len(rects) >= 2 and self.stack_anchor_rect is None:
                self.stack_anchor_rect = _combined_rect(rects)
                self.final_score_rect = rects[-1]
            if quadrant == "custom" and rects:
                self.final_score_rect = rects[-1]
            if quadrant == "above_final":
                self.summary_anchor_rect = kwargs.get("anchor_rect")
            return rects

    image = QImage(420, 220, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    renderer = AnchorSpyOverlayRenderer()
    renderer.paint(painter, project, 1400, 420, 220)
    painter.end()

    assert renderer.stack_anchor_rect is not None
    assert renderer.final_score_rect is not None
    assert renderer.summary_anchor_rect is not None
    assert (
        abs(renderer.summary_anchor_rect.center().x() - renderer.final_score_rect.center().x()) <= 1
    )
    assert (
        abs(renderer.summary_anchor_rect.center().x() - renderer.stack_anchor_rect.center().x())
        > 20
    )


def test_overlay_renderer_uses_imported_summary_text_override_after_final_shot() -> None:
    project = Project(name="Imported Summary Override")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100)]
    project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa",
        raw_seconds=13.05,
        final_time=17.05,
        score_counts={"PD": 4},
    )

    assert (
        OverlayRenderer._text_box_text(project, 1200, "imported_summary", "Edited summary", True)
        == "Edited summary"
    )
    assert (
        OverlayRenderer._text_box_text(project, 800, "imported_summary", "Edited summary", True)
        == ""
    )


def test_overlay_renderer_uses_review_metric_configuration_and_stage_data() -> None:
    project = Project(name="WYSIWYG Review Summary")
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [ShotEvent(time_ms=26500, score=ScoreMark(letter=ScoreLetter.DOWN_3))]
    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.enabled = True
    project.scoring.competitor_name = "Shooter"
    project.scoring.competitor_place = 5
    project.scoring.division = "Carry Optics"
    project.scoring.classification = "Sharpshooter"
    project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa",
        competitor_name="Shooter",
        competitor_place=5,
        division="Carry Optics",
        classification="Sharpshooter",
        raw_seconds=21.71,
        final_time=23.71,
        aggregate_points=3,
        score_counts={"Points Down": 3},
    )
    project.scoring.comparison_competitors = [
        {
            "name": f"Shooter {index}",
            "place": index,
            "division": "Carry Optics" if index <= 11 else "Stock Service Pistol",
            "classification": "Sharpshooter" if index <= 8 else "Marksman",
            "final_time": 18.0 + index,
        }
        for index in range(1, 28)
        if index != 5
    ]

    assert OverlayRenderer._text_box_text(
        project,
        26500,
        "imported_summary",
        "",
        True,
        [
            "score_time",
            "raw_time",
            "points_down",
            "penalties",
            "division_placement",
            "class_placement",
            "overall_placement",
        ],
    ) == (
        "Score / Time 23.71\n"
        "Raw Time 21.71s\n"
        "Points Down 3\n"
        "Penalties 0\n"
        "CO - 5/11\n"
        "SS - 5/8\n"
        "Overall - 5/27"
    )
    assert OverlayRenderer._text_box_text(
        project,
        26500,
        "imported_summary",
        "Summary\nRaw 21.71\nPD 3\nFinal 23.71",
        True,
        ["score_time", "raw_time", "points_down", "penalties"],
    ) == ("Score / Time 23.71\nRaw Time 21.71s\nPoints Down 3\nPenalties 0")


def test_overlay_renderer_matches_browser_line_height_for_multiline_imported_summary() -> None:
    project = Project(name="Imported Summary Browser Line Height")
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100)]
    project.overlay.position = OverlayPosition.TOP
    project.overlay.style_type = "square"
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.font_size = 14
    project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            source="imported_summary",
            text="Geometry\nRaw 23.24\nPoints 101\nHF 4.3460",
            quadrant="top_left",
            background_color="#ff0000",
            text_color="#ffffff",
            opacity=1.0,
        )
    ]
    project.scoring.imported_stage = ImportedStageScore(
        match_type="uspsa",
        raw_seconds=23.24,
        aggregate_points=101.0,
        total_points=101.0,
        hit_factor=4.3460,
    )

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 1200, 320, 180)
    painter.end()

    red_pixels: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                red_pixels.append((x, y))

    assert red_pixels
    min_y = min(y for _x, y in red_pixels)
    max_y = max(y for _x, y in red_pixels)

    assert 64 <= (max_y - min_y + 1) <= 68


def test_overlay_renderer_can_lock_review_boxes_to_overlay_stack() -> None:
    project = Project(name="Review Box Stack Lock")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.shot_quadrant = "top_left"
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            lock_to_stack=True,
            source="manual",
            text="Review Box",
            quadrant="custom",
            x=0.75,
            y=0.25,
            background_color="#ff0000",
            text_color="#ffffff",
            opacity=1.0,
            width=160,
            height=48,
        )
    ]

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 0, 320, 180)
    painter.end()

    red_pixels: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                red_pixels.append((x, y))

    assert red_pixels
    center_x = (min(x for x, _y in red_pixels) + max(x for x, _y in red_pixels)) / 2
    center_y = (min(y for _x, y in red_pixels) + max(y for _x, y in red_pixels)) / 2

    assert center_x < 120
    assert center_y < 80


def test_overlay_renderer_uses_unlocked_review_box_custom_coordinates() -> None:
    project = Project(name="Review Box Custom Coordinates")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.text_boxes = [
        OverlayTextBox(
            enabled=True,
            lock_to_stack=False,
            source="manual",
            text="Review Box",
            quadrant="custom",
            x=0.75,
            y=0.25,
            background_color="#ff0000",
            text_color="#ffffff",
            opacity=1.0,
            width=80,
            height=40,
        )
    ]

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, project, 0, 320, 180)
    painter.end()

    red_pixels: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                red_pixels.append((x, y))

    assert red_pixels
    center_x = (min(x for x, _y in red_pixels) + max(x for x, _y in red_pixels)) / 2
    center_y = (min(y for _x, y in red_pixels) + max(y for _x, y in red_pixels)) / 2

    assert center_x == pytest.approx(320 * 0.75, abs=3)
    assert center_y == pytest.approx(180 * 0.25, abs=3)


def test_export_burns_manual_custom_box_into_output_video(
    synthetic_video_factory, tmp_path: Path
) -> None:
    video_path = synthetic_video_factory(name="custom-box-export")
    project = Project(name="Manual Custom Box Export")
    project.primary_video = probe_video(video_path)
    project.overlay.position = OverlayPosition.TOP
    project.overlay.show_timer = False
    project.overlay.show_draw = False
    project.overlay.show_shots = False
    project.overlay.show_score = False
    project.overlay.custom_box_enabled = True
    project.overlay.custom_box_mode = "manual"
    project.overlay.custom_box_text = "Review Box"
    project.overlay.custom_box_quadrant = "top_left"
    project.overlay.custom_box_background_color = "#ff0000"
    project.overlay.custom_box_text_color = "#ffffff"
    project.overlay.custom_box_opacity = 1.0
    project.overlay.custom_box_width = 160
    project.overlay.custom_box_height = 48

    output_path = tmp_path / "custom-box-export-output.mp4"
    export_project(project, output_path)

    frame = _frame_rgb(output_path, 0.1)
    red_dominant_pixels = (
        (frame[:, :, 0] > 120)
        & (frame[:, :, 0] > frame[:, :, 1] + 40)
        & (frame[:, :, 0] > frame[:, :, 2] + 40)
    )
    assert int(red_dominant_pixels.sum()) > 20


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
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                center_red += 1
    for y in range(24):
        for x in range(70):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
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
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                center_red += 1
    for y in range(24):
        for x in range(70):
            color = image.pixelColor(x, y)
            if (
                color.red() > 120
                and color.red() > color.green() + 40
                and color.red() > color.blue() + 40
            ):
                corner_red += 1

    assert center_red > 20
    assert center_red > corner_red


def test_overlay_renderer_keeps_timer_anchor_stable_in_custom_quadrant() -> None:
    project = Project(name="Custom Overlay Anchor")
    project.overlay.position = OverlayPosition.TOP
    project.overlay.shot_quadrant = "custom"
    project.overlay.custom_x = 0.5
    project.overlay.custom_y = 0.5
    project.overlay.show_draw = False
    project.overlay.show_shots = True
    project.overlay.show_score = False
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [ShotEvent(time_ms=1100)]
    project.overlay.timer_badge.background_color = "#ff0000"
    project.overlay.timer_badge.text_color = "#ffffff"
    project.overlay.timer_badge.opacity = 1.0
    project.overlay.shot_badge.background_color = "#0000ff"
    project.overlay.shot_badge.text_color = "#ffffff"
    project.overlay.shot_badge.opacity = 1.0
    project.overlay.current_shot_badge.background_color = "#0000ff"
    project.overlay.current_shot_badge.text_color = "#ffffff"
    project.overlay.current_shot_badge.opacity = 1.0

    before = QImage(220, 120, QImage.Format.Format_ARGB32)
    before.fill(QColor("#000000"))
    before_painter = QPainter(before)
    OverlayRenderer().paint(before_painter, project, 200, 220, 120)
    before_painter.end()

    after = QImage(220, 120, QImage.Format.Format_ARGB32)
    after.fill(QColor("#000000"))
    after_painter = QPainter(after)
    OverlayRenderer().paint(after_painter, project, 1200, 220, 120)
    after_painter.end()

    def red_centroid(image: QImage) -> tuple[float, float, int]:
        total_x = 0.0
        total_y = 0.0
        count = 0
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if (
                    color.red() > 120
                    and color.red() > color.green() + 40
                    and color.red() > color.blue() + 40
                ):
                    total_x += x
                    total_y += y
                    count += 1
        return (total_x / count, total_y / count, count)

    before_x, before_y, before_count = red_centroid(before)
    after_x, after_y, after_count = red_centroid(after)

    assert before_count > 20
    assert after_count > 20
    assert abs(before_x - after_x) < 3
    assert abs(before_y - after_y) < 3


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


def test_merge_export_supports_many_sources_and_still_images(
    synthetic_video_factory, tmp_path: Path
) -> None:
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


def test_merged_duration_uses_per_source_sync_offsets() -> None:
    project = Project(name="Per Source Sync Duration")
    project.primary_video = VideoAsset(
        path="/tmp/primary.mp4", duration_ms=1000, width=640, height=360, fps=30.0
    )
    project.merge_sources = [
        MergeSource(
            asset=VideoAsset(
                path="/tmp/secondary.mp4", duration_ms=1200, width=640, height=360, fps=30.0
            ),
            sync_offset_ms=-300,
        ),
        MergeSource(
            asset=VideoAsset(
                path="/tmp/tertiary.mp4", duration_ms=1500, width=640, height=360, fps=30.0
            ),
            sync_offset_ms=400,
        ),
    ]

    assert _merged_duration_ms(project, project.merge_sources) == 1500


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
    assert {
        "universal_vertical",
        "short_form_vertical",
        "youtube_long_1080p",
        "youtube_long_4k",
    } <= preset_ids


def test_export_accepts_expected_decoder_broken_pipe_after_successful_encode() -> None:
    log_lines = [
        "decoder: [out#0/rawvideo @ 0x1] Error writing trailer: Broken pipe",
        "decoder: Conversion failed!",
        "encoder: frame=  942 fps= 66 q=-1.0 Lsize=   93069KiB",
    ]

    assert _is_expected_decoder_pipe_shutdown(1, 0, log_lines)
    assert not _is_expected_decoder_pipe_shutdown(1, 1, log_lines)


def test_export_prunes_expected_decoder_broken_pipe_lines_from_successful_log() -> None:
    log_lines = [
        "Export target: /tmp/example.mp4",
        "decoder: [out#0/rawvideo @ 0x1] Error writing trailer: Broken pipe",
        "decoder: Conversion failed!",
        "encoder: frame=  942 fps= 66 q=-1.0 Lsize=   93069KiB",
    ]

    assert _prune_expected_decoder_pipe_shutdown_lines(log_lines)
    assert "Broken pipe" not in "\n".join(log_lines)
    assert "Conversion failed!" not in "\n".join(log_lines)
    assert (
        log_lines[-1]
        == "decoder: rawvideo pipe closed after the encoder finished the shortest stream; decoder shutdown was expected."
    )


def test_export_uses_target_dimensions_and_stores_ffmpeg_log(
    synthetic_video_factory, tmp_path: Path
) -> None:
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

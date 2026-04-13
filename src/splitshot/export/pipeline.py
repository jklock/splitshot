from __future__ import annotations

import math
import os
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter

from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    Project,
    VideoAsset,
)
from splitshot.media.ffmpeg import ffmpeg_command
from splitshot.merge.layouts import calculate_merge_canvas
from splitshot.overlay.render import OverlayRenderer
from splitshot.scoring.logic import calculate_hit_factor


_QT_GUI_APP: QGuiApplication | None = None
_SUPPORTED_EXPORT_EXTENSIONS = {".m4v", ".mkv", ".mov", ".mp4"}
_FASTSTART_EXPORT_EXTENSIONS = {".m4v", ".mov", ".mp4"}


@dataclass(slots=True)
class BaseRenderPlan:
    command: list[str]
    width: int
    height: int
    fps: float
    duration_ms: int


def _ensure_qt_gui_application() -> QGuiApplication:
    global _QT_GUI_APP

    instance = QGuiApplication.instance()
    if isinstance(instance, QGuiApplication):
        return instance

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _QT_GUI_APP = QGuiApplication(["splitshot-export"])
    return _QT_GUI_APP


def _normalize_output_target(output_path: str | Path) -> Path:
    output_target = Path(output_path).expanduser()
    if not output_target.suffix:
        output_target = output_target.with_suffix(".mp4")
    if output_target.suffix.lower() not in _SUPPORTED_EXPORT_EXTENSIONS:
        supported = ", ".join(ext.lstrip(".") for ext in sorted(_SUPPORTED_EXPORT_EXTENSIONS))
        raise ValueError(
            f"Unsupported export format '{output_target.suffix or '<none>'}'. Supported extensions: {supported}."
        )
    return output_target


def _quality_crf(quality: ExportQuality) -> str:
    return {
        ExportQuality.HIGH: "18",
        ExportQuality.MEDIUM: "23",
        ExportQuality.LOW: "28",
    }[quality]


def _codec_name(codec: ExportVideoCodec) -> str:
    return {
        ExportVideoCodec.H264: "libx264",
        ExportVideoCodec.HEVC: "libx265",
    }[codec]


def _output_fps(project: Project) -> float:
    source_fps = project.primary_video.fps or 30.0
    if project.export.frame_rate == ExportFrameRate.FPS_30:
        return 30.0
    if project.export.frame_rate == ExportFrameRate.FPS_60:
        return 60.0
    return source_fps


def _ratio_value(aspect_ratio: AspectRatio) -> tuple[int, int] | None:
    return {
        AspectRatio.ORIGINAL: None,
        AspectRatio.LANDSCAPE: (16, 9),
        AspectRatio.PORTRAIT: (9, 16),
        AspectRatio.SQUARE: (1, 1),
        AspectRatio.PORTRAIT_45: (4, 5),
    }[aspect_ratio]


def _ensure_even(value: int) -> int:
    value = max(2, int(value))
    return value if value % 2 == 0 else value - 1


def compute_crop_box(
    width: int,
    height: int,
    aspect_ratio: AspectRatio,
    center_x: float,
    center_y: float,
) -> tuple[int, int, int, int]:
    target = _ratio_value(aspect_ratio)
    if target is None:
        return 0, 0, _ensure_even(width), _ensure_even(height)

    target_ratio = target[0] / target[1]
    current_ratio = width / height
    if current_ratio > target_ratio:
        crop_height = _ensure_even(height)
        crop_width = _ensure_even(int(round(crop_height * target_ratio)))
    else:
        crop_width = _ensure_even(width)
        crop_height = _ensure_even(int(round(crop_width / target_ratio)))

    crop_width = max(2, min(width, crop_width))
    crop_height = max(2, min(height, crop_height))

    center_px = center_x * width
    center_py = center_y * height
    left = int(round(center_px - (crop_width / 2)))
    top = int(round(center_py - (crop_height / 2)))
    left = max(0, min(width - crop_width, left))
    top = max(0, min(height - crop_height, top))
    return left, top, crop_width, crop_height


def _merge_assets(project: Project) -> list[VideoAsset]:
    if project.merge_sources:
        return [source.asset for source in project.merge_sources if source.asset.path]
    if project.secondary_video is None or not project.secondary_video.path:
        return []
    return [project.secondary_video]


def _merged_duration_ms(project: Project, merge_assets: list[VideoAsset]) -> int:
    primary = project.primary_video.duration_ms
    if not merge_assets:
        return primary
    if len(merge_assets) == 1:
        secondary = merge_assets[0].duration_ms
        offset = project.analysis.sync_offset_ms
        secondary_visible = max(0, secondary - max(0, offset))
        secondary_end = max(0, -offset) + secondary_visible
        return max(primary, secondary_end)
    return max([primary, *[asset.duration_ms for asset in merge_assets]])


def _build_grid_merge_plan(project: Project, merge_assets: list[VideoAsset]) -> BaseRenderPlan:
    fps = _output_fps(project)
    sources = [project.primary_video, *merge_assets]
    tile_width = max(2, int(project.primary_video.width or 0))
    tile_height = max(2, int(project.primary_video.height or 0))
    columns = max(1, math.ceil(math.sqrt(len(sources))))
    rows = math.ceil(len(sources) / columns)

    input_args = [
        *ffmpeg_command([
            "-v",
            "info",
        ]),
        "-i",
        project.primary_video.path,
    ]
    for asset in merge_assets:
        if asset.is_still_image:
            input_args.extend(["-loop", "1", "-framerate", f"{fps:.3f}", "-i", asset.path])
        else:
            input_args.extend(["-i", asset.path])
    input_args.append("-an")

    chain_parts: list[str] = []
    layout_parts: list[str] = []
    for index, _source in enumerate(sources):
        chain_parts.append(
            f"[{index}:v]setpts=PTS-STARTPTS,scale={tile_width}:{tile_height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={tile_width}:{tile_height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[t{index}]"
        )
        layout_parts.append(f"{(index % columns) * tile_width}_{(index // columns) * tile_height}")

    stacked_inputs = "".join(f"[t{index}]" for index in range(len(sources)))
    filter_complex = ";".join(
        [
            *chain_parts,
            (
                f"{stacked_inputs}xstack=inputs={len(sources)}:layout={'|'.join(layout_parts)}:"
                "fill=black:shortest=0,format=rgba[f]"
            ),
        ]
    )

    command = [
        *input_args,
        "-filter_complex",
        filter_complex,
        "-map",
        "[f]",
        "-r",
        f"{fps:.3f}",
        "-pix_fmt",
        "rgba",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    return BaseRenderPlan(
        command=command,
        width=tile_width * columns,
        height=tile_height * rows,
        fps=fps,
        duration_ms=_merged_duration_ms(project, merge_assets),
    )


def _build_single_video_plan(project: Project) -> BaseRenderPlan:
    fps = _output_fps(project)
    command = ffmpeg_command([
        "-v",
        "info",
        "-i",
        project.primary_video.path,
        "-an",
        "-vf",
        f"fps={fps:.3f},format=rgba",
        "-pix_fmt",
        "rgba",
        "-f",
        "rawvideo",
        "pipe:1",
    ])
    return BaseRenderPlan(
        command=command,
        width=project.primary_video.width,
        height=project.primary_video.height,
        fps=fps,
        duration_ms=project.primary_video.duration_ms,
    )


def _build_merge_plan(project: Project) -> BaseRenderPlan:
    merge_assets = _merge_assets(project)
    if not merge_assets:
        return _build_single_video_plan(project)
    if len(merge_assets) > 1:
        return _build_grid_merge_plan(project, merge_assets)

    secondary = merge_assets[0]
    canvas = calculate_merge_canvas(
        project.primary_video,
        secondary,
        project.merge.layout,
        project.merge.pip_size_percent,
        project.merge.pip_x,
        project.merge.pip_y,
    )
    fps = _output_fps(project)
    offset_ms = project.analysis.sync_offset_ms

    input_args = [
        *ffmpeg_command([
            "-v",
            "info",
        ]),
        "-i",
        project.primary_video.path,
    ]
    if offset_ms > 0:
        input_args.extend(["-ss", f"{offset_ms / 1000:.3f}"])
    if secondary.is_still_image:
        input_args.extend(["-loop", "1", "-framerate", f"{fps:.3f}", "-i", secondary.path])
    else:
        input_args.extend(["-i", secondary.path])
    input_args.append("-an")

    secondary_chain = "[1:v]setpts=PTS-STARTPTS"
    if offset_ms < 0:
        secondary_chain += f",tpad=start_duration={abs(offset_ms) / 1000:.3f}:color=black"

    if project.merge.layout == MergeLayout.SIDE_BY_SIDE:
        filter_complex = (
            f"[0:v]setpts=PTS-STARTPTS,scale=-2:{canvas.primary_rect.height}[p];"
            f"{secondary_chain},scale=-2:{canvas.secondary_rect.height}[s];"
            "[p][s]hstack=inputs=2:shortest=0,format=rgba[f]"
        )
    elif project.merge.layout == MergeLayout.ABOVE_BELOW:
        filter_complex = (
            f"[0:v]setpts=PTS-STARTPTS,scale={canvas.primary_rect.width}:-2[p];"
            f"{secondary_chain},scale={canvas.secondary_rect.width}:-2[s];"
            "[p][s]vstack=inputs=2:shortest=0,format=rgba[f]"
        )
    else:
        filter_complex = (
            f"[0:v]setpts=PTS-STARTPTS,scale={canvas.primary_rect.width}:{canvas.primary_rect.height}[main];"
            f"{secondary_chain},scale={canvas.secondary_rect.width}:{canvas.secondary_rect.height}[pip];"
            f"[main][pip]overlay=x={canvas.secondary_rect.x}:y={canvas.secondary_rect.y}:"
            "eof_action=pass:shortest=0:repeatlast=0,format=rgba[f]"
        )

    command = [
        *input_args,
        "-filter_complex",
        filter_complex,
        "-map",
        "[f]",
        "-r",
        f"{fps:.3f}",
        "-pix_fmt",
        "rgba",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    return BaseRenderPlan(
        command=command,
        width=canvas.width,
        height=canvas.height,
        fps=fps,
        duration_ms=_merged_duration_ms(project, [secondary]),
    )


def build_base_render_plan(project: Project) -> BaseRenderPlan:
    if project.merge.enabled and project.secondary_video is not None:
        return _build_merge_plan(project)
    return _build_single_video_plan(project)


def _target_dimensions(project: Project, width: int, height: int) -> tuple[int, int]:
    target_width = project.export.target_width
    target_height = project.export.target_height
    if target_width is None or target_height is None:
        return _ensure_even(width), _ensure_even(height)
    return _ensure_even(target_width), _ensure_even(target_height)


def _image_to_rgba_bytes(image: QImage) -> bytes:
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return bytes(rgba.bits()[: rgba.sizeInBytes()])


def _start_log_reader(
    pipe,
    prefix: str,
    log_lines: list[str],
    log_callback: Callable[[str], None] | None,
) -> threading.Thread:
    def drain() -> None:
        if pipe is None:
            return
        for raw_line in iter(pipe.readline, b""):
            text = raw_line.decode("utf-8", errors="replace").rstrip()
            if not text:
                continue
            line = f"{prefix}: {text}"
            log_lines.append(line)
            if log_callback is not None:
                log_callback(line)

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    return thread


def _encoder_command(
    project: Project,
    output_width: int,
    output_height: int,
    fps: float,
    output_target: Path,
    pass_number: int | None = None,
    passlogfile: Path | None = None,
    first_pass: bool = False,
) -> list[str]:
    video_bitrate = f"{project.export.video_bitrate_mbps:g}M"
    audio_bitrate = f"{project.export.audio_bitrate_kbps}k"
    input_args = [
        "-v",
        "info",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{output_width}x{output_height}",
        "-r",
        f"{fps:.3f}",
        "-i",
        "pipe:0",
    ]
    audio_args = [] if first_pass else [
        "-i",
        project.primary_video.path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
    ]
    encode_args = [
        "-c:v",
        _codec_name(project.export.video_codec),
        "-preset",
        project.export.ffmpeg_preset,
        "-b:v",
        video_bitrate,
        "-pix_fmt",
        "yuv420p",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
    ]
    if pass_number is None:
        bitrate_index = encode_args.index("-b:v")
        encode_args[bitrate_index:bitrate_index] = ["-crf", _quality_crf(project.export.quality)]
    if pass_number is not None and passlogfile is not None:
        encode_args.extend(["-pass", str(pass_number), "-passlogfile", str(passlogfile)])
    audio_encode_args = ["-an"] if first_pass else [
        "-c:a",
        project.export.audio_codec.value,
        "-ar",
        str(project.export.audio_sample_rate),
        "-b:a",
        audio_bitrate,
    ]
    output_args = ["-f", "null", os.devnull] if first_pass else [
        *(["-movflags", "+faststart"] if output_target.suffix.lower() in _FASTSTART_EXPORT_EXTENSIONS else []),
        "-shortest",
        str(output_target),
    ]
    command = ffmpeg_command([*input_args, *audio_args, *encode_args, *audio_encode_args, *output_args])
    return command


def _render_pass(
    project: Project,
    plan: BaseRenderPlan,
    crop_box: tuple[int, int, int, int],
    output_width: int,
    output_height: int,
    encoder_command: list[str],
    log_lines: list[str],
    log_callback: Callable[[str], None] | None,
    progress_callback: Callable[[float], None] | None,
    progress_start: float,
    progress_span: float,
) -> None:
    crop_left, crop_top, crop_width, crop_height = crop_box
    decoder = subprocess.Popen(
        plan.command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        encoder_command,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    decoder_log_thread = _start_log_reader(decoder.stderr, "decoder", log_lines, log_callback)
    encoder_log_thread = _start_log_reader(encoder.stderr, "encoder", log_lines, log_callback)
    renderer = OverlayRenderer()
    bytes_per_frame = plan.width * plan.height * 4
    total_frames = max(1, int(math.ceil((plan.duration_ms / 1000.0) * plan.fps)))

    try:
        for frame_index in range(total_frames):
            raw = decoder.stdout.read(bytes_per_frame)
            if len(raw) < bytes_per_frame:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(plan.height, plan.width, 4).copy()
            cropped = frame[crop_top : crop_top + crop_height, crop_left : crop_left + crop_width].copy()
            image = QImage(
                cropped.data,
                cropped.shape[1],
                cropped.shape[0],
                cropped.strides[0],
                QImage.Format_RGBA8888,
            )
            if image.width() != output_width or image.height() != output_height:
                image = image.scaled(
                    output_width,
                    output_height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            painter = QPainter(image)
            renderer.paint(
                painter,
                project,
                int(round((frame_index / plan.fps) * 1000)),
                output_width,
                output_height,
            )
            painter.end()

            encoder.stdin.write(_image_to_rgba_bytes(image))
            if progress_callback is not None:
                frame_progress = min((frame_index + 1) / total_frames, 1.0)
                progress_callback(min(progress_start + (frame_progress * progress_span), 1.0))
    finally:
        if decoder.stdout is not None:
            decoder.stdout.close()
        if encoder.stdin is not None:
            encoder.stdin.close()

    decoder_return = decoder.wait()
    encoder_return = encoder.wait()
    decoder_log_thread.join(timeout=2)
    encoder_log_thread.join(timeout=2)

    if decoder_return != 0 and not _is_expected_decoder_pipe_shutdown(decoder_return, encoder_return, log_lines):
        raise RuntimeError("Base video render failed")
    if encoder_return != 0:
        raise RuntimeError("MP4 encode failed")


def _is_expected_decoder_pipe_shutdown(decoder_return: int, encoder_return: int, log_lines: list[str]) -> bool:
    if decoder_return == 0 or encoder_return != 0:
        return False
    decoder_log = "\n".join(line for line in log_lines if line.startswith("decoder:"))
    return "Broken pipe" in decoder_log and "Conversion failed!" in decoder_log


def export_project(
    project: Project,
    output_path: str | Path,
    progress_callback: Callable[[float], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> Path:
    if not project.primary_video.path:
        raise ValueError("Primary video is required for export")

    _ensure_qt_gui_application()
    project.scoring.hit_factor = calculate_hit_factor(project)
    plan = build_base_render_plan(project)
    crop_left, crop_top, crop_width, crop_height = compute_crop_box(
        plan.width,
        plan.height,
        project.export.aspect_ratio,
        project.export.crop_center_x,
        project.export.crop_center_y,
    )
    output_width, output_height = _target_dimensions(project, crop_width, crop_height)

    output_target = _normalize_output_target(output_path)
    output_target.parent.mkdir(parents=True, exist_ok=True)
    project.export.last_log = ""
    project.export.last_error = None
    log_lines: list[str] = [
        f"Export target: {output_target}",
        f"Container: {output_target.suffix.lower()}",
        f"Preset: {project.export.preset.value}",
        f"Video: {project.export.video_codec.value} {output_width}x{output_height} {plan.fps:.3f} fps {project.export.video_bitrate_mbps:g} Mbps",
        f"Audio: {project.export.audio_codec.value} {project.export.audio_sample_rate} Hz {project.export.audio_bitrate_kbps} kbps",
        f"Color: {project.export.color_space.value}",
        f"Two pass requested: {project.export.two_pass}",
        f"Decoder command: {shlex.join(plan.command)}",
    ]

    try:
        crop_box = (crop_left, crop_top, crop_width, crop_height)
        if project.export.two_pass:
            with TemporaryDirectory(prefix="splitshot-export-pass-") as pass_dir:
                passlogfile = Path(pass_dir) / "ffmpeg-pass"
                pass_one_command = _encoder_command(
                    project,
                    output_width,
                    output_height,
                    plan.fps,
                    output_target,
                    pass_number=1,
                    passlogfile=passlogfile,
                    first_pass=True,
                )
                pass_two_command = _encoder_command(
                    project,
                    output_width,
                    output_height,
                    plan.fps,
                    output_target,
                    pass_number=2,
                    passlogfile=passlogfile,
                    first_pass=False,
                )
                log_lines.append(f"Encoder pass 1 command: {shlex.join(pass_one_command)}")
                log_lines.append(f"Encoder pass 2 command: {shlex.join(pass_two_command)}")
                _render_pass(
                    project,
                    plan,
                    crop_box,
                    output_width,
                    output_height,
                    pass_one_command,
                    log_lines,
                    log_callback,
                    progress_callback,
                    0.0,
                    0.5,
                )
                _render_pass(
                    project,
                    plan,
                    crop_box,
                    output_width,
                    output_height,
                    pass_two_command,
                    log_lines,
                    log_callback,
                    progress_callback,
                    0.5,
                    0.5,
                )
        else:
            encoder_command = _encoder_command(project, output_width, output_height, plan.fps, output_target)
            log_lines.append(f"Encoder command: {shlex.join(encoder_command)}")
            _render_pass(
                project,
                plan,
                crop_box,
                output_width,
                output_height,
                encoder_command,
                log_lines,
                log_callback,
                progress_callback,
                0.0,
                1.0,
            )
    except RuntimeError as exc:
        project.export.last_error = str(exc)
        project.export.last_log = "\n".join(log_lines[-400:])
        raise RuntimeError(project.export.last_log or str(exc)) from exc

    project.export.last_log = "\n".join(log_lines[-400:])

    return output_target

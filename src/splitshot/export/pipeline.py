from __future__ import annotations

import json
import math
import os
import shlex
import subprocess
import sys
import threading
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtWidgets import QApplication

from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    MergePlacementMode,
    MergePlacementSlot,
    MergeSource,
    MergeSourceAssetPathKind,
    Project,
)
from splitshot.media.ffmpeg import ffmpeg_command, run_ffprobe_json
from splitshot.merge.layouts import calculate_merge_canvas, calculate_pip_rect
from splitshot.overlay.render import OverlayRenderer
from splitshot.scoring.logic import calculate_hit_factor

_QT_GUI_APP: QGuiApplication | None = None
_SUPPORTED_EXPORT_EXTENSIONS = {".m4v", ".mkv", ".mov", ".mp4"}
_FASTSTART_EXPORT_EXTENSIONS = {".m4v", ".mov", ".mp4"}
_EXPORT_QT_MAIN_THREAD_ERROR = (
    "SplitShot export must initialize Qt on the main thread before browser exports run."
)


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

    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(_EXPORT_QT_MAIN_THREAD_ERROR)

    if sys.platform != "win32":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _QT_GUI_APP = QApplication(["splitshot-export"])
    return _QT_GUI_APP


def prepare_export_runtime() -> QGuiApplication:
    return _ensure_qt_gui_application()


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


def _trim_active(trim_derivative: object) -> bool:
    return bool(
        trim_derivative is not None
        and getattr(trim_derivative, "active_path_kind", None)
        == MergeSourceAssetPathKind.LOCAL_DERIVATIVE
        and getattr(trim_derivative, "derivative_path", None)
    )


def _active_export_project(project: Project) -> Project:
    active_project = deepcopy(project)
    if _trim_active(active_project.primary_trim_derivative):
        derivative_asset = active_project.primary_trim_derivative.derivative_asset
        if derivative_asset.path:
            active_project.primary_video = derivative_asset
    for source in active_project.merge_sources:
        if _trim_active(source.trim_derivative) and source.trim_derivative.derivative_asset.path:
            source.asset = source.trim_derivative.derivative_asset
    if active_project.merge_sources:
        active_project.secondary_video = active_project.merge_sources[0].asset
    return active_project


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
        crop_width = _ensure_even(round(crop_height * target_ratio))
    else:
        crop_width = _ensure_even(width)
        crop_height = _ensure_even(round(crop_width / target_ratio))

    crop_width = max(2, min(width, crop_width))
    crop_height = max(2, min(height, crop_height))

    center_px = center_x * width
    center_py = center_y * height
    left = round(center_px - (crop_width / 2))
    top = round(center_py - (crop_height / 2))
    left = max(0, min(width - crop_width, left))
    top = max(0, min(height - crop_height, top))
    return left, top, crop_width, crop_height


def _merge_sources(project: Project) -> list[MergeSource]:
    if project.merge_sources:
        return [source for source in project.merge_sources if source.asset.path]
    if project.secondary_video is None or not project.secondary_video.path:
        return []
    return [
        MergeSource(
            asset=project.secondary_video,
            pip_size_percent=project.merge.pip_size_percent,
            pip_x=project.merge.pip_x,
            pip_y=project.merge.pip_y,
            opacity=1.0,
            sync_offset_ms=int(project.analysis.sync_offset_ms),
        )
    ]


def _source_sync_offset_ms(source: MergeSource) -> int:
    return int(getattr(source, "sync_offset_ms", 0) or 0)


def _source_active_path(source: MergeSource) -> str:
    trim = getattr(source, "trim_derivative", None)
    if _trim_active(trim):
        return str(trim.derivative_path)
    return source.asset.path


def _source_opacity(source: MergeSource) -> float:
    raw_opacity = getattr(source, "opacity", 1.0)
    if raw_opacity is None:
        return 1.0
    return max(0.0, min(1.0, float(raw_opacity)))


def _source_uses_looped_still_input(source: MergeSource) -> bool:
    return source.asset.is_still_image and source.asset.media_kind != "animated_gif"


def _source_input_args(source: MergeSource, fps: float) -> list[str]:
    asset = source.asset
    active_path = _source_active_path(source)
    offset_ms = _source_sync_offset_ms(source)
    input_args: list[str] = []
    if offset_ms > 0 and not asset.is_still_image and asset.media_kind != "animated_gif":
        input_args.extend(["-ss", f"{offset_ms / 1000:.3f}"])
    if _source_uses_looped_still_input(source):
        input_args.extend(["-loop", "1", "-framerate", f"{fps:.3f}", "-i", active_path])
    elif asset.media_kind == "animated_gif":
        input_args.extend(["-stream_loop", "-1", "-ignore_loop", "0", "-i", active_path])
    else:
        input_args.extend(["-i", active_path])
    return input_args


def _source_end_ms(source: MergeSource) -> int:
    duration_ms = int(source.asset.duration_ms or 0)
    if duration_ms <= 0:
        return 0
    offset_ms = _source_sync_offset_ms(source)
    visible_duration_ms = max(0, duration_ms - max(0, offset_ms))
    return max(0, -offset_ms) + visible_duration_ms


def _merged_duration_ms(project: Project, merge_sources: list[MergeSource]) -> int:
    primary = project.primary_video.duration_ms
    if not merge_sources:
        return primary
    source_ends = [_source_end_ms(source) for source in merge_sources]
    return max([primary, *source_ends])


_RESOLVED_MERGE_SOURCE_ANGLE_ROLES = frozenset({"primary", "follow", "static", "detail"})

_CAMERA_ROLE_PRIORITY: dict[str, int] = {
    "primary": 0,
    "follow": 1,
    "static": 2,
    "detail": 3,
}


def _normalized_merge_source_angle_role(source: MergeSource) -> str:
    raw = (
        str(getattr(source, "angle_role", "") or getattr(source, "camera_role", "") or "")
        .strip()
        .lower()
    )
    if raw in _RESOLVED_MERGE_SOURCE_ANGLE_ROLES:
        return raw
    return "follow"


def _camera_role_priority(source: MergeSource) -> int:
    role = _normalized_merge_source_angle_role(source)
    return _CAMERA_ROLE_PRIORITY.get(role, 99)


def _merge_source_role_sort_key(source: MergeSource) -> tuple:
    return (_camera_role_priority(source), source.id)


def _project_merge_seed_mode(project: Project) -> MergePlacementMode:
    return {
        MergeLayout.SIDE_BY_SIDE: MergePlacementMode.SIDE_BY_SIDE,
        MergeLayout.ABOVE_BELOW: MergePlacementMode.ABOVE_BELOW,
        MergeLayout.PIP: MergePlacementMode.PIP,
        MergeLayout.FULL_SCREEN_PORTRAIT: MergePlacementMode.FULL_SCREEN_PORTRAIT,
        MergeLayout.DUAL_CENTER_HUD: MergePlacementMode.DUAL_CENTER_HUD,
        MergeLayout.DUAL_TOP_HUD: MergePlacementMode.DUAL_TOP_HUD,
    }.get(project.merge.layout, MergePlacementMode.PIP)


def _resolved_merge_source_mode(source: MergeSource, project: Project) -> MergePlacementMode:
    placement = getattr(source, "placement", None)
    if (
        placement is not None
        and getattr(placement, "mode", None) is not None
        and str(placement.mode) != "auto"
    ):
        return placement.mode
    return _project_merge_seed_mode(project)


def _resolved_merge_source_slot(source: MergeSource, project: Project) -> MergePlacementSlot:
    mode = _resolved_merge_source_mode(source, project)
    placement = getattr(source, "placement", None)
    if (
        placement is not None
        and getattr(placement, "slot", None) is not None
        and str(placement.slot) != "auto"
    ):
        return placement.slot
    if mode == MergePlacementMode.PIP:
        return MergePlacementSlot.OVERLAY
    if mode in {
        MergePlacementMode.BASE,
        MergePlacementMode.FULL_SCREEN_PORTRAIT,
        MergePlacementMode.DUAL_CENTER_HUD,
        MergePlacementMode.DUAL_TOP_HUD,
    }:
        return MergePlacementSlot.CENTER
    role = _normalized_merge_source_angle_role(source)
    if role == "primary" or mode in {
        MergePlacementMode.SIDE_BY_SIDE,
        MergePlacementMode.ABOVE_BELOW,
    }:
        return (
            MergePlacementSlot.LEFT
            if mode == MergePlacementMode.SIDE_BY_SIDE
            else MergePlacementSlot.TOP
        )
    return (
        MergePlacementSlot.RIGHT
        if mode == MergePlacementMode.SIDE_BY_SIDE
        else MergePlacementSlot.BOTTOM
    )


@dataclass(slots=True)
class ResolvedMergeSourcePlacement:
    source: MergeSource
    mode: MergePlacementMode
    slot: MergePlacementSlot
    priority: int


def _resolved_merge_source_placements(
    project: Project, merge_sources: list[MergeSource]
) -> list[ResolvedMergeSourcePlacement]:
    sorted_sources = sorted(merge_sources, key=_merge_source_role_sort_key)
    return [
        ResolvedMergeSourcePlacement(
            source=s,
            mode=_resolved_merge_source_mode(s, project),
            slot=_resolved_merge_source_slot(s, project),
            priority=_camera_role_priority(s),
        )
        for s in sorted_sources
    ]


def _build_grid_merge_plan(project: Project, merge_sources: list[MergeSource]) -> BaseRenderPlan:
    fps = _output_fps(project)
    sorted_sources = sorted(merge_sources, key=_merge_source_role_sort_key)
    merge_assets = [source.asset for source in sorted_sources]
    sources = [project.primary_video, *merge_assets]
    tile_width = max(2, int(project.primary_video.width or 0))
    tile_height = max(2, int(project.primary_video.height or 0))
    columns = max(1, math.ceil(math.sqrt(len(sources))))
    rows = math.ceil(len(sources) / columns)

    input_args = [
        *ffmpeg_command(
            [
                "-v",
                "info",
            ]
        ),
        "-i",
        project.primary_video.path,
    ]
    for source, asset in zip(merge_sources, merge_assets, strict=False):
        input_args.extend(_source_input_args(source, fps))
    input_args.append("-an")

    chain_parts: list[str] = []
    layout_parts: list[str] = []
    for index, source in enumerate(sources):
        source_chain = f"[{index}:v]setpts=PTS-STARTPTS"
        if index > 0:
            offset_ms = _source_sync_offset_ms(merge_sources[index - 1])
            if offset_ms < 0:
                source_chain += f",tpad=start_duration={abs(offset_ms) / 1000:.3f}:color=black"
        chain_parts.append(
            f"{source_chain},scale={tile_width}:{tile_height}:"
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
        duration_ms=_merged_duration_ms(project, merge_sources),
    )


def _build_multi_pip_merge_plan(
    project: Project, merge_sources: list[MergeSource]
) -> BaseRenderPlan:
    fps = _output_fps(project)
    sorted_sources = sorted(merge_sources, key=_merge_source_role_sort_key)
    input_args = [
        *ffmpeg_command(["-v", "info"]),
        "-i",
        project.primary_video.path,
    ]
    for source in sorted_sources:
        input_args.extend(_source_input_args(source, fps))
    input_args.append("-an")

    filter_parts = [
        f"[0:v]setpts=PTS-STARTPTS,scale={project.primary_video.width}:{project.primary_video.height}[base0]"
    ]
    previous_label = "base0"
    for index, source in enumerate(merge_sources, start=1):
        asset = source.asset
        offset_ms = _source_sync_offset_ms(source)
        placement = getattr(source, "placement", None)
        placement_mode = str(getattr(placement, "mode", "pip") or "pip")
        pip_size = (
            source.pip_size_percent
            if source.pip_size_percent is not None
            else project.merge.pip_size_percent
        )
        pip_x = source.pip_x if source.pip_x is not None else project.merge.pip_x
        pip_y = source.pip_y if source.pip_y is not None else project.merge.pip_y
        if placement_mode == "base":
            rect = calculate_pip_rect(
                project.primary_video,
                asset,
                100,
                0.5,
                0.5,
            )
        else:
            rect = calculate_pip_rect(
                project.primary_video,
                asset,
                pip_size,
                pip_x,
                pip_y,
            )
        asset_chain = f"[{index}:v]setpts=PTS-STARTPTS"
        if offset_ms < 0:
            asset_chain += f",tpad=start_duration={abs(offset_ms) / 1000:.3f}:color=black"
        if _source_opacity(source) < 1.0:
            asset_chain += f",format=rgba,colorchannelmixer=aa={_source_opacity(source):.3f}"
        filter_parts.append(f"{asset_chain},scale={rect.width}:{rect.height}[pip{index}]")
        filter_parts.append(
            f"[{previous_label}][pip{index}]overlay=x={rect.x}:y={rect.y}:"
            f"eof_action=pass:shortest=0:repeatlast=0[base{index}]"
        )
        previous_label = f"base{index}"
    filter_parts.append(f"[{previous_label}]format=rgba[f]")

    command = [
        *input_args,
        "-filter_complex",
        ";".join(filter_parts),
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
        width=project.primary_video.width,
        height=project.primary_video.height,
        fps=fps,
        duration_ms=_merged_duration_ms(project, merge_sources),
    )


def _build_single_video_plan(project: Project) -> BaseRenderPlan:
    fps = _output_fps(project)
    command = ffmpeg_command(
        [
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
        ]
    )
    return BaseRenderPlan(
        command=command,
        width=project.primary_video.width,
        height=project.primary_video.height,
        fps=fps,
        duration_ms=project.primary_video.duration_ms,
    )


def _build_merge_plan(project: Project) -> BaseRenderPlan:
    merge_sources = _merge_sources(project)
    if not merge_sources:
        return _build_single_video_plan(project)
    if len(merge_sources) > 1:
        if project.merge.layout == MergeLayout.PIP:
            return _build_multi_pip_merge_plan(project, merge_sources)
        return _build_grid_merge_plan(project, merge_sources)

    secondary_source = merge_sources[0]
    secondary = secondary_source.asset
    canvas = calculate_merge_canvas(
        project.primary_video,
        secondary,
        project.merge.layout,
        secondary_source.pip_size_percent
        if secondary_source.pip_size_percent is not None
        else project.merge.pip_size_percent,
        secondary_source.pip_x,
        secondary_source.pip_y,
    )
    fps = _output_fps(project)
    offset_ms = _source_sync_offset_ms(secondary_source)

    input_args = [
        *ffmpeg_command(
            [
                "-v",
                "info",
            ]
        ),
        "-i",
        project.primary_video.path,
    ]
    input_args.extend(_source_input_args(secondary_source, fps))
    input_args.append("-an")

    secondary_chain = "[1:v]setpts=PTS-STARTPTS"
    if offset_ms < 0:
        secondary_chain += f",tpad=start_duration={abs(offset_ms) / 1000:.3f}:color=black"
    if project.merge.layout == MergeLayout.PIP and _source_opacity(secondary_source) < 1.0:
        secondary_chain += (
            f",format=rgba,colorchannelmixer=aa={_source_opacity(secondary_source):.3f}"
        )

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
        duration_ms=_merged_duration_ms(project, [secondary_source]),
    )


def build_base_render_plan(project: Project) -> BaseRenderPlan:
    if project.merge.enabled and _merge_sources(project):
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


_EXPECTED_DECODER_PIPE_SHUTDOWN_FRAGMENTS = (
    "Broken pipe",
    "Error muxing a packet",
    "Task finished with error code: -32",
    "Terminating thread with return code -32",
    "Error writing trailer",
    "Error closing file",
    "Conversion failed!",
)


def _prune_expected_decoder_pipe_shutdown_lines(log_lines: list[str]) -> bool:
    cleaned_lines: list[str] = []
    suppressed = False
    for line in log_lines:
        if line.startswith("decoder:") and any(
            fragment in line for fragment in _EXPECTED_DECODER_PIPE_SHUTDOWN_FRAGMENTS
        ):
            suppressed = True
            continue
        cleaned_lines.append(line)
    if suppressed:
        cleaned_lines.append(
            "decoder: rawvideo pipe closed after the encoder finished the shortest stream; decoder shutdown was expected."
        )
        log_lines[:] = cleaned_lines
    return suppressed


def _encoder_command(
    project: Project,
    output_width: int,
    output_height: int,
    fps: float,
    output_target: Path,
    pass_number: int | None = None,
    passlogfile: Path | None = None,
    first_pass: bool = False,
    fade_in_s: float = 0.0,
    fade_out_s: float = 0.0,
    duration_s: float = 0.0,
    fade_audio: bool = False,
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
    audio_args = (
        []
        if first_pass
        else [
            "-i",
            project.primary_video.path,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
        ]
    )
    normalized_fade_in, normalized_fade_out = _normalized_output_fades(
        fade_in_s, fade_out_s, duration_s
    )
    video_filters: list[str] = []
    audio_filters: list[str] = []
    if normalized_fade_in > 0:
        video_filters.append(f"fade=t=in:st=0:d={normalized_fade_in:.3f}:color=black")
        audio_filters.append(f"afade=t=in:st=0:d={normalized_fade_in:.3f}")
    if normalized_fade_out > 0:
        fade_out_start = max(0.0, duration_s - normalized_fade_out)
        video_filters.append(
            f"fade=t=out:st={fade_out_start:.3f}:d={normalized_fade_out:.3f}:color=black"
        )
        audio_filters.append(f"afade=t=out:st={fade_out_start:.3f}:d={normalized_fade_out:.3f}")
    encode_args = [
        *([] if not video_filters else ["-vf", ",".join(video_filters)]),
        "-c:v",
        _codec_name(project.export.video_codec),
        "-preset",
        project.export.ffmpeg_preset,
        "-threads",
        "4",
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
    audio_encode_args = (
        ["-an"]
        if first_pass
        else [
            *([] if not fade_audio or not audio_filters else ["-af", ",".join(audio_filters)]),
            "-c:a",
            project.export.audio_codec.value,
            "-ar",
            str(project.export.audio_sample_rate),
            "-b:a",
            audio_bitrate,
        ]
    )
    output_args = (
        ["-f", "null", os.devnull]
        if first_pass
        else [
            *(
                ["-movflags", "+faststart"]
                if output_target.suffix.lower() in _FASTSTART_EXPORT_EXTENSIONS
                else []
            ),
            "-shortest",
            str(output_target),
        ]
    )
    command = ffmpeg_command(
        [*input_args, *audio_args, *encode_args, *audio_encode_args, *output_args]
    )
    return command


def _normalized_output_fades(
    fade_in_s: float, fade_out_s: float, duration_s: float
) -> tuple[float, float]:
    duration = max(0.0, float(duration_s or 0.0))
    fade_in = max(0.0, float(fade_in_s or 0.0))
    fade_out = max(0.0, float(fade_out_s or 0.0))
    total = fade_in + fade_out
    if duration <= 0 or total <= duration:
        return fade_in, fade_out
    scale = duration / total
    return fade_in * scale, fade_out * scale


def _input_has_audio(path: str | Path) -> bool:
    try:
        info = run_ffprobe_json(Path(path))
    except (OSError, RuntimeError, ValueError):
        return False
    return any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))


def _read_exact(pipe: Any, n: int) -> bytes:
    chunks: list[bytes] = []
    while n > 0:
        chunk = pipe.read(n)
        if not chunk:
            break
        chunks.append(chunk)
        n -= len(chunk)
    return b"".join(chunks)


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
    # Decoder stderr is buffered until process outcomes are known. A downstream
    # encoder exit otherwise surfaces expected pipe-shutdown noise as live errors.
    decoder_log_thread = _start_log_reader(decoder.stderr, "decoder", log_lines, None)
    encoder_log_thread = _start_log_reader(encoder.stderr, "encoder", log_lines, log_callback)
    renderer = OverlayRenderer()
    bytes_per_frame = plan.width * plan.height * 4
    total_frames = max(1, math.ceil((plan.duration_ms / 1000.0) * plan.fps))
    encoder_pipe_broken = False
    try:
        for frame_index in range(total_frames):
            raw = _read_exact(decoder.stdout, bytes_per_frame)
            if len(raw) < bytes_per_frame:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(plan.height, plan.width, 4).copy()
            cropped = frame[
                crop_top : crop_top + crop_height, crop_left : crop_left + crop_width
            ].copy()
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
                round((frame_index / plan.fps) * 1000),
                output_width,
                output_height,
            )
            painter.end()

            try:
                encoder.stdin.write(_image_to_rgba_bytes(image))
            except BrokenPipeError:
                encoder_pipe_broken = True
                break
            if progress_callback is not None:
                frame_progress = min((frame_index + 1) / total_frames, 1.0)
                progress_callback(min(progress_start + (frame_progress * progress_span), 1.0))
    finally:
        if encoder_pipe_broken and decoder.poll() is None:
            decoder.terminate()
        if decoder.stdout is not None:
            decoder.stdout.close()
        if encoder.stdin is not None:
            try:
                encoder.stdin.close()
            except BrokenPipeError:
                encoder_pipe_broken = True

    decoder_return = decoder.wait()
    encoder_return = encoder.wait()
    decoder_log_thread.join(timeout=2)
    encoder_log_thread.join(timeout=2)

    expected_decoder_shutdown = _is_expected_decoder_pipe_shutdown(
        decoder_return, encoder_return, log_lines
    )
    if (
        expected_decoder_shutdown
        and _prune_expected_decoder_pipe_shutdown_lines(log_lines)
        and log_callback is not None
    ):
        log_callback(log_lines[-1])

    if decoder_return != 0 and not expected_decoder_shutdown and encoder_return == 0:
        raise RuntimeError(f"Base video render failed (decoder exit code {decoder_return})")
    if encoder_return != 0:
        reason = (
            f"signal {-encoder_return}" if encoder_return < 0 else f"exit code {encoder_return}"
        )
        message = f"MP4 encode failed ({reason})"
        log_lines.append(f"encoder: {message}")
        if log_callback is not None:
            log_callback(log_lines[-1])
        raise RuntimeError(message)


def _is_expected_decoder_pipe_shutdown(
    decoder_return: int, encoder_return: int, log_lines: list[str]
) -> bool:
    if decoder_return == 0 or encoder_return != 0:
        return False
    decoder_log = "\n".join(line for line in log_lines if line.startswith("decoder:"))
    return "Broken pipe" in decoder_log and "Conversion failed!" in decoder_log


def _frame_profile_to_aspect_ratio(frame_profile: str) -> AspectRatio:
    mapping: dict[str, AspectRatio] = {
        "16:9": AspectRatio.LANDSCAPE,
        "9:16": AspectRatio.PORTRAIT,
        "1:1": AspectRatio.SQUARE,
        "4:5": AspectRatio.PORTRAIT_45,
    }
    return mapping.get(frame_profile.strip().lower(), AspectRatio.ORIGINAL)


def _validate_export_output(output_target: Path) -> None:
    if not output_target.exists():
        raise RuntimeError(f"Export output missing: {output_target}")
    if output_target.stat().st_size <= 0:
        raise RuntimeError(f"Export output is empty: {output_target}")
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(output_target),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        info = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f"Export output is invalid: {output_target} ({exc})") from exc
    streams = info.get("streams", [])
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise RuntimeError(f"Export output has no video stream: {output_target}")


def export_project(
    project: Project,
    output_path: str | Path,
    progress_callback: Callable[[float], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
    frame_profile: str | None = None,
    fade_in_s: float = 0.0,
    fade_out_s: float = 0.0,
    fade_audio: bool = False,
) -> Path:
    original_project = project
    project = _active_export_project(project)
    project.export = original_project.export
    project.export.last_log = ""
    project.export.last_error = None
    if not project.primary_video.path:
        raise ValueError("Primary video is required for export")

    _ensure_qt_gui_application()
    project.scoring.hit_factor = calculate_hit_factor(project)
    plan = build_base_render_plan(project)
    effective_aspect = (
        _frame_profile_to_aspect_ratio(frame_profile)
        if frame_profile
        else project.export.aspect_ratio
    )
    crop_left, crop_top, crop_width, crop_height = compute_crop_box(
        plan.width,
        plan.height,
        effective_aspect,
        project.export.crop_center_x,
        project.export.crop_center_y,
    )
    output_width, output_height = _target_dimensions(project, crop_width, crop_height)
    duration_s = max(0.0, plan.duration_ms / 1000.0)
    fade_audio = fade_audio and _input_has_audio(project.primary_video.path)

    output_target = _normalize_output_target(output_path)
    output_target.parent.mkdir(parents=True, exist_ok=True)
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

    def sync_export_log(line: str) -> None:
        project.export.last_log = "\n".join(log_lines[-400:])
        if log_callback is not None:
            log_callback(line)

    project.export.last_log = "\n".join(log_lines[-400:])

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
                    fade_in_s=fade_in_s,
                    fade_out_s=fade_out_s,
                    duration_s=duration_s,
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
                    fade_in_s=fade_in_s,
                    fade_out_s=fade_out_s,
                    duration_s=duration_s,
                    fade_audio=fade_audio,
                )
                log_lines.append(f"Encoder pass 1 command: {shlex.join(pass_one_command)}")
                log_lines.append(f"Encoder pass 2 command: {shlex.join(pass_two_command)}")
                project.export.last_log = "\n".join(log_lines[-400:])
                _render_pass(
                    project,
                    plan,
                    crop_box,
                    output_width,
                    output_height,
                    pass_one_command,
                    log_lines,
                    sync_export_log,
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
                    sync_export_log,
                    progress_callback,
                    0.5,
                    0.5,
                )
        else:
            encoder_command = _encoder_command(
                project,
                output_width,
                output_height,
                plan.fps,
                output_target,
                fade_in_s=fade_in_s,
                fade_out_s=fade_out_s,
                duration_s=duration_s,
                fade_audio=fade_audio,
            )
            log_lines.append(f"Encoder command: {shlex.join(encoder_command)}")
            project.export.last_log = "\n".join(log_lines[-400:])
            _render_pass(
                project,
                plan,
                crop_box,
                output_width,
                output_height,
                encoder_command,
                log_lines,
                sync_export_log,
                progress_callback,
                0.0,
                1.0,
            )
    except RuntimeError as exc:
        project.export.last_error = str(exc)
        project.export.last_log = "\n".join(log_lines[-400:])
        raise RuntimeError(project.export.last_log or str(exc)) from exc

    _validate_export_output(output_target)
    project.export.last_log = "\n".join(log_lines[-400:])

    return output_target

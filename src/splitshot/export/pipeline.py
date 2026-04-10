from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PySide6.QtGui import QImage, QPainter

from splitshot.domain.models import AspectRatio, ExportQuality, MergeLayout, Project
from splitshot.merge.layouts import calculate_merge_canvas
from splitshot.overlay.render import OverlayRenderer
from splitshot.scoring.logic import calculate_hit_factor


@dataclass(slots=True)
class BaseRenderPlan:
    command: list[str]
    width: int
    height: int
    fps: float
    duration_ms: int


def _quality_crf(quality: ExportQuality) -> str:
    return {
        ExportQuality.HIGH: "18",
        ExportQuality.MEDIUM: "23",
        ExportQuality.LOW: "28",
    }[quality]


def _ratio_value(aspect_ratio: AspectRatio) -> tuple[int, int] | None:
    return {
        AspectRatio.ORIGINAL: None,
        AspectRatio.LANDSCAPE: (16, 9),
        AspectRatio.PORTRAIT: (9, 16),
        AspectRatio.SQUARE: (1, 1),
        AspectRatio.PORTRAIT_45: (4, 5),
    }[aspect_ratio]


def _ensure_even(value: int) -> int:
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


def _merged_duration_ms(project: Project) -> int:
    primary = project.primary_video.duration_ms
    secondary = project.secondary_video.duration_ms if project.secondary_video else 0
    offset = project.analysis.sync_offset_ms
    secondary_visible = max(0, secondary - max(0, offset))
    secondary_end = max(0, -offset) + secondary_visible
    return max(primary, secondary_end)


def _build_single_video_plan(project: Project) -> BaseRenderPlan:
    fps = project.primary_video.fps or 30.0
    command = [
        "ffmpeg",
        "-v",
        "error",
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
    return BaseRenderPlan(
        command=command,
        width=project.primary_video.width,
        height=project.primary_video.height,
        fps=fps,
        duration_ms=project.primary_video.duration_ms,
    )


def _build_merge_plan(project: Project) -> BaseRenderPlan:
    assert project.secondary_video is not None
    canvas = calculate_merge_canvas(
        project.primary_video,
        project.secondary_video,
        project.merge.layout,
        project.merge.pip_size,
    )
    fps = project.primary_video.fps or 30.0
    offset_ms = project.analysis.sync_offset_ms

    input_args = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        project.primary_video.path,
    ]
    if offset_ms > 0:
        input_args.extend(["-ss", f"{offset_ms / 1000:.3f}"])
    input_args.extend(["-i", project.secondary_video.path, "-an"])

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
        duration_ms=_merged_duration_ms(project),
    )


def build_base_render_plan(project: Project) -> BaseRenderPlan:
    if project.merge.enabled and project.secondary_video is not None:
        return _build_merge_plan(project)
    return _build_single_video_plan(project)


def export_project(
    project: Project,
    output_path: str | Path,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    if not project.primary_video.path:
        raise ValueError("Primary video is required for export")

    project.scoring.hit_factor = calculate_hit_factor(project)
    plan = build_base_render_plan(project)
    crop_left, crop_top, output_width, output_height = compute_crop_box(
        plan.width,
        plan.height,
        project.export.aspect_ratio,
        project.export.crop_center_x,
        project.export.crop_center_y,
    )

    output_target = Path(output_path)
    output_target.parent.mkdir(parents=True, exist_ok=True)

    decoder = subprocess.Popen(
        plan.command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{output_width}x{output_height}",
            "-r",
            f"{plan.fps:.3f}",
            "-i",
            "pipe:0",
            "-i",
            project.primary_video.path,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            _quality_crf(project.export.quality),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_target),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    renderer = OverlayRenderer()
    bytes_per_frame = plan.width * plan.height * 4
    total_frames = max(1, int(math.ceil((plan.duration_ms / 1000.0) * plan.fps)))

    try:
        for frame_index in range(total_frames):
            raw = decoder.stdout.read(bytes_per_frame)
            if len(raw) < bytes_per_frame:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(plan.height, plan.width, 4).copy()
            cropped = frame[crop_top : crop_top + output_height, crop_left : crop_left + output_width].copy()
            image = QImage(
                cropped.data,
                output_width,
                output_height,
                cropped.strides[0],
                QImage.Format_RGBA8888,
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

            encoder.stdin.write(cropped.tobytes())
            if progress_callback is not None:
                progress_callback(min((frame_index + 1) / total_frames, 1.0))
    finally:
        if decoder.stdout is not None:
            decoder.stdout.close()
        if encoder.stdin is not None:
            encoder.stdin.close()

    decoder_stderr = decoder.stderr.read().decode("utf-8", errors="replace") if decoder.stderr else ""
    encoder_stderr = encoder.stderr.read().decode("utf-8", errors="replace") if encoder.stderr else ""
    decoder_return = decoder.wait()
    encoder_return = encoder.wait()

    if decoder_return != 0:
        raise RuntimeError(decoder_stderr.strip() or "Base video render failed")
    if encoder_return != 0:
        raise RuntimeError(encoder_stderr.strip() or "MP4 encode failed")

    return output_target

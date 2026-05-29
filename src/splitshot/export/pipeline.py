from __future__ import annotations

import math
import os
import shlex
import subprocess
import sys
import threading
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtWidgets import QApplication

from splitshot.domain.models import (
    AspectRatio,
    ExportFrameRate,
    ExportQuality,
    ExportVideoCodec,
    MERGE_SOURCE_ANGLE_ROLE_VALUES,
    MergeLayout,
    MergeSource,
    OverlayPosition,
    Project,
)
from splitshot.media.ffmpeg import ffmpeg_command
from splitshot.merge.layouts import Rect, calculate_merge_canvas, calculate_pip_rect
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
    audio_source_path: str | None = None
    audio_sync_offset_ms: int = 0


@dataclass(slots=True)
class ResolvedMergeSourcePlacement:
    source: MergeSource
    source_id: str
    stable_index: int
    order_index: int
    layer_index: int
    angle_role: str
    mode: str
    slot: str
    target_kind: str
    target_source_id: str | None


_CAMERA_ROLE_PRIORITY = {
    role: index for index, role in enumerate(MERGE_SOURCE_ANGLE_ROLE_VALUES)
}
_CAMERA_ROLE_BASE_TARGET_PRIORITY = {
    "primary": 0,
    "static": 1,
    "follow": 2,
    "detail": 3,
}
_MERGE_SOURCE_PREVIEW_PLACEMENT_MODES = {
    "auto",
    "base",
    "side_by_side",
    "above_below",
    "pip",
    "full_screen_portrait",
    "dual_center_hud",
    "dual_top_hud",
}
_MERGE_SOURCE_PREVIEW_PLACEMENT_SLOTS = {
    "auto",
    "left",
    "right",
    "top",
    "bottom",
    "center",
    "overlay",
}


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


def _output_fps(project: Project, *, reference_asset: Any = None) -> float:
    source_fps = float(getattr(reference_asset, "fps", 0) or project.primary_video.fps or 30.0)
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


def _normalized_merge_source_angle_role(source: MergeSource | None) -> str:
    normalized = str(getattr(source, "angle_role", "") or "").strip().lower()
    if normalized in _CAMERA_ROLE_PRIORITY:
        return normalized
    asset = getattr(source, "asset", None)
    return "detail" if getattr(asset, "is_still_image", False) else "follow"


def _camera_role_priority(angle_role: object) -> int:
    normalized = str(angle_role or "").strip().lower()
    return _CAMERA_ROLE_PRIORITY.get(normalized, len(_CAMERA_ROLE_PRIORITY))


def _camera_role_base_target_priority(angle_role: object) -> int:
    normalized = str(angle_role or "").strip().lower()
    return _CAMERA_ROLE_BASE_TARGET_PRIORITY.get(
        normalized,
        len(_CAMERA_ROLE_BASE_TARGET_PRIORITY),
    )


def _merge_source_stable_order_index(source: MergeSource, fallback_index: int) -> int:
    order_index = getattr(getattr(source, "placement", None), "order_index", None)
    if order_index is None:
        return fallback_index
    return max(0, int(order_index))


def _merge_source_role_sort_key(source: MergeSource, stable_index: int) -> tuple[int, int, int]:
    return (
        _camera_role_priority(_normalized_merge_source_angle_role(source)),
        _merge_source_stable_order_index(source, stable_index),
        stable_index,
    )


def _project_merge_seed_mode(project: Project, angle_role: str) -> str:
    normalized_layout = str(project.merge.layout or "").strip().lower()
    if angle_role == "primary":
        return "base"
    if angle_role == "detail":
        if normalized_layout in {"pip", "full_screen_portrait"}:
            return normalized_layout
        return "pip"
    if normalized_layout in {
        "side_by_side",
        "above_below",
        "dual_center_hud",
        "dual_top_hud",
    }:
        return normalized_layout
    return "side_by_side"


def _merge_source_preview_slot_values(mode: str) -> list[str]:
    if mode in {"side_by_side", "dual_center_hud", "dual_top_hud"}:
        return ["left", "right"]
    if mode == "above_below":
        return ["top", "bottom"]
    if mode == "pip":
        return ["overlay", "left", "right", "top", "bottom", "center"]
    return ["center"]


def _camera_role_seed_slot(angle_role: str, mode: str) -> str:
    if mode in {"side_by_side", "dual_center_hud", "dual_top_hud"}:
        return "left" if angle_role == "static" else "right"
    if mode == "above_below":
        return "top" if angle_role == "static" else "bottom"
    if mode == "pip":
        return "overlay"
    return "center"


def _merge_source_requested_mode(source: MergeSource) -> str:
    requested = str(getattr(source.placement, "mode", "") or "").strip().lower()
    return requested if requested in _MERGE_SOURCE_PREVIEW_PLACEMENT_MODES else "auto"


def _resolved_merge_source_mode(project: Project, source: MergeSource) -> str:
    requested = _merge_source_requested_mode(source)
    if requested != "auto":
        return requested
    return _project_merge_seed_mode(project, _normalized_merge_source_angle_role(source))


def _resolved_merge_source_slot(project: Project, source: MergeSource, mode: str) -> str:
    requested = str(getattr(source.placement, "slot", "") or "").strip().lower()
    if requested not in _MERGE_SOURCE_PREVIEW_PLACEMENT_SLOTS or requested == "auto":
        return _camera_role_seed_slot(_normalized_merge_source_angle_role(source), mode)
    allowed_slots = _merge_source_preview_slot_values(mode)
    return requested if requested in allowed_slots else _camera_role_seed_slot(
        _normalized_merge_source_angle_role(source),
        mode,
    )


def _merge_source_base_target_sort_key(item: ResolvedMergeSourcePlacement) -> tuple[int, int, int, int]:
    if item.mode in {"base", "full_screen_portrait"}:
        mode_priority = 0
    elif item.mode in {
        "side_by_side",
        "above_below",
        "dual_center_hud",
        "dual_top_hud",
    }:
        mode_priority = 1
    else:
        mode_priority = 2
    return (
        mode_priority,
        _camera_role_base_target_priority(item.angle_role),
        item.order_index,
        item.stable_index,
    )


def _preferred_merge_source_base_target(
    resolved_sources: list[ResolvedMergeSourcePlacement],
    *,
    exclude_source_id: str,
) -> ResolvedMergeSourcePlacement | None:
    for candidate in sorted(resolved_sources, key=_merge_source_base_target_sort_key):
        if candidate.source_id == exclude_source_id:
            continue
        if candidate.mode in {
            "base",
            "side_by_side",
            "above_below",
            "full_screen_portrait",
            "dual_center_hud",
            "dual_top_hud",
        }:
            return candidate
    return None


def _resolved_merge_source_placements_for_export(
    project: Project,
    merge_sources: list[MergeSource],
) -> list[ResolvedMergeSourcePlacement]:
    role_sorted_sources = [
        (stable_index, source)
        for stable_index, source in sorted(
            enumerate(merge_sources),
            key=lambda item: _merge_source_role_sort_key(item[1], item[0]),
        )
    ]

    resolved_sources: list[ResolvedMergeSourcePlacement] = []
    for stable_index, source in role_sorted_sources:
        order_index = _merge_source_stable_order_index(source, stable_index)
        layer_index = getattr(getattr(source, "placement", None), "layer_index", None)
        if layer_index is None:
            layer_index = order_index
        angle_role = _normalized_merge_source_angle_role(source)
        mode = _resolved_merge_source_mode(project, source)
        slot = _resolved_merge_source_slot(project, source, mode)
        resolved_sources.append(
            ResolvedMergeSourcePlacement(
                source=source,
                source_id=str(getattr(source, "id", "") or stable_index),
                stable_index=stable_index,
                order_index=order_index,
                layer_index=max(0, int(layer_index)),
                angle_role=angle_role,
                mode=mode,
                slot=slot,
                target_kind="primary_video",
                target_source_id=None,
            )
        )

    resolved_source_ids = {item.source_id for item in resolved_sources}
    finalized_sources: list[ResolvedMergeSourcePlacement] = []
    for item in resolved_sources:
        requested_target_source_id = str(item.source.placement.target_source_id or "").strip() or None
        requested_target_kind = str(item.source.placement.target_kind or "").strip().lower()
        target_kind = "primary_video"
        target_source_id = None
        if item.mode in {"pip", "full_screen_portrait"}:
            if (
                requested_target_kind == "merge_source"
                and requested_target_source_id in resolved_source_ids
                and requested_target_source_id != item.source_id
            ):
                target_kind = "merge_source"
                target_source_id = requested_target_source_id
            elif _merge_source_requested_mode(item.source) == "auto":
                preferred_target = _preferred_merge_source_base_target(
                    resolved_sources,
                    exclude_source_id=item.source_id,
                )
                if preferred_target is not None:
                    target_kind = "merge_source"
                    target_source_id = preferred_target.source_id
        finalized_sources.append(
            ResolvedMergeSourcePlacement(
                source=item.source,
                source_id=item.source_id,
                stable_index=item.stable_index,
                order_index=item.order_index,
                layer_index=item.layer_index,
                angle_role=item.angle_role,
                mode=item.mode,
                slot=item.slot,
                target_kind=target_kind,
                target_source_id=target_source_id,
            )
        )
    return finalized_sources


def _preferred_merge_anchor_source(
    resolved_sources: list[ResolvedMergeSourcePlacement],
) -> MergeSource | None:
    for item in resolved_sources:
        if item.angle_role == "primary":
            return item.source
    for item in resolved_sources:
        if item.mode == "base":
            return item.source
    return resolved_sources[0].source if resolved_sources else None


def _preferred_merge_visual_anchor_source(
    resolved_sources: list[ResolvedMergeSourcePlacement],
) -> MergeSource | None:
    for item in sorted(resolved_sources, key=_merge_source_base_target_sort_key):
        if item.mode in {"base", "full_screen_portrait"}:
            return item.source
    return None


def _merge_source_supports_audio_anchor(source: MergeSource | None) -> bool:
    if source is None:
        return False
    asset = source.asset
    return (
        bool(asset.path)
        and not asset.is_still_image
        and asset.media_kind != "animated_gif"
    )


def _preferred_merge_audio_anchor_source(
    resolved_sources: list[ResolvedMergeSourcePlacement],
) -> MergeSource | None:
    anchor_source = _preferred_merge_anchor_source(resolved_sources)
    if _merge_source_supports_audio_anchor(anchor_source):
        return anchor_source
    for item in resolved_sources:
        if _merge_source_supports_audio_anchor(item.source):
            return item.source
    return None


def _clamp_unit(value: float | None, default: float = 1.0) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _merge_source_canvas_rect(project: Project, *, reference_asset: Any = None) -> Rect:
    canvas_asset = project.primary_video if reference_asset is None else reference_asset
    return Rect(
        0,
        0,
        max(2, int(getattr(canvas_asset, "width", 0) or project.primary_video.width or 0)),
        max(2, int(getattr(canvas_asset, "height", 0) or project.primary_video.height or 0)),
    )


def _merge_source_pip_rect(project: Project, source: MergeSource, frame_rect: Rect) -> Rect:
    asset = source.asset
    source_width = max(1, int(asset.width or 1))
    source_height = max(1, int(asset.height or 1))
    effective_pip_size = source.pip_size_percent
    if effective_pip_size is None:
        effective_pip_size = int(project.merge.pip_size_percent or 35)
    inset_width = max(1, int(round(frame_rect.width * (float(effective_pip_size) / 100.0))))
    inset_height = max(1, int(round((source_height / source_width) * inset_width)))
    if inset_height > frame_rect.height:
        fit_scale = frame_rect.height / float(inset_height)
        inset_width = max(1, int(round(inset_width * fit_scale)))
        inset_height = max(1, int(round(inset_height * fit_scale)))
    travel_x = max(0, frame_rect.width - inset_width)
    travel_y = max(0, frame_rect.height - inset_height)
    pip_x = _clamp_unit(getattr(source, "pip_x", 1.0), 1.0)
    pip_y = _clamp_unit(getattr(source, "pip_y", 1.0), 1.0)
    return Rect(
        frame_rect.x + int(round(travel_x * pip_x)),
        frame_rect.y + int(round(travel_y * pip_y)),
        inset_width,
        inset_height,
    )


def _merge_source_pip_preview_rect(
    project: Project,
    source: MergeSource,
    frame_rect: Rect,
    slot: str,
) -> Rect:
    if slot == "overlay":
        return _merge_source_pip_rect(project, source, frame_rect)
    slot_coordinates = {
        "left": {"pip_x": 0.0, "pip_y": 0.5},
        "right": {"pip_x": 1.0, "pip_y": 0.5},
        "top": {"pip_x": 0.5, "pip_y": 0.0},
        "bottom": {"pip_x": 0.5, "pip_y": 1.0},
        "center": {"pip_x": 0.5, "pip_y": 0.5},
    }.get(
        slot,
        {
            "pip_x": _clamp_unit(getattr(source, "pip_x", 1.0), 1.0),
            "pip_y": _clamp_unit(getattr(source, "pip_y", 1.0), 1.0),
        },
    )
    slot_source = deepcopy(source)
    slot_source.pip_x = slot_coordinates["pip_x"]
    slot_source.pip_y = slot_coordinates["pip_y"]
    return _merge_source_pip_rect(project, slot_source, frame_rect)


def _merge_source_preview_rect(
    project: Project,
    resolved: ResolvedMergeSourcePlacement,
    frame_rect: Rect,
) -> Rect:
    mode = resolved.mode
    slot = resolved.slot
    if mode == "base":
        return Rect(frame_rect.x, frame_rect.y, frame_rect.width, frame_rect.height)
    if mode == "side_by_side":
        left_width = max(1, frame_rect.width // 2)
        right_width = max(1, frame_rect.width - left_width)
        use_left = slot == "left"
        return Rect(
            frame_rect.x if use_left else frame_rect.x + left_width,
            frame_rect.y,
            left_width if use_left else right_width,
            frame_rect.height,
        )
    if mode == "above_below":
        top_height = max(1, frame_rect.height // 2)
        bottom_height = max(1, frame_rect.height - top_height)
        use_top = slot == "top"
        return Rect(
            frame_rect.x,
            frame_rect.y if use_top else frame_rect.y + top_height,
            frame_rect.width,
            top_height if use_top else bottom_height,
        )
    if mode == "full_screen_portrait":
        portrait_width = max(
            1,
            min(frame_rect.width, int(round(frame_rect.height * (9 / 16)))),
        )
        return Rect(
            frame_rect.x + max(0, int(round((frame_rect.width - portrait_width) / 2))),
            frame_rect.y,
            portrait_width,
            frame_rect.height,
        )
    if mode == "dual_center_hud":
        gutter_width = min(
            max(24, int(round(frame_rect.height * 0.18))),
            max(24, frame_rect.width - 2),
        )
        left_width = max(1, (frame_rect.width - gutter_width) // 2)
        right_width = max(1, frame_rect.width - gutter_width - left_width)
        use_left = slot == "left"
        return Rect(
            frame_rect.x if use_left else frame_rect.x + left_width + gutter_width,
            frame_rect.y,
            left_width if use_left else right_width,
            frame_rect.height,
        )
    if mode == "dual_top_hud":
        hud_height = min(
            max(24, int(round(frame_rect.height * 0.18))),
            max(24, frame_rect.height - 2),
        )
        left_width = max(1, frame_rect.width // 2)
        right_width = max(1, frame_rect.width - left_width)
        use_left = slot == "left"
        return Rect(
            frame_rect.x if use_left else frame_rect.x + left_width,
            frame_rect.y + hud_height,
            left_width if use_left else right_width,
            max(1, frame_rect.height - hud_height),
        )
    return _merge_source_pip_preview_rect(project, resolved.source, frame_rect, slot)


def _merge_source_draw_sort_key(item: ResolvedMergeSourcePlacement) -> tuple[int, int, int, int]:
    if item.mode == "base":
        z_group = 10
    elif item.mode in {"side_by_side", "above_below", "dual_center_hud", "dual_top_hud"}:
        z_group = 20
    elif item.mode == "full_screen_portrait":
        z_group = 30
    else:
        z_group = 40
    return (z_group, item.layer_index, item.order_index, item.stable_index)


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
        )
    ]


def _source_sync_offset_ms(source: MergeSource) -> int:
    return int(getattr(source, "sync_offset_ms", 0) or 0)


def _source_opacity(source: MergeSource) -> float:
    raw_opacity = getattr(source, "opacity", 1.0)
    if raw_opacity is None:
        return 1.0
    return max(0.0, min(1.0, float(raw_opacity)))


def _source_uses_looped_still_input(source: MergeSource) -> bool:
    return source.asset.is_still_image and source.asset.media_kind != "animated_gif"


def _source_input_args(source: MergeSource, fps: float) -> list[str]:
    asset = source.asset
    offset_ms = _source_sync_offset_ms(source)
    input_args: list[str] = []
    if offset_ms > 0 and not asset.is_still_image and asset.media_kind != "animated_gif":
        input_args.extend(["-ss", f"{offset_ms / 1000:.3f}"])
    if _source_uses_looped_still_input(source):
        input_args.extend(["-loop", "1", "-framerate", f"{fps:.3f}", "-i", asset.path])
    elif asset.media_kind == "animated_gif":
        input_args.extend(["-stream_loop", "-1", "-ignore_loop", "0", "-i", asset.path])
    else:
        input_args.extend(["-i", asset.path])
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


def _build_grid_merge_plan(project: Project, merge_sources: list[MergeSource]) -> BaseRenderPlan:
    fps = _output_fps(project)
    merge_assets = [source.asset for source in merge_sources]
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
    for source in merge_sources:
        input_args.extend(_source_input_args(source, fps))
    input_args.append("-an")

    filter_parts = [
        f"[0:v]setpts=PTS-STARTPTS,scale={project.primary_video.width}:{project.primary_video.height}[base0]"
    ]
    previous_label = "base0"
    for index, source in enumerate(merge_sources, start=1):
        asset = source.asset
        offset_ms = _source_sync_offset_ms(source)
        rect = calculate_pip_rect(
            project.primary_video,
            asset,
            source.pip_size_percent
            if source.pip_size_percent is not None
            else project.merge.pip_size_percent,
            source.pip_x,
            source.pip_y,
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


def _rect_filter_chain(
    input_label: str,
    rect: Rect,
    *,
    output_label: str,
    fit_mode: str = "contain",
    offset_ms: int = 0,
    opacity: float | None = None,
) -> str:
    chain = f"{input_label}setpts=PTS-STARTPTS"
    if offset_ms < 0:
        chain += f",tpad=start_duration={abs(offset_ms) / 1000:.3f}:color=black"
    if fit_mode == "cover":
        chain += (
            f",scale={rect.width}:{rect.height}:force_original_aspect_ratio=increase,"
            f"crop={rect.width}:{rect.height}"
        )
    else:
        chain += (
            f",scale={rect.width}:{rect.height}:force_original_aspect_ratio=decrease,"
            f"pad={rect.width}:{rect.height}:(ow-iw)/2:(oh-ih)/2:color=black"
        )
    if opacity is not None and opacity < 1.0:
        chain += f",format=rgba,colorchannelmixer=aa={opacity:.3f}"
    return f"{chain}[{output_label}]"


def _build_positioned_two_source_merge_plan(
    project: Project,
    secondary_source: MergeSource,
    canvas,
    *,
    primary_fit_mode: str = "contain",
    secondary_fit_mode: str = "contain",
) -> BaseRenderPlan:
    if canvas.secondary_rect is None:
        raise ValueError("Positioned merge layouts require a secondary rectangle")

    fps = _output_fps(project)
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

    filter_complex = ";".join(
        [
            f"color=c=black:s={canvas.width}x{canvas.height}:r={fps:.3f}[bg0]",
            _rect_filter_chain(
                "[0:v]",
                canvas.primary_rect,
                output_label="v0",
                fit_mode=primary_fit_mode,
            ),
            _rect_filter_chain(
                "[1:v]",
                canvas.secondary_rect,
                output_label="v1",
                fit_mode=secondary_fit_mode,
                offset_ms=_source_sync_offset_ms(secondary_source),
                opacity=_source_opacity(secondary_source),
            ),
            (
                f"[bg0][v0]overlay=x={canvas.primary_rect.x}:y={canvas.primary_rect.y}:"
                "eof_action=pass:shortest=0:repeatlast=1[bg1]"
            ),
            (
                f"[bg1][v1]overlay=x={canvas.secondary_rect.x}:y={canvas.secondary_rect.y}:"
                "eof_action=pass:shortest=0:repeatlast=0,format=rgba[f]"
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
        width=canvas.width,
        height=canvas.height,
        fps=fps,
        duration_ms=_merged_duration_ms(project, [secondary_source]),
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


def _build_source_owned_merge_plan(
    project: Project,
    merge_sources: list[MergeSource],
) -> BaseRenderPlan:
    resolved_sources = _resolved_merge_source_placements_for_export(project, merge_sources)
    if not resolved_sources:
        return _build_single_video_plan(project)

    visual_anchor_source = _preferred_merge_visual_anchor_source(resolved_sources)
    audio_anchor_source = _preferred_merge_audio_anchor_source(resolved_sources)
    fps_reference_asset = None
    if visual_anchor_source is not None:
        fps_reference_asset = visual_anchor_source.asset
    elif audio_anchor_source is not None:
        fps_reference_asset = audio_anchor_source.asset
    fps = _output_fps(
        project,
        reference_asset=fps_reference_asset,
    )
    canvas_rect = _merge_source_canvas_rect(
        project,
        reference_asset=None if visual_anchor_source is None else visual_anchor_source.asset,
    )
    audio_source_path = project.primary_video.path
    audio_sync_offset_ms = 0
    if audio_anchor_source is not None and audio_anchor_source.asset.path:
        audio_source_path = audio_anchor_source.asset.path
        audio_sync_offset_ms = _source_sync_offset_ms(audio_anchor_source)

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
    input_indices: dict[str, int] = {}
    for input_index, resolved in enumerate(resolved_sources, start=1):
        input_indices[resolved.source_id] = input_index
        input_args.extend(_source_input_args(resolved.source, fps))
    input_args.append("-an")

    rect_cache: dict[str, Rect] = {}
    resolved_by_id = {item.source_id: item for item in resolved_sources}

    def resolve_rect(
        item: ResolvedMergeSourcePlacement,
        active_stack: set[str] | None = None,
    ) -> Rect:
        if item.source_id in rect_cache:
            return rect_cache[item.source_id]
        if active_stack is None:
            active_stack = set()
        if item.source_id in active_stack:
            return canvas_rect
        active_stack.add(item.source_id)
        target_frame = canvas_rect
        if item.target_kind == "merge_source" and item.target_source_id:
            target_item = resolved_by_id.get(item.target_source_id)
            if target_item is not None:
                target_frame = resolve_rect(target_item, active_stack)
        rect = _merge_source_preview_rect(project, item, target_frame)
        rect_cache[item.source_id] = rect
        active_stack.remove(item.source_id)
        return rect

    filter_parts = [
        f"color=c=black:s={canvas_rect.width}x{canvas_rect.height}:r={fps:.3f}[bg0]",
        _rect_filter_chain(
            "[0:v]",
            canvas_rect,
            output_label="primary0",
            fit_mode="contain",
        ),
        "[bg0][primary0]overlay=x=0:y=0:eof_action=pass:shortest=0:repeatlast=1[canvas0]",
    ]
    previous_label = "canvas0"
    for overlay_index, item in enumerate(
        sorted(resolved_sources, key=_merge_source_draw_sort_key),
        start=1,
    ):
        rect = resolve_rect(item)
        output_label = f"merge{overlay_index}"
        filter_parts.append(
            _rect_filter_chain(
                f"[{input_indices[item.source_id]}:v]",
                rect,
                output_label=output_label,
                fit_mode="contain",
                offset_ms=_source_sync_offset_ms(item.source),
                opacity=_source_opacity(item.source),
            )
        )
        next_label = f"canvas{overlay_index}"
        filter_parts.append(
            f"[{previous_label}][{output_label}]overlay=x={rect.x}:y={rect.y}:"
            f"eof_action=pass:shortest=0:repeatlast=0[{next_label}]"
        )
        previous_label = next_label
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
        width=canvas_rect.width,
        height=canvas_rect.height,
        fps=fps,
        duration_ms=_merged_duration_ms(project, [item.source for item in resolved_sources]),
        audio_source_path=audio_source_path,
        audio_sync_offset_ms=audio_sync_offset_ms,
    )


def _build_merge_plan(project: Project) -> BaseRenderPlan:
    if project.merge_sources:
        return _build_source_owned_merge_plan(
            project,
            [source for source in project.merge_sources if source.asset.path],
        )

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
    if project.merge.layout in {
        MergeLayout.FULL_SCREEN_PORTRAIT,
        MergeLayout.DUAL_CENTER_HUD,
        MergeLayout.DUAL_TOP_HUD,
    }:
        return _build_positioned_two_source_merge_plan(
            project,
            secondary_source,
            canvas,
            primary_fit_mode=(
                "cover"
                if project.merge.layout == MergeLayout.FULL_SCREEN_PORTRAIT
                else "contain"
            ),
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
    audio_start_ms: int = 0,
    audio_duration_ms: int | None = None,
    audio_source_path: str | None = None,
    audio_sync_offset_ms: int = 0,
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
    resolved_audio_source_path = str(audio_source_path or project.primary_video.path or "").strip()
    combined_audio_start_ms = int(audio_start_ms) + int(audio_sync_offset_ms)
    audio_delay_ms = max(0, -combined_audio_start_ms)
    audio_input_start_ms = max(0, combined_audio_start_ms)
    audio_input_duration_ms = None
    if audio_duration_ms is not None:
        audio_input_duration_ms = max(0, int(audio_duration_ms) - audio_delay_ms)
    include_audio = (
        not first_pass
        and bool(resolved_audio_source_path)
        and (audio_input_duration_ms is None or audio_input_duration_ms > 0)
    )
    audio_args = (
        []
        if not include_audio
        else [
            *(
                ["-ss", f"{audio_input_start_ms / 1000:.3f}"]
                if audio_input_start_ms > 0
                else []
            ),
            *(
                ["-itsoffset", f"{audio_delay_ms / 1000:.3f}"] if audio_delay_ms > 0 else []
            ),
            *(
                ["-t", f"{audio_input_duration_ms / 1000:.3f}"]
                if audio_input_duration_ms is not None and audio_input_duration_ms > 0
                else []
            ),
            "-i",
            resolved_audio_source_path,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
        ]
    )
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
    audio_encode_args = (
        ["-an"]
        if not include_audio
        else [
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


def _read_exact(pipe: Any, n: int) -> bytes:  # noqa: ANN401
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
    source_start_ms: int = 0,
    output_duration_ms: int | None = None,
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
    effective_duration_ms = max(
        0,
        output_duration_ms if output_duration_ms is not None else plan.duration_ms,
    )
    total_frames = max(1, int(math.ceil((effective_duration_ms / 1000.0) * plan.fps)))
    source_start_frame = max(0, int(round((max(0, source_start_ms) / 1000.0) * plan.fps)))
    try:
        for _ in range(source_start_frame):
            skipped = _read_exact(decoder.stdout, bytes_per_frame)
            if len(skipped) < bytes_per_frame:
                return
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
                int(round(((source_start_frame + frame_index) / plan.fps) * 1000)),
                output_width,
                output_height,
            )
            painter.end()

            try:
                encoder.stdin.write(_image_to_rgba_bytes(image))
            except BrokenPipeError:
                break
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

    expected_decoder_shutdown = _is_expected_decoder_pipe_shutdown(
        decoder_return, encoder_return, log_lines
    )
    if (
        expected_decoder_shutdown
        and _prune_expected_decoder_pipe_shutdown_lines(log_lines)
        and log_callback is not None
    ):
        log_callback(log_lines[-1])

    if decoder_return != 0 and not expected_decoder_shutdown:
        raise RuntimeError("Base video render failed")
    if encoder_return != 0:
        raise RuntimeError("MP4 encode failed")


def _is_expected_decoder_pipe_shutdown(
    decoder_return: int, encoder_return: int, log_lines: list[str]
) -> bool:
    if decoder_return == 0 or encoder_return != 0:
        return False
    decoder_log = "\n".join(line for line in log_lines if line.startswith("decoder:"))
    return "Broken pipe" in decoder_log and "Conversion failed!" in decoder_log


def export_project(
    project: Project,
    output_path: str | Path,
    progress_callback: Callable[[float], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
    timeline_start_ms: int = 0,
    timeline_end_ms: int | None = None,
) -> Path:
    project.export.last_log = ""
    project.export.last_error = None
    if not project.primary_video.path:
        raise ValueError("Primary video is required for export")

    _ensure_qt_gui_application()
    project.scoring.hit_factor = calculate_hit_factor(project)
    plan = build_base_render_plan(project)
    effective_start_ms = max(0, min(int(timeline_start_ms or 0), plan.duration_ms))
    requested_end_ms = plan.duration_ms if timeline_end_ms is None else int(timeline_end_ms)
    effective_end_ms = max(
        effective_start_ms,
        min(max(effective_start_ms, requested_end_ms), plan.duration_ms),
    )
    effective_duration_ms = max(0, effective_end_ms - effective_start_ms)
    if effective_duration_ms <= 0:
        raise ValueError("Export window produced no video frames.")
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
    log_lines: list[str] = [
        f"Export target: {output_target}",
        f"Container: {output_target.suffix.lower()}",
        f"Preset: {project.export.preset.value}",
        f"Video: {project.export.video_codec.value} {output_width}x{output_height} {plan.fps:.3f} fps {project.export.video_bitrate_mbps:g} Mbps",
        f"Audio: {project.export.audio_codec.value} {project.export.audio_sample_rate} Hz {project.export.audio_bitrate_kbps} kbps",
        f"Audio source: {plan.audio_source_path or project.primary_video.path} (offset {plan.audio_sync_offset_ms} ms)",
        f"Color: {project.export.color_space.value}",
        f"Two pass requested: {project.export.two_pass}",
        f"Render window: {effective_start_ms}ms → {effective_end_ms}ms ({effective_duration_ms}ms)",
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
                    audio_start_ms=effective_start_ms,
                    audio_duration_ms=effective_duration_ms,
                    audio_source_path=plan.audio_source_path,
                    audio_sync_offset_ms=plan.audio_sync_offset_ms,
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
                    audio_start_ms=effective_start_ms,
                    audio_duration_ms=effective_duration_ms,
                    audio_source_path=plan.audio_source_path,
                    audio_sync_offset_ms=plan.audio_sync_offset_ms,
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
                    source_start_ms=effective_start_ms,
                    output_duration_ms=effective_duration_ms,
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
                    source_start_ms=effective_start_ms,
                    output_duration_ms=effective_duration_ms,
                )
        else:
            encoder_command = _encoder_command(
                project,
                output_width,
                output_height,
                plan.fps,
                output_target,
                audio_start_ms=effective_start_ms,
                audio_duration_ms=effective_duration_ms,
                audio_source_path=plan.audio_source_path,
                audio_sync_offset_ms=plan.audio_sync_offset_ms,
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
                source_start_ms=effective_start_ms,
                output_duration_ms=effective_duration_ms,
            )
    except RuntimeError as exc:
        project.export.last_error = str(exc)
        project.export.last_log = "\n".join(log_lines[-400:])
        raise RuntimeError(project.export.last_log or str(exc)) from exc

    project.export.last_log = "\n".join(log_lines[-400:])

    return output_target


def export_output_profile(
    project: Project,
    output_path: Path,
    render_plan: dict,
    progress_callback: Callable[[float], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> Path:
    """Export a project using an OutputProfile render plan.
    Supports Trim Dead Time and Shot Data on Screen overlay from the profile.
    Delegates to existing export_project for base rendering.
    """
    frame_profile = render_plan.get("frame_profile", "source")
    metric_captions = render_plan.get("metric_caption_preset", {})
    lead_in_card = render_plan.get("lead_in_card", {})
    brand_mark = render_plan.get("brand_mark", {})
    run_window = render_plan.get("run_window") or {}
    render_start_ms = int(run_window.get("start_ms") or 0)
    render_end_ms = run_window.get("end_ms")

    original_export = deepcopy(project.export)
    original_overlay = deepcopy(project.overlay)
    original_metric_caption_overlay = deepcopy(project._metric_caption_overlay)
    original_lead_in_card = deepcopy(project._lead_in_card)
    original_brand_mark = deepcopy(project._brand_mark)

    try:
        if frame_profile != "source":
            ratio_map = {
                "16:9": AspectRatio.LANDSCAPE,
                "9:16": AspectRatio.PORTRAIT,
                "1:1": AspectRatio.SQUARE,
                "4:5": AspectRatio.PORTRAIT_45,
            }
            target_ratio = ratio_map.get(frame_profile)
            if target_ratio is not None:
                project.export.aspect_ratio = target_ratio

        if metric_captions:
            _apply_metric_captions_to_project(project, metric_captions)
        if lead_in_card:
            _apply_lead_in_card_to_project(project, lead_in_card)
        if brand_mark:
            _apply_brand_mark_to_project(project, brand_mark)

        if log_callback:
            log_callback(
                f"Exporting with profile: frame={frame_profile}, "
                f"trim=({render_start_ms}→{render_end_ms if render_end_ms is not None else 'source_end'}), "
                f"captions={bool(metric_captions)}, "
                f"lead_in={bool(lead_in_card)}, "
                f"brand={bool(brand_mark)}"
            )

        result = export_project(
            project,
            output_path,
            progress_callback,
            log_callback,
            timeline_start_ms=render_start_ms,
            timeline_end_ms=None if render_end_ms is None else int(render_end_ms),
        )

        if log_callback:
            log_callback(f"Export complete: {result}")
        return result
    except Exception as exc:
        if log_callback:
            log_callback(f"Export failed: {exc}")
        raise
    finally:
        last_log = project.export.last_log
        last_error = project.export.last_error
        project.export = original_export
        project.export.last_log = last_log
        project.export.last_error = last_error
        project.overlay = original_overlay
        project._metric_caption_overlay = original_metric_caption_overlay
        project._lead_in_card = original_lead_in_card
        project._brand_mark = original_brand_mark


def _apply_metric_captions_to_project(project: Project, captions: dict) -> None:
    """Apply metric caption settings to project overlay state."""
    enabled_fields = {
        str(field).strip()
        for field in captions.get("enabled_fields", [])
        if str(field).strip()
    }
    show_timer = "cumulative_time" in enabled_fields
    show_draw = "first_shot_reaction" in enabled_fields
    show_shots = "split_times" in enabled_fields
    show_score = "hit_factor" in enabled_fields or "penalties" in enabled_fields
    position = str(captions.get("position", "bottom_right") or "bottom_right").strip().lower()

    project._metric_caption_overlay = {
        "enabled_fields": sorted(enabled_fields),
        "show_split_times": show_shots,
        "show_shot_scores": show_shots and show_score,
    } if enabled_fields else None

    project.overlay.show_timer = show_timer
    project.overlay.show_draw = show_draw
    project.overlay.show_shots = show_shots
    project.overlay.show_score = show_score
    if enabled_fields and project.overlay.position == OverlayPosition.NONE:
        project.overlay.position = OverlayPosition.BOTTOM
    if position in {"bottom_left", "bottom_right"}:
        project.overlay.shot_quadrant = position
        project.overlay.timer_lock_to_stack = True
        project.overlay.draw_lock_to_stack = True
        project.overlay.score_lock_to_stack = True


def _apply_lead_in_card_to_project(project: Project, card: dict) -> None:
    """Apply lead-in card settings to project state."""
    project._lead_in_card = card


def _apply_brand_mark_to_project(project: Project, brand: dict) -> None:
    """Apply brand mark settings to project state."""
    project._brand_mark = brand

from __future__ import annotations

from dataclasses import dataclass

from splitshot.domain.models import MergeLayout, PipSize, VideoAsset


@dataclass(slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(slots=True)
class MergeCanvas:
    width: int
    height: int
    primary_rect: Rect
    secondary_rect: Rect | None


def _scale_to_height(width: int, height: int, target_height: int) -> tuple[int, int]:
    ratio = target_height / float(height)
    return int(round(width * ratio)), target_height


def _scale_to_width(width: int, height: int, target_width: int) -> tuple[int, int]:
    ratio = target_width / float(width)
    return target_width, int(round(height * ratio))


def _pip_scale(size: PipSize | int | float) -> float:
    if isinstance(size, PipSize):
        return {
            PipSize.SMALL: 0.25,
            PipSize.MEDIUM: 0.35,
            PipSize.LARGE: 0.50,
        }[size]
    return max(0.10, min(0.95, float(size) / 100.0))


def _clamp_unit(value: float | None, default: float = 1.0) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def calculate_pip_rect(
    primary: VideoAsset,
    secondary: VideoAsset,
    pip_size: PipSize | int | float,
    pip_x: float | None = 1.0,
    pip_y: float | None = 1.0,
) -> Rect:
    inset_scale = _pip_scale(pip_size)
    inset_width = max(2, int(round(primary.width * inset_scale)))
    inset_height = max(2, int(round((secondary.height / secondary.width) * inset_width)))
    margin = max(12, int(primary.width * 0.02))
    max_width = max(2, primary.width - (margin * 2))
    max_height = max(2, primary.height - (margin * 2))
    fit_scale = min(1.0, max_width / inset_width, max_height / inset_height)
    inset_width = max(2, int(round(inset_width * fit_scale)))
    inset_height = max(2, int(round(inset_height * fit_scale)))
    travel_x = max(0, primary.width - inset_width - (margin * 2))
    travel_y = max(0, primary.height - inset_height - (margin * 2))
    inset_x = margin + int(round(_clamp_unit(pip_x, 1.0) * travel_x))
    inset_y = margin + int(round(_clamp_unit(pip_y, 1.0) * travel_y))
    return Rect(inset_x, inset_y, inset_width, inset_height)


def calculate_merge_canvas(
    primary: VideoAsset,
    secondary: VideoAsset | None,
    layout: MergeLayout,
    pip_size: PipSize | int | float,
    pip_x: float | None = 1.0,
    pip_y: float | None = 1.0,
) -> MergeCanvas:
    if secondary is None:
        return MergeCanvas(
            width=primary.width,
            height=primary.height,
            primary_rect=Rect(0, 0, primary.width, primary.height),
            secondary_rect=None,
        )

    if layout == MergeLayout.SIDE_BY_SIDE:
        target_height = max(primary.height, secondary.height)
        p_width, p_height = _scale_to_height(primary.width, primary.height, target_height)
        s_width, s_height = _scale_to_height(secondary.width, secondary.height, target_height)
        return MergeCanvas(
            width=p_width + s_width,
            height=target_height,
            primary_rect=Rect(0, 0, p_width, p_height),
            secondary_rect=Rect(p_width, 0, s_width, s_height),
        )

    if layout == MergeLayout.ABOVE_BELOW:
        target_width = max(primary.width, secondary.width)
        p_width, p_height = _scale_to_width(primary.width, primary.height, target_width)
        s_width, s_height = _scale_to_width(secondary.width, secondary.height, target_width)
        return MergeCanvas(
            width=target_width,
            height=p_height + s_height,
            primary_rect=Rect(0, 0, p_width, p_height),
            secondary_rect=Rect(0, p_height, s_width, s_height),
        )

    pip_rect = calculate_pip_rect(primary, secondary, pip_size, pip_x, pip_y)
    return MergeCanvas(
        width=primary.width,
        height=primary.height,
        primary_rect=Rect(0, 0, primary.width, primary.height),
        secondary_rect=pip_rect,
    )

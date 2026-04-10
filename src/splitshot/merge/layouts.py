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


def _pip_scale(size: PipSize) -> float:
    return {
        PipSize.SMALL: 0.25,
        PipSize.MEDIUM: 0.35,
        PipSize.LARGE: 0.50,
    }[size]


def calculate_merge_canvas(
    primary: VideoAsset,
    secondary: VideoAsset | None,
    layout: MergeLayout,
    pip_size: PipSize,
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

    inset_scale = _pip_scale(pip_size)
    inset_width = int(round(primary.width * inset_scale))
    inset_height = int(round((secondary.height / secondary.width) * inset_width))
    margin = max(12, int(primary.width * 0.02))
    return MergeCanvas(
        width=primary.width,
        height=primary.height,
        primary_rect=Rect(0, 0, primary.width, primary.height),
        secondary_rect=Rect(
            primary.width - inset_width - margin,
            primary.height - inset_height - margin,
            inset_width,
            inset_height,
        ),
    )

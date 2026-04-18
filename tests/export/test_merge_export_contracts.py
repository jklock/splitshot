from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from splitshot.domain.models import MergeLayout, MergeSource, Project, VideoAsset
from splitshot.export.pipeline import _build_merge_plan, export_project
from splitshot.merge.layouts import calculate_merge_canvas, calculate_pip_rect


def _asset(path: str, width: int = 640, height: int = 360, duration_ms: int = 1000) -> VideoAsset:
    return VideoAsset(path=path, width=width, height=height, duration_ms=duration_ms, fps=30.0)


def _command_text(command: list[str]) -> str:
    return shlex.join(command)


def test_non_pip_merge_layout_math_remains_explicit_and_stable() -> None:
    primary = _asset("/tmp/primary.mp4", width=640, height=360)
    secondary = _asset("/tmp/secondary.mp4", width=320, height=240)

    side_by_side = calculate_merge_canvas(primary, secondary, MergeLayout.SIDE_BY_SIDE, 35, 0.2, 0.8)
    assert side_by_side.width == 1120
    assert side_by_side.height == 360
    assert side_by_side.primary_rect.x == 0
    assert side_by_side.primary_rect.y == 0
    assert side_by_side.primary_rect.width == 640
    assert side_by_side.primary_rect.height == 360
    assert side_by_side.secondary_rect is not None
    assert side_by_side.secondary_rect.x == 640
    assert side_by_side.secondary_rect.y == 0
    assert side_by_side.secondary_rect.width == 480
    assert side_by_side.secondary_rect.height == 360

    above_below = calculate_merge_canvas(primary, secondary, MergeLayout.ABOVE_BELOW, 35, 0.2, 0.8)
    assert above_below.width == 640
    assert above_below.height == 840
    assert above_below.primary_rect.x == 0
    assert above_below.primary_rect.y == 0
    assert above_below.primary_rect.width == 640
    assert above_below.primary_rect.height == 360
    assert above_below.secondary_rect is not None
    assert above_below.secondary_rect.x == 0
    assert above_below.secondary_rect.y == 360
    assert above_below.secondary_rect.width == 640
    assert above_below.secondary_rect.height == 480


def test_grid_merge_plan_uses_source_order_and_per_source_offsets() -> None:
    project = Project(name="Grid Merge Contract")
    project.primary_video = _asset("/tmp/primary.mp4")
    project.merge.enabled = True
    project.merge.layout = MergeLayout.SIDE_BY_SIDE
    project.merge_sources = [
        MergeSource(asset=_asset("/tmp/first.mp4"), sync_offset_ms=250),
        MergeSource(asset=_asset("/tmp/second.mp4"), sync_offset_ms=-125),
    ]

    plan = _build_merge_plan(project)
    command = _command_text(plan.command)

    assert command.index("/tmp/primary.mp4") < command.index("/tmp/first.mp4") < command.index("/tmp/second.mp4")
    assert "-ss 0.250 -i /tmp/first.mp4" in command
    assert "[2:v]setpts=PTS-STARTPTS,tpad=start_duration=0.125:color=black" in command
    assert "xstack=inputs=3" in command
    assert plan.width == 1280
    assert plan.height == 720
    assert plan.duration_ms == 1125


def test_multi_pip_merge_plan_uses_per_source_positions_and_offsets() -> None:
    project = Project(name="Multi PiP Contract")
    project.primary_video = _asset("/tmp/primary.mp4")
    project.merge.enabled = True
    project.merge.layout = MergeLayout.PIP
    first = MergeSource(
        asset=_asset("/tmp/first.mp4", width=320, height=180),
        pip_size_percent=25,
        pip_x=0.0,
        pip_y=0.0,
        sync_offset_ms=100,
    )
    second = MergeSource(
        asset=_asset("/tmp/second.mp4", width=320, height=180),
        pip_size_percent=50,
        pip_x=1.0,
        pip_y=1.0,
        sync_offset_ms=-200,
    )
    project.merge_sources = [first, second]

    plan = _build_merge_plan(project)
    command = _command_text(plan.command)
    first_rect = calculate_pip_rect(project.primary_video, first.asset, 25, 0.0, 0.0)
    second_rect = calculate_pip_rect(project.primary_video, second.asset, 50, 1.0, 1.0)

    assert command.index("/tmp/first.mp4") < command.index("/tmp/second.mp4")
    assert "-ss 0.100 -i /tmp/first.mp4" in command
    assert "[2:v]setpts=PTS-STARTPTS,tpad=start_duration=0.200:color=black" in command
    assert f"overlay=x={first_rect.x}:y={first_rect.y}" in command
    assert f"overlay=x={second_rect.x}:y={second_rect.y}" in command
    assert plan.width == 640
    assert plan.height == 360
    assert plan.duration_ms == 1200


def test_export_clears_stale_log_state_before_early_validation_error(tmp_path: Path) -> None:
    project = Project(name="Stale Export Log")
    project.export.last_log = "old ffmpeg output"
    project.export.last_error = "old failure"

    with pytest.raises(ValueError, match="Primary video is required"):
        export_project(project, tmp_path / "missing-primary.mp4")

    assert project.export.last_log == ""
    assert project.export.last_error is None

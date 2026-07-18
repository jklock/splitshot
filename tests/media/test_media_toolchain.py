from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from splitshot.media.ffmpeg import MediaError, resolve_media_binary, trim_video
from splitshot.media.probe import probe_video


def test_ffmpeg_resolver_uses_path(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / ("ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg")
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert resolve_media_binary("ffmpeg") == str(executable)


def test_ffmpeg_resolver_requires_path(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "")

    with pytest.raises(MediaError, match="Could not find ffmpeg"):
        resolve_media_binary("ffmpeg")


def test_trim_video_honors_start_and_end_boundaries(
    synthetic_video_factory, tmp_path: Path
) -> None:
    source = synthetic_video_factory(
        name="wysiwyg-trim",
        duration_ms=10_000,
        beep_ms=3_000,
        shot_times_ms=[4_000, 5_500, 7_000],
    )
    output = tmp_path / "trimmed.mp4"

    trim_video(str(source), str(output), start_s=1.0, end_s=9.0)

    asset = probe_video(output)
    assert asset.duration_ms == pytest.approx(8_000, abs=40)


def test_trim_video_rejects_reversed_boundaries(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="end_s must be greater than start_s"):
        trim_video(str(tmp_path / "source.mp4"), str(tmp_path / "trimmed.mp4"), 4.0, 4.0)

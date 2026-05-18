from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from splitshot.media.ffmpeg import MediaError, resolve_media_binary


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

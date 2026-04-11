from __future__ import annotations

import stat
import sys
from pathlib import Path

from splitshot.media.ffmpeg import resolve_media_binary


def test_ffmpeg_resolver_prefers_configured_bundle(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / ("ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg")
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("SPLITSHOT_FFMPEG_DIR", str(tmp_path))

    assert resolve_media_binary("ffmpeg") == str(executable)

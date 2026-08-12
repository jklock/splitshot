from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_COMMAND_MARKERS = (
    "playwright/driver/package/cli.js run-driver",
    "chrome-headless-shell",
)
PLAYWRIGHT_PROFILE_MARKERS = (
    str(REPO_ROOT / "tmp" / "codex" / "playwright_"),
    str(REPO_ROOT / ".tmp_tests" / "playwright_"),
)


def _kill_stray_playwright_processes() -> None:
    current_pid = os.getpid()
    result = subprocess.run(
        ["ps", "-Ao", "pid=,command="],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        if not pid_text.isdigit():
            continue
        pid = int(pid_text)
        if pid == current_pid:
            continue
        if not any(marker in command for marker in PLAYWRIGHT_COMMAND_MARKERS):
            continue
        if "chrome-headless-shell" in command and not any(
            marker in command for marker in PLAYWRIGHT_PROFILE_MARKERS
        ):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue


@pytest.fixture(autouse=True)
def _cleanup_browser_test_processes():
    yield
    _kill_stray_playwright_processes()

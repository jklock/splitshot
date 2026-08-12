#!/usr/bin/env python3
"""Run the local Electron release preflight for the current platform."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(command: list[str]) -> None:
    print(f"[preflight] {' '.join(command)}")
    subprocess.run(command, cwd=REPO, check=True)


def main() -> int:
    if sys.platform == "darwin":
        build_command = ["npm", "--prefix", "electron", "run", "build:app:mac"]
        source_smoke_command = [
            "uv",
            "run",
            "python",
            "scripts/testing/run_electron_iterate.py",
            "--tier",
            "source",
            "--scenario",
            "startup",
        ]
        packaged_smoke_command = [
            "uv",
            "run",
            "python",
            "scripts/testing/run_electron_iterate.py",
            "--tier",
            "unpacked",
            "--scenario",
            "launch",
            "--build-if-needed",
        ]
    elif sys.platform == "win32":
        build_command = ["npm", "--prefix", "electron", "run", "build:smoke:win"]
        source_smoke_command = ["npm", "--prefix", "electron", "run", "test:electron-smoke"]
        packaged_smoke_command = ["uv", "run", "python", "scripts/testing/test_electron_app.py"]
    else:
        build_command = ["npm", "--prefix", "electron", "run", "build:smoke:linux"]
        source_smoke_command = [
            "xvfb-run",
            "-a",
            "uv",
            "run",
            "python",
            "scripts/testing/run_electron_iterate.py",
            "--tier",
            "source",
            "--scenario",
            "startup",
        ]
        packaged_smoke_command = [
            "xvfb-run",
            "-a",
            "uv",
            "run",
            "python",
            "scripts/testing/test_electron_app.py",
        ]

    commands = [
        ["uv", "run", "splitshot", "--check"],
        ["node", "scripts/bundle-python.js"],
        ["node", "scripts/bundle-python.js", "check"],
        ["npm", "--prefix", "electron", "install"],
        ["npm", "--prefix", "electron", "run", "test:launch-intent"],
        ["uv", "run", "pytest", "tests/electron/test_headless_server.py", "--no-header", "-q"],
        ["uv", "run", "python", "scripts/audits/electron_parity_audit.py", "--mode", "parity"],
        source_smoke_command,
        build_command,
        packaged_smoke_command,
    ]

    for command in commands:
        run(command)
    print("[preflight] Electron release preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

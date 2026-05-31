#!/usr/bin/env python3
"""Run the local Electron release preflight for the current platform."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from packaged_support import (  # noqa: E402
    RUNTIME_MANIFEST_ARTIFACT,
    SUPPORT_EVIDENCE_ARTIFACT,
    write_release_gate_summary,
)

REPO = Path(__file__).resolve().parents[2]


def run(command: list[str]) -> float:
    print(f"[preflight] {' '.join(command)}")
    started = time.monotonic()
    subprocess.run(command, cwd=REPO, check=True)
    return round(time.monotonic() - started, 3)


def _artifact_refs() -> list[str]:
    return [
        "artifacts/backend-startup/ready-line.json",
        "artifacts/backend-startup/claim-health-trace.json",
        "artifacts/backend-jobs/job-event-trace.json",
        "artifacts/backend-practiscore/parity-matrix.json",
        "artifacts/backend-practiscore/bundle-drift-check.json",
        str(RUNTIME_MANIFEST_ARTIFACT),
        str(SUPPORT_EVIDENCE_ARTIFACT),
    ]


def main() -> int:
    if sys.platform == "darwin":
        build_command = ["npm", "--prefix", "electron", "run", "build:smoke:mac"]
        source_smoke_command = ["npm", "--prefix", "electron", "run", "test:electron-smoke"]
        packaged_smoke_command = ["uv", "run", "python", "scripts/testing/test_packaged_artifact.py"]
    elif sys.platform == "win32":
        build_command = ["npm", "--prefix", "electron", "run", "build:smoke:win"]
        source_smoke_command = ["npm", "--prefix", "electron", "run", "test:electron-smoke"]
        packaged_smoke_command = ["uv", "run", "python", "scripts/testing/test_packaged_artifact.py"]
    else:
        build_command = ["npm", "--prefix", "electron", "run", "build:smoke:linux"]
        source_smoke_command = [
            "xvfb-run",
            "-a",
            "npm",
            "--prefix",
            "electron",
            "run",
            "test:electron-smoke",
        ]
        packaged_smoke_command = [
            "xvfb-run",
            "-a",
            "uv",
            "run",
            "python",
            "scripts/testing/test_packaged_artifact.py",
        ]

    commands = [
        {"name": "runtime-check", "command": ["uv", "run", "splitshot", "--check"]},
        {"name": "bundle-build", "command": ["node", "scripts/bundle-python.js"]},
        {"name": "bundle-check", "command": ["node", "scripts/bundle-python.js", "check"]},
        {"name": "electron-install", "command": ["npm", "--prefix", "electron", "install"]},
        {
            "name": "launch-intent-tests",
            "command": ["npm", "--prefix", "electron", "run", "test:launch-intent"],
        },
        {
            "name": "headless-server-tests",
            "command": [
                "uv",
                "run",
                "pytest",
                "tests/electron/test_headless_server.py",
                "--no-header",
                "-q",
            ],
        },
        {
            "name": "electron-parity-audit",
            "command": ["uv", "run", "python", "scripts/audits/electron_parity_audit.py", "--mode", "parity"],
        },
        {"name": "source-smoke", "command": source_smoke_command},
        {"name": "packaged-build", "command": build_command},
        {"name": "packaged-smoke", "command": packaged_smoke_command},
    ]

    command_records: list[dict[str, object]] = []
    artifact_refs = _artifact_refs()
    write_release_gate_summary(
        command_records=command_records,
        status="in-progress",
        artifact_refs=artifact_refs,
    )

    for spec in commands:
        record: dict[str, object] = {
            "name": spec["name"],
            "command": spec["command"],
            "status": "running",
        }
        command_records.append(record)
        write_release_gate_summary(
            command_records=command_records,
            status="in-progress",
            artifact_refs=artifact_refs,
        )
        try:
            record["duration_seconds"] = run(spec["command"])
            record["status"] = "passed"
        except subprocess.CalledProcessError as exc:
            record["status"] = "failed"
            record["returncode"] = exc.returncode
            write_release_gate_summary(
                command_records=command_records,
                status="failed",
                artifact_refs=artifact_refs,
                failed_command=record,
            )
            raise
        write_release_gate_summary(
            command_records=command_records,
            status="in-progress",
            artifact_refs=artifact_refs,
        )

    write_release_gate_summary(
        command_records=command_records,
        status="passed",
        artifact_refs=artifact_refs,
    )
    print("[preflight] Electron release preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the v1.0.7 source-app release proof bundle and write deterministic artifacts."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = REPO / "artifacts" / "v107-release-proof" / "source"
RELEASE_PROOF_ENV = "SPLITSHOT_RELEASE_PROOF_ARTIFACT_ROOT"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"[source-release-proof] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=REPO, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()

    artifact_root = args.artifact_root.expanduser().resolve()
    workflow_root = artifact_root / "workflow"
    surface_root = artifact_root / "surface-audit"
    artifact_root.mkdir(parents=True, exist_ok=True)
    workflow_root.mkdir(parents=True, exist_ok=True)
    surface_root.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env[RELEASE_PROOF_ENV] = str(workflow_root)

    run(
        [
            "uv",
            "run",
            "pytest",
            "tests/browser/test_browser_full_app_e2e.py::test_browser_full_app_real_media_stage_release_workflow_truth_gate",
            "-q",
        ],
        env=env,
    )
    run(
        [
            "uv",
            "run",
            "python",
            "scripts/audits/browser/run_browser_ui_surface_audit.py",
            "--primary-video",
            "tests/fixtures/media/e2e-stage.mp4",
            "--artifact-root",
            str(surface_root),
            "--report-json",
            str(artifact_root / "ui-surface-audit.json"),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

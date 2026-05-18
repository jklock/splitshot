#!/usr/bin/env python3
"""Fail fast when Electron CI/package validation relies on local-only repo inputs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXTURES = [
    REPO / "tests" / "fixtures" / "media" / "stage.mp4",
    REPO / "tests" / "fixtures" / "media" / "stage-merge.mp4",
]
SCANNED_FILES = [
    REPO / "scripts" / "testing" / "test_packaged_app_e2e.py",
    REPO / "scripts" / "testing" / "e2e-playwright.cjs",
    REPO / "scripts" / "audits" / "browser" / "run_browser_av_audit.py",
    REPO / "scripts" / "audits" / "browser" / "run_browser_interaction_audit.py",
    REPO / "scripts" / "audits" / "browser" / "run_browser_ui_surface_audit.py",
    REPO / "scripts" / "audits" / "browser" / "run_browser_export_matrix.py",
]
FORBIDDEN_SNIPPETS = [
    "tests/artifacts/test_video",
    "example_data/stage.mp4",
    "WARN: video failed",
    'video_path.write_text("")',
]


def _is_tracked(path: Path) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def main() -> int:
    errors: list[str] = []

    for fixture in FIXTURES:
        if not fixture.is_file():
            errors.append(f"Missing required tracked fixture: {fixture}")
        elif not _is_tracked(fixture):
            errors.append(f"Fixture is present but not tracked by git: {fixture}")

    for path in SCANNED_FILES:
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                errors.append(f"Forbidden local-only fixture reference in {path}: {snippet}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: Electron CI inputs are tracked and local-only fixture paths are not referenced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

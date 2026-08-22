#!/usr/bin/env python3
"""Reject generated, machine-local, or unexpectedly large files tracked by Git."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MAX_BLOB_BYTES = 5 * 1024 * 1024
GENERATED_DIRS = {
    ".archive",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "htmlcov",
    "logs",
    "node_modules",
}
PRIVATE_PATH_PREFIXES = (
    ".codex/",
    ".github/instructions/",
    ".vscode/",
    "tests/docs/",
)
PRIVATE_PATHS = {
    ".github/copilot-instructions.md",
    "AGENTS.md",
}
MEDIA_SUFFIXES = {
    ".avi",
    ".gif",
    ".icns",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".png",
    ".wav",
    ".webm",
}
APPROVED_MEDIA_PREFIXES = (
    "docs/screenshots/",
    "electron/assets/",
)
APPROVED_MEDIA_FILES = {
    "src/splitshot/browser/static/githublogo.png",
    "src/splitshot/browser/static/logo.png",
    "tests/fixtures/media/e2e-stage.mp4",
    "tests/fixtures/media/stage-merge.mp4",
    "tests/fixtures/media/stage.mp4",
}
MACHINE_PATH_ALLOWLIST = {
    # These assertions deliberately exercise platform-specific input normalization.
    "tests/browser/test_browser_control.py",
    "tests/scripts/test_check_tracked_tree_hygiene.py",
    "tests/scripts/test_run_installed_app_pane_audit.py",
}
TEXT_SUFFIXES = {
    ".cjs",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def _machine_path_pattern() -> re.Pattern[str]:
    unix_roots = "/" + "(?:Users|Volumes|home)" + "/"
    windows_root = "[A-Za-z]:" + re.escape("\\Users\\")
    return re.compile(f"(?:{unix_roots}|{windows_root})[^\\s\\\"']+", re.IGNORECASE)


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed")
    return result.stdout


def tracked_paths(repo: Path) -> list[str]:
    output = _git(repo, "ls-files", "-z")
    paths = (item.decode("utf-8") for item in output.split(b"\0") if item)
    return sorted(path for path in paths if (repo / path).is_file())


def tracked_blob(repo: Path, path: str) -> bytes:
    return (repo / path).read_bytes()


def audit(repo: Path) -> list[str]:
    violations: list[str] = []
    machine_path = _machine_path_pattern()

    for path in tracked_paths(repo):
        pure_path = PurePosixPath(path)
        lower_path = path.lower()
        lower_name = pure_path.name.lower()

        if path in PRIVATE_PATHS or path.startswith(PRIVATE_PATH_PREFIXES):
            violations.append(f"private development material: {path}")
        if any(part in GENERATED_DIRS for part in pure_path.parts):
            violations.append(f"generated directory: {path}")
        if any(
            part.startswith("browser-audit") and part.endswith(".ssproj")
            for part in pure_path.parts
        ):
            violations.append(f"generated browser project: {path}")
        if lower_path == "output.txt" or lower_name.endswith(".log"):
            violations.append(f"generated output/log: {path}")

        suffix = pure_path.suffix.lower()
        approved_media = path in APPROVED_MEDIA_FILES or path.startswith(APPROVED_MEDIA_PREFIXES)
        if suffix in MEDIA_SUFFIXES and not approved_media:
            violations.append(f"unexpected media: {path}")

        blob = tracked_blob(repo, path)
        if len(blob) > MAX_BLOB_BYTES:
            violations.append(f"unapproved blob over 5 MiB ({len(blob)} bytes): {path}")

        if suffix in TEXT_SUFFIXES and path not in MACHINE_PATH_ALLOWLIST:
            text = blob.decode("utf-8", errors="replace")
            match = machine_path.search(text)
            if match:
                violations.append(f"machine-specific absolute path: {path}")

    return sorted(set(violations))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)

    try:
        violations = audit(args.repo.resolve())
    except RuntimeError as exc:
        print(f"tracked-tree hygiene check failed: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("Tracked-tree hygiene violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Tracked-tree hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "testing" / "check_tracked_tree_hygiene.py"
SPEC = importlib.util.spec_from_file_location("check_tracked_tree_hygiene", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
HYGIENE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HYGIENE)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def tracked_repo(tmp_path: Path, files: dict[str, bytes]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    git(repo, "add", ".")
    return repo


def test_audit_accepts_approved_assets_and_portable_text(tmp_path: Path) -> None:
    repo = tracked_repo(
        tmp_path,
        {
            "README.md": b"Use /path/to/project on Unix.\n",
            "docs/screenshots/ProjectPane.png": b"png",
            "electron/assets/icon.icns": b"icon",
            "tests/fixtures/media/e2e-stage.mp4": b"video",
        },
    )

    assert HYGIENE.audit(repo) == []


def test_audit_reports_each_disallowed_tracked_file_class(tmp_path: Path) -> None:
    repo = tracked_repo(
        tmp_path,
        {
            ".archive/notes.md": b"internal",
            "browser-audit-deadbeef.ssproj/project.json": b"{}",
            "output.txt": b"generated",
            "run.log": b"log",
            "docs/demo.mp4": b"video",
            "notes.md": b"local: /Users/alice/splitshot/project.ssproj\n",
            "large.bin": b"x" * (HYGIENE.MAX_BLOB_BYTES + 1),
        },
    )

    violations = HYGIENE.audit(repo)

    assert any("generated directory: .archive/notes.md" in item for item in violations)
    assert any("generated browser project:" in item for item in violations)
    assert any("generated output/log: output.txt" in item for item in violations)
    assert any("generated output/log: run.log" in item for item in violations)
    assert any("unexpected media: docs/demo.mp4" in item for item in violations)
    assert any("machine-specific absolute path: notes.md" in item for item in violations)
    assert any("unapproved blob over 5 MiB" in item for item in violations)


def test_audit_allows_machine_paths_only_in_explicit_test_fixtures(tmp_path: Path) -> None:
    repo = tracked_repo(
        tmp_path,
        {
            "tests/browser/test_browser_control.py": b"value = '/Users/test/project'\n",
            "docs/example.md": b"value = '/home/alice/project'\n",
        },
    )

    assert HYGIENE.audit(repo) == ["machine-specific absolute path: docs/example.md"]

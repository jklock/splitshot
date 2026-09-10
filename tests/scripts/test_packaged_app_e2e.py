from __future__ import annotations

import importlib.util
import signal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "test_packaged_app_e2e.py"
SPEC = importlib.util.spec_from_file_location("test_packaged_app_e2e_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ocr_text_is_readable_accepts_expected_overlay_words() -> None:
    assert MODULE._ocr_text_is_readable("Shot 1 Draw 3.02s")
    assert MODULE._ocr_text_is_readable("Hit Factor 3.78")
    assert MODULE._ocr_text_is_readable("Packaged custom review box")
    assert MODULE._ocr_text_is_readable(
        "Final 72.51 Points Down 8 Penalties 0 Division PCC Class MA Overall 1/27"
    )


def test_ocr_text_is_readable_rejects_tofu_like_output() -> None:
    assert not MODULE._ocr_text_is_readable("")
    assert not MODULE._ocr_text_is_readable("□□□□□□□□")
    assert not MODULE._ocr_text_is_readable("0000000000")


def test_playwright_export_file_matches_browser_proof_location() -> None:
    artifacts_dir = ROOT / "artifacts"
    assert (
        MODULE._playwright_export_file(artifacts_dir)
        == artifacts_dir / "exports" / "e2e-export-test.mp4"
    )


def test_default_packaged_artifact_root_uses_phase_12_tree(monkeypatch) -> None:
    monkeypatch.setattr(MODULE.sys, "platform", "darwin")
    assert (
        MODULE._default_packaged_artifact_root()
        == ROOT / "artifacts" / "v107-release-proof" / "packaged-local-mac"
    )


def test_resolve_tool_uses_windows_fallback_when_path_lookup_misses(
    monkeypatch, tmp_path: Path
) -> None:
    fallback_dir = tmp_path / "Program Files" / "Tesseract-OCR"
    fallback_dir.mkdir(parents=True)
    executable = fallback_dir / "tesseract.exe"
    executable.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(MODULE.sys, "platform", "win32")
    monkeypatch.setattr(MODULE.shutil, "which", lambda command: None)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "Program Files"))
    resolved = MODULE._resolve_tool(
        "tesseract",
        windows_fallbacks=(r"%ProgramFiles%\\Tesseract-OCR\\tesseract.exe",),
    )
    assert Path(resolved) == executable


def test_resolve_tool_raises_for_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr(MODULE.shutil, "which", lambda command: None)
    monkeypatch.setattr(MODULE.sys, "platform", "darwin")
    with pytest.raises(FileNotFoundError, match="Required executable not found"):
        MODULE._resolve_tool("missing-binary")


def test_stop_process_terminates_posix_process_group(monkeypatch) -> None:
    signals: list[tuple[int, int]] = []

    class Process:
        pid = 42

        @staticmethod
        def poll():
            return None

        @staticmethod
        def wait(timeout):
            assert timeout == 10

    monkeypatch.setattr(MODULE.os, "name", "posix")
    monkeypatch.setattr(MODULE.os, "killpg", lambda pid, value: signals.append((pid, value)))

    MODULE._stop_process(Process())

    assert signals == [(42, signal.SIGTERM)]


def test_stop_process_terminates_windows_process_tree(monkeypatch) -> None:
    commands: list[list[str]] = []

    class Process:
        pid = 84

        @staticmethod
        def poll():
            return None

        @staticmethod
        def wait(timeout):
            assert timeout == 10

    monkeypatch.setattr(MODULE.os, "name", "nt")
    monkeypatch.setattr(
        MODULE.subprocess,
        "run",
        lambda command, **kwargs: commands.append(command),
    )

    MODULE._stop_process(Process())

    assert commands == [["taskkill", "/PID", "84", "/T", "/F"]]

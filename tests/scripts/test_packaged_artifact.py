from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "test_packaged_artifact.py"
SPEC = importlib.util.spec_from_file_location("test_packaged_artifact_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_install_windows_artifact_rejects_empty_locator_output(monkeypatch, tmp_path: Path) -> None:
    artifact = tmp_path / "SplitShot Installer.exe"
    artifact.write_text("stub", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command: list[str], *, env=None, cwd=None):  # noqa: ANN001
        calls.append(command)

        class Result:
            stdout = ""

        return Result()

    monkeypatch.setattr(MODULE, "_run", fake_run)
    monkeypatch.setattr(MODULE.sys, "platform", "win32")

    with pytest.raises(
        FileNotFoundError, match="Installed SplitShot.exe not found after NSIS install"
    ):
        MODULE._install_windows_artifact(artifact)

    assert len(calls) == 2

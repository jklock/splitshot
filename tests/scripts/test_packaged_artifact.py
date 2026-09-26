from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

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

    def fake_run(command: list[str], *, env=None, cwd=None):
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


def test_packaged_electron_main_disables_runtime_bytecode_writes() -> None:
    main_js = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")
    assert "env.PYTHONDONTWRITEBYTECODE = '1';" in main_js


def test_validate_bundle_symlinks_accepts_internal_target(tmp_path: Path) -> None:
    app = tmp_path / "SplitShot.app"
    target = app / "Contents" / "Resources" / "runtime"
    target.parent.mkdir(parents=True)
    target.write_text("runtime", encoding="utf-8")
    (target.parent / "runtime-link").symlink_to(target.name)

    MODULE._validate_bundle_symlinks(app)


def test_validate_bundle_symlinks_rejects_external_target(tmp_path: Path) -> None:
    app = tmp_path / "SplitShot.app"
    links = app / "Contents" / "Resources"
    links.mkdir(parents=True)
    external = tmp_path / "host-python"
    external.write_text("python", encoding="utf-8")
    link = links / "python"
    link.symlink_to(external)

    with pytest.raises(ValueError, match="Symbolic link escapes app bundle"):
        MODULE._validate_bundle_symlinks(app)


def test_validate_bundle_symlinks_rejects_broken_target(tmp_path: Path) -> None:
    app = tmp_path / "SplitShot.app"
    links = app / "Contents" / "Resources"
    links.mkdir(parents=True)
    link = links / "python"
    link.symlink_to("missing-python")

    with pytest.raises(ValueError, match="Invalid symbolic link in app bundle"):
        MODULE._validate_bundle_symlinks(app)


def _macos_app_with_python(tmp_path: Path) -> tuple[Path, Path]:
    app = tmp_path / "SplitShot.app"
    python_bin = app / "Contents" / "Resources" / "bundle" / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("python", encoding="utf-8")
    return app, python_bin


def test_validate_macos_python_runtime_accepts_bundled_library(
    monkeypatch, tmp_path: Path
) -> None:
    app, python_bin = _macos_app_with_python(tmp_path)
    library = python_bin.parent.parent / "lib" / "libpython3.12.dylib"
    library.parent.mkdir(parents=True)
    library.write_text("library", encoding="utf-8")
    output = (
        f"{python_bin}:\n"
        "\t@executable_path/../lib/libpython3.12.dylib "
        "(compatibility version 3.12.0, current version 3.12.0)\n"
        "\t/usr/lib/libSystem.B.dylib "
        "(compatibility version 1.0.0, current version 1311.0.0)\n"
    )
    monkeypatch.setattr(MODULE, "_run", lambda command: SimpleNamespace(stdout=output))

    MODULE._validate_macos_python_runtime(app)


def test_validate_macos_python_runtime_rejects_host_framework(
    monkeypatch, tmp_path: Path
) -> None:
    app, python_bin = _macos_app_with_python(tmp_path)
    output = (
        f"{python_bin}:\n"
        "\t/Library/Frameworks/Python.framework/Versions/3.12/Python "
        "(compatibility version 3.12.0, current version 3.12.0)\n"
    )
    monkeypatch.setattr(MODULE, "_run", lambda command: SimpleNamespace(stdout=output))

    with pytest.raises(ValueError, match="depends on a host library"):
        MODULE._validate_macos_python_runtime(app)


def test_bundle_uses_uv_managed_python_for_macos_runtime() -> None:
    bundle_script = (ROOT / "scripts" / "bundle-python.js").read_text(encoding="utf-8")
    assert "['python', 'install', '--managed-python', '--no-bin', pythonVersion]" in bundle_script
    assert "['python', 'find', '--managed-python', '--resolve-links', pythonVersion]" in bundle_script
    assert "bundlePosixStdlib(pythonVersion, pythonExe)" in bundle_script
    assert "process.env.SPLITSHOT_SKIP_HOST_LINKAGE_AUDIT === '1'" in bundle_script

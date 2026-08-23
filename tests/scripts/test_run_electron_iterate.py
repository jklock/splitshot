from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "run_electron_iterate.py"
SPEC = importlib.util.spec_from_file_location("run_electron_iterate_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_environment_isolates_temp_and_application_settings() -> None:
    env = MODULE._env()

    assert env["TMPDIR"] == str(MODULE.TMP_ROOT)
    assert env["TMP"] == str(MODULE.TMP_ROOT)
    assert env["TEMP"] == str(MODULE.TMP_ROOT)
    assert env["SPLITSHOT_SETTINGS_PATH"] == str(
        MODULE.TMP_ROOT / "electron-iterate-settings.json"
    )


def test_default_scenarios_follow_tier() -> None:
    assert MODULE._default_scenarios("source") == ["startup"]
    assert MODULE._default_scenarios("unpacked") == ["launch"]
    assert MODULE._default_scenarios("installed") == ["full"]


def test_resolve_scenarios_accepts_full_source_inventory() -> None:
    scenarios = [
        "startup",
        "project",
        "media",
        "compose",
        "trim",
        "score",
        "splits",
        "markers",
        "overlay",
        "review",
        "export",
        "queue",
        "metrics",
        "shotml",
        "settings",
    ]
    assert MODULE._resolve_scenarios("source", scenarios) == scenarios


def test_resolve_scenarios_rejects_invalid_packaged_choice() -> None:
    with pytest.raises(SystemExit, match="Unsupported unpacked scenario"):
        MODULE._resolve_scenarios("unpacked", ["compose"])


def test_workflow_proof_requires_explicit_project_when_local_fixture_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(MODULE, "DEFAULT_WORKFLOW_PROJECT", ROOT / "missing-workflow-project")
    with pytest.raises(SystemExit, match="requires --project-path"):
        MODULE._resolve_project_path(None, "source", ["settings"])


def test_should_rebuild_unpacked_app_when_missing(tmp_path: Path) -> None:
    assert MODULE._should_rebuild_unpacked_app(tmp_path / "SplitShot.app") is True


def test_run_packaged_uses_slice_and_reads_audit(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    audit_path = artifact_root / "audit.json"
    audit_path.write_text(
        json.dumps({"artifact_root": str(artifact_root), "slice": "launch"}), encoding="utf-8"
    )
    commands: list[list[str]] = []

    monkeypatch.setattr(MODULE, "_run", lambda command, env: commands.append(command))

    result = MODULE._run_packaged_slice(
        tmp_path / "SplitShot.app",
        "launch",
        artifact_root,
        tmp_path / "05072026",
        {},
    )

    assert result["slice"] == "launch"
    assert commands == [
        [
            "uv",
            "run",
            "python",
            "scripts/audits/browser/run_installed_app_pane_audit.py",
            "--app",
            str(tmp_path / "SplitShot.app"),
            "--project-path",
            str(tmp_path / "05072026"),
            "--artifact-root",
            str(artifact_root),
            "--slice",
            "launch",
        ]
    ]


def test_run_source_scenarios_passes_all_requested_scenarios(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    result_path = artifact_root / "source-electron-iterate.json"
    result_path.write_text(json.dumps({"tier": "source"}), encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(MODULE, "_run", lambda command, env: commands.append(command))

    result = MODULE._run_source_scenarios(
        ["startup", "trim"],
        artifact_root,
        tmp_path / "05072026",
        {},
    )

    assert result["tier"] == "source"
    assert commands == [
        [
            "node",
            str(ROOT / "electron" / "tests" / "iterate.test.js"),
            "--artifacts",
            str(artifact_root),
            "--project-path",
            str(tmp_path / "05072026"),
            "--scenario",
            "startup",
            "--scenario",
            "trim",
        ]
    ]


def test_run_packaged_full_aggregates_subslices(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path]] = []
    original = MODULE._run_packaged_slice

    def fake_run_packaged_slice(app_path, slice_name, artifact_root, project_path, env):
        if slice_name == "full":
            return original(app_path, slice_name, artifact_root, project_path, env)
        calls.append((slice_name, artifact_root))
        artifact_root.mkdir(parents=True, exist_ok=True)
        return {"slice": slice_name, "findings": []}

    monkeypatch.setattr(MODULE, "_run_packaged_slice", fake_run_packaged_slice)

    result = original(
        tmp_path / "SplitShot.app",
        "full",
        tmp_path / "artifacts",
        tmp_path / "05072026",
        {},
    )

    assert [slice_name for slice_name, _root in calls] == [
        "launch",
        "panes",
        "trim",
        "queue-individual",
        "queue-combined",
    ]
    assert result["slice"] == "full"
    assert result["findings"] == []
    assert (tmp_path / "artifacts" / "audit.json").exists()

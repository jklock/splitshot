from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "packaged_support.py"
SPEC = importlib.util.spec_from_file_location("packaged_support_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _minimal_runtime_manifest() -> dict:
    return {
        "manifest_schema_version": 1,
        "generated_at": "2026-05-30T00:00:00Z",
        "application": {"name": "splitshot", "version": "1.1.0"},
        "bundle": {
            "platform": "darwin",
            "arch": "arm64",
            "python_executable": ".venv/bin/python",
            "site_packages": ".venv/lib/python3.12/site-packages",
            "source_root": "src",
            "ffmpeg_root": "src/splitshot/resources/ffmpeg/macos",
        },
        "source_inputs": {},
        "tool_versions": {
            "node": {"version": "v22.0.0"},
            "electron": {},
            "electron-builder": {},
            "playwright": {},
            "python": {
                "version": "3.12.3",
                "implementation": "cpython",
                "distribution_count": 0,
                "distribution_fingerprint": "abc123",
            },
            "ffmpeg": {},
            "ffprobe": {},
        },
        "python_distributions": [],
        "bundle_inventory": {
            "critical_paths": [],
            "source_tree": {"path": "src", "file_count": 0, "total_bytes": 0, "sha256": "def456"},
        },
    }


def test_guess_bundle_root_resolves_macos_layout(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / "SplitShot.app" / "Contents" / "Resources" / "bundle"
    executable = tmp_path / "SplitShot.app" / "Contents" / "MacOS" / "SplitShot"
    bundle_root.mkdir(parents=True)
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(MODULE.sys, "platform", "darwin")
    assert MODULE.guess_bundle_root(executable) == bundle_root


def test_export_runtime_manifest_writes_installed_artifact_record(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    manifest_payload = _minimal_runtime_manifest()
    (bundle_root / "runtime-manifest.json").write_text(
        json.dumps(manifest_payload), encoding="utf-8"
    )
    artifact = tmp_path / "SplitShot.dmg"
    artifact.write_bytes(b"artifact-binary")
    executable = tmp_path / "SplitShot"
    executable.write_text("stub", encoding="utf-8")
    destination = tmp_path / "runtime-manifest-artifact.json"

    record = MODULE.export_runtime_manifest(
        bundle_root=bundle_root,
        installed_executable=executable,
        artifact_path=artifact,
        artifact_kind="dmg",
        destination=destination,
    )

    written = json.loads(destination.read_text(encoding="utf-8"))
    assert written == record
    assert record["artifact_kind"] == "dmg"
    assert record["artifact_sha256"] == hashlib.sha256(b"artifact-binary").hexdigest()
    assert record["manifest"] == manifest_payload
    assert record["bundle_root"] == str(bundle_root.resolve())


def test_update_support_evidence_merges_sections_and_builds_collection_policy(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "support-evidence-summary.json"
    MODULE.update_support_evidence(
        "installation",
        {
            "artifact_path": "/tmp/SplitShot.dmg",
            "bundle_root": "/tmp/installed/bundle",
            "runtime_manifest_artifact": "/tmp/runtime-manifest.json",
            "bundle_manifest_path": "/tmp/installed/bundle/runtime-manifest.json",
        },
        destination=destination,
    )
    payload = MODULE.update_support_evidence(
        "packaged_smoke",
        {
            "ready_file": "/tmp/ready-events.jsonl",
            "stdout_log": "/tmp/stdout.log",
            "stderr_log": "/tmp/stderr.log",
            "backend_log_root": "/tmp/support/logs",
        },
        destination=destination,
    )

    policy = payload["collection_policy"]
    assert {entry["label"] for entry in policy["file_artifacts"]} >= {
        "artifact_file",
        "runtime_manifest_artifact",
        "bundle_manifest",
        "packaged_smoke_ready_events",
        "packaged_smoke_stdout",
        "packaged_smoke_stderr",
    }
    assert policy["collection_roots"]["installed_bundle_root"] == "/tmp/installed/bundle"
    assert policy["collection_roots"]["backend_log_root"] == "/tmp/support/logs"


def test_write_release_gate_summary_uses_current_risk_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    risk_register = tmp_path / "risk-register.json"
    risk_register.write_text(
        json.dumps(
            {
                "program_state": {"current_gate": "Gate 6"},
                "risks": [
                    {
                        "risk_id": "R-000",
                        "disposition": "retired",
                        "status": "retired",
                        "residual_level": "none",
                        "decision": "proceed",
                        "blocking_gate": "Gate 0",
                    },
                    {
                        "risk_id": "R-006",
                        "disposition": "carried-forward",
                        "status": "open",
                        "residual_level": "medium",
                        "decision": "hold",
                        "blocking_gate": "Gate 7",
                        "evidence_artifacts": ["artifacts/backend-certification/release-gate-summary.json"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(MODULE, "RISK_REGISTER_ARTIFACT", risk_register)
    destination = tmp_path / "release-gate-summary.json"

    summary = MODULE.write_release_gate_summary(
        command_records=[{"name": "packaged-smoke", "status": "failed"}],
        status="failed",
        artifact_refs=["artifacts/backend-practiscore/parity-matrix.json"],
        destination=destination,
    )

    assert summary["program_state"] == {"current_gate": "Gate 6"}
    assert summary["residual_risks"] == [
        {
            "risk_id": "R-006",
            "status": "open",
            "residual_level": "medium",
            "decision": "hold",
            "disposition": "carried-forward",
            "blocking_gate": "Gate 7",
            "evidence_artifacts": ["artifacts/backend-certification/release-gate-summary.json"],
        }
    ]
    assert destination.is_file()
    assert summary["commands"][0]["name"] == "packaged-smoke"

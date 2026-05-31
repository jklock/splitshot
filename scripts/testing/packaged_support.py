#!/usr/bin/env python3
"""Shared packaged-runtime manifest and support-evidence helpers."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BACKEND_CERT_DIR = REPO / "artifacts" / "backend-certification"
RUNTIME_MANIFEST_ARTIFACT = BACKEND_CERT_DIR / "runtime-manifest.json"
SUPPORT_EVIDENCE_ARTIFACT = BACKEND_CERT_DIR / "support-evidence-summary.json"
RELEASE_GATE_ARTIFACT = BACKEND_CERT_DIR / "release-gate-summary.json"
RISK_REGISTER_ARTIFACT = REPO / "artifacts" / "backend-risk" / "risk-register.json"


def _utcnow_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def guess_bundle_root(executable: Path) -> Path | None:
    resolved = executable.resolve()
    if (
        sys.platform == "darwin"
        and resolved.parent.name == "MacOS"
        and resolved.parent.parent.name == "Contents"
    ):
        candidate = resolved.parent.parent / "Resources" / "bundle"
        if candidate.is_dir():
            return candidate
    candidate = resolved.parent / "resources" / "bundle"
    if candidate.is_dir():
        return candidate
    return None


def validate_runtime_manifest(payload: dict[str, Any]) -> None:
    required_top_level = {
        "application",
        "bundle",
        "bundle_inventory",
        "generated_at",
        "manifest_schema_version",
        "python_distributions",
        "source_inputs",
        "tool_versions",
    }
    missing = sorted(required_top_level.difference(payload))
    if missing:
        raise ValueError(f"Runtime manifest missing required keys: {', '.join(missing)}")
    if payload.get("manifest_schema_version") != 1:
        raise ValueError(
            f"Unsupported runtime manifest schema version: {payload.get('manifest_schema_version')}"
        )
    bundle = payload.get("bundle")
    if not isinstance(bundle, dict) or not str(bundle.get("python_executable", "")).strip():
        raise ValueError("Runtime manifest bundle metadata is incomplete.")
    tool_versions = payload.get("tool_versions")
    if not isinstance(tool_versions, dict):
        raise ValueError("Runtime manifest tool_versions must be an object.")
    python_info = tool_versions.get("python")
    if not isinstance(python_info, dict):
        raise ValueError("Runtime manifest python tool metadata is incomplete.")
    if not str(python_info.get("distribution_fingerprint", "")).strip():
        raise ValueError("Runtime manifest python distribution fingerprint is missing.")
    distributions = payload.get("python_distributions")
    if not isinstance(distributions, list):
        raise ValueError("Runtime manifest python_distributions must be a list.")


def export_runtime_manifest(
    *,
    bundle_root: Path,
    installed_executable: Path,
    artifact_path: Path | None = None,
    artifact_kind: str | None = None,
    destination: Path = RUNTIME_MANIFEST_ARTIFACT,
) -> dict[str, Any]:
    manifest_path = bundle_root / "runtime-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Bundled runtime manifest not found at {manifest_path}")
    manifest = _load_json(manifest_path)
    validate_runtime_manifest(manifest)
    record = {
        "schema_version": 1,
        "generated_at": _utcnow_iso(),
        "artifact_kind": artifact_kind or "unknown",
        "artifact_path": str(artifact_path.resolve()) if artifact_path else None,
        "artifact_sha256": sha256_file(artifact_path)
        if artifact_path and artifact_path.is_file()
        else None,
        "installed_executable": str(installed_executable.resolve()),
        "bundle_root": str(bundle_root.resolve()),
        "bundle_manifest_path": str(manifest_path.resolve()),
        "bundle_manifest_sha256": sha256_file(manifest_path),
        "manifest": manifest,
    }
    write_json(destination, record)
    return record


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _add_file_ref(
    refs: list[dict[str, str]],
    seen: set[tuple[str, str]],
    label: str,
    raw_path: Any,
) -> None:
    path_text = str(raw_path or "").strip()
    if not path_text:
        return
    key = (label, path_text)
    if key in seen:
        return
    refs.append({"label": label, "path": path_text})
    seen.add(key)


def _add_dir_ref(
    refs: dict[str, str],
    label: str,
    raw_path: Any,
) -> None:
    path_text = str(raw_path or "").strip()
    if path_text:
        refs[label] = path_text


def build_support_collection_policy(summary: dict[str, Any]) -> dict[str, Any]:
    file_artifacts: list[dict[str, str]] = []
    seen_files: set[tuple[str, str]] = set()
    collection_roots: dict[str, str] = {}
    collection_order: list[str] = []

    installation = summary.get("installation") if isinstance(summary.get("installation"), dict) else {}
    packaged_smoke = summary.get("packaged_smoke") if isinstance(summary.get("packaged_smoke"), dict) else {}
    packaged_e2e = summary.get("packaged_e2e") if isinstance(summary.get("packaged_e2e"), dict) else {}

    for label, raw_path in (
        ("artifact_file", installation.get("artifact_path")),
        ("runtime_manifest_artifact", installation.get("runtime_manifest_artifact")),
        ("bundle_manifest", installation.get("bundle_manifest_path")),
        ("packaged_smoke_ready_events", packaged_smoke.get("ready_file")),
        ("packaged_smoke_stdout", packaged_smoke.get("stdout_log")),
        ("packaged_smoke_stderr", packaged_smoke.get("stderr_log")),
        ("packaged_e2e_ready_events", packaged_e2e.get("ready_file")),
        ("packaged_e2e_stdout", packaged_e2e.get("stdout_log")),
        ("packaged_e2e_stderr", packaged_e2e.get("stderr_log")),
        ("packaged_e2e_summary", packaged_e2e.get("playwright_summary")),
        ("packaged_e2e_export", packaged_e2e.get("export_file")),
        ("packaged_e2e_ocr_image", packaged_e2e.get("proof_image")),
        ("packaged_e2e_ocr_text", packaged_e2e.get("proof_text")),
    ):
        before = len(file_artifacts)
        _add_file_ref(file_artifacts, seen_files, label, raw_path)
        if len(file_artifacts) != before:
            collection_order.append(label)

    for label, raw_path in (
        ("installed_bundle_root", installation.get("bundle_root")),
        ("backend_log_root", packaged_smoke.get("backend_log_root")),
        ("backend_cache_root", packaged_smoke.get("backend_cache_root")),
        ("backend_app_data_root", packaged_smoke.get("backend_app_data_root")),
        ("electron_log_root", packaged_smoke.get("electron_log_root")),
        ("electron_user_data_root", packaged_smoke.get("electron_user_data_root")),
        ("electron_crash_dumps_root", packaged_smoke.get("electron_crash_dumps_root")),
        ("playwright_log_dir", packaged_e2e.get("playwright_log_dir")),
    ):
        _add_dir_ref(collection_roots, label, raw_path)

    return {
        "file_artifacts": file_artifacts,
        "collection_roots": collection_roots,
        "collection_order": collection_order,
    }


def update_support_evidence(
    section: str,
    payload: dict[str, Any],
    *,
    destination: Path = SUPPORT_EVIDENCE_ARTIFACT,
) -> dict[str, Any]:
    current: dict[str, Any]
    if destination.exists():
        current = _load_json(destination)
    else:
        current = {
            "schema_version": 1,
            "generated_at": _utcnow_iso(),
            "platform": _platform_label(),
        }
    existing_section = current.get(section)
    if isinstance(existing_section, dict):
        current[section] = _deep_merge(existing_section, payload)
    else:
        current[section] = payload
    current["generated_at"] = _utcnow_iso()
    current["platform"] = _platform_label()
    current["collection_policy"] = build_support_collection_policy(current)
    write_json(destination, current)
    return current


def _platform_label() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def _deferred_platforms() -> list[str]:
    current = _platform_label()
    return [item for item in ["macos", "windows", "linux"] if item != current]


def _residual_risks() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not RISK_REGISTER_ARTIFACT.is_file():
        return ({}, [])
    payload = _load_json(RISK_REGISTER_ARTIFACT)
    residual = []
    for risk in payload.get("risks", []):
        if risk.get("disposition") == "retired":
            continue
        residual.append(
            {
                "risk_id": risk.get("risk_id"),
                "status": risk.get("status"),
                "residual_level": risk.get("residual_level"),
                "decision": risk.get("decision"),
                "disposition": risk.get("disposition"),
                "blocking_gate": risk.get("blocking_gate"),
                "evidence_artifacts": risk.get("evidence_artifacts") or risk.get("required_artifacts"),
            }
        )
    return (payload.get("program_state") or {}, residual)


def write_release_gate_summary(
    *,
    command_records: list[dict[str, Any]],
    status: str,
    artifact_refs: list[str] | None = None,
    failed_command: dict[str, Any] | None = None,
    destination: Path = RELEASE_GATE_ARTIFACT,
) -> dict[str, Any]:
    program_state, residual_risks = _residual_risks()
    refs = [
        str(RISK_REGISTER_ARTIFACT),
        str(RUNTIME_MANIFEST_ARTIFACT),
        str(SUPPORT_EVIDENCE_ARTIFACT),
        *(artifact_refs or []),
    ]
    unique_refs: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        ref_text = str(ref or "").strip()
        if not ref_text or ref_text in seen:
            continue
        unique_refs.append(ref_text)
        seen.add(ref_text)
    payload = {
        "schema_version": 1,
        "generated_at": _utcnow_iso(),
        "status": status,
        "platform": _platform_label(),
        "platform_coverage": {
            "validated_now": [_platform_label()],
            "deferred": _deferred_platforms(),
        },
        "program_state": program_state,
        "artifact_refs": unique_refs,
        "commands": command_records,
        "failed_command": failed_command,
        "risk_register": str(RISK_REGISTER_ARTIFACT),
        "residual_risks": residual_risks,
    }
    write_json(destination, payload)
    return payload

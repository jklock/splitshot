#!/usr/bin/env python3
"""Build a fail-closed per-OS packaged release summary from explicit evidence records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from validate_packaged_release_evidence import (
        DEFAULT_MANIFEST,
        _manifest_cases,
        validate_manifest,
        validate_platform_summary,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_packaged_release_evidence import (  # type: ignore[no-redef]
        DEFAULT_MANIFEST,
        _manifest_cases,
        validate_manifest,
        validate_platform_summary,
    )

ROOT = Path(__file__).resolve().parents[2]
PLATFORM_BY_SYS = {"darwin": "macos", "win32": "windows", "linux": "linux"}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload


def _relative(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _case_records(
    artifact_root: Path,
    expected_cases: set[str],
    proof_contract: list[str],
) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    case_root = artifact_root / "case-results"
    for path in sorted(case_root.glob("*.json")) if case_root.is_dir() else []:
        payload = _load(path)
        case_id = str(payload.get("id") or "")
        if not case_id or case_id in records:
            continue
        status = str(payload.get("status") or "gap")
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
        satisfied = set(payload.get("proof_contract") or [])
        not_applicable = payload.get("not_applicable_proof")
        if not isinstance(not_applicable, dict):
            not_applicable = {}
        invalid_exemptions = sorted(
            key for key, reason in not_applicable.items() if not str(reason).strip()
        )
        missing_contract = sorted(set(proof_contract) - satisfied - set(not_applicable))
        if status == "passed" and (not evidence or missing_contract or invalid_exemptions):
            status = "gap"
        records[case_id] = {
            "id": case_id,
            "status": status,
            "evidence": [str(item) for item in evidence],
            "proof_contract": sorted(satisfied),
            "missing_proof_contract": missing_contract,
            "not_applicable_proof": not_applicable,
            "invalid_proof_exemptions": invalid_exemptions,
            "record": _relative(artifact_root, path),
        }
    return [
        records.get(
            case_id,
            {
                "id": case_id,
                "status": "gap",
                "evidence": [],
                "proof_contract": [],
                "missing_proof_contract": proof_contract,
                "reason": "no explicit installed-package case result",
            },
        )
        for case_id in sorted(expected_cases)
    ]


def _identity_counts(artifact_root: Path) -> tuple[dict[str, int], list[dict[str, Any]]]:
    inventory_path = artifact_root / "runtime-inventory.json"
    map_path = artifact_root / "inventory-case-map.json"
    results_path = artifact_root / "identity-results.json"
    inventory = _load(inventory_path) if inventory_path.is_file() else {"identities": []}
    mappings = _load(map_path) if map_path.is_file() else {"mappings": []}
    result_payload = _load(results_path) if results_path.is_file() else {"identities": []}
    identities = list(inventory.get("identities") or [])
    mapping_rows = list(mappings.get("mappings") or [])
    result_rows = list(result_payload.get("identities") or [])
    result_by_key = {
        (
            str(item.get("pane") or ""),
            str(item.get("identity") or ""),
            int(item.get("occurrence") or 0),
        ): item
        for item in result_rows
        if isinstance(item, dict)
    }
    disposition: list[dict[str, Any]] = []
    mapped = 0
    exercised = 0
    passed = 0
    failed = 0
    skipped = 0
    gaps = 0
    mapped_keys = {
        (
            str(item.get("pane") or ""),
            str(item.get("identity") or ""),
            int(item.get("occurrence") or 0),
        )
        for item in mapping_rows
        if isinstance(item, dict) and item.get("mapped") is True
    }
    for item in identities:
        key = (
            str(item.get("pane") or ""),
            str(item.get("identity") or ""),
            int(item.get("occurrence") or 0),
        )
        is_mapped = key in mapped_keys
        mapped += int(is_mapped)
        result = result_by_key.get(key)
        status = str((result or {}).get("status") or "gap")
        if result:
            exercised += 1
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
        elif status == "skipped":
            skipped += 1
        else:
            gaps += 1
        disposition.append(
            {
                "pane": key[0],
                "identity": key[1],
                "occurrence": key[2],
                "mapped": is_mapped,
                "status": status,
                "case_id": str((result or {}).get("case_id") or ""),
                "evidence": list((result or {}).get("evidence") or []),
            }
        )
    return (
        {
            "discovered": len(identities),
            "mapped": mapped,
            "exercised": exercised,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "gaps": gaps,
        },
        disposition,
    )


def _artifacts(artifact_root: Path, required: list[str]) -> dict[str, list[str]]:
    candidates = {
        "package_identity": [artifact_root / "package-identity.json"],
        "corpus_preflight": [artifact_root / "corpus-preflight.json"],
        "runtime_inventory": [artifact_root / "runtime-inventory.json"],
        "inventory_case_map": [artifact_root / "inventory-case-map.json"],
        "action_ledger": [artifact_root / "action-ledger.json"],
        "request_ledger": [artifact_root / "request-ledger.json"],
        "persistence_ledger": [artifact_root / "identity-results.json"],
        "viewport_and_accessibility": [artifact_root / "screenshots.json"],
        "reopen_and_restart": [artifact_root / "reopen-restart.json"],
        "individual_output": [artifact_root / "exports" / "e2e-export-test.mp4"],
        "combined_output": [artifact_root / "exports" / "combined-output.mp4"],
        "rendered_output_analysis": [artifact_root / "rendered-output-proof.json"],
        "application_logs": [artifact_root / "e2e-logs" / "e2e.log"],
        "platform_summary": [artifact_root / "platform-summary.json"],
    }
    return {
        family: [
            _relative(artifact_root, path)
            for path in candidates.get(family, [])
            if path.is_file() or family == "platform_summary"
        ]
        for family in required
    }


def build_summary(
    artifact_root: Path,
    *,
    platform: str,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    manifest = _load(manifest_path)
    manifest_result = validate_manifest(manifest_path)
    package_identity_path = artifact_root / "package-identity.json"
    package_identity = _load(package_identity_path) if package_identity_path.is_file() else {}
    expected_cases = _manifest_cases(manifest, platform)
    cases = _case_records(artifact_root, expected_cases, list(manifest["proof_contract"]))
    counts, identity_disposition = _identity_counts(artifact_root)
    summary = {
        "platform": platform,
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_result["manifest_sha256"],
        "source_commit": package_identity.get("source_commit", ""),
        "source_tree_clean": package_identity.get("source_tree_clean", False),
        "package_sha256": package_identity.get("package_sha256", ""),
        "corpus_revision": package_identity.get("corpus_revision", ""),
        "counts": counts,
        "cases": cases,
        "identity_disposition": identity_disposition,
        "artifacts": _artifacts(artifact_root, list(manifest["required_artifact_families"])),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--platform",
        choices=("macos", "windows", "linux"),
        default=PLATFORM_BY_SYS.get(sys.platform),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    if not args.platform:
        parser.error("--platform is required on this operating system")
    artifact_root = args.artifact_root.resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_root / "platform-summary.json"
    summary = build_summary(artifact_root, platform=args.platform, manifest_path=args.manifest)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    validation = validate_platform_summary(
        summary_path, manifest_path=args.manifest, artifact_root=artifact_root
    )
    validation_path = artifact_root / "platform-summary-validation.json"
    validation_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result": validation["result"],
                "platform": args.platform,
                "counts": summary["counts"],
                "case_gaps": sum(1 for item in summary["cases"] if item["status"] == "gap"),
                "errors": validation["errors"],
                "summary": str(summary_path),
            },
            indent=2,
        )
    )
    return 0 if validation["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

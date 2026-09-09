#!/usr/bin/env python3
"""Build a fail-closed summary for a v1.0.7 non-publishing test release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "tests" / "release_validation" / "v107-test-cases.json"


def _load(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"missing or empty artifact: {path.name}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON artifact {path.name}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"artifact must contain an object: {path.name}")
        return {}
    return payload


def _artifact_exists(root: Path, entry: str) -> bool:
    candidate = (root / entry.split("#", 1)[0]).resolve()
    return (
        candidate.is_relative_to(root.resolve())
        and candidate.is_file()
        and candidate.stat().st_size > 0
    )


def build_summary(
    artifact_root: Path,
    *,
    platform: str,
    expected_commit: str = "",
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    errors: list[str] = []
    manifest = _load(manifest_path, errors)
    if manifest.get("schema_version") != 1:
        errors.append("test manifest schema_version must be 1")
    if manifest.get("release") != "1.0.7":
        errors.append("test manifest release must be 1.0.7")
    if platform not in manifest.get("required_platforms", []):
        errors.append(f"unsupported platform: {platform}")

    identity = _load(artifact_root / "package-identity.json", errors)
    corpus = _load(artifact_root / "corpus-preflight.json", errors)
    e2e = _load(artifact_root / "summary.json", errors)
    observations = _load(artifact_root / "case-observations.json", errors)
    rendered = _load(artifact_root / "rendered-output-proof.json", errors)
    restart = _load(artifact_root / "reopen-restart.json", errors)
    platform_proof = _load(artifact_root / "platform-proof.json", errors)

    source_commit = str(identity.get("source_commit") or "")
    if not source_commit:
        errors.append("package source_commit is required")
    if expected_commit and source_commit != expected_commit:
        errors.append(
            f"package source_commit mismatch: expected {expected_commit}, got {source_commit}"
        )
    if identity.get("source_tree_clean") is not True:
        errors.append("package source_tree_clean must be true")
    if not str(identity.get("package_sha256") or ""):
        errors.append("package_sha256 is required")
    corpus_revision = str(manifest.get("corpus_revision") or "")
    if identity.get("corpus_revision") != corpus_revision:
        errors.append("package corpus_revision does not match the v107 test manifest")
    if corpus.get("result") != "passed" or corpus.get("corpus_revision") != corpus_revision:
        errors.append("locked v107 corpus preflight did not pass")

    if e2e.get("result") != "passed" or e2e.get("scope") != "release-proof":
        errors.append("full packaged v107 E2E did not pass in release-proof scope")
    if e2e.get("failures") or e2e.get("pageErrors") or e2e.get("pageErrorsList"):
        errors.append("full packaged v107 E2E recorded failures or page errors")
    inventory = e2e.get("runtimeInventory") if isinstance(e2e.get("runtimeInventory"), dict) else {}
    discovered = inventory.get("discovered")
    if not isinstance(discovered, int) or discovered <= 0:
        errors.append("runtime inventory discovered count must be positive")
    elif inventory.get("mapped") != discovered or inventory.get("gaps") != 0:
        errors.append("runtime inventory must be fully mapped with zero gaps")

    expected_cases = set(manifest.get("cases") or [])
    raw_cases = observations.get("cases") if isinstance(observations.get("cases"), list) else []
    actual: dict[str, dict[str, Any]] = {}
    for item in raw_cases:
        if not isinstance(item, dict):
            errors.append("case observation must be an object")
            continue
        case_id = str(item.get("id") or "")
        if not case_id or case_id in actual:
            errors.append(f"duplicate or empty case observation: {case_id or '<empty>'}")
            continue
        actual[case_id] = item
    missing_cases = sorted(expected_cases - set(actual))
    unknown_cases = sorted(set(actual) - expected_cases)
    if missing_cases:
        errors.append(f"missing v107 cases: {missing_cases}")
    if unknown_cases:
        errors.append(f"unknown v107 cases: {unknown_cases}")
    for case_id in sorted(expected_cases & set(actual)):
        item = actual[case_id]
        if item.get("status") != "passed":
            errors.append(f"{case_id}: status must be passed")
        evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []
        if not evidence:
            errors.append(f"{case_id}: evidence is required")
        for entry in evidence:
            if not _artifact_exists(artifact_root, str(entry)):
                errors.append(f"{case_id}: missing or empty evidence {entry}")

    if rendered.get("result") != "passed":
        errors.append("rendered individual and combined output proof did not pass")
    for output in ("individual", "combined"):
        record = rendered.get(output) if isinstance(rendered.get(output), dict) else {}
        if not record.get("video") or not record.get("audio") or not record.get("sha256"):
            errors.append(f"rendered {output} output lacks video/audio/hash proof")
    if restart.get("result") != "passed":
        errors.append("project reopen/restart proof did not pass")
    if platform_proof.get("platform") != platform:
        errors.append("platform proof does not match requested platform")
    checks = platform_proof.get("checks") if isinstance(platform_proof.get("checks"), dict) else {}
    for check in (manifest.get("platform_checks") or {}).get(platform, []):
        if not isinstance(checks.get(check), dict) or checks[check].get("passed") is not True:
            errors.append(f"required platform check did not pass: {check}")

    video = artifact_root / "full-e2e-test.webm"
    if not video.is_file() or video.stat().st_size == 0:
        errors.append("full packaged E2E video is missing or empty")

    passed_cases = sum(
        actual.get(case_id, {}).get("status") == "passed" for case_id in expected_cases
    )
    return {
        "result": "passed" if not errors else "failed",
        "release": manifest.get("release", ""),
        "platform": platform,
        "source_commit": source_commit,
        "source_tree_clean": identity.get("source_tree_clean", False),
        "package_sha256": identity.get("package_sha256", ""),
        "corpus_revision": identity.get("corpus_revision", ""),
        "runtime_inventory": inventory,
        "cases": {
            "required": len(expected_cases),
            "passed": passed_cases,
            "gaps": len(expected_cases) - passed_cases,
        },
        "full_session_video": "full-e2e-test.webm"
        if video.is_file() and video.stat().st_size > 0
        else "",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--platform", choices=("macos", "windows", "linux"), required=True)
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    summary = build_summary(
        root,
        platform=args.platform,
        expected_commit=args.expected_commit,
        manifest_path=args.manifest,
    )
    output = root / "v107-test-release-summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

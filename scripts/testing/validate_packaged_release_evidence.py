#!/usr/bin/env python3
"""Fail-closed validation and aggregation for exhaustive packaged release evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "tests" / "release_validation" / "manifest-v1.json"
REQUIRED_FEATURE_SHARDS = {
    "shell",
    "project-practiscore",
    "media",
    "compose",
    "trim",
    "score",
    "splits-waveform",
    "markers",
    "overlay",
    "review",
    "export",
    "intro-outro",
    "queue",
    "metrics",
    "shotml",
    "settings",
    "rendered-output",
}
VALID_CASE_STATUSES = {"passed", "failed", "skipped", "gap"}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_cases(manifest: dict[str, Any], platform: str | None = None) -> set[str]:
    cases = {str(case_id) for shard in manifest["shards"] for case_id in shard["cases"]}
    if platform:
        cases.update(str(item) for item in manifest["platform_cases"][platform])
    return cases


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = _load(path)
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    platforms = manifest.get("required_platforms")
    if platforms != ["macos", "windows", "linux"]:
        errors.append("required_platforms must be macos, windows, linux")
    shards = manifest.get("shards")
    if not isinstance(shards, list):
        errors.append("shards must be a list")
        shards = []
    shard_ids = [str(item.get("id") or "") for item in shards if isinstance(item, dict)]
    if set(shard_ids) != REQUIRED_FEATURE_SHARDS or len(shard_ids) != len(set(shard_ids)):
        errors.append(
            f"shards must be unique and exactly {sorted(REQUIRED_FEATURE_SHARDS)}; "
            f"got {sorted(shard_ids)}"
        )
    case_ids: list[str] = []
    for shard in shards:
        if not isinstance(shard, dict) or not isinstance(shard.get("cases"), list):
            errors.append("every shard must contain a cases list")
            continue
        if not shard["cases"]:
            errors.append(f"shard {shard.get('id')} has no cases")
        case_ids.extend(str(item) for item in shard["cases"])
    platform_cases = manifest.get("platform_cases")
    if not isinstance(platform_cases, dict) or set(platform_cases) != set(platforms or []):
        errors.append("platform_cases must define each required platform exactly once")
    else:
        for platform, items in platform_cases.items():
            if not isinstance(items, list) or not items:
                errors.append(f"platform {platform} has no cases")
            else:
                case_ids.extend(str(item) for item in items)
    if len(case_ids) != len(set(case_ids)):
        errors.append("case ids must be globally unique")
    for key in ("proof_contract", "required_artifact_families", "forbidden_input_roots"):
        values = manifest.get(key)
        if not isinstance(values, list) or not values:
            errors.append(f"{key} must be a non-empty list")
    return {
        "result": "passed" if not errors else "failed",
        "manifest_id": manifest.get("manifest_id", ""),
        "manifest_sha256": _sha256(path),
        "shards": len(shards),
        "cases": len(case_ids),
        "errors": errors,
    }


def validate_platform_summary(
    summary_path: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    manifest_result = validate_manifest(manifest_path)
    manifest = _load(manifest_path)
    summary = _load(summary_path)
    errors = list(manifest_result["errors"])
    platform = str(summary.get("platform") or "")
    if platform not in manifest["required_platforms"]:
        errors.append(f"invalid platform: {platform or '<missing>'}")
        expected_cases: set[str] = set()
    else:
        expected_cases = _manifest_cases(manifest, platform)
    if summary.get("manifest_id") != manifest["manifest_id"]:
        errors.append("manifest_id mismatch")
    if summary.get("manifest_sha256") != manifest_result["manifest_sha256"]:
        errors.append("manifest_sha256 mismatch")
    if not str(summary.get("source_commit") or "").strip():
        errors.append("source_commit is required")
    if summary.get("source_tree_clean") is not True:
        errors.append("source_tree_clean must be true")
    if not str(summary.get("package_sha256") or "").strip():
        errors.append("package_sha256 is required")
    if not str(summary.get("corpus_revision") or "").strip():
        errors.append("corpus_revision is required")

    raw_cases = summary.get("cases")
    if not isinstance(raw_cases, list):
        errors.append("cases must be a list")
        raw_cases = []
    actual_case_ids = [str(item.get("id") or "") for item in raw_cases if isinstance(item, dict)]
    if len(actual_case_ids) != len(set(actual_case_ids)):
        errors.append("summary case ids must be unique")
    missing = sorted(expected_cases - set(actual_case_ids))
    unknown = sorted(set(actual_case_ids) - expected_cases)
    if missing:
        errors.append(f"missing cases: {missing}")
    if unknown:
        errors.append(f"unknown cases: {unknown}")
    for item in raw_cases:
        if not isinstance(item, dict):
            errors.append("case entries must be objects")
            continue
        case_id = str(item.get("id") or "")
        status = str(item.get("status") or "")
        if status not in VALID_CASE_STATUSES:
            errors.append(f"{case_id}: invalid status {status}")
        elif status != "passed":
            errors.append(f"{case_id}: status {status}")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{case_id}: evidence is required")

    counts = summary.get("counts")
    if not isinstance(counts, dict):
        errors.append("counts must be an object")
        counts = {}
    expected_count = len(expected_cases)
    actual_passed = sum(
        1 for item in raw_cases if isinstance(item, dict) and item.get("status") == "passed"
    )
    discovered = counts.get("discovered")
    if not isinstance(discovered, int) or discovered <= 0:
        errors.append(f"counts.discovered must be a positive integer; got {discovered!r}")
        discovered = 0
    required_counts = {
        "discovered": discovered,
        "mapped": discovered,
        "exercised": discovered,
        "passed": discovered,
        "failed": 0,
        "skipped": 0,
        "gaps": 0,
    }
    for key, value in required_counts.items():
        if counts.get(key) != value:
            errors.append(f"counts.{key} must be {value}; got {counts.get(key)!r}")
    if actual_passed != expected_count:
        errors.append(f"passed case records must total {expected_count}; got {actual_passed}")

    artifact_families = summary.get("artifacts")
    if not isinstance(artifact_families, dict):
        errors.append("artifacts must be an object")
        artifact_families = {}
    required_artifacts = set(manifest["required_artifact_families"])
    missing_families = sorted(required_artifacts - set(artifact_families))
    if missing_families:
        errors.append(f"missing artifact families: {missing_families}")
    if artifact_root:
        resolved_root = artifact_root.resolve()
        for family, entries in artifact_families.items():
            if not isinstance(entries, list) or not entries:
                errors.append(f"artifact family {family} must have files")
                continue
            for entry in entries:
                candidate = (resolved_root / str(entry)).resolve()
                if not candidate.is_relative_to(resolved_root):
                    errors.append(f"artifact escapes root: {entry}")
                elif not candidate.is_file() or candidate.stat().st_size == 0:
                    errors.append(f"artifact missing or empty: {entry}")
    return {
        "result": "passed" if not errors else "failed",
        "platform": platform,
        "source_commit": summary.get("source_commit", ""),
        "source_tree_clean": summary.get("source_tree_clean", False),
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_result["manifest_sha256"],
        "corpus_revision": summary.get("corpus_revision", ""),
        "package_sha256": summary.get("package_sha256", ""),
        "counts": required_counts if not errors else counts,
        "errors": errors,
    }


def aggregate(
    summaries: list[Path],
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    expected_commit: str = "",
) -> dict[str, Any]:
    manifest_result = validate_manifest(manifest_path)
    manifest = _load(manifest_path)
    validated = [validate_platform_summary(path, manifest_path=manifest_path) for path in summaries]
    errors = list(manifest_result["errors"])
    by_platform: dict[str, dict[str, Any]] = {}
    for item in validated:
        platform = str(item.get("platform") or "")
        if platform in by_platform:
            errors.append(f"duplicate platform summary: {platform}")
        by_platform[platform] = item
        errors.extend(f"{platform}: {error}" for error in item["errors"])
    required_platforms = set(manifest["required_platforms"])
    if set(by_platform) != required_platforms:
        errors.append(
            f"platform summaries must be exactly {sorted(required_platforms)}; "
            f"got {sorted(by_platform)}"
        )
    commits = {str(item.get("source_commit") or "") for item in validated}
    if len(commits) != 1:
        errors.append(f"platform source commits differ: {sorted(commits)}")
    elif expected_commit and commits != {expected_commit}:
        errors.append(f"source commit mismatch: expected {expected_commit}, got {sorted(commits)}")
    corpus_revisions = {str(item.get("corpus_revision") or "") for item in validated}
    if len(corpus_revisions) != 1:
        errors.append(f"platform corpus revisions differ: {sorted(corpus_revisions)}")
    return {
        "result": "passed" if not errors else "failed",
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_result["manifest_sha256"],
        "source_commit": next(iter(commits), "") if len(commits) == 1 else "",
        "corpus_revision": next(iter(corpus_revisions), "") if len(corpus_revisions) == 1 else "",
        "platforms": by_platform,
        "errors": errors,
    }


def _write_or_print(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("--output", type=Path)
    platform_parser = subparsers.add_parser("platform")
    platform_parser.add_argument("summary", type=Path)
    platform_parser.add_argument("--artifact-root", type=Path)
    platform_parser.add_argument("--output", type=Path)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("summaries", type=Path, nargs="+")
    aggregate_parser.add_argument("--expected-commit", default="")
    aggregate_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "manifest":
        result = validate_manifest(args.manifest)
    elif args.command == "platform":
        result = validate_platform_summary(
            args.summary, manifest_path=args.manifest, artifact_root=args.artifact_root
        )
    else:
        result = aggregate(
            args.summaries,
            manifest_path=args.manifest,
            expected_commit=args.expected_commit,
        )
    _write_or_print(result, args.output)
    return 0 if result["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "validate_packaged_release_evidence.py"
MANIFEST = ROOT / "tests" / "release_validation" / "manifest-v1.json"
SPEC = importlib.util.spec_from_file_location(
    "validate_packaged_release_evidence_module", MODULE_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _passing_summary(platform: str) -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_result = MODULE.validate_manifest(MANIFEST)
    cases = sorted(MODULE._manifest_cases(manifest, platform))
    count = len(cases)
    return {
        "platform": platform,
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_result["manifest_sha256"],
        "source_commit": "abc123",
        "source_tree_clean": True,
        "package_sha256": f"package-{platform}",
        "corpus_revision": "splitshot-release-corpus-v1",
        "counts": {
            "discovered": count,
            "mapped": count,
            "exercised": count,
            "passed": count,
            "failed": 0,
            "skipped": 0,
            "gaps": 0,
        },
        "cases": [
            {"id": case_id, "status": "passed", "evidence": [f"cases/{case_id}.json"]}
            for case_id in cases
        ],
        "artifacts": {
            family: [f"{family}/proof.json"] for family in manifest["required_artifact_families"]
        },
    }


def test_exhaustive_manifest_is_valid_and_complete() -> None:
    report = MODULE.validate_manifest(MANIFEST)

    assert report["result"] == "passed"
    assert report["shards"] == 17
    assert report["cases"] > 120


def test_platform_summary_fails_closed_on_gap(tmp_path: Path) -> None:
    payload = _passing_summary("macos")
    payload["cases"][0]["status"] = "gap"
    payload["counts"]["passed"] -= 1
    payload["counts"]["gaps"] = 1
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(payload), encoding="utf-8")

    report = MODULE.validate_platform_summary(summary, manifest_path=MANIFEST)

    assert report["result"] == "failed"
    assert any("status gap" in error for error in report["errors"])


def test_platform_summary_fails_closed_on_missing_case(tmp_path: Path) -> None:
    payload = _passing_summary("linux")
    payload["cases"].pop()
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(payload), encoding="utf-8")

    report = MODULE.validate_platform_summary(summary, manifest_path=MANIFEST)

    assert report["result"] == "failed"
    assert any("missing cases" in error for error in report["errors"])


def test_aggregate_requires_three_matching_platforms(tmp_path: Path) -> None:
    paths = []
    for platform in ("macos", "windows", "linux"):
        path = tmp_path / f"{platform}.json"
        path.write_text(json.dumps(_passing_summary(platform)), encoding="utf-8")
        paths.append(path)

    report = MODULE.aggregate(paths, manifest_path=MANIFEST, expected_commit="abc123")

    assert report["result"] == "passed"
    assert set(report["platforms"]) == {"macos", "windows", "linux"}


def test_aggregate_rejects_commit_mismatch(tmp_path: Path) -> None:
    paths = []
    for platform in ("macos", "windows", "linux"):
        payload = _passing_summary(platform)
        if platform == "windows":
            payload["source_commit"] = "different"
        path = tmp_path / f"{platform}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)

    report = MODULE.aggregate(paths, manifest_path=MANIFEST)

    assert report["result"] == "failed"
    assert any("source commits differ" in error for error in report["errors"])

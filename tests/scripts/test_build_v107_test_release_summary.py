from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "build_v107_test_release_summary.py"
MANIFEST = ROOT / "tests" / "release_validation" / "v107-test-cases.json"
EXHAUSTIVE_MANIFEST = ROOT / "tests" / "release_validation" / "manifest-v1.json"
SPEC = importlib.util.spec_from_file_location("build_v107_test_release_summary_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_json(root: Path, name: str, payload: dict) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _complete_evidence(root: Path, platform: str = "macos") -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    exhaustive = json.loads(EXHAUSTIVE_MANIFEST.read_text(encoding="utf-8"))
    exhaustive_cases = [
        case_id
        for shard in exhaustive["shards"]
        for case_id in shard["cases"]
    ]
    platform_cases = exhaustive["platform_cases"][platform]
    _write_json(
        root,
        "package-identity.json",
        {
            "source_commit": "abc123",
            "source_tree_clean": True,
            "package_sha256": "package-hash",
            "corpus_revision": manifest["corpus_revision"],
        },
    )
    _write_json(
        root,
        "corpus-preflight.json",
        {"result": "passed", "corpus_revision": manifest["corpus_revision"]},
    )
    _write_json(
        root,
        "summary.json",
        {
            "result": "passed",
            "scope": "release-proof",
            "failures": [],
            "pageErrors": 0,
            "pageErrorsList": [],
            "runtimeInventory": {"discovered": 913, "mapped": 913, "gaps": 0},
        },
    )
    evidence = root / "proof.json"
    evidence.write_text("{}", encoding="utf-8")
    for case_id in exhaustive_cases + platform_cases:
        filename = "".join(
            character if character.isalnum() or character in "._-" else "-"
            for character in case_id
        )
        _write_json(
            root,
            f"case-results/{filename}.json",
            {"id": case_id, "status": "passed", "evidence": ["proof.json"]},
        )
    rendered_record = {"video": {"codec": "h264"}, "audio": {"codec": "aac"}, "sha256": "hash"}
    _write_json(
        root,
        "rendered-output-proof.json",
        {"result": "passed", "individual": rendered_record, "combined": rendered_record},
    )
    _write_json(root, "reopen-restart.json", {"result": "passed"})
    _write_json(
        root,
        "identity-results.json",
        {"counts": {"total": 913, "passed": 913, "gaps": 0}},
    )
    required_checks = manifest["platform_checks"][platform]
    _write_json(
        root,
        "platform-proof.json",
        {
            "platform": platform,
            "checks": {check: {"passed": True} for check in required_checks},
        },
    )
    feature_video = root / "full-feature-validation.mp4"
    feature_video.write_bytes(b"video")
    _write_json(
        root,
        "full-feature-validation.json",
        {
            "result": "passed",
            "sha256": hashlib.sha256(b"video").hexdigest(),
            "rendered_outputs_are_final_segments": True,
            "cases": {
                "required": len(exhaustive_cases),
                "covered": len(exhaustive_cases),
                "gaps": 0,
            },
        },
    )


def test_complete_v107_test_release_evidence_passes(tmp_path: Path) -> None:
    _complete_evidence(tmp_path)

    summary = MODULE.build_summary(
        tmp_path,
        platform="macos",
        expected_commit="abc123",
        manifest_path=MANIFEST,
    )

    assert summary["result"] == "passed"
    expected_cases = sum(
        len(shard["cases"])
        for shard in json.loads(EXHAUSTIVE_MANIFEST.read_text(encoding="utf-8"))["shards"]
    )
    expected_cases += len(
        json.loads(EXHAUSTIVE_MANIFEST.read_text(encoding="utf-8"))["platform_cases"]["macos"]
    )
    assert summary["cases"] == {
        "required": expected_cases,
        "passed": expected_cases,
        "gaps": 0,
    }
    assert summary["runtime_inventory"] == {"discovered": 913, "mapped": 913, "gaps": 0}
    assert summary["full_feature_validation_video"] == "full-feature-validation.mp4"
    assert summary["errors"] == []


def test_v107_test_release_evidence_fails_closed(tmp_path: Path) -> None:
    _complete_evidence(tmp_path)
    case_file = next((tmp_path / "case-results").glob("*.json"))
    case_file.unlink()
    (tmp_path / "full-feature-validation.mp4").unlink()

    summary = MODULE.build_summary(
        tmp_path,
        platform="macos",
        expected_commit="different",
        manifest_path=MANIFEST,
    )

    assert summary["result"] == "failed"
    assert summary["cases"]["gaps"] == 1
    assert any("source_commit mismatch" in error for error in summary["errors"])
    assert any("missing v107 cases" in error for error in summary["errors"])
    assert "full-feature validation video is missing or empty" in summary["errors"]

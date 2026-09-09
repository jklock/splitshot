from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "build_v107_test_release_summary.py"
MANIFEST = ROOT / "tests" / "release_validation" / "v107-test-cases.json"
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
    _write_json(
        root,
        "case-observations.json",
        {
            "cases": [
                {"id": case_id, "status": "passed", "evidence": ["proof.json"]}
                for case_id in manifest["cases"]
            ]
        },
    )
    rendered_record = {"video": {"codec": "h264"}, "audio": {"codec": "aac"}, "sha256": "hash"}
    _write_json(
        root,
        "rendered-output-proof.json",
        {"result": "passed", "individual": rendered_record, "combined": rendered_record},
    )
    _write_json(root, "reopen-restart.json", {"result": "passed"})
    required_check = manifest["platform_checks"][platform][0]
    _write_json(
        root,
        "platform-proof.json",
        {"platform": platform, "checks": {required_check: {"passed": True}}},
    )
    (root / "full-e2e-test.webm").write_bytes(b"video")


def test_complete_v107_test_release_evidence_passes(tmp_path: Path) -> None:
    _complete_evidence(tmp_path)

    summary = MODULE.build_summary(
        tmp_path,
        platform="macos",
        expected_commit="abc123",
        manifest_path=MANIFEST,
    )

    assert summary["result"] == "passed"
    assert summary["cases"] == {"required": 30, "passed": 30, "gaps": 0}
    assert summary["runtime_inventory"] == {"discovered": 913, "mapped": 913, "gaps": 0}
    assert summary["full_session_video"] == "full-e2e-test.webm"
    assert summary["errors"] == []


def test_v107_test_release_evidence_fails_closed(tmp_path: Path) -> None:
    _complete_evidence(tmp_path)
    observations = json.loads((tmp_path / "case-observations.json").read_text(encoding="utf-8"))
    observations["cases"].pop()
    _write_json(tmp_path, "case-observations.json", observations)
    (tmp_path / "full-e2e-test.webm").unlink()

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
    assert "full packaged E2E video is missing or empty" in summary["errors"]

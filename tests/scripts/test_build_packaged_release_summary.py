from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "build_packaged_release_summary.py"
MANIFEST = ROOT / "tests" / "release_validation" / "manifest-v1.json"
SPEC = importlib.util.spec_from_file_location("build_packaged_release_summary_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_summary_builder_exposes_every_missing_case_and_identity_gap(tmp_path: Path) -> None:
    (tmp_path / "package-identity.json").write_text(
        json.dumps(
            {
                "source_commit": "abc123",
                "source_tree_clean": True,
                "package_sha256": "package",
                "corpus_revision": "splitshot-release-corpus-v1",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "runtime-inventory.json").write_text(
        json.dumps(
            {"identities": [{"pane": "project", "identity": "id:project-name", "occurrence": 0}]}
        ),
        encoding="utf-8",
    )
    (tmp_path / "inventory-case-map.json").write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "pane": "project",
                        "identity": "id:project-name",
                        "occurrence": 0,
                        "mapped": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = MODULE.build_summary(tmp_path, platform="macos", manifest_path=MANIFEST)

    assert summary["counts"] == {
        "discovered": 1,
        "mapped": 1,
        "exercised": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "gaps": 1,
    }
    assert len(summary["cases"]) > 120
    assert all(item["status"] == "gap" for item in summary["cases"])


def test_case_contract_allows_only_explained_non_applicable_layers(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    case_id = manifest["shards"][0]["cases"][0]
    case_root = tmp_path / "case-results"
    case_root.mkdir()
    (case_root / "case.json").write_text(
        json.dumps(
            {
                "id": case_id,
                "status": "passed",
                "evidence": ["package-identity.json"],
                "proof_contract": ["one_action"],
                "not_applicable_proof": {
                    item: "read-only package assertion"
                    for item in manifest["proof_contract"]
                    if item != "one_action"
                },
            }
        ),
        encoding="utf-8",
    )

    records = MODULE._case_records(
        tmp_path,
        {case_id},
        manifest["proof_contract"],
    )

    assert records[0]["status"] == "passed"
    assert records[0]["missing_proof_contract"] == []

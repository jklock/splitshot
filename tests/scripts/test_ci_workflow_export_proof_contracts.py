from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E2E_SCRIPT = ROOT / "scripts" / "testing" / "e2e-playwright.cjs"
TEST_WORKFLOWS = [
    ROOT / ".github" / "workflows" / "test-linux.yml",
    ROOT / ".github" / "workflows" / "test-macos.yml",
    ROOT / ".github" / "workflows" / "test-windows.yml",
]
PACKAGED_WORKFLOWS = [
    ROOT / ".github" / "workflows" / "build-linux.yml",
    ROOT / ".github" / "workflows" / "build-macos.yml",
    ROOT / ".github" / "workflows" / "build-windows.yml",
    ROOT / ".github" / "workflows" / "release.yml",
]


def test_packaged_e2e_script_writes_export_artifact_under_artifacts_tree() -> None:
    script = E2E_SCRIPT.read_text(encoding="utf-8")

    assert (
        "const exportDir = process.env.E2E_EXPORT_DIR || path.join(artifactRoot, 'exports');"
        in script
    )
    assert "const canonicalExportFile = path.join(exportDir, 'e2e-export-test.mp4');" in script
    assert "fs.copyFileSync(outputPath, canonicalExportFile);" in script
    assert "artifacts.push(canonicalExportFile);" in script
    assert "const stopAfterExport = e2eScope === 'export-proof';" in script
    assert "String(payload?.status || '').includes('Processed ')" in script
    assert "outputPath.length > 0" not in script
    assert '.trim-source-card[data-source-id="${sourceId}"]' in script
    assert ".trim-sync-card" not in script
    assert "page.locator('#queue-show-log').click()" in script
    assert '.queue-membership-btn[data-stage-id="${activeStageId}"]' in script
    assert ".queue-add-btn" not in script
    assert "#export-path" not in script
    assert "#show-export-log" not in script
    assert "profile_create_ms: 5000" in script
    assert "profile_edit_ms: 5000" in script
    assert "def _proof_windows_export_text" in (
        ROOT / "scripts" / "testing" / "test_packaged_app_e2e.py"
    ).read_text(encoding="utf-8")


def _assert_real_corpus_contract(source: str, workflow_name: str) -> None:
    assert "tests/release_data/primary.MP4" in source, workflow_name
    assert "tests/release_data/secondary.MP4" in source, workflow_name
    assert "tests/release_data/practiscore.csv" in source, workflow_name
    assert "--script-arg=--scope" in source, workflow_name
    assert "--script-arg=release-proof" in source, workflow_name
    assert "scripts/testing/test_packaged_app_e2e.py" in source, workflow_name
    assert "tests/fixtures/media/e2e-stage.mp4" not in source, workflow_name


def test_ci_test_workflows_use_real_corpus_for_packaged_e2e_validation() -> None:
    for workflow in TEST_WORKFLOWS:
        source = workflow.read_text(encoding="utf-8")
        _assert_real_corpus_contract(source, workflow.name)
        assert "scripts/testing/build_packaged_release_summary.py" in source, workflow.name
        assert "artifacts/v107-release-proof/github-review/" in source, workflow.name
        if workflow.name == "test-windows.yml":
            assert "scripts/testing/validate_release_data.py" in source, workflow.name
            assert "find electron/build -type f -name '*.exe' | head -n 1" in source, workflow.name
            assert source.count("Install Tesseract") >= 2, workflow.name
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name


def test_packaged_build_and_release_workflows_use_real_corpus() -> None:
    for workflow in PACKAGED_WORKFLOWS:
        source = workflow.read_text(encoding="utf-8")
        _assert_real_corpus_contract(source, workflow.name)
        assert "artifacts/v107-release-proof/github-review/" in source, workflow.name
        if workflow.name == "build-windows.yml":
            assert "scripts/testing/validate_release_data.py" in source, workflow.name
            assert "find electron/build -type f -name '*.exe' | head -n 1" in source, workflow.name
            assert source.count("Install Tesseract") >= 2, workflow.name
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name
        if workflow.name == "release.yml":
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name
            assert "scripts/testing/build_packaged_release_summary.py" in source, workflow.name
            assert "validate_packaged_release_evidence.py aggregate" in source, workflow.name
            assert "--expected-commit" in source, workflow.name


def test_macos_test_package_is_signed_without_using_release_notarization() -> None:
    test_workflow = (ROOT / ".github" / "workflows" / "test-macos.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'SPLITSHOT_MAC_NOTARIZE: "0"' in test_workflow
    assert "Prepare macOS signing certificate" in test_workflow
    assert "Prepare macOS notarization credentials" not in test_workflow
    assert "codesign --verify --deep --strict" in test_workflow
    assert "spctl --assess" not in test_workflow
    assert "Prepare macOS notarization credentials" in release_workflow
    assert 'SPLITSHOT_MAC_NOTARIZE: "0"' not in release_workflow

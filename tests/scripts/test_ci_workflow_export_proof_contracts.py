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
    assert "const exportFile = path.join(exportDir, 'e2e-export-test.mp4');" in script
    assert "artifacts.push(artifactCopyPath);" in script
    assert "const stopAfterExport = e2eScope === 'export-proof';" in script
    assert "String(payload?.status || '').includes('Processed ')" in script
    assert "outputPath.length > 0" not in script
    assert '.trim-source-card[data-source-id="${sourceId}"]' in script
    assert ".trim-sync-card" not in script
    assert "page.locator('#queue-show-log').click()" in script
    assert "#export-path" not in script
    assert "#show-export-log" not in script
    assert "def _proof_windows_export_text" in (
        ROOT / "scripts" / "testing" / "test_packaged_app_e2e.py"
    ).read_text(encoding="utf-8")


def test_ci_test_workflows_use_compact_fixture_for_packaged_e2e_validation() -> None:
    for workflow in TEST_WORKFLOWS:
        source = workflow.read_text(encoding="utf-8")
        has_fixture_env = "SPLITSHOT_E2E_VIDEO: tests/fixtures/media/e2e-stage.mp4" in source
        has_fixture_arg = "--script-arg=tests/fixtures/media/e2e-stage.mp4" in source
        assert has_fixture_env or has_fixture_arg, f"{workflow.name}: missing E2E fixture"
        assert "--script-arg=--scope" in source, workflow.name
        assert "--script-arg=release-proof" in source, workflow.name
        assert "artifacts/v107-release-proof/github-review/" in source, workflow.name
        if workflow.name == "test-windows.yml":
            assert (
                "scripts/testing/verify_e2e_fixture.py tests/fixtures/media/e2e-stage.mp4 --min-shots 1 --min-duration 5"
                in source
            ), workflow.name
            assert "find electron/build -type f -name '*.exe' | head -n 1" in source, workflow.name
            assert source.count("Install Tesseract") >= 2, workflow.name
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name
        assert "scripts/testing/test_packaged_app_e2e.py" in source, workflow.name


def test_packaged_build_and_release_workflows_use_compact_e2e_fixture() -> None:
    for workflow in PACKAGED_WORKFLOWS:
        source = workflow.read_text(encoding="utf-8")
        has_fixture_env = "SPLITSHOT_E2E_VIDEO: tests/fixtures/media/e2e-stage.mp4" in source
        has_fixture_arg = "--script-arg=tests/fixtures/media/e2e-stage.mp4" in source
        assert has_fixture_env or has_fixture_arg, workflow.name
        assert "--script-arg=--scope" in source, workflow.name
        assert "--script-arg=release-proof" in source, workflow.name
        assert "artifacts/v107-release-proof/github-review/" in source, workflow.name
        if workflow.name == "build-windows.yml":
            assert (
                "scripts/testing/verify_e2e_fixture.py tests/fixtures/media/e2e-stage.mp4 --min-shots 1 --min-duration 5"
                in source
            ), workflow.name
            assert "find electron/build -type f -name '*.exe' | head -n 1" in source, workflow.name
            assert source.count("Install Tesseract") >= 2, workflow.name
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name
        if workflow.name == "release.yml":
            assert 'SPLITSHOT_E2E_OCR_PROOF: "1"' in source, workflow.name
        assert "scripts/testing/test_packaged_app_e2e.py" in source, workflow.name


def test_macos_test_package_is_signed_without_using_release_notarization() -> None:
    test_workflow = (ROOT / ".github" / "workflows" / "test-macos.yml").read_text(
        encoding="utf-8"
    )
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert 'SPLITSHOT_MAC_NOTARIZE: "0"' in test_workflow
    assert "Prepare macOS signing certificate" in test_workflow
    assert "Prepare macOS notarization credentials" not in test_workflow
    assert "codesign --verify --deep --strict" in test_workflow
    assert "spctl --assess" not in test_workflow
    assert "Prepare macOS notarization credentials" in release_workflow
    assert 'SPLITSHOT_MAC_NOTARIZE: "0"' not in release_workflow

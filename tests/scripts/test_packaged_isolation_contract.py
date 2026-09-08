from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_packaged_validation_isolates_python_and_electron_application_data() -> None:
    harness = (ROOT / "scripts/testing/test_packaged_app_e2e.py").read_text(encoding="utf-8")
    electron_main = (ROOT / "electron/main.js").read_text(encoding="utf-8")
    config = (ROOT / "src/splitshot/config.py").read_text(encoding="utf-8")

    assert '"SPLITSHOT_APP_DIR": str(artifact_root / "app-data")' in harness
    assert '"SPLITSHOT_ELECTRON_USER_DATA_DIR"' in harness
    assert "SPLITSHOT_ELECTRON_USER_DATA_DIR" in electron_main
    assert "app.setPath('userData'" in electron_main
    assert 'os.environ.get("SPLITSHOT_APP_DIR"' in config


def test_packaged_intro_outro_picker_accepts_an_ordered_test_sequence() -> None:
    electron_main = (ROOT / "electron/main.js").read_text(encoding="utf-8")
    harness = (ROOT / "scripts/testing/test_packaged_app_e2e.py").read_text(encoding="utf-8")

    assert "SPLITSHOT_ELECTRON_TEST_IN_OUT_PATHS" in electron_main
    assert "testInOutPathIndex += 1" in electron_main
    assert 'env["SPLITSHOT_ELECTRON_TEST_IN_OUT_PATHS"]' in harness

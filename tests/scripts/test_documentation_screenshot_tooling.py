from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(relative_path: str, name: str):
    path = ROOT / relative_path
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_screenshot_manifest_is_complete_and_requires_real_video_inputs() -> None:
    module = load_module(
        "scripts/docs/capture_browser_screenshots.py", "capture_browser_screenshots"
    )
    assert module.SCREENSHOT_FILENAMES == (
        "ProjectPane.png",
        "MediaPane.png",
        "ComposePane.png",
        "TrimPane.png",
        "ScorePane.png",
        "ScorePane2.png",
        "SplitsPane.png",
        "SplitsExpanded.png",
        "WaveformExpanded.png",
        "MarkersPane.png",
        "MarkersPane2.png",
        "OverlayPane.png",
        "OverlayPane2.png",
        "ColorPickerModal.png",
        "ReviewPane.png",
        "ReviewPane2.png",
        "ExportPane.png",
        "ExportPane2.png",
        "IntroOutroPane.png",
        "QueuePane.png",
        "ProcessingLogModal.png",
        "MetricsPane.png",
        "MetricsExpanded.png",
        "ShotMLPane.png",
        "ShotMLPane2.png",
        "SettingsPane.png",
        "SettingsPane2.png",
    )
    assert module.VIEWPORT == {"width": 1400, "height": 900}
    assert not hasattr(module, "SOURCE_VIDEO")
    assert module.PRACTISCORE == ROOT / "example_data/IDPA/IDPA.csv"
    assert module.WORK_ROOT.is_relative_to(ROOT / "tmp/codex")
    assert hasattr(module, "prewarm_boundary_media")
    assert hasattr(module, "stabilize_intro_outro_preview")
    assert hasattr(module, "restore_primary_stage")


def test_screenshot_capture_rejects_test_fixtures_and_duplicate_sources(tmp_path: Path) -> None:
    module = load_module(
        "scripts/docs/capture_browser_screenshots.py", "capture_browser_screenshots_inputs"
    )
    real_primary = tmp_path / "primary.mp4"
    real_secondary = tmp_path / "secondary.mp4"
    real_primary.write_bytes(b"primary")
    real_secondary.write_bytes(b"secondary")

    assert module.validated_real_video(real_primary, label="Primary") == real_primary.resolve()
    assert (
        module.validated_real_video(real_secondary, label="Secondary") == real_secondary.resolve()
    )
    assert module.validated_video_pair(real_primary, real_secondary) == (
        real_primary.resolve(),
        real_secondary.resolve(),
    )

    try:
        module.validated_video_pair(real_primary, real_primary)
    except ValueError as exc:
        assert "must be different files" in str(exc)
    else:
        raise AssertionError("Duplicate documentation video sources were accepted")

    fixture = ROOT / "tests/fixtures/media/e2e-stage.mp4"
    try:
        module.validated_real_video(fixture, label="Primary")
    except ValueError as exc:
        assert "must not come from tests/" in str(exc)
    else:
        raise AssertionError("Test fixture was accepted as documentation footage")


def test_screenshot_capture_requires_decoded_primary_and_secondary_frames() -> None:
    source = (ROOT / "scripts/docs/capture_browser_screenshots.py").read_text()
    assert "stabilize_visible_video_frames(page)" in source
    assert "document.querySelectorAll('#merge-preview-layer video')" in source
    assert 'result["primaryReady"]' in source
    assert 'result["secondaryReady"]' in source
    assert 'result["activeToolName"] != "intro-outro"' in source
    assert 'not result["secondaryVisible"]' in source
    assert "stats.mean > 8" in source
    assert "stats.variance > 12" in source
    assert "validate_showcase_state(page)" in source


def test_screenshot_capture_keeps_summary_selectors_generic_and_output_dynamic() -> None:
    source = (ROOT / "scripts/docs/capture_browser_screenshots.py").read_text()
    assert 'selector_labels != ["Division", "Class", "Overall"]' in source
    assert r"/^Overall - \d+\/\d+$/" in source
    assert '"Division Placement"' in source
    assert '"Class Placement"' in source
    assert '"Division + Class Placement"' in source


def test_browser_audit_projects_route_outside_fixture_tree(tmp_path: Path) -> None:
    interaction = load_module(
        "scripts/audits/browser/run_browser_interaction_audit.py",
        "run_browser_interaction_audit",
    )
    generated = Path(interaction._audit_project_path(interaction.DEFAULT_PRIMARY_VIDEO))
    assert generated.parent.is_relative_to(ROOT / "tmp/codex")
    assert not generated.is_relative_to(ROOT / "tests/fixtures")

    surface = load_module(
        "scripts/audits/browser/run_browser_ui_surface_audit.py",
        "run_browser_ui_surface_audit",
    )
    explicit = surface.audit_project_path(tmp_path / "audit-output")
    assert explicit.parent == (tmp_path / "audit-output").resolve()
    assert explicit.suffix == ".ssproj"
    assert not explicit.is_relative_to(ROOT / "tests/fixtures")

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


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


def test_screenshot_manifest_is_complete_and_uses_clean_clone_fixtures() -> None:
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
        "ExportLogModal.png",
        "QueuePane.png",
        "MetricsPane.png",
        "MetricsExpanded.png",
        "ShotMLPane.png",
        "ShotMLPane2.png",
        "SettingsPane.png",
        "SettingsPane2.png",
    )
    assert module.VIEWPORT == {"width": 1440, "height": 1024}
    assert module.SOURCE_VIDEO == ROOT / "tests/fixtures/media/e2e-stage.mp4"
    assert module.PRACTISCORE == ROOT / "example_data/IDPA/IDPA.csv"
    assert module.WORK_ROOT.is_relative_to(ROOT / "tmp/codex")


def test_screenshot_capture_requires_decoded_primary_and_secondary_frames() -> None:
    source = (ROOT / "scripts/docs/capture_browser_screenshots.py").read_text()
    assert "stabilize_visible_video_frames(page)" in source
    assert 'document.querySelectorAll(\'#merge-preview-layer video\')' in source
    assert 'result["primaryReady"]' in source
    assert 'result["secondaryReady"]' in source
    assert 'result["playerVisible"] and not result["secondaryVisible"]' in source


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

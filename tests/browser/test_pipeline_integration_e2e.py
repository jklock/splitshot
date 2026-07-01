from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

from tests.browser.helpers.export_verifier import assert_video_file


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.mark.slow
def test_practiscore_import_to_export_full_pipeline(
    synthetic_video_factory, tmp_path: Path
) -> None:
    """Import practiscore, configure overlay, export, verify output with ffprobe.

    Catches data-flow bugs where practiscore context fields
    (classification, division, competitor_name, competitor_place, stage_number)
    are lost between import and export or cleared during export request handling.
    """
    primary_path = Path(
        synthetic_video_factory(
            name="pipeline-practiscore",
            duration_ms=3000,
            beep_ms=500,
            shot_times_ms=[800, 1200, 1600],
        )
    )
    practiscore_path = EXAMPLES_DIR / "IDPA" / "IDPA.csv"

    controller = ProjectController()
    controller.load_primary_video(str(primary_path))
    controller.import_practiscore_file(str(practiscore_path), source_name=practiscore_path.name)
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
        classification="UN",
        division="CO",
    )

    assert controller.project.scoring.classification == "UN"
    assert controller.project.scoring.division == "CO"
    assert controller.project.scoring.competitor_name == "John Klockenkemper"
    assert controller.project.scoring.competitor_place == 4
    assert controller.project.scoring.stage_number == 2

    controller.project.overlay.position = "top"
    controller.project.overlay.badge_size = "XL"
    controller.project.overlay.show_score = True
    controller.project.overlay.show_timer = True
    controller.project.overlay.show_shots = True

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)

    try:
        output_path = tmp_path / "practiscore-export.mp4"
        _post_json(f"{server.url}api/export", {"path": str(output_path)})

        assert output_path.exists(), f"Export file not found: {output_path}"
        assert output_path.stat().st_size > 0, f"Export file is empty: {output_path}"
        info = assert_video_file(str(output_path), min_duration_s=1.0)
        assert info.get("codec", "").lower() in {"h264", "h.264", "libx264", "avc1"}, (
            f"Expected H.264, got {info.get('codec', 'unknown')}"
        )

        state = _get_json(f"{server.url}api/state")
        scoring = state["project"]["scoring"]
        assert scoring["classification"] == "UN"
        assert scoring["division"] == "CO"
        assert scoring["competitor_name"] == "John Klockenkemper"
        assert scoring["competitor_place"] == 4
        assert scoring["stage_number"] == 2
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_resolution_settings_applied(synthetic_video_factory, tmp_path: Path) -> None:
    """Verify setting target_width/target_height via API produces output at that resolution."""
    primary_path = Path(
        synthetic_video_factory(
            name="resolution-test",
            duration_ms=2000,
            resolution=(1920, 1080),
        )
    )

    controller = ProjectController()
    controller.load_primary_video(str(primary_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)

    try:
        _post_json(
            f"{server.url}api/export/settings",
            {
                "target_width": 1280,
                "target_height": 720,
            },
        )
        output_path = tmp_path / "resolution-export.mp4"
        _post_json(f"{server.url}api/export", {"path": str(output_path)})

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        info = assert_video_file(
            str(output_path),
            min_duration_s=0.5,
            expected_width=1280,
            expected_height=720,
        )
        assert info["width"] == 1280, f"Expected width 1280, got {info.get('width')}"
        assert info["height"] == 720, f"Expected height 720, got {info.get('height')}"
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_merge_pip_produces_valid_output(synthetic_video_factory, tmp_path: Path) -> None:
    """Merge (PIP) export produces a valid video with correct codec/duration."""
    primary_path = Path(
        synthetic_video_factory(name="merge-primary", duration_ms=3000, resolution=(640, 360))
    )
    merge_path = Path(
        synthetic_video_factory(name="merge-secondary", duration_ms=3000, resolution=(640, 360))
    )

    controller = ProjectController()
    controller.load_primary_video(str(primary_path))
    controller.add_merge_source(str(merge_path))
    controller.set_merge_enabled(True)
    controller.project.merge.layout = "pip"
    controller.project.merge.pip_size_percent = 35

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)

    try:
        output_path = tmp_path / "merge-export.mp4"
        _post_json(f"{server.url}api/export", {"path": str(output_path)})

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        info = assert_video_file(str(output_path), min_duration_s=1.0)
        assert info.get("codec", "").lower() in {"h264", "h.264", "libx264", "avc1"}
        assert info.get("width", 0) > 0
        assert info.get("height", 0) > 0
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_combined_practiscore_merge_overlay(synthetic_video_factory, tmp_path: Path) -> None:
    """Combined: practiscore scoring + merge + overlay -> export -> verify.

    Exercises the full workflow a user would complete for a real match stage.
    """
    primary_path = Path(
        synthetic_video_factory(
            name="combined-primary",
            duration_ms=3000,
            shot_times_ms=[800, 1400, 2200],
        )
    )
    merge_path = Path(
        synthetic_video_factory(
            name="combined-secondary",
            duration_ms=3000,
            shot_times_ms=[900, 1500, 2300],
        )
    )
    practiscore_path = EXAMPLES_DIR / "IDPA" / "IDPA.csv"

    controller = ProjectController()
    controller.load_primary_video(str(primary_path))
    controller.import_practiscore_file(str(practiscore_path), source_name=practiscore_path.name)
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
        classification="UN",
        division="CO",
    )
    controller.add_merge_source(str(merge_path))
    controller.set_merge_enabled(True)
    controller.project.merge.layout = "pip"
    controller.project.merge.pip_size_percent = 35

    controller.project.overlay.position = "top"
    controller.project.overlay.badge_size = "XL"
    controller.project.overlay.show_score = True
    controller.project.overlay.show_timer = True
    controller.project.overlay.show_shots = True
    controller.project.overlay.style_type = "bubble"

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)

    try:
        output_path = tmp_path / "combined-export.mp4"
        _post_json(f"{server.url}api/export", {"path": str(output_path)})

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        info = assert_video_file(str(output_path), min_duration_s=1.0)
        assert info.get("codec", "").lower() in {"h264", "h.264", "libx264", "avc1"}

        state = _get_json(f"{server.url}api/state")
        scoring = state["project"]["scoring"]
        assert scoring["classification"] == "UN", f"Expected UN, got {scoring['classification']}"
        assert scoring["division"] == "CO", f"Expected CO, got {scoring['division']}"
        assert scoring["competitor_name"] == "John Klockenkemper"
        assert scoring["competitor_place"] == 4
        assert scoring["stage_number"] == 2
        assert state["project"]["merge"]["enabled"] is True
        assert state["project"]["merge"]["layout"] == "pip"
    finally:
        server.shutdown()

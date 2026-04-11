from __future__ import annotations

from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_local_first_left_rail_shell() -> None:
    html = (STATIC_ROOT / "index.html").read_text()

    assert 'class="rail"' in html
    assert 'data-page="open"' in html
    assert 'data-page="review"' in html
    assert 'data-page="timing"' in html
    assert 'data-page="edit"' in html
    assert 'data-page="merge"' in html
    assert 'data-page="overlay"' in html
    assert 'data-page="scoring"' in html
    assert 'data-page="layout"' in html
    assert 'data-page="export"' in html
    assert "Choose Primary Video" in html
    assert "Choose Secondary Video" in html
    assert "upload" not in html.lower()


def test_browser_ui_exposes_video_overlay_and_scoring_controls() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'id="primary-file-input" type="file"' in html
    assert 'id="secondary-file-input" type="file"' in html
    assert 'id="primary-video" controls' in html
    assert 'id="live-overlay"' in html
    assert 'id="score-layer"' in html
    assert 'id="overlay-position"' in html
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="scoring-preset"' in html
    assert "/api/files/primary" in js
    assert "/api/files/secondary" in js
    assert "/api/scoring/profile" in js
    assert "/api/scoring/position" in js
    assert "/api/sync" in js


def test_browser_ui_uses_hard_edged_contiguous_tool_shell() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()

    assert "border-radius: 0;" in css
    assert "border-radius: 8px" not in css
    assert "border-radius: 9px" not in css
    assert "border-radius: 10px" not in css
    assert ".page.active {\n  display: grid;\n  gap: 0;" in css
    assert ".panel-grid {\n  display: grid;\n  gap: 0;" in css
    assert ".metric-grid {\n  display: grid;\n  gap: 0;" in css

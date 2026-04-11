from __future__ import annotations

from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_review_first_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'class="tool-rail"' in html
    assert 'class="review-grid"' in html
    assert 'class="review-stack"' in html
    assert 'class="inspector"' in html
    assert 'data-tool="review"' in html
    assert 'data-tool="timing"' in html
    assert 'data-tool="edit"' in html
    assert 'data-tool="scoring"' in html
    assert 'data-tool="overlay"' in html
    assert 'data-tool="merge"' in html
    assert 'data-tool="layout"' in html
    assert 'data-tool="export"' in html
    assert "<span>🍎</span><b>Review</b>" in html
    assert "<span>🍎</span><b>Score</b>" in html
    assert "Open Stage Video" in html
    assert html.count("Open Stage Video") == 1
    assert "Local review cockpit" not in html
    assert "Start here" not in html
    assert "SplitShot analyzes" not in html
    assert "No cloud transfer" not in html
    assert "upload" not in html.lower()


def test_browser_ui_keeps_video_timeline_waveform_and_inspector_together() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'id="primary-video" controls' in html
    assert 'id="live-overlay"' in html
    assert 'id="score-layer"' in html
    assert 'id="timeline-strip"' in html
    assert 'id="waveform"' in html
    assert 'id="split-card-grid"' in html
    assert 'id="selected-shot-copy"' in html
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="scoring-preset"' in html
    assert "/api/files/primary" in js
    assert "/api/files/secondary" in js
    assert "setActiveTool" in js
    assert "setActivePage" not in js


def test_browser_ui_uses_hard_edged_contiguous_tool_shell() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()

    assert "border-radius: 0;" in css
    assert "border-radius: 8px" not in css
    assert "border-radius: 9px" not in css
    assert "border-radius: 10px" not in css
    assert ".review-grid {\n  display: grid;" in css
    assert ".button-grid {\n  display: grid;\n  gap: 0;" in css
    assert ".metrics-strip {\n  display: grid;" in css
    assert "grid-template-columns: 68px minmax(0, 1fr);" in css
    assert "font-family: -apple-system" in css
    assert "font-size: 13px;" in css

from __future__ import annotations

from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_review_first_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'class="tool-rail"' in html
    assert 'class="status-strip"' in html
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
    assert '<img class="rail-logo" src="/static/logo.png" alt="SplitShot" />' in html
    assert "<b>Review</b>" in html
    assert "<b>Score</b>" in html
    assert "🍎" not in html
    assert 'class="topbar"' not in html
    assert 'class="command-strip"' not in html
    assert 'class="empty-start"' not in html
    assert 'class="metrics-strip"' not in html
    assert 'class="sidebar-section sidebar-metrics"' not in html
    assert 'class="rail-action"' not in html
    assert "Open Stage Video" not in html
    assert "Add Second Angle" not in html
    assert "Refresh" not in html
    assert 'id="current-file"' in html
    assert 'id="selected-shot-panel"' in html
    assert "Local review cockpit" not in html
    assert "Start here" not in html
    assert "SplitShot analyzes" not in html
    assert "No cloud transfer" not in html
    assert "upload" not in html.lower()


def test_browser_ui_keeps_video_timeline_waveform_and_inspector_together() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert html.index('class="video-stage"') < html.index('class="waveform-panel"')
    assert html.index('class="waveform-panel"') < html.index('class="inspector"')
    assert 'id="primary-video" controls' in html
    assert 'id="live-overlay"' in html
    assert 'id="score-layer"' in html
    assert 'id="timeline-strip"' in html
    assert 'id="waveform"' in html
    assert 'id="expand-waveform"' in html
    assert 'data-waveform-mode="select"' in html
    assert 'data-waveform-mode="add"' in html
    assert 'data-waveform-mode="beep"' in html
    assert 'id="waveform-shot-list"' in html
    assert 'id="timing-workbench"' in html
    assert 'id="expand-timing"' in html
    assert 'id="split-card-grid"' in html
    assert 'id="selected-shot-copy"' in html
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="scoring-preset"' in html
    assert "/api/files/primary" in js
    assert "/api/files/secondary" in js
    assert "/api/activity" in js
    assert "handleWaveformPointerDown" in js
    assert "handleWaveformPointerMove" in js
    assert "handleKeyboardEdit" in js
    assert "empty-start" not in js
    assert "setActiveTool" in js
    assert "setActivePage" not in js


def test_browser_ui_uses_hard_edged_contiguous_tool_shell() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()

    assert "border-radius: 0;" in css
    assert "border-radius: 8px" not in css
    assert "border-radius: 9px" not in css
    assert "border-radius: 10px" not in css
    assert "html,\nbody {\n  height: 100%;" in css
    assert "overflow: hidden;" in css
    assert ".review-grid {\n  display: grid;" in css
    assert ".button-grid {\n  display: grid;\n  gap: 0;" in css
    assert ".status-strip {\n  align-items: center;" in css
    assert ".command-strip" not in css
    assert ".empty-start" not in css
    assert ".metrics-strip" not in css
    assert ".rail-action" not in css
    assert "grid-template-columns: 76px minmax(0, 1fr);" in css
    assert "grid-template-rows: 32px minmax(0, 1fr);" in css
    assert "grid-template-rows: minmax(320px, 1fr) 206px;" in css
    assert ".cockpit.waveform-expanded .review-grid" in css
    assert ".cockpit.timing-expanded .timing-workbench" in css
    assert "font-family: -apple-system" in css
    assert "font-size: 13px;" in css


def test_browser_static_logo_is_packaged() -> None:
    assert (STATIC_ROOT / "logo.png").is_file()

"""Verify v107 multi-stage UI elements exist in static browser sources."""

from __future__ import annotations

from pathlib import Path

STATIC_ROOT = Path("src/splitshot/browser/static")


def test_media_and_queue_nav_buttons_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'data-tool="media"' in html
    assert 'data-tool="queue"' in html
    assert "<b>Media</b>" in html
    assert "<b>Queue</b>" in html


def test_media_and_queue_pane_containers_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="media-pane"' in html
    assert 'id="queue-pane"' in html
    assert 'data-tool-pane="media"' in html
    assert 'data-tool-pane="queue"' in html


def test_add_to_queue_button_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="add-to-queue"' in html
    assert "Add To Queue" in html


def test_media_pane_js_exists():
    media_js = STATIC_ROOT / "panes" / "media-pane.js"
    assert media_js.exists()
    source = media_js.read_text()
    assert "createMediaPane" in source
    assert "selectStage" in source
    assert "importPrimaryMedia" in source
    assert "importAddedMedia" in source
    assert "renderStageRow" in source


def test_queue_pane_js_exists():
    queue_js = STATIC_ROOT / "panes" / "queue-pane.js"
    assert queue_js.exists()
    source = queue_js.read_text()
    assert "createQueuePane" in source
    assert "addToQueue" in source
    assert "applySettingsToAll" in source
    assert "processAll" in source
    assert "processIntoOneFile" in source
    assert "queueStatusBadge" in source


def test_app_js_imports_media_and_queue():
    app_source = (STATIC_ROOT / "app.js").read_text()
    assert 'createMediaPane' in app_source
    assert 'createQueuePane' in app_source
    assert 'media-pane.js' in app_source
    assert 'queue-pane.js' in app_source


def test_app_js_registers_valid_tool_ids():
    app_source = (STATIC_ROOT / "app.js").read_text()
    assert '"media"' in app_source
    assert '"queue"' in app_source


def test_app_js_creates_pane_instances():
    app_source = (STATIC_ROOT / "app.js").read_text()
    assert "mediaPane = createMediaPane" in app_source
    assert "queuePane = createQueuePane" in app_source


def test_app_js_renders_panes_on_refresh():
    app_source = (STATIC_ROOT / "app.js").read_text()
    assert "mediaPane.render()" in app_source
    assert "queuePane.render()" in app_source


def test_shell_runtime_wires_add_to_queue():
    shell_source = (STATIC_ROOT / "lib" / "shell-runtime.js").read_text()
    assert '"add-to-queue"' in shell_source
    assert "/api/project/queue/add" in shell_source

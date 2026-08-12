"""Verify v107 multi-stage UI elements exist in static browser sources."""

from __future__ import annotations

from pathlib import Path

STATIC_ROOT = Path("src/splitshot/browser/static")


def test_media_and_queue_nav_buttons_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'data-tool="media"' in html
    assert 'data-tool="queue"' in html
    assert "Media</button>" in html
    assert "Queue</button>" in html


def test_media_and_queue_pane_containers_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="media-pane"' in html
    assert 'id="queue-pane"' in html
    assert 'data-tool-pane="media"' in html
    assert 'data-tool-pane="queue"' in html


def test_media_pane_js_exists():
    media_js = STATIC_ROOT / "panes" / "media-pane.js"
    assert media_js.exists()
    source = media_js.read_text()
    assert "createMediaPane" in source
    assert "selectStage" in source
    assert "renderActiveStageSection" in source
    assert "renderStagesSection" in source
    assert "createStage" in source
    assert "renderInventoryFileRow" in source
    assert "media-add-stage-full" in source


def test_queue_pane_js_exists():
    queue_js = STATIC_ROOT / "panes" / "queue-pane.js"
    assert queue_js.exists()
    source = queue_js.read_text()
    assert "createQueuePane" in source
    assert "updateQueueMembership" in source
    assert "applySettingsToQueued" not in source
    assert "processAll" in source
    assert "processIntoOneFile" in source
    assert "queueStatusLabel" in source
    assert "Process Queue" in source
    assert "Process as One File" in source
    assert "queue-apply-all-btn" not in source
    assert "queue-stage-card" in source
    assert "visibleQueueEntries" in source


def test_trim_sync_pane_js_exists():
    trim_js = STATIC_ROOT / "panes" / "trim-sync-pane.js"
    assert trim_js.exists()
    source = trim_js.read_text()
    assert "createTrimSyncPane" in source
    assert "trim-source-card" in source
    assert "trim-global-row" in source


def test_app_js_imports_media_and_queue():
    app_source = (STATIC_ROOT / "app.js").read_text()
    assert "createMediaPane" in app_source
    assert "createQueuePane" in app_source
    assert "media-pane.js" in app_source
    assert "queue-pane.js" in app_source


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


def test_queue_pane_wires_add_to_queue():
    queue_source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "/api/project/queue/add" in queue_source


def test_queue_apply_all_route_remains_for_compatibility_without_ui_control():
    server_source = Path("src/splitshot/browser/server.py").read_text()
    queue_source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert '"/api/project/queue/apply-all"' in server_source
    assert "/api/project/queue/apply-all" not in queue_source

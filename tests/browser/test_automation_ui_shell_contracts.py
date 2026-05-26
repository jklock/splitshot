from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "index.html"
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"
MATCH_VIEW_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "views" / "match-view.js"
SERVER_PY = REPO_ROOT / "src" / "splitshot" / "browser" / "server.py"


def _extract_ui_routes(app_js_text: str) -> set[str]:
    pattern = re.compile(r'callApi\s*\(\s*"(/api/[^"]+)"')
    return set(pattern.findall(app_js_text))


def _extract_server_routes(server_py_text: str) -> set[str]:
    routes = set()
    route_map_pattern = re.compile(r'"(/api/[^"]+)"\s*:\s*(?:\(|self\._|\w)')
    routes.update(route_map_pattern.findall(server_py_text))
    route_map_pattern2 = re.compile(r'"(/api/[^"]+)"\s*:\s*\(')
    routes.update(route_map_pattern2.findall(server_py_text))
    route_map_pattern3 = re.compile(r'"(/api/[^"]+)"\s*:\s*self\._')
    routes.update(route_map_pattern3.findall(server_py_text))
    path_pattern = re.compile(r'self\.path\s*==\s*"(/api/[^"]+)"')
    routes.update(path_pattern.findall(server_py_text))
    get_pattern = re.compile(r'request_path\s*==\s*"(/api/[^"]+)"')
    routes.update(get_pattern.findall(server_py_text))
    return routes


def test_automation_shell_exposes_three_splitshot_surfaces() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    source = APP_JS.read_text(encoding="utf-8")
    assert 'data-surface="single"' in html
    assert 'data-surface="multi"' in html
    assert 'data-surface="library"' in html
    assert html.count('data-shell-family="stage-workspace"') == 3
    assert 'data-shell-view="stage"' in html
    assert 'data-shell-view="match"' in html
    assert 'data-shell-view="library"' in html
    assert "Stage Video Edit" in html
    assert "Match Video Edit" in html
    assert "Performance Library" in html
    assert "Match Recap" in html
    assert "Stage Composite" in html
    assert "Video &amp; Data" in html
    assert "Run Padding" in html
    assert "Overlay Data" in html
    assert "Aspect Ratio / Framing" in html
    assert "Stage Recipe" not in html
    assert 'window.localStorage.getItem("splitshot.activeSurface")' in source
    assert 'callApi("/api/output-profiles/list",' in source
    assert 'callApi("/api/workspace/stage/clip/list", { stage_id: stageId })' in source
    assert 'callApi("/api/angle/director/plan"' in source
    assert '"/api/library/list"' in source
    assert "Review Source" in html
    assert "Shared Defaults" in html
    assert "Stage Overrides" in html
    assert "function workspaceShell(viewName) {" in source
    assert '[data-shell-family="stage-workspace"][data-shell-view="${viewName}"]' in source
    assert 'const shell = workspaceShell(viewName);' in source
    assert 'document.querySelector(".match-workspace-shell")' not in source
    assert 'document.querySelector(".library-workspace-shell")' not in source
    assert 'callApi("/api/workspace/defaults"' in source
    assert 'callApi("/api/workspace/stage/override"' in source


def test_non_landing_views_avoid_emoji_and_use_compact_full_width_workspaces() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    landing_start = html.index('<div id="view-landing"')
    landing_end = html.index('<div id="view-stage"', landing_start)
    view_root_start = html.index('<div id="view-root">')
    non_landing_html = html[view_root_start:landing_start] + html[landing_end:]
    for functional_glyph in ["⚙", "🔒", "🔓", "◀", "▶"]:
        non_landing_html = non_landing_html.replace(functional_glyph, "")
    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    assert not emoji_pattern.search(non_landing_html)
    assert "<h2>Match Video Edit</h2>" not in non_landing_html
    assert "<h2>Performance Library</h2>" not in non_landing_html
    assert 'class="status-bar workspace-status-bar" aria-label="Match workspace status"' in html
    assert 'class="status-bar workspace-status-bar" aria-label="Performance library status"' in html
    layout_css = (
        REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "styles" / "layout.css"
    ).read_text(encoding="utf-8")
    assert ".match-workspace {\n  width: 100%;" in layout_css
    assert ".library-workspace {\n  width: 100%;" in layout_css
    assert ".view-match {\n  background: #13151a;\n  padding: 0;" in layout_css
    assert ".view-library {\n  background: #0f1115;\n  padding: 0;" in layout_css


def test_match_shell_contract_keeps_preview_tiles_and_pinned_lower_pane() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    match_view = MATCH_VIEW_JS.read_text(encoding="utf-8")

    assert 'aria-label="Match stage selection and lower detail pane"' in html
    assert 'class="workspace-lower-pane" aria-label="Selected stage information"' in html
    assert 'id="match-stage-detail-panel"' in html
    assert 'id="match-stage-workflow-panel"' in html
    assert '<video class="match-stage-preview-video"' in match_view
    assert "The selected stage stays pinned while you move between defaults, overrides, recap, composite, and export." in match_view


def test_ui_routes_are_registered_on_server() -> None:
    app_js_text = APP_JS.read_text(encoding="utf-8")
    server_py_text = SERVER_PY.read_text(encoding="utf-8")
    ui_routes = _extract_ui_routes(app_js_text)
    server_routes = _extract_server_routes(server_py_text)
    assert "/api/workspace/setup-once/apply" not in ui_routes, (
        "Expected /api/workspace/setup-once/apply to be removed from UI routes"
    )
    assert "/api/workspace/defaults/reset" in server_routes, (
        "Expected /api/workspace/defaults/reset to be registered in server.py"
    )
    known_unregistered: set[str] = set()
    for route in known_unregistered:
        assert route in ui_routes, f"Expected {route} in UI routes but not found"
        assert route not in server_routes, f"Expected {route} to be unregistered on server, but it is registered"
    missing = ui_routes - server_routes
    real_missing = {
        r for r in missing
        if not r.endswith("/") and "${" not in r and "{" not in r and "+" not in r
    }
    real_missing = real_missing - known_unregistered
    assert not real_missing, (
        f"UI calls routes not registered in server.py: {sorted(real_missing)}"
    )


def test_critical_routes_are_registered() -> None:
    server_py_text = SERVER_PY.read_text(encoding="utf-8")
    server_routes = _extract_server_routes(server_py_text)
    required_routes = {
        "/api/workspace/apply-from-first",
        "/api/workspace/apply-from-first/preview",
        "/api/workspace/defaults/reset",
        "/api/library/backup/create",
        "/api/library/backup/restore",
        "/api/output-profiles/list",
        "/api/output-profiles/create",
        "/api/output-profiles/update",
        "/api/output-profiles/delete",
        "/api/output-profiles/render",
        "/api/workspace/stage/clip/list",
        "/api/workspace/stage/clip/add",
        "/api/workspace/stage/clip/update",
        "/api/workspace/stage/clip/remove",
        "/api/angle/align",
        "/api/angle/director/plan",
        "/api/angle/director/generate",
        "/api/angle/director/override",
        "/api/audio/mix",
        "/api/library/list",
        "/api/library/filter",
        "/api/library/stage/open",
        "/api/library/match/open",
        "/api/landing/recent",
        "/api/library/tags/update",
        "/api/library/notes/update",
        "/api/library/export/csv",
        "/api/library/export/json",
        "/api/workspace/export",
        "/api/workspace/recap/render",
    }
    missing = required_routes - server_routes
    assert not missing, f"Required routes missing from server.py: {sorted(missing)}"


def test_backup_handlers_are_not_nested_inside_setup_once_handler() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    backup_create_index = source.index('$("library-backup-create")')
    backup_restore_index = source.index('$("library-backup-restore")')
    setup_once_index = source.index('$("setup-once-apply")')
    assert backup_create_index < setup_once_index
    assert backup_restore_index < setup_once_index


def test_stage_composite_routes_are_registered() -> None:
    """Every stage composite route must be in server.py route table."""
    import ast
    import inspect
    from splitshot.browser import server

    source = inspect.getsource(server)
    routes_found: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/api/"):
            routes_found.add(node.value)

    composite_routes: set[str] = {
        "/api/workspace/stage/clip/list",
        "/api/workspace/stage/clip/add",
        "/api/workspace/stage/clip/update",
        "/api/workspace/stage/clip/remove",
        "/api/angle/align",
        "/api/angle/director/plan",
        "/api/angle/director/generate",
        "/api/angle/director/override",
    }
    missing = composite_routes - routes_found
    assert not missing, f"Stage composite routes not found in server source: {missing}"

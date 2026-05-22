from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "index.html"
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"


def test_automation_shell_exposes_three_splitshot_surfaces() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    source = APP_JS.read_text(encoding="utf-8")

    assert 'data-surface="single"' in html
    assert 'data-surface="multi"' in html
    assert 'data-surface="library"' in html
    assert "Stage Video Edit" in html
    assert "Match Video Edit" in html
    assert "Performance Library" in html
    assert "Match Recap" in html
    assert "Stage Composite" in html
    assert "Trim Dead Time" in html
    assert "Shot Data on Screen" in html

    assert 'window.localStorage.getItem("splitshot.activeSurface")' in source
    assert 'callApi("/api/output-profiles/list", {})' in source
    assert 'callApi("/api/workspace/stage/clip/list", { stage_id: stageId })' in source
    assert 'callApi("/api/angle/director/plan"' in source
    assert 'callApi("/api/library/list", {})' in source
    assert "Review Source" in html
    assert "Shared Defaults" in html
    assert "Stage Overrides" in html
    assert 'callApi("/api/workspace/defaults"' in source
    assert 'callApi("/api/workspace/stage/override"' in source


def test_non_landing_views_avoid_emoji_and_use_compact_full_width_workspaces() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    landing_start = html.index('<div id="view-landing"')
    landing_end = html.index('<div id="view-stage"', landing_start)
    # Exclude shell header (shared across all views) from emoji check
    view_root_start = html.index('<div id="view-root">')
    non_landing_html = html[view_root_start:landing_start] + html[landing_end:]
    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

    assert not emoji_pattern.search(non_landing_html)
    assert "<h2>Match Video Edit</h2>" not in non_landing_html
    assert "<h2>Performance Library</h2>" not in non_landing_html
    assert 'class="workspace-action-bar" aria-label="Match workspace actions"' in html
    assert 'class="workspace-action-bar" aria-label="Performance library actions"' in html

    layout_css = (
        REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "styles" / "layout.css"
    ).read_text(encoding="utf-8")
    assert ".match-workspace {\n  width: 100%;" in layout_css
    assert ".library-workspace {\n  width: 100%;" in layout_css
    assert ".view-match {\n  background: #13151a;\n  padding: 0;" in layout_css
    assert ".view-library {\n  background: #0f1115;\n  padding: 0;" in layout_css

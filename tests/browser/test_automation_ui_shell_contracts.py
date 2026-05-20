from __future__ import annotations

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
    assert "Single Video" in html
    assert "Multi Video" in html
    assert "Performance Library" in html
    assert "Match Recap" in html
    assert "Stage Composite" in html
    assert "Run Window" in html
    assert "Metric Captions" in html

    assert 'window.localStorage.getItem("splitshot.activeSurface")' in source
    assert 'callApi("/api/output-profiles/list", {})' in source
    assert 'callApi("/api/workspace/stage/clip/list", { stage_id: stageId })' in source
    assert 'callApi("/api/angle/director/plan"' in source
    assert 'callApi("/api/library/list", {})' in source


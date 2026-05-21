from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "index.html"
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"
LANDING_CSS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "styles" / "landing.css"


def test_landing_page_html_present() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="landing-page"' in html
    assert 'class="landing-hero"' in html
    assert 'class="landing-cards"' in html
    assert 'class="landing-card"' in html
    assert 'class="landing-recent"' in html
    assert 'id="landing-recent-list"' in html
    assert 'class="landing-quick-start"' in html
    assert 'class="landing-footer"' in html


def test_landing_page_three_entry_cards() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert html.count('class="landing-card"') == 3
    assert "Stage Video Edit" in html
    assert "Match Video Edit" in html
    assert "Performance Library" in html


def test_landing_page_surface_buttons_renamed() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "Stage Video Edit" in html
    assert "Match Video Edit" in html
    assert ">Single Video<" not in html
    assert ">Multi Video<" not in html


def test_landing_page_home_button() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="surface-go-home"' in html


def test_landing_page_css_exists() -> None:
    assert LANDING_CSS.exists()
    css = LANDING_CSS.read_text(encoding="utf-8")

    assert ".landing-card" in css
    assert ".landing-hero" in css
    assert "#landing-page" in css
    assert ".landing-footer" in css


def test_landing_page_has_visited_logic() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "splitshot.hasVisited" in source
    assert "first" in source and "visit" in source.lower()

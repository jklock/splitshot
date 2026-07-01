from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _ensure_project_with_primary_and_merge(
    page, primary_path: Path, merge_path: Path, project_name: str
) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(primary_path.parent / project_name)
        page.evaluate(f"() => createNewProject({json.dumps(project_dir)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")

    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        page.locator("#primary-file-input").set_input_files(str(primary_path))
        page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

    merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
    if merge_count == 0:
        page.locator("#merge-media-input").set_input_files(str(merge_path))
        page.wait_for_function("() => (state?.project?.merge_sources || []).length > 0")


def test_compose_pane_renders_merge_sources(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-primary"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)
                assert page.evaluate("activeTool") == "merge"

                assert page.locator(".merge-media-card").count() >= 1
                assert page.locator("#merge-enabled").count() == 1
                assert page.locator("#merge-layout").count() == 1
                assert page.locator("#pip-size").count() == 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_merge_enabled_toggle(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-toggle"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-toggle-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-toggle.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)

                initial = page.evaluate("() => Boolean(state?.project?.merge?.enabled)")
                page.locator("#merge-enabled").click()
                page.wait_for_timeout(100)
                toggled = page.evaluate("() => Boolean(state?.project?.merge?.enabled)")
                assert toggled != initial
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_layout_select_changes_value(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-layout"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-layout-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-layout.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)

                page.locator("#merge-layout").select_option("above_below")
                page.wait_for_timeout(100)
                later = page.evaluate("() => state?.project?.merge?.layout || 'side_by_side'")
                assert later == "above_below"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_no_sync_analysis_buttons_in_merge(synthetic_video_factory) -> None:
    from pathlib import Path as P

    merge_pane_source = (
        P(__file__).resolve().parents[2] / "src/splitshot/browser/static/panes/merge-pane.js"
    ).read_text()
    assert "Re-run beep sync" not in merge_pane_source
    assert "Analyze beep sync" not in merge_pane_source
    assert "supports_sync_analysis" not in merge_pane_source
    assert "trim-analyze-btn" not in merge_pane_source


def test_compose_pip_preview_layer_renders_with_items(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-pip2", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-pip2-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-pip2.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                page.evaluate(
                    "() => { const cb = document.getElementById('merge-enabled'); if (cb) cb.checked = true; }"
                )
                page.evaluate(
                    "() => { const cb = document.getElementById('show-pip'); if (cb) cb.checked = true; }"
                )
                page.wait_for_timeout(100)

                page.locator("#merge-layout").select_option("pip")
                page.wait_for_timeout(200)

                page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
                page.wait_for_timeout(300)

                preview_items = page.locator("#merge-preview-layer .merge-preview-item")
                assert preview_items.count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_layout_change_updates_merge_state(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-layout2", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-layout2-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-layout2.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                assert page.locator("#merge-layout").count() == 1
                before = page.evaluate("() => state?.project?.merge?.layout || 'side_by_side'")

                page.locator("#merge-layout").select_option("above_below")
                page.wait_for_timeout(200)

                after = page.evaluate("() => state?.project?.merge?.layout || ''")
                assert after == "above_below"
                assert after != before

                assert page.locator(".media-add-stage-btn, #merge-media-list").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_per_source_size_changes_preview_dimensions(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-srcsize", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-srcsize-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-srcsize.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                page.evaluate(
                    "() => { const cb = document.getElementById('merge-enabled'); if (cb) cb.checked = true; }"
                )
                page.evaluate(
                    "() => { const cb = document.getElementById('show-pip'); if (cb) cb.checked = true; }"
                )
                page.wait_for_timeout(100)
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_timeout(400)

                assert page.locator(".merge-media-card").count() >= 1

                card = page.locator(".merge-media-card").first
                card.locator(".pane-toggle").click()
                page.wait_for_timeout(300)

                size_slider = page.locator('[data-merge-source-field="size"]').first
                assert size_slider.count() == 1

                size_before = size_slider.evaluate("el => el.value")
                size_slider.evaluate(
                    "el => { el.value = '65'; el.dispatchEvent(new Event('input', {bubbles: true})); }"
                )
                page.wait_for_timeout(100)
                size_slider.evaluate(
                    "el => { el.dispatchEvent(new Event('change', {bubbles: true})); }"
                )
                page.wait_for_timeout(500)

                source_state = page.evaluate(
                    "() => {"
                    "  const s = (state?.project?.merge_sources || [])[0];"
                    "  return s?.pip_size_percent ?? null;"
                    "}"
                )
                assert source_state is not None
                assert source_state != int(size_before)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_per_source_opacity_persists(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-srcop", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-srcop-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-srcop.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                opacity_before = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.opacity ?? 1"
                )

                page.evaluate(
                    "() => {"
                    "  const input = document.querySelector('[data-merge-source-field=\"opacity\"]');"
                    "  if (input) { input.value = '45'; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true})); }"
                    "}"
                )
                page.wait_for_timeout(500)

                opacity_after = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.opacity ?? 0"
                )
                assert opacity_after == pytest.approx(0.45, abs=0.01)
                assert opacity_after != opacity_before
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_per_source_position_x_persists(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-srcposx", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-srcposx-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-srcposx.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                pos_x_before = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.pip_x ?? 1"
                )

                page.evaluate(
                    "() => {"
                    "  const input = document.querySelector('[data-merge-source-field=\"x\"]');"
                    "  if (input) { input.value = '0.35'; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true})); }"
                    "}"
                )
                page.wait_for_timeout(500)

                pos_x_after = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.pip_x ?? 0"
                )
                assert float(pos_x_after) == pytest.approx(0.35, abs=0.01)
                assert pos_x_after != pos_x_before
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_per_source_position_y_persists(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-srcposy", beep_ms=400))
    merge_path = Path(synthetic_video_factory(name="compose-qa-srcposy-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-srcposy.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(300)

                pos_y_before = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.pip_y ?? 1"
                )

                page.evaluate(
                    "() => {"
                    "  const input = document.querySelector('[data-merge-source-field=\"y\"]');"
                    "  if (input) { input.value = '0.65'; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true})); }"
                    "}"
                )
                page.wait_for_timeout(500)

                pos_y_after = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.pip_y ?? 0"
                )
                assert float(pos_y_after) == pytest.approx(0.65, abs=0.01)
                assert pos_y_after != pos_y_before
            finally:
                browser.close()
    finally:
        server.shutdown()

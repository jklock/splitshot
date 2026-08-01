from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from tests.browser.helpers.video_test_helpers import create_project


def _open_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _prepare_stage(page, primary_path: Path, project_path: Path) -> str:
    create_project(page, str(project_path))
    page.evaluate("() => callApi('/api/project/stage/create', {})")
    page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
        str(primary_path),
    )
    page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
    return page.evaluate("state.project.active_stage_id")


def test_queue_pane_membership_and_status_are_visible(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-membership", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-membership.ssproj")
                page.locator("button[data-tool='queue']").click(force=True)
                page.locator(".queue-membership-btn").first.click()
                page.wait_for_function(
                    "(id) => state.project.queue.some((entry) => entry.stage_id === id)",
                    arg=stage_id,
                )
                card = page.locator(f'[data-queue-stage-id="{stage_id}"]')
                assert card.is_visible()
                assert "queued" in card.inner_text().lower()
                assert page.locator("#queue-process-btn").is_visible()
                assert page.locator("#queue-combined-btn").is_visible()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_uses_flat_og_controls_without_apply_settings_ui(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-controls", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-controls.ssproj")
                page.evaluate(
                    "(id) => callApi('/api/project/queue/add', { stage_id: id })", stage_id
                )
                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator("#queue-apply-all-btn").count() == 0
                assert page.locator("#queue-stage-select").count() == 0
                assert page.get_by_text("Match Stages", exact=True).is_visible()
                assert page.get_by_text("Process", exact=True).is_visible()
                assert page.get_by_role("button", name="Process Queue", exact=True).is_visible()
                assert page.get_by_role("button", name="Process as One File", exact=True).is_visible()
                assert page.locator(".queue-status-pill").count() == 0
                assert page.locator(".queue-status-text").count() == 1
                assert page.locator(".queue-stage-list").is_visible()
                assert page.locator(".queue-stage-toggle").count() == 0
                assert page.get_by_role("button", name="Show Output Folder").is_enabled()
                assert page.get_by_role("button", name="Show Log").is_visible()
                assert page.locator("#queue-include-intro").is_disabled()
                assert page.locator("#queue-include-outro").is_disabled()
                assert page.locator("#queue-combined-btn").evaluate(
                    "button => getComputedStyle(button).backgroundColor"
                ) == "rgb(57, 208, 111)"
                assert page.locator("#queue-fade-in").input_value() == "0.5"
                assert page.locator("#queue-fade-out").input_value() == "0.5"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_intro_outro_pane_previews_match_overlay_and_queue_include_choice(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="intro-pane-preview", beep_ms=250))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(intro.parent / "intro-pane.ssproj"))
                page.evaluate(
                    "(path) => callApi('/api/project/in-out/media', { kind: 'intro', path })",
                    str(intro),
                )
                page.evaluate(
                    "() => callApi('/api/project/intro-outro/overlay', { kind: 'intro', text_boxes: [{ enabled: true, source: 'match_summary', summary_metric_ids: ['stage_count'], quadrant: 'top_right', text: '', background_color: '#000000', text_color: '#ffffff', opacity: 0.9, font_size: 28, font_bold: true }] })"
                )
                intro_nav = page.locator("button[data-tool='intro-outro']")
                queue_nav = page.locator("button[data-tool='queue']")
                assert intro_nav.inner_text() == "In / Out"
                assert intro_nav.evaluate("node => node.compareDocumentPosition(document.querySelector(\"button[data-tool='queue']\")) & Node.DOCUMENT_POSITION_FOLLOWING")
                intro_nav.click(force=True)
                assert page.get_by_role("heading", name="Intro / Outro", exact=True).is_visible()
                assert page.get_by_role("button", name="Intro", exact=True).is_visible()
                assert page.get_by_role("button", name="Outro", exact=True).is_visible()
                assert page.locator("#intro-outro-fade-in").input_value() == "0.5"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.5"
                page.locator("#intro-outro-fade-in").fill("0.7")
                page.locator("#intro-outro-fade-in").dispatch_event("change")
                page.wait_for_function("() => state.project.intro_clip.fade_in_s === 0.7")
                page.locator("#intro-outro-fade-out").fill("0.9")
                page.locator("#intro-outro-fade-out").dispatch_event("change")
                page.wait_for_function("() => state.project.intro_clip.fade_out_s === 0.9")
                page.get_by_role("button", name="Outro", exact=True).click()
                assert page.locator("#intro-outro-fade-in").input_value() == "0.5"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.5"
                page.locator("#intro-outro-fade-in").fill("1.1")
                page.locator("#intro-outro-fade-in").dispatch_event("change")
                page.wait_for_function("() => state.project.outro_clip.fade_in_s === 1.1")
                page.locator("#intro-outro-fade-out").fill("1.3")
                page.locator("#intro-outro-fade-out").dispatch_event("change")
                page.wait_for_function("() => state.project.outro_clip.fade_out_s === 1.3")
                page.get_by_role("button", name="Intro", exact=True).click()
                assert page.locator("#intro-outro-fade-in").input_value() == "0.7"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.9"
                page.wait_for_function("() => document.querySelector('#primary-video').src.includes('/media/intro')")
                assert page.locator(".intro-outro-preview-badge").inner_text() == "Stages 1"
                assert page.locator(".intro-outro-preview-badge").get_attribute(
                    "data-intro-outro-box-drag"
                ) == "true"
                assert page.get_by_role("button", name="Add Text Box").is_visible()
                assert page.get_by_role("button", name="Add Match Results").is_visible()

                card = page.locator(".intro-outro-box").first
                card.locator('[data-box-field="source"]').select_option("manual")
                card.locator('[data-box-field="text"]').fill("Stable intro title")
                card.locator('[data-box-field="text"]').dispatch_event("change")
                card.locator('[data-box-field="quadrant"]').select_option("custom")
                shape_control = card.locator('[data-box-field="style_type"]')
                shape_element = shape_control.element_handle()
                assert shape_element is not None
                shape_control.select_option("rounded")
                card.locator('[data-box-field="x"]').fill("0.21")
                page.wait_for_timeout(300)
                card.locator('[data-box-field="y"]').fill("0.73")
                card.locator('[data-box-field="y"]').dispatch_event("change")
                for field, value in {
                    "width": "320",
                    "height": "96",
                    "font_family": "Arial",
                    "font_size": "34",
                    "opacity": "62",
                }.items():
                    control = card.locator(f'[data-box-field="{field}"]')
                    control.fill(value)
                    control.dispatch_event("change")
                bold_control = card.locator('[data-box-field="font_bold"]')
                italic_control = card.locator('[data-box-field="font_italic"]')
                bold_control.click(force=True)
                assert bold_control.is_checked() is False
                italic_control.click(force=True)
                assert italic_control.is_checked() is True
                page.wait_for_function(
                    """() => {
                        const box = state?.project?.intro_clip?.overlay?.text_boxes?.[0];
                        return box?.text === 'Stable intro title'
                            && box?.quadrant === 'custom'
                            && box?.style_type === 'rounded'
                            && box?.x === 0.21
                            && box?.y === 0.73
                            && box?.width === 320
                            && box?.height === 96
                            && box?.font_size === 34
                            && box?.opacity === 0.62
                            && box?.font_bold === false
                            && box?.font_italic === true;
                    }"""
                )
                page.wait_for_timeout(500)
                assert shape_element.evaluate("element => element.isConnected") is True
                assert card.locator('[data-box-field="text"]').input_value() == "Stable intro title"
                assert card.locator('[data-box-field="x"]').input_value() == "0.21"
                assert card.locator('[data-box-field="y"]').input_value() == "0.73"

                badge = page.locator(".intro-outro-preview-badge")
                badge_box = badge.bounding_box()
                stage_box = page.locator("#video-stage").bounding_box()
                assert badge_box is not None
                assert stage_box is not None
                drag_x = min(stage_box["x"] + stage_box["width"] - 40, badge_box["x"] + 90)
                drag_y = max(stage_box["y"] + 40, badge_box["y"] - 70)
                page.mouse.move(
                    badge_box["x"] + (badge_box["width"] / 2),
                    badge_box["y"] + (badge_box["height"] / 2),
                )
                page.mouse.down()
                page.mouse.move(drag_x, drag_y, steps=8)
                page.mouse.up()
                page.wait_for_function(
                    """() => {
                        const box = state?.project?.intro_clip?.overlay?.text_boxes?.[0];
                        return box?.quadrant === 'custom' && box?.x !== 0.21 && box?.y !== 0.73;
                    }"""
                )

                queue_nav.click(force=True)
                assert page.locator("#queue-include-intro").is_enabled()
                assert page.locator("#queue-include-intro").is_checked()
                assert page.locator("#queue-include-outro").is_disabled()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_in_out_video_picker_updates_preview_and_queue_state(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="in-out-picker", beep_ms=250))

    def choose_video(
        kind: str, current: str | None, default_root: str | None = None
    ) -> str:
        assert kind == "in_out_media"
        return str(intro)

    server = BrowserControlServer(port=0, path_chooser=choose_video)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(intro.parent / "in-out-picker.ssproj"))
                page.locator("button[data-tool='intro-outro']").click(force=True)
                page.get_by_role("button", name="Select Video", exact=True).click()
                page.wait_for_function(
                    "() => Boolean(state?.project?.intro_clip?.asset?.path)"
                )
                assert page.locator(".intro-outro-file").inner_text() == intro.name
                assert "/media/intro" in page.locator("#primary-video").get_attribute("src")
                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator("#queue-include-intro").is_enabled()
                assert page.locator("#queue-include-intro").is_checked()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_in_out_video_picker_uses_packaged_native_bridge(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="in-out-native-picker", beep_ms=250))

    def unexpected_browser_picker(
        kind: str, current: str | None, default_root: str | None = None
    ) -> str:
        raise AssertionError(f"Browser path picker should not be used for {kind}")

    server = BrowserControlServer(port=0, path_chooser=unexpected_browser_picker)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.expose_function("pickInOutVideo", lambda: str(intro))
            page.add_init_script(
                "window.splitshot = { openInOutVideoDialog: () => window.pickInOutVideo() };"
            )
            page.goto(server.url, wait_until="domcontentloaded")
            try:
                create_project(page, str(intro.parent / "in-out-native-picker.ssproj"))
                page.locator("button[data-tool='intro-outro']").click(force=True)
                page.get_by_role("button", name="Select Video", exact=True).click()
                page.wait_for_function(
                    "() => Boolean(state?.project?.intro_clip?.asset?.path)"
                )
                assert page.locator(".intro-outro-file").inner_text() == intro.name
                assert "/media/intro" in page.locator("#primary-video").get_attribute("src")
            finally:
                browser.close()
    finally:
        server.shutdown()

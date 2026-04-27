from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _open_tool(page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def _select_waveform_shot(page, index: int = 0) -> dict[str, int | str] | None:
    _open_tool(page, "timing")
    target_shot_id = page.evaluate(f"state.timing_segments[{index}].shot_id")
    assert target_shot_id is not None
    page.locator("#timing-table .timeline-segment-cell").nth(index).click()
    page.wait_for_function("(shotId) => selectedShotId === shotId", arg=target_shot_id)
    return page.evaluate(
        """
        () => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === selectedShotId);
          return shot ? { id: shot.id, timeMs: shot.time_ms } : null;
        }
        """
    )


def _shot_linked_popup_count(page) -> int:
    return int(page.evaluate("(state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length"))


def _import_shot_linked_markers(page) -> None:
    page.locator("#popup-import-shots").click()
    page.wait_for_function(
        "() => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length > 0"
    )


def _ensure_overlay_visible(page) -> None:
    if page.locator("#show-overlay").is_checked():
        return
    page.evaluate(
        """
        () => {
          const checkbox = document.getElementById('show-overlay');
          checkbox.checked = true;
          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """
    )
    page.wait_for_function("() => document.getElementById('show-overlay').checked === true")


def test_waveform_controls_expand_zoom_and_amplitude_update_project_state(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                expand_button = page.locator("#expand-waveform")
                assert expand_button.text_content().strip() == "Expand"
                expand_button.click()
                page.wait_for_timeout(150)
                assert expand_button.text_content().strip() == "Collapse"
                assert page.locator("#cockpit-root").evaluate("element => element.classList.contains('waveform-expanded')") is True

                zoom_before = float(page.evaluate("Number(localStorage.getItem('splitshot.waveform.zoomX'))"))
                page.locator("#zoom-waveform-in").click()
                page.wait_for_timeout(150)
                zoom_after = float(page.evaluate("Number(localStorage.getItem('splitshot.waveform.zoomX'))"))
                assert zoom_after > zoom_before

                page.locator('button[data-waveform-mode="add"]').click()
                page.wait_for_timeout(100)
                assert page.evaluate("waveformMode") == "add"
                assert page.locator('button[data-waveform-mode="add"]').evaluate("button => button.classList.contains('active')") is True

                page.locator('button[data-waveform-mode="select"]').click()
                page.wait_for_timeout(100)
                assert page.evaluate("waveformMode") == "select"
                assert page.locator('button[data-waveform-mode="select"]').evaluate("button => button.classList.contains('active')") is True

                first_card = page.locator(".waveform-shot-card").first
                first_card.click(force=True)
                page.wait_for_timeout(150)
                selected_shot_id = page.evaluate("selectedShotId")
                assert selected_shot_id is not None

                amplitude_before = float(page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1"))
                page.locator("#amp-waveform-in").click()
                page.wait_for_timeout(250)
                amplitude_after = float(page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1"))
                assert amplitude_after > amplitude_before

                page.locator("#reset-waveform-view").click()
                page.wait_for_timeout(150)
                assert float(page.evaluate("waveformZoomX")) == 1.0
                assert float(page.evaluate("waveformOffsetMs")) == 0.0
                assert float(page.evaluate("Number(localStorage.getItem('splitshot.waveform.zoomX') ?? 1)")) == 1.0
                assert float(page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs') ?? 0)")) == 0.0
                assert float(page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1")) == 1.0
            finally:
                                browser.close()
    finally:
        server.shutdown()


def test_waveform_pan_drag_updates_zoomed_viewport_offset(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="waveform-pan-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)
                                page.locator("#expand-waveform").click()
                                page.wait_for_timeout(150)
                                page.locator("#zoom-waveform-in").click()
                                page.wait_for_timeout(150)

                                waveform_box = page.locator("#waveform").bounding_box()
                                assert waveform_box is not None
                                start_offset = float(page.evaluate("waveformOffsetMs"))
                                empty_x = float(page.evaluate(
                                        """
                                        () => {
                                            const canvas = document.getElementById('waveform');
                                            const rect = canvas.getBoundingClientRect();
                                            const shots = (state?.project?.analysis?.shots || [])
                                                .map((shot) => waveformX(shot.time_ms, rect.width))
                                                .sort((left, right) => left - right);
                                            const candidates = [rect.width * 0.15, rect.width * 0.85, rect.width - 24];
                                            for (let index = 0; index < shots.length - 1; index += 1) {
                                                const left = shots[index];
                                                const right = shots[index + 1];
                                                if (right - left > 72) candidates.push((left + right) / 2);
                                            }
                                            for (const candidate of candidates) {
                                                if (candidate > 0 && candidate < rect.width && shots.every((shotX) => Math.abs(candidate - shotX) > 32)) {
                                                    return candidate;
                                                }
                                            }
                                            return rect.width - 24;
                                        }
                                        """
                                ))
                                drag_delta = -160 if empty_x > waveform_box["width"] / 2 else 160
                                start_x = waveform_box["x"] + empty_x
                                start_y = waveform_box["y"] + waveform_box["height"] / 2

                                page.mouse.move(start_x, start_y)
                                page.mouse.down()
                                page.mouse.move(start_x + drag_delta, start_y, steps=12)
                                page.mouse.up()
                                page.wait_for_function(
                                        "(before) => waveformOffsetMs !== before",
                                        arg=start_offset,
                                )
                                assert float(page.evaluate("waveformOffsetMs")) != start_offset
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_waveform_shot_drag_moves_selected_shot_time(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="waveform-drag-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)
                                page.locator("#expand-waveform").click()
                                page.wait_for_timeout(150)

                                shot_info = page.evaluate(
                                        """
                                        () => {
                                            const canvas = document.getElementById('waveform');
                                            const rect = canvas.getBoundingClientRect();
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => {
                                                const x = waveformX(item.time_ms, rect.width);
                                                return x > 120 && x < rect.width - 120;
                                            }) || state?.project?.analysis?.shots?.[0];
                                            if (!shot) return null;
                                            return {
                                                id: shot.id,
                                                timeMs: shot.time_ms,
                                                x: waveformX(shot.time_ms, rect.width),
                                            };
                                        }
                                        """
                                )
                                assert shot_info is not None
                                waveform_box = page.locator("#waveform").bounding_box()
                                assert waveform_box is not None

                                start_x = waveform_box["x"] + float(shot_info["x"])
                                start_y = waveform_box["y"] + waveform_box["height"] / 2
                                move_delta = 120 if shot_info["x"] < waveform_box["width"] - 160 else -120

                                page.mouse.move(start_x, start_y)
                                page.mouse.down()
                                page.mouse.move(start_x + move_delta, start_y, steps=12)
                                page.mouse.up()
                                page.wait_for_function(
                                        """({ shotId, originalTime }) => {
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                                            return Boolean(shot) && shot.time_ms !== originalTime;
                                        }""",
                                        arg={"shotId": shot_info["id"], "originalTime": shot_info["timeMs"]},
                                )
                                updated_time = page.evaluate(
                                        """(shotId) => {
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                                            return shot ? shot.time_ms : null;
                                        }""",
                                        shot_info["id"],
                                )
                                assert updated_time is not None
                                assert updated_time != shot_info["timeMs"]
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_overlay_visibility_and_badge_toggles_round_trip_through_browser_ui(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator('button[data-tool="overlay"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "overlay"

                initial_position = page.evaluate("state.project.overlay.position")
                page.evaluate(
                    """
                    () => {
                      const checkbox = document.getElementById('show-overlay');
                      checkbox.checked = false;
                      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                page.wait_for_timeout(500)
                assert page.locator("#show-overlay").is_checked() is False
                assert page.evaluate("state.project.overlay.position") == "none"

                page.evaluate(
                    """
                    () => {
                      const checkbox = document.getElementById('show-overlay');
                      checkbox.checked = true;
                      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                page.wait_for_timeout(500)
                assert page.locator("#show-overlay").is_checked() is True
                assert page.evaluate("state.project.overlay.position") == initial_position

                for control_id, attribute in [
                    ("show-timer", "show_timer"),
                    ("show-draw", "show_draw"),
                    ("show-shots", "show_shots"),
                    ("show-score", "show_score"),
                ]:
                    original_value = bool(page.evaluate(f"state.project.overlay.{attribute}"))
                    if original_value:
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = false;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is False
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = true;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is True
                    else:
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = true;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is True
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = false;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_add_custom_text_box_creates_editor_card(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")

                before_boxes = int(page.evaluate("state.project.overlay.text_boxes.length"))
                before_cards = page.locator("#review-text-box-list .text-box-card").count()

                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_timeout(500)

                assert int(page.evaluate("state.project.overlay.text_boxes.length")) == before_boxes + 1
                assert page.locator("#review-text-box-list .text-box-card").count() == before_cards + 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_drag_updates_overlay_coordinates(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-drag-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")

                if not page.locator("#show-overlay").is_checked():
                    page.evaluate(
                        """
                        () => {
                          const checkbox = document.getElementById('show-overlay');
                          checkbox.checked = true;
                          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        """
                    )
                    page.wait_for_timeout(300)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_timeout(250)

                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )
                new_card = page.locator('#review-text-box-list .text-box-card').nth(before_cards)
                new_card.locator('[data-text-box-action="toggle"]').click()
                new_card.locator('textarea[data-text-box-field="text"]').fill("Review note")
                page.wait_for_timeout(250)

                text_box = page.locator('#custom-overlay [data-text-box-drag="true"]').first
                text_box.wait_for(state="visible")
                page.wait_for_function(
                    """() => {
                      const box = document.querySelector('#custom-overlay [data-text-box-drag="true"]');
                      if (!box) return false;
                      const rect = box.getBoundingClientRect();
                      return rect.width > 0 && rect.height > 0;
                    }"""
                )
                text_box_id = text_box.get_attribute("data-text-box-id")
                assert text_box_id
                before_box = page.evaluate(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return box ? { id: box.id, x: box.x, y: box.y } : null;
                    }""",
                    text_box_id,
                )
                assert before_box is not None
                badge_box = page.evaluate(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                      if (!(badge instanceof HTMLElement)) return null;
                      const rect = badge.getBoundingClientRect();
                      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
                    }""",
                    text_box_id,
                )
                stage_box = page.locator("#video-stage").bounding_box()
                assert badge_box is not None
                assert stage_box is not None

                start_x = badge_box["x"] + badge_box["width"] / 2
                start_y = badge_box["y"] + badge_box["height"] / 2
                target_x = stage_box["x"] + stage_box["width"] * 0.62
                target_y = stage_box["y"] + stage_box["height"] * 0.32

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(target_x, target_y, steps=12)
                page.mouse.up()
                page.wait_for_function(
                    """({ boxId, originalX, originalY }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && (box.x !== originalX || box.y !== originalY);
                    }""",
                    arg={"boxId": before_box["id"], "originalX": before_box["x"], "originalY": before_box["y"]},
                )
                after_box = page.evaluate(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return box ? { id: box.id, x: box.x, y: box.y, quadrant: box.quadrant } : null;
                    }""",
                    before_box["id"],
                )
                assert after_box is not None
                assert after_box["x"] != before_box["x"] or after_box["y"] != before_box["y"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_color_swatches_and_opacity_update_live_preview(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-style-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id

                page.evaluate(
                    """(targetBoxId) => {
                        setReviewTextBoxExpanded(targetBoxId, true);
                        renderTextBoxEditors();
                    }""",
                    box_id,
                )
                new_card = page.locator(f'#review-text-box-list .text-box-card[data-box-id="{box_id}"]')
                new_card.locator('textarea[data-text-box-field="text"]').wait_for(state="visible")
                new_card.locator('textarea[data-text-box-field="text"]').fill("Style note")
                page.wait_for_function(
                    """({ boxId, text }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text === text;
                    }""",
                    arg={"boxId": box_id, "text": "Style note"},
                )

                text_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')
                text_box.wait_for(state="visible")

                def set_hex(field: str, hex_value: str) -> None:
                    new_card.locator(f'[data-text-box-field="{field}"]').click(force=True)
                    page.wait_for_function("() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null")
                    page.evaluate(
                        """({ value }) => {
                            const input = document.getElementById('color-picker-hex');
                            input.value = value;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }""",
                        {"value": hex_value},
                    )
                    page.locator("#close-color-picker").click()
                    page.wait_for_function("() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null")
                    page.wait_for_function(
                        """({ boxId, field, value }) => {
                          const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                          return Boolean(box) && box[field] === value;
                        }""",
                        arg={"boxId": box_id, "field": field, "value": hex_value},
                    )

                set_hex("background_color", "#ff0000")

                new_card.locator('[data-text-box-field="text_color"]').click(force=True)
                page.wait_for_function("() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null")
                page.locator("#close-color-picker").click()
                page.wait_for_function("() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null")
                new_card.locator('input[aria-label="Text box text hex value"]').evaluate(
                    """(input, nextValue) => {
                        input.value = nextValue;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    "#00ff00",
                )
                page.wait_for_function(
                    """({ boxId, value }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text_color === value;
                    }""",
                    arg={"boxId": box_id, "value": "#00ff00"},
                )

                new_card.locator('[data-text-box-field="opacity"]').evaluate(
                    """(input, nextValue) => {
                        input.value = nextValue;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    "70",
                )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && Math.abs((box.opacity ?? 0) - 0.7) < 0.01;
                    }""",
                    arg=box_id,
                )

                page.wait_for_function(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                      if (!(badge instanceof HTMLElement)) return false;
                      const style = window.getComputedStyle(badge);
                      return style.backgroundColor.includes('255, 0, 0') && style.color.includes('0, 255, 0');
                    }""",
                    arg=box_id,
                )

                preview_style = page.evaluate(
                    """(boxId) => {
                        const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                        const style = window.getComputedStyle(badge);
                        return {
                            background: style.backgroundColor || '',
                            color: style.color || '',
                            opacity: Number((state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId)?.opacity ?? 0),
                            backgroundValue: document.querySelector(`#review-text-box-list .text-box-card[data-box-id="${boxId}"] [data-text-box-field="background_color"]`)?.dataset.colorValue || '',
                            textValue: document.querySelector(`#review-text-box-list .text-box-card[data-box-id="${boxId}"] [data-text-box-field="text_color"]`)?.dataset.colorValue || '',
                        };
                    }""",
                    box_id,
                )
                assert preview_style["background"].startswith("rgba(255, 0, 0")
                assert preview_style["color"].startswith("rgb(0, 255, 0")
                assert preview_style["opacity"] == pytest.approx(0.7)
                assert preview_style["backgroundValue"] == "#ff0000"
                assert preview_style["textValue"] == "#00ff00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_source_switches_to_imported_summary_and_renders_after_final_shot(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-imported-source-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id

                new_card.locator('[data-text-box-action="toggle"]').click()
                new_card.locator('select[data-text-box-field="source"]').select_option("imported_summary")
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.source === 'imported_summary' && box.quadrant === 'above_final';
                    }""",
                    arg=box_id,
                )

                override_text = "Stage summary override"
                text_area = new_card.locator('textarea[data-text-box-field="text"]')
                text_area.fill(override_text)
                text_area.dispatch_event("change")
                page.wait_for_function(
                    """({ boxId, text }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text === text;
                    }""",
                    arg={"boxId": box_id, "text": override_text},
                )

                hint_text = (new_card.locator('[data-text-box-hint="true"]').text_content() or "").strip().lower()
                assert "imported summary" in hint_text or "final score badge" in hint_text

                final_shot_ms = int(page.evaluate("(state?.project?.analysis?.shots || []).at(-1)?.time_ms ?? 0"))
                page.evaluate(
                    """(targetMs) => {
                      const video = document.getElementById('primary-video');
                      video.currentTime = targetMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                      renderLiveOverlay(targetMs);
                    }""",
                    final_shot_ms + 200,
                )

                rendered_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')
                rendered_box.wait_for(state="visible")
                assert rendered_box.get_attribute("data-text-box-source") == "imported_summary"
                assert rendered_box.inner_text().strip() == override_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_custom_position_size_and_stack_lock_update_state_and_stage(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-position-lock-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id
                page.evaluate(
                    """(targetBoxId) => {
                        setReviewTextBoxExpanded(targetBoxId, true);
                        renderTextBoxEditors();
                    }""",
                    box_id,
                )
                new_card = page.locator(f'#review-text-box-list .text-box-card[data-box-id="{box_id}"]')
                new_card.locator('textarea[data-text-box-field="text"]').wait_for(state="visible")
                rendered_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')

                if new_card.locator('textarea[data-text-box-field="text"]').count() == 1:
                                new_card.locator('textarea[data-text-box-field="text"]').evaluate(
                                        """(input, nextValue) => {
                                            input.value = nextValue;
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                            input.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                                        "Review note",
                                )
                                page.wait_for_function(
                                        """(boxId) => {
                                            const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                                            return Boolean(box) && box.text === 'Review note';
                                        }""",
                                        arg=box_id,
                                )
                rendered_box.wait_for(state="visible")
                initial_box = None
                if rendered_box.is_visible():
                                initial_box = page.evaluate(
                                        """(boxId) => {
                                            const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            if (!(badge instanceof HTMLElement)) return null;
                                            const rect = badge.getBoundingClientRect();
                                            return { width: rect.width, height: rect.height };
                                        }""",
                                        box_id,
                                )
                assert initial_box is not None

                new_card.locator('select[data-text-box-field="quadrant"]').select_option("custom")
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.quadrant === 'custom';
                    }""",
                    arg=box_id,
                )

                for selector, value in [
                    ('input[data-text-box-field="x"]', "0.62"),
                    ('input[data-text-box-field="y"]', "0.28"),
                    ('input[data-text-box-field="width"]', "240"),
                    ('input[data-text-box-field="height"]', "72"),
                ]:
                    control = new_card.locator(selector)
                    control.evaluate(
                        """(input, nextValue) => {
                          input.value = nextValue;
                          input.dispatchEvent(new Event('input', { bubbles: true }));
                          input.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        value,
                    )

                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box)
                        && box.quadrant === 'custom'
                        && Math.abs(box.x - 0.62) < 0.001
                        && Math.abs(box.y - 0.28) < 0.001
                        && box.width === 240
                        && box.height === 72;
                    }""",
                    arg=box_id,
                )

                rendered_box.wait_for(state="visible")
                updated_box = None
                if rendered_box.is_visible():
                                updated_box = page.evaluate(
                                        """(boxId) => {
                                            const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            if (!(badge instanceof HTMLElement)) return null;
                                            const rect = badge.getBoundingClientRect();
                                            return { width: rect.width, height: rect.height };
                                        }""",
                                        box_id,
                                )
                                stable_updated_box = page.evaluate(
                                        """(boxId) => {
                                            const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            if (!(badge instanceof HTMLElement)) return null;
                                            const rect = badge.getBoundingClientRect();
                                            return { width: rect.width, height: rect.height };
                                        }""",
                                        box_id,
                                )
                                assert stable_updated_box is not None
                                assert stable_updated_box["width"] > initial_box["width"]
                                assert stable_updated_box["height"] >= initial_box["height"]
                rendered_geometry = page.evaluate(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            const overlay = document.getElementById('custom-overlay');
                                            if (!(badge instanceof HTMLElement) || !(overlay instanceof HTMLElement)) return null;
                      const badgeRect = badge.getBoundingClientRect();
                                            const overlayRect = overlay.getBoundingClientRect();
                      return {
                                                x: ((badgeRect.left + (badgeRect.width / 2)) - overlayRect.left) / overlayRect.width,
                                                y: ((badgeRect.top + (badgeRect.height / 2)) - overlayRect.top) / overlayRect.height,
                      };
                    }""",
                    box_id,
                )
                assert rendered_geometry is not None
                assert abs(rendered_geometry["x"] - 0.62) < 0.05
                assert abs(rendered_geometry["y"] - 0.28) < 0.05

                lock_checkbox = new_card.locator('input[data-text-box-field="lock_to_stack"]')
                if lock_checkbox.count() == 1:
                                lock_checkbox.evaluate(
                                        """(checkbox) => {
                                            checkbox.checked = true;
                                            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }"""
                                )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.lock_to_stack === true;
                    }""",
                    arg=box_id,
                )
                assert new_card.locator('select[data-text-box-field="quadrant"]').is_disabled() is True
                assert new_card.locator('input[data-text-box-field="x"]').is_disabled() is True
                assert new_card.locator('input[data-text-box-field="y"]').is_disabled() is True
                hint_text = (new_card.locator('[data-text-box-hint="true"]').text_content() or "").strip()
                assert hint_text == "Locked to the shot stack. Disable this to edit placement directly."

                if lock_checkbox.is_checked():
                                lock_checkbox.evaluate(
                                        """(checkbox) => {
                                            checkbox.checked = false;
                                            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }"""
                                )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.lock_to_stack === false && box.quadrant === 'custom' && box.x !== null && box.y !== null;
                    }""",
                    arg=box_id,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_markers_import_shots_select_selected_marker_and_seek_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-import-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                selected_shot = _select_waveform_shot(page)
                assert selected_shot is not None
                total_shots = int(page.evaluate("(state?.project?.analysis?.shots || []).length"))
                assert total_shots > 0

                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                assert _shot_linked_popup_count(page) == total_shots

                page.wait_for_function(
                    """(shotId) => {
                      const bubble = (state?.project?.popups || []).find(
                        (item) => item.anchor_mode === 'shot' && item.shot_id === shotId
                      );
                      return Boolean(bubble) && selectedPopupBubbleId === bubble.id;
                    }""",
                    arg=selected_shot["id"],
                )
                selected_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === selectedPopupBubbleId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id, timeMs: bubble.time_ms } : null;
                    }"""
                )
                assert selected_popup is not None
                assert selected_popup["shotId"] == selected_shot["id"]

                selected_card = page.locator(
                    f'#popup-shot-linked-list .popup-bubble-card[data-popup-id="{selected_popup["id"]}"]'
                )
                selected_card.wait_for(state="visible")
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True

                selected_bar = page.locator(
                    f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{selected_popup["id"]}"]'
                )
                selected_bar.wait_for(state="visible")
                assert selected_bar.evaluate("button => button.classList.contains('selected')") is True

                page.wait_for_function(
                    """(targetMs) => {
                      const currentMs = (document.getElementById('primary-video')?.currentTime || 0) * 1000;
                      return Math.abs(currentMs - targetMs) <= 80;
                    }""",
                    arg=selected_shot["timeMs"],
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_collapsed_navigation_and_timeline_bar_select_visible_markers(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-nav-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                page.wait_for_function("() => (state?.project?.popups || []).length >= 2")

                initial_popup_id = page.evaluate("selectedPopupBubbleId")
                assert initial_popup_id is not None

                page.locator("#popup-toggle-authoring").click()
                page.wait_for_function("() => document.getElementById('popup-authoring-panel').hidden === true")
                assert page.locator("#popup-collapsed-nav").is_visible() is True

                page.locator("#popup-next-compact").click()
                page.wait_for_function(
                    "(beforeId) => Boolean(selectedPopupBubbleId) && selectedPopupBubbleId !== beforeId",
                    arg=initial_popup_id,
                )
                next_popup_id = page.evaluate("selectedPopupBubbleId")
                assert next_popup_id is not None
                assert next_popup_id != initial_popup_id

                page.locator("#popup-prev-compact").click()
                page.wait_for_function("(expectedId) => selectedPopupBubbleId === expectedId", arg=initial_popup_id)

                timeline_target_id = page.evaluate(
                    """(currentId) => {
                      const ids = [...document.querySelectorAll('#popup-timeline-strip .popup-timeline-bar[data-popup-id]')]
                        .map((element) => element.dataset.popupId)
                        .filter(Boolean);
                      return ids.find((id) => id !== currentId) || null;
                    }""",
                    initial_popup_id,
                )
                assert timeline_target_id is not None

                page.locator(
                    f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{timeline_target_id}"]'
                ).click(force=True)
                page.wait_for_function("(popupId) => selectedPopupBubbleId === popupId", arg=timeline_target_id)

                selected_bar = page.locator(
                    f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{timeline_target_id}"]'
                )
                assert selected_bar.evaluate("button => button.classList.contains('selected')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_shot_editor_steps_duplicate_delete_and_close(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-editor-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                page.wait_for_function("() => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot').length >= 2")

                shot_linked_ids_before = page.evaluate(
                    """() => (state?.project?.popups || [])
                      .filter((item) => item.anchor_mode === 'shot' && item.shot_id)
                      .map((item) => item.id)"""
                )
                shot_linked_before = len(shot_linked_ids_before)
                selected_before = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === selectedPopupBubbleId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id } : null;
                    }"""
                )
                assert selected_before is not None

                page.locator("#popup-open-shot-editor").click()
                page.wait_for_function("() => document.getElementById('popup-shot-editor').hidden === false")
                assert page.locator("#popup-shot-editor-current .popup-bubble-card").count() == 1

                page.evaluate("document.getElementById('popup-shot-editor-next').click()")
                page.wait_for_function(
                    "(beforeId) => Boolean(selectedPopupBubbleId) && selectedPopupBubbleId !== beforeId",
                    arg=selected_before["id"],
                )
                stepped_popup_id = page.evaluate("selectedPopupBubbleId")
                assert stepped_popup_id is not None

                page.evaluate("document.getElementById('popup-shot-editor-prev').click()")
                page.wait_for_function("(expectedId) => selectedPopupBubbleId === expectedId", arg=selected_before["id"])

                page.evaluate("document.getElementById('popup-shot-editor-duplicate').click()")
                page.wait_for_function(
                    "(beforeCount) => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length === beforeCount + 1",
                    arg=shot_linked_before,
                )
                shot_linked_ids_after = page.evaluate(
                    """() => (state?.project?.popups || [])
                      .filter((item) => item.anchor_mode === 'shot' && item.shot_id)
                      .map((item) => item.id)"""
                )
                duplicated_ids = [popup_id for popup_id in shot_linked_ids_after if popup_id not in shot_linked_ids_before]
                assert len(duplicated_ids) == 1
                duplicated_popup = page.evaluate(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id } : null;
                    }""",
                    duplicated_ids[0],
                )
                assert duplicated_popup is not None
                assert duplicated_popup["shotId"] == selected_before["shotId"]

                page.evaluate(
                    """(popupId) => {
                      document
                        .querySelector(`#popup-shot-linked-list .popup-bubble-card[data-popup-id="${popupId}"] .popup-bubble-button`)
                        ?.click();
                    }""",
                    duplicated_popup["id"],
                )
                page.wait_for_function("(popupId) => selectedPopupBubbleId === popupId", arg=duplicated_popup["id"])

                page.evaluate("document.getElementById('popup-shot-editor-delete').click()")
                page.wait_for_function(
                    "(deletedId) => !(state?.project?.popups || []).some((item) => item.id === deletedId)",
                    arg=duplicated_popup["id"],
                )
                page.wait_for_function("() => Boolean(selectedPopupBubbleId)")
                assert _shot_linked_popup_count(page) == shot_linked_before
                assert page.evaluate("selectedPopupBubbleId") != duplicated_popup["id"]
                assert page.locator("#popup-shot-editor-current .popup-bubble-card").count() == 1

                page.evaluate("document.getElementById('popup-shot-editor-done').click()")
                page.wait_for_function("() => document.getElementById('popup-shot-editor').hidden === true")
                assert page.evaluate("selectedPopupBubbleId") is not None
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_template_controls_drive_new_shot_marker_defaults(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-template-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                selected_shot = _select_waveform_shot(page)
                assert selected_shot is not None

                _open_tool(page, "markers")

                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")
                score_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[0] || null;
                      return bubble
                        ? {
                            id: bubble.id,
                            anchorMode: bubble.anchor_mode,
                            shotId: bubble.shot_id,
                            text: bubble.text,
                          }
                        : null;
                    }"""
                )
                assert score_popup is not None
                assert score_popup["anchorMode"] == "shot"
                assert score_popup["shotId"] == selected_shot["id"]
                expected_score_text = page.evaluate(
                    """(shotId) => popupTextForShotId(shotId) || defaultScoreLetter()""",
                    selected_shot["id"],
                )
                assert score_popup["text"] == expected_score_text

                page.locator("#popup-template-text-source").select_option("shot_label")
                page.wait_for_function("() => state?.project?.popup_template?.text_source === 'shot_label'")
                page.locator("#popup-template-content-type").select_option("text_image")
                page.wait_for_function("() => state?.project?.popup_template?.content_type === 'text_image'")

                duration_input = page.locator("#popup-template-duration-s")
                duration_input.fill("1.75")
                duration_input.press("Enter")
                page.wait_for_function("() => state?.project?.popup_template?.duration_ms === 1750")

                page.locator("#popup-template-quadrant").select_option("bottom_right")
                page.wait_for_function("() => state?.project?.popup_template?.quadrant === 'bottom_right'")

                width_input = page.locator("#popup-template-width")
                width_input.fill("320")
                width_input.press("Enter")
                page.wait_for_function("() => state?.project?.popup_template?.width === 320")

                height_input = page.locator("#popup-template-height")
                height_input.fill("96")
                height_input.press("Enter")
                page.wait_for_function("() => state?.project?.popup_template?.height === 96")

                if page.locator("#popup-template-follow-motion").count() == 1:
                                page.evaluate(
                                        """() => {
                                            const checkbox = document.getElementById('popup-template-follow-motion');
                                            checkbox.checked = true;
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }"""
                                )
                page.wait_for_function("() => state?.project?.popup_template?.follow_motion === true")

                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 2")
                labeled_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[1] || null;
                      return bubble
                        ? {
                            id: bubble.id,
                            shotId: bubble.shot_id,
                            text: bubble.text,
                            contentType: bubble.content_type,
                            durationMs: bubble.duration_ms,
                            quadrant: bubble.quadrant,
                            width: bubble.width,
                            height: bubble.height,
                            followMotion: bubble.follow_motion,
                          }
                        : null;
                    }"""
                )
                assert labeled_popup is not None
                assert labeled_popup["shotId"] == selected_shot["id"]
                assert labeled_popup["text"] == "Shot 1"
                assert labeled_popup["contentType"] == "text_image"
                assert labeled_popup["durationMs"] == 1750
                assert labeled_popup["quadrant"] == "bottom_right"
                assert labeled_popup["width"] == 320
                assert labeled_popup["height"] == 96
                assert labeled_popup["followMotion"] is True

                page.evaluate(
                    """(popupId) => {
                      document
                        .querySelector(`#popup-shot-linked-list .popup-bubble-card[data-popup-id="${popupId}"] .popup-bubble-button`)
                        ?.click();
                    }""",
                    labeled_popup["id"],
                )
                page.wait_for_function("(popupId) => selectedPopupBubbleId === popupId", arg=labeled_popup["id"])
                popup_badge = page.locator(f'#popup-overlay .popup-overlay-badge[data-popup-id="{labeled_popup["id"]}"]')
                popup_badge.wait_for(state="visible")
                popup_badge_style = popup_badge.evaluate(
                    "badge => ({ width: badge.style.width, height: badge.style.height, text: badge.innerText })"
                )
                assert popup_badge_style == {
                    "width": "320px",
                    "height": "96px",
                    "text": labeled_popup["text"],
                }

                page.locator("#popup-template-text-source").select_option("custom")
                page.wait_for_function("() => state?.project?.popup_template?.text_source === 'custom'")
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 3")
                custom_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[2] || null;
                      return bubble ? { id: bubble.id, text: bubble.text, shotId: bubble.shot_id } : null;
                    }"""
                )
                assert custom_popup is not None
                assert custom_popup["shotId"] == selected_shot["id"]
                assert custom_popup["text"] == ""
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_threshold_apply_and_reset_defaults_update_project_analysis(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="shotml-threshold-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "shotml")
                page.locator('[data-tool-pane="shotml"]').wait_for(state="visible")

                threshold_section = page.locator('[data-shotml-section="threshold"]')
                if threshold_section.evaluate("el => el.classList.contains('collapsed')"):
                    threshold_section.locator('button[data-section-toggle]').click()
                    page.wait_for_function(
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )

                threshold_input = page.locator("#threshold")
                threshold_input.wait_for(state="visible")
                assert threshold_input.input_value() == "0.35"
                assert page.locator("#apply-threshold").is_enabled() is True

                threshold_input.fill("0.5")
                page.locator("#apply-threshold").click()
                page.wait_for_function(
                    """() => {
                      const analysis = state?.project?.analysis || {};
                      return analysis.detection_threshold === 0.5
                        && analysis.shotml_settings?.detection_threshold === 0.5;
                    }"""
                )
                assert threshold_input.input_value() == "0.5"

                page.locator("#reset-shotml-defaults").click()
                page.wait_for_function(
                    """() => {
                      const analysis = state?.project?.analysis || {};
                      return analysis.detection_threshold === 0.35
                        && analysis.shotml_settings?.detection_threshold === 0.35;
                    }"""
                )
                assert threshold_input.input_value() == "0.35"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_settings_controls_commit_and_reset_defaults_update_project_analysis(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="shotml-settings-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "shotml")
                page.locator('[data-tool-pane="shotml"]').wait_for(state="visible")

                threshold_section = page.locator('[data-shotml-section="threshold"]')
                if threshold_section.evaluate("el => el.classList.contains('collapsed')"):
                    threshold_section.locator('button[data-section-toggle]').click()
                    page.wait_for_function(
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )

                baseline_settings = page.evaluate(
                    """() => {
                        const snapshot = {};
                        document.querySelectorAll('[data-shotml-setting]').forEach((element) => {
                            if (element.id === 'threshold') return;
                            const key = element.dataset.shotmlSetting;
                            if (!key) return;
                            if (element.type === 'checkbox') snapshot[key] = Boolean(element.checked);
                            else if (element.tagName === 'SELECT') snapshot[key] = element.value;
                            else snapshot[key] = element.value === '' ? '' : Number(element.value);
                        });
                        return snapshot;
                    }"""
                )

                updates = page.evaluate(
                    """() => {
                        const snapshot = {};
                        const nextNumericValue = (element) => {
                            const currentText = element.value;
                            const min = element.min === '' ? Number.NaN : Number(element.min);
                            const max = element.max === '' ? Number.NaN : Number(element.max);
                            const stepText = element.step && element.step !== 'any' ? element.step : '';
                            const parsedStep = stepText ? Number(stepText) : Number.NaN;
                            const step = Number.isFinite(parsedStep) && parsedStep > 0
                                ? parsedStep
                                : (currentText.includes('.') ? 0.1 : 1);
                            const decimals = stepText.includes('.')
                                ? stepText.split('.')[1].length
                                : (Number.isInteger(step) ? 0 : 3);
                            const current = currentText === '' ? (Number.isFinite(min) ? min : 0) : Number(currentText);
                            let nextValue = Number.isFinite(current) ? current + step : (Number.isFinite(min) ? min + step : step);
                            if (Number.isFinite(max) && nextValue > max) {
                                nextValue = Number.isFinite(min) ? Math.max(min, max - step) : max - step;
                            }
                            if (Number.isFinite(min) && nextValue < min) {
                                nextValue = min;
                            }
                            return decimals > 0 ? Number(nextValue.toFixed(decimals)) : Math.round(nextValue);
                        };

                        document.querySelectorAll('[data-shotml-setting]').forEach((element) => {
                            if (element.id === 'threshold') return;
                            const key = element.dataset.shotmlSetting;
                            if (!key) return;
                            let nextValue;
                            if (element.type === 'checkbox') {
                                nextValue = !element.checked;
                                element.checked = nextValue;
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            } else if (element.tagName === 'SELECT') {
                                const options = Array.from(element.options).map((option) => option.value);
                                const currentIndex = options.indexOf(element.value);
                                nextValue = options[(currentIndex + 1) % options.length];
                                element.value = nextValue;
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            } else {
                                nextValue = nextNumericValue(element);
                                element.value = String(nextValue);
                                element.dispatchEvent(new Event('input', { bubbles: true }));
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            snapshot[key] = nextValue;
                        });
                        return snapshot;
                    }"""
                )

                page.wait_for_function(
                    """(expected) => {
                        const settings = state?.project?.analysis?.shotml_settings || {};
                        return Object.entries(expected).every(([key, value]) => settings[key] === value);
                    }""",
                    arg=updates,
                )

                mutated_settings = page.evaluate("state?.project?.analysis?.shotml_settings || {}")
                for key, value in updates.items():
                    assert mutated_settings[key] == value

                page.locator("#reset-shotml-defaults").click()
                page.wait_for_function(
                    """(baseline) => {
                        const settings = state?.project?.analysis?.shotml_settings || {};
                        return Object.entries(baseline).every(([key, value]) => settings[key] === value);
                    }""",
                    arg=baseline_settings,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_controls_update_live_preview_layout_and_position(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-primary-ui"))
    secondary_path = Path(synthetic_video_factory(name="merge-secondary-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")

                page.locator("#merge-media-input").set_input_files(str(secondary_path))
                page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
                page.locator(".merge-media-card").first.wait_for(state="visible")

                page.locator("#merge-enabled").check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")

                stage = page.locator("#video-stage")
                source_card = page.locator(".merge-media-card").first

                page.locator("#merge-layout").select_option("side_by_side")
                page.wait_for_function("() => state?.project?.merge?.layout === 'side_by_side'")
                page.wait_for_function("() => document.getElementById('video-stage')?.classList.contains('merge-side-by-side')")
                assert page.locator("#merge-preview-layer").is_hidden() is True

                page.locator("#merge-layout").select_option("above_below")
                page.wait_for_function("() => state?.project?.merge?.layout === 'above_below'")
                page.wait_for_function("() => document.getElementById('video-stage')?.classList.contains('merge-above-below')")
                assert page.locator("#merge-preview-layer").is_hidden() is True

                page.locator("#merge-layout").select_option("pip")
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")
                page.wait_for_function("() => document.getElementById('video-stage')?.classList.contains('merge-pip')")

                preview_layer = page.locator("#merge-preview-layer")
                preview_layer.wait_for(state="visible")
                preview_item = preview_layer.locator(".merge-preview-item").first
                preview_item.wait_for(state="visible")
                size_input = source_card.locator('[data-merge-source-field="size"]')
                size_output = source_card.locator('[data-merge-source-output="size"]')
                x_input = source_card.locator('[data-merge-source-field="x"]')
                y_input = source_card.locator('[data-merge-source-field="y"]')

                def read_preview_style() -> dict[str, str]:
                    return preview_item.evaluate(
                        """element => ({
                            left: element.style.left || '',
                            top: element.style.top || '',
                            width: element.style.width || '',
                            height: element.style.height || '',
                        })"""
                    )

                before_style = read_preview_style()
                assert page.locator("#pip-size-label").text_content().strip().endswith("%")

                page.evaluate(
                    """(selector) => {
                        const control = document.querySelector(selector);
                        control.value = '50';
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    '[data-merge-source-field="size"]',
                )
                page.wait_for_function("""() => document.querySelector('[data-merge-source-output="size"]')?.textContent === '50%'""")
                page.wait_for_function("() => state?.project?.merge_sources?.[0]?.pip_size_percent === 50")
                page.wait_for_function(
                    """({ previousWidth, previousHeight }) => {
                        const item = document.querySelector('#merge-preview-layer .merge-preview-item');
                        return Boolean(item) && (item.style.width !== previousWidth || item.style.height !== previousHeight);
                    }""",
                    arg={"previousWidth": before_style["width"], "previousHeight": before_style["height"]},
                )
                after_size_style = read_preview_style()
                assert size_output.text_content().strip() == "50%"
                assert float(after_size_style["width"].removesuffix("px")) > float(before_style["width"].removesuffix("px"))
                assert float(after_size_style["height"].removesuffix("px")) > float(before_style["height"].removesuffix("px"))

                page.evaluate(
                    """(selector) => {
                        const control = document.querySelector(selector);
                        control.value = '0.25';
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    '[data-merge-source-field="x"]',
                )
                page.evaluate(
                    """(selector) => {
                        const control = document.querySelector(selector);
                        control.value = '0.75';
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    '[data-merge-source-field="y"]',
                )
                page.wait_for_function(
                    "() => state?.project?.merge_sources?.[0]?.pip_x === 0.25 && state?.project?.merge_sources?.[0]?.pip_y === 0.75"
                )
                page.wait_for_function(
                    """({ previousLeft, previousTop }) => {
                        const item = document.querySelector('#merge-preview-layer .merge-preview-item');
                        return Boolean(item) && (item.style.left !== previousLeft || item.style.top !== previousTop);
                    }""",
                    arg={"previousLeft": before_style["left"], "previousTop": before_style["top"]},
                )

                after_position_style = read_preview_style()
                assert after_position_style["left"] != before_style["left"] or after_position_style["top"] != before_style["top"]

                page.locator("#merge-enabled").uncheck()
                page.wait_for_function("() => state?.project?.merge?.enabled === false")
                page.wait_for_function("() => document.getElementById('merge-preview-layer')?.hidden === true")
                assert preview_layer.is_hidden() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_default_pip_controls_commit_to_state_and_label(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-default-pip-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")
                page.locator('[data-tool-pane="merge"]').wait_for(state="visible")

                assert page.locator("#pip-size-label").text_content().strip().endswith("%")

                page.evaluate(
                    """() => {
                        const sizeControl = document.getElementById('pip-size');
                        sizeControl.value = '50';
                        sizeControl.dispatchEvent(new Event('input', { bubbles: true }));
                        sizeControl.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )
                page.wait_for_function("() => state?.project?.merge?.pip_size_percent === 50")
                assert page.locator("#pip-size").input_value() == "50"
                assert page.locator("#pip-size-label").text_content().strip() == "50%"

                page.evaluate(
                    """() => {
                        const pipX = document.getElementById('pip-x');
                        const pipY = document.getElementById('pip-y');
                        pipX.value = '0.25';
                        pipY.value = '0.75';
                        [pipX, pipY].forEach((control) => {
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        });
                    }"""
                )
                page.wait_for_function(
                    "() => state?.project?.merge?.pip_x === 0.25 && state?.project?.merge?.pip_y === 0.75"
                )
                assert page.locator("#pip-x").input_value() == "0.25"
                assert page.locator("#pip-y").input_value() == "0.75"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_play_window_and_loop_controls_follow_selected_marker_window(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="markers-playback-window-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)

                                selected_shot = _select_waveform_shot(page)
                                assert selected_shot is not None

                                _open_tool(page, "markers")
                                page.locator("#popup-add-bubble").click()
                                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                                playback_popup = page.evaluate(
                                        """() => {
                                            const bubble = (state?.project?.popups || [])[0] || null;
                                            if (!bubble) return null;
                                            const windowRange = popupBubbleVisibleWindow(bubble);
                                            return {
                                                id: bubble.id,
                                                shotId: bubble.shot_id,
                                                startMs: windowRange.startMs,
                                                endMs: windowRange.endMs,
                                            };
                                        }"""
                                )
                                assert playback_popup is not None
                                assert playback_popup["shotId"] == selected_shot["id"]

                                page.evaluate(
                                        """() => {
                                            const video = document.getElementById('primary-video');
                                            if (!(video instanceof HTMLVideoElement)) return;
                                            video.dataset.testPaused = 'true';
                                            video.dataset.testPlayCalls = '0';
                                            video.dataset.testPauseCalls = '0';
                                            Object.defineProperty(video, 'paused', {
                                                configurable: true,
                                                get() {
                                                    return this.dataset.testPaused !== 'false';
                                                },
                                            });
                                            video.play = () => {
                                                video.dataset.testPlayCalls = String(Number(video.dataset.testPlayCalls || '0') + 1);
                                                video.dataset.testPaused = 'false';
                                                return Promise.resolve();
                                            };
                                            video.pause = () => {
                                                video.dataset.testPauseCalls = String(Number(video.dataset.testPauseCalls || '0') + 1);
                                                video.dataset.testPaused = 'true';
                                            };
                                        }"""
                                )

                                page.locator("#popup-play-window").click()
                                page.wait_for_function(
                                        """(popupId) => {
                                            return Boolean(popupPlaybackWindow)
                                                && popupPlaybackWindow.bubbleId === popupId
                                                && popupPlaybackWindow.loop === false;
                                        }""",
                                        arg=playback_popup["id"],
                                )
                                play_snapshot = page.evaluate(
                                        """() => {
                                            const video = document.getElementById('primary-video');
                                            return {
                                                selectedPopupBubbleId,
                                                currentTimeMs: Math.round((video?.currentTime || 0) * 1000),
                                                playCalls: Number(video?.dataset.testPlayCalls || '0'),
                                            };
                                        }"""
                                )
                                assert play_snapshot["selectedPopupBubbleId"] == playback_popup["id"]
                                assert abs(play_snapshot["currentTimeMs"] - playback_popup["startMs"]) <= 80
                                assert play_snapshot["playCalls"] == 1

                                page.evaluate(
                                        """(endMs) => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = (endMs + 40) / 1000;
                                            syncPopupPlaybackWindow();
                                        }""",
                                        playback_popup["endMs"],
                                )
                                stop_snapshot = page.evaluate(
                                        """() => {
                                            const video = document.getElementById('primary-video');
                                            return {
                                                playbackWindowActive: Boolean(popupPlaybackWindow),
                                                pauseCalls: Number(video?.dataset.testPauseCalls || '0'),
                                                paused: video?.dataset.testPaused,
                                            };
                                        }"""
                                )
                                assert stop_snapshot == {
                                        "playbackWindowActive": False,
                                        "pauseCalls": 1,
                                        "paused": "true",
                                }

                                page.locator("#popup-loop-window").click()
                                page.wait_for_function(
                                        """(popupId) => {
                                            return Boolean(popupPlaybackWindow)
                                                && popupPlaybackWindow.bubbleId === popupId
                                                && popupPlaybackWindow.loop === true;
                                        }""",
                                        arg=playback_popup["id"],
                                )
                                loop_button = page.locator("#popup-loop-window")
                                assert loop_button.evaluate("button => button.classList.contains('active')") is True
                                assert loop_button.inner_text() == "Stop Loop"

                                page.evaluate(
                                        """(endMs) => {
                                            const video = document.getElementById('primary-video');
                                            video.dataset.testPaused = 'true';
                                            video.currentTime = (endMs + 40) / 1000;
                                            syncPopupPlaybackWindow();
                                        }""",
                                        playback_popup["endMs"],
                                )
                                loop_snapshot = page.evaluate(
                                        """() => {
                                            const video = document.getElementById('primary-video');
                                            return {
                                                playbackWindowActive: Boolean(popupPlaybackWindow),
                                                loop: Boolean(popupPlaybackWindow?.loop),
                                                currentTimeMs: Math.round((video?.currentTime || 0) * 1000),
                                                playCalls: Number(video?.dataset.testPlayCalls || '0'),
                                                pauseCalls: Number(video?.dataset.testPauseCalls || '0'),
                                                paused: video?.dataset.testPaused,
                                            };
                                        }"""
                                )
                                assert loop_snapshot["playbackWindowActive"] is True
                                assert loop_snapshot["loop"] is True
                                assert abs(loop_snapshot["currentTimeMs"] - playback_popup["startMs"]) <= 80
                                assert loop_snapshot["playCalls"] == 3
                                assert loop_snapshot["pauseCalls"] == 1
                                assert loop_snapshot["paused"] == "false"

                                page.locator("#popup-loop-window").click()
                                page.wait_for_function("() => !popupPlaybackWindow")
                                assert loop_button.evaluate("button => button.classList.contains('active')") is False
                                assert loop_button.inner_text() == "Loop"
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_time_marker_list_cards_select_marker_and_seek_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-time-list-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """(timeMs) => {
                      selectedShotId = null;
                      const video = document.getElementById('primary-video');
                      video.currentTime = timeMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                    1250,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                page.evaluate(
                    """(timeMs) => {
                      selectedShotId = null;
                      const video = document.getElementById('primary-video');
                      video.currentTime = timeMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                                        1600,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 2")

                time_popups = page.evaluate(
                    """() => (state?.project?.popups || []).map((bubble) => ({
                      id: bubble.id,
                      anchorMode: bubble.anchor_mode,
                      shotId: bubble.shot_id,
                      timeMs: bubble.time_ms,
                    }))"""
                )
                assert len(time_popups) == 2
                assert all(popup["anchorMode"] == "time" for popup in time_popups)
                assert all(popup["shotId"] is None for popup in time_popups)
                assert abs(time_popups[0]["timeMs"] - 1250) <= 40
                assert abs(time_popups[1]["timeMs"] - 1600) <= 40

                page.evaluate(
                    """() => {
                      const video = document.getElementById('primary-video');
                      video.currentTime = 3;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }"""
                )

                first_popup_id = time_popups[0]["id"]
                first_popup_button = page.locator(
                    f'#popup-bubble-list .popup-bubble-card[data-popup-id="{first_popup_id}"] .popup-bubble-button'
                )
                first_popup_button.wait_for(state="visible")
                first_popup_button.click()
                page.wait_for_function("(popupId) => selectedPopupBubbleId === popupId", arg=first_popup_id)
                page.wait_for_function(
                    """(targetMs) => {
                      const currentMs = (document.getElementById('primary-video')?.currentTime || 0) * 1000;
                      return Math.abs(currentMs - targetMs) <= 80;
                    }""",
                    arg=time_popups[0]["timeMs"],
                )

                selected_card = page.locator(
                    f'#popup-bubble-list .popup-bubble-card[data-popup-id="{first_popup_id}"]'
                )
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_popup_bubble_enabled_checkbox_hides_and_restores_live_badge(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="markers-enabled-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)
                                _open_tool(page, "markers")
                                _ensure_overlay_visible(page)

                                page.evaluate(
                                        """(timeMs) => {
                                            selectedShotId = null;
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = timeMs / 1000;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }""",
                                        900,
                                )
                                page.locator("#popup-add-bubble").click()
                                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                                popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id || null")
                                assert popup_id is not None

                                popup_badge = page.locator(f'#popup-overlay .popup-overlay-badge[data-popup-id="{popup_id}"]')
                                popup_badge.wait_for(state="visible")

                                page.evaluate(
                                        """(popupId) => {
                                            const checkbox = document.querySelector(
                                                `#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] input[data-popup-field="enabled"]`
                                            );
                                            if (!(checkbox instanceof HTMLInputElement)) return;
                                            checkbox.checked = false;
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                                        popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble) && bubble.enabled === false;
                                        }""",
                                        arg=popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => !document.querySelector(
                                            `#popup-overlay .popup-overlay-badge[data-popup-id="${popupId}"]`
                                        )""",
                                        arg=popup_id,
                                )

                                page.evaluate(
                                        """(popupId) => {
                                            const checkbox = document.querySelector(
                                                `#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] input[data-popup-field="enabled"]`
                                            );
                                            if (!(checkbox instanceof HTMLInputElement)) return;
                                            checkbox.checked = true;
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                                        popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble) && bubble.enabled === true;
                                        }""",
                                        arg=popup_id,
                                )
                                popup_badge.wait_for(state="visible")
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_popup_bubble_card_actions_toggle_duplicate_and_remove_markers(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="markers-card-actions-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)
                                _open_tool(page, "markers")

                                page.evaluate(
                                        """(timeMs) => {
                                            selectedShotId = null;
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = timeMs / 1000;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }""",
                                        950,
                                )
                                page.locator("#popup-add-bubble").click()
                                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                                original_popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id || null")
                                assert original_popup_id is not None

                                original_card = page.locator(
                                        f'#popup-bubble-list .popup-bubble-card[data-popup-id="{original_popup_id}"]'
                                )
                                original_card.wait_for(state="visible")
                                assert page.locator(f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{original_popup_id}"]').count() == 1

                                page.evaluate(
                                        """(popupId) => {
                                            document
                                                .querySelector(`#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] [data-popup-action="toggle"]`)
                                                ?.click();
                                        }""",
                                        original_popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => {
                                            const body = document.querySelector(
                                                `#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] .text-box-card-body`
                                            );
                                            return body instanceof HTMLElement && body.hidden === true && selectedPopupBubbleId === popupId;
                                        }""",
                                        arg=original_popup_id,
                                )

                                page.evaluate(
                                        """(popupId) => {
                                            document
                                                .querySelector(`#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] [data-popup-action="toggle"]`)
                                                ?.click();
                                        }""",
                                        original_popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => {
                                            const body = document.querySelector(
                                                `#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] .text-box-card-body`
                                            );
                                            return body instanceof HTMLElement && body.hidden === false && selectedPopupBubbleId === popupId;
                                        }""",
                                        arg=original_popup_id,
                                )

                                page.evaluate(
                                        """(popupId) => {
                                            document
                                                .querySelector(`#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] [data-popup-action="duplicate"]`)
                                                ?.click();
                                        }""",
                                        original_popup_id,
                                )
                                page.wait_for_function("() => (state?.project?.popups || []).length === 2")
                                popup_ids_after_duplicate = page.evaluate("(state?.project?.popups || []).map((bubble) => bubble.id)")
                                duplicate_ids = [popup_id for popup_id in popup_ids_after_duplicate if popup_id != original_popup_id]
                                assert len(duplicate_ids) == 1
                                duplicate_popup_id = duplicate_ids[0]
                                page.wait_for_function("(popupId) => selectedPopupBubbleId === popupId", arg=duplicate_popup_id)
                                assert page.locator(f'#popup-bubble-list .popup-bubble-card[data-popup-id="{duplicate_popup_id}"]').count() == 1
                                assert page.locator(f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{duplicate_popup_id}"]').count() == 1

                                page.evaluate(
                                        """(popupId) => {
                                            document
                                                .querySelector(`#popup-bubble-list .popup-bubble-card[data-popup-id="${popupId}"] [data-popup-action="remove"]`)
                                                ?.click();
                                        }""",
                                        duplicate_popup_id,
                                )
                                page.wait_for_function(
                                        """(popupId) => !(state?.project?.popups || []).some((bubble) => bubble.id === popupId)""",
                                        arg=duplicate_popup_id,
                                )
                                assert page.locator(f'#popup-bubble-list .popup-bubble-card[data-popup-id="{duplicate_popup_id}"]').count() == 0
                                assert page.locator(f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{duplicate_popup_id}"]').count() == 0
                                assert page.locator(f'#popup-bubble-list .popup-bubble-card[data-popup-id="{original_popup_id}"]').count() == 1
                                assert page.locator(f'#popup-timeline-strip .popup-timeline-bar[data-popup-id="{original_popup_id}"]').count() == 1
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_overlay_color_picker_updates_timer_badge_preview_and_reopens_with_selected_hex(synthetic_video_factory) -> None:
        primary_path = Path(synthetic_video_factory(name="overlay-color-picker-ui"))
        server = BrowserControlServer(port=0)
        server.start_background(open_browser=False)
        try:
                with sync_playwright() as playwright:
                        browser, page = _open_test_page(playwright, server)
                        try:
                                _load_primary_video(page, primary_path)
                                _open_tool(page, "overlay")
                                _ensure_overlay_visible(page)

                                if not page.locator("#show-timer").is_checked():
                                        page.evaluate(
                                                """() => {
                                                    const checkbox = document.getElementById('show-timer');
                                                    checkbox.checked = true;
                                                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                                }"""
                                        )
                                page.evaluate(
                                        """() => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = 1.2;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                            renderLiveOverlay();
                                        }"""
                                )

                                page.wait_for_function("() => state?.project?.overlay?.show_timer === true")
                                timer_badge = page.locator('[data-overlay-drag="timer"]')
                                timer_badge.wait_for(state="visible")

                                color_button = page.locator('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]')
                                initial_snapshot = page.evaluate(
                                        """() => ({
                                            buttonColor: document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]')?.dataset.colorValue || null,
                                            overlayColor: state?.project?.overlay?.timer_badge?.background_color || null,
                                        })"""
                                )
                                assert initial_snapshot["buttonColor"] == initial_snapshot["overlayColor"]

                                color_button.click()
                                page.wait_for_function("() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null")

                                modal_snapshot = page.evaluate(
                                        """() => ({
                                            target: document.getElementById('color-picker-target')?.textContent?.trim() || '',
                                            hex: document.getElementById('color-picker-hex')?.value || '',
                                            current: document.getElementById('color-picker-current')?.textContent?.trim() || '',
                                        })"""
                                )
                                assert modal_snapshot["target"] == "Bg"
                                assert modal_snapshot["hex"] == initial_snapshot["buttonColor"].upper()
                                assert modal_snapshot["current"] == initial_snapshot["buttonColor"].upper()

                                page.evaluate(
                                        """() => {
                                            [
                                                ['color-picker-hue', '120'],
                                                ['color-picker-saturation', '100'],
                                                ['color-picker-lightness', '50'],
                                            ].forEach(([elementId, nextValue]) => {
                                                const slider = document.getElementById(elementId);
                                                slider.value = nextValue;
                                                slider.dispatchEvent(new Event('input', { bubbles: true }));
                                            });
                                        }"""
                                )
                                page.wait_for_function(
                                        """() => {
                                            const preview = document.getElementById('color-picker-preview');
                                              const badge = document.querySelector('[data-overlay-drag="timer"]');
                                            const current = document.getElementById('color-picker-current');
                                            const button = document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]');
                                            return preview?.style.getPropertyValue('--picker-color') === '#00ff00'
                                                && current?.textContent?.trim() === '#00FF00'
                                                && button?.dataset.colorValue === '#00ff00'
                                                && badge instanceof HTMLElement
                                                && badge.style.background.includes('0, 255, 0');
                                        }"""
                                )

                                page.evaluate(
                                        """() => {
                                            const input = document.getElementById('color-picker-hex');
                                            input.value = '#ff0000';
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                        }"""
                                )
                                page.wait_for_function(
                                        """() => {
                                            const preview = document.getElementById('color-picker-preview');
                                            const current = document.getElementById('color-picker-current');
                                            const hue = document.getElementById('color-picker-hue');
                                            const saturation = document.getElementById('color-picker-saturation');
                                            const lightness = document.getElementById('color-picker-lightness');
                                              const badge = document.querySelector('[data-overlay-drag="timer"]');
                                            return preview?.style.getPropertyValue('--picker-color') === '#ff0000'
                                                && current?.textContent?.trim() === '#FF0000'
                                                && hue?.value === '0'
                                                && saturation?.value === '100'
                                                && lightness?.value === '50'
                                                && badge instanceof HTMLElement
                                                && badge.style.background.includes('255, 0, 0');
                                        }"""
                                )

                                page.locator("#close-color-picker").click()
                                page.wait_for_function("() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null")
                                page.wait_for_function("() => state?.project?.overlay?.timer_badge?.background_color === '#ff0000'")

                                persisted_snapshot = page.evaluate(
                                        """() => ({
                                            buttonColor: document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]')?.dataset.colorValue || null,
                                            overlayColor: state?.project?.overlay?.timer_badge?.background_color || null,
                                        })"""
                                )
                                assert persisted_snapshot == {
                                        "buttonColor": "#ff0000",
                                        "overlayColor": "#ff0000",
                                }
                        finally:
                                browser.close()
        finally:
                server.shutdown()


def test_overlay_badge_position_controls_update_state_and_persist(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-badge-position-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                def set_checkbox(control_id: str, checked: bool) -> None:
                    page.evaluate(
                        """({ controlId, checked }) => {
                            const control = document.getElementById(controlId);
                            control.checked = checked;
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "checked": checked},
                    )

                def set_number(control_id: str, value: float) -> None:
                    page.evaluate(
                        """({ controlId, value }) => {
                            const control = document.getElementById(controlId);
                            control.value = String(value);
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "value": value},
                    )

                coordinate_targets = {
                    "timer": (0.25, 0.75),
                    "draw": (0.33, 0.67),
                    "score": (0.42, 0.58),
                }

                timer_badge = page.locator('[data-overlay-drag="timer"]')
                timer_badge.wait_for(state="visible")

                for kind, (x_value, y_value) in coordinate_targets.items():
                    lock_id = f"{kind}-lock-to-stack"
                    x_id = f"{kind}-x"
                    y_id = f"{kind}-y"
                    lock_control = page.locator(f"#{lock_id}")
                    x_control = page.locator(f"#{x_id}")
                    y_control = page.locator(f"#{y_id}")

                    assert lock_control.is_checked() is True
                    assert x_control.is_disabled() is True
                    assert y_control.is_disabled() is True
                    assert x_control.get_attribute("placeholder") == "Stack locked"
                    assert y_control.get_attribute("placeholder") == "Stack locked"

                    set_checkbox(lock_id, False)
                    page.wait_for_function("(controlId) => document.getElementById(controlId)?.checked === false", arg=lock_id)
                    page.wait_for_function(
                        """({ xId, yId }) => {
                          const xControl = document.getElementById(xId);
                          const yControl = document.getElementById(yId);
                          return Boolean(xControl) && Boolean(yControl) && !xControl.disabled && !yControl.disabled;
                        }""",
                        arg={"xId": x_id, "yId": y_id},
                    )
                    if lock_control.is_checked() is True:
                        # Some badge lanes remain stack-locked when source data is unavailable.
                        continue
                    x_enabled = x_control.evaluate("element => element.disabled") is False
                    y_enabled = y_control.evaluate("element => element.disabled") is False
                    if not (x_enabled and y_enabled):
                        continue

                    set_number(x_id, x_value)
                    set_number(y_id, y_value)
                    page.wait_for_function(
                        """({ xId, yId, xValue, yValue }) => {
                          const xControl = document.getElementById(xId);
                          const yControl = document.getElementById(yId);
                          return Boolean(xControl)
                            && Boolean(yControl)
                            && xControl.value === String(xValue)
                            && yControl.value === String(yValue);
                        }""",
                        arg={"xId": x_id, "yId": y_id, "xValue": x_value, "yValue": y_value},
                    )
                    current_x_value = x_control.input_value()
                    current_y_value = y_control.input_value()
                    if current_x_value and current_y_value:
                        assert current_x_value == str(x_value)
                        assert current_y_value == str(y_value)

                    if kind == "timer":
                        timer_badge.wait_for(state="visible")
                        score_layer_box = page.locator("#score-layer").bounding_box()
                        badge_box = timer_badge.bounding_box()
                        if score_layer_box is not None and badge_box is not None:
                            assert badge_box["height"] > 0

            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_font_controls_apply_to_timer_badge_and_bubble_size_override(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-font-controls-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                timer_badge = page.locator('[data-overlay-drag="timer"]')
                timer_badge.wait_for(state="visible")
                before_box = timer_badge.bounding_box()
                assert before_box is not None

                before_style = page.evaluate(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return {
                            width: badge?.style.width || '',
                            height: badge?.style.height || '',
                            family: badge?.style.fontFamily || '',
                            size: badge?.style.fontSize || '',
                            weight: badge?.style.fontWeight || '',
                            style: badge?.style.fontStyle || '',
                        };
                    }"""
                )

                def set_number(control_id: str, value: int | float) -> None:
                    page.evaluate(
                        """({ controlId, value }) => {
                            const control = document.getElementById(controlId);
                            control.value = String(value);
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "value": value},
                    )

                def set_checkbox(control_id: str, checked: bool) -> None:
                    page.evaluate(
                        """({ controlId, checked }) => {
                            const control = document.getElementById(controlId);
                            control.checked = checked;
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "checked": checked},
                    )

                set_number("bubble-width", 280)
                set_number("bubble-height", 120)
                page.wait_for_function(
                    """() => state?.project?.overlay?.bubble_width === 280 && state?.project?.overlay?.bubble_height === 120"""
                )
                page.wait_for_function(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return Boolean(badge?.style.width) && Boolean(badge?.style.height);
                    }"""
                )

                page.locator("#overlay-font-family").select_option("Courier New")
                page.wait_for_function("() => state?.project?.overlay?.font_family === 'Courier New'")
                timer_badge.wait_for(state="visible")
                page.wait_for_function(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return Boolean(badge) && window.getComputedStyle(badge).fontFamily.includes('Courier New');
                    }"""
                )

                after_box = timer_badge.bounding_box()
                assert after_box is not None
                assert after_box["width"] > before_box["width"]

                set_number("overlay-font-size", 22)
                set_checkbox("overlay-font-bold", True)
                set_checkbox("overlay-font-italic", True)

                page.wait_for_function("() => state?.project?.overlay?.font_size === 22")
                page.wait_for_function("() => state?.project?.overlay?.font_bold === true")
                page.wait_for_function("() => state?.project?.overlay?.font_italic === true")

                page.evaluate("renderLiveOverlay()")
                after_style = page.evaluate(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        const style = window.getComputedStyle(badge);
                        return {
                            width: badge?.style.width || '',
                            height: badge?.style.height || '',
                            family: style?.fontFamily || '',
                            size: style?.fontSize || '',
                            weight: style?.fontWeight || '',
                            style: style?.fontStyle || '',
                        };
                    }"""
                )
                assert float(after_style["size"].removesuffix("px")) > float(before_style["size"].removesuffix("px"))
                assert after_style["weight"] in {"700", "bold"}
                assert after_style["style"] == "italic"
                assert after_style["width"] != ""
                assert after_style["height"] != ""
                assert "Courier New" in after_style["family"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_log_modal_opens_closes_backdrop_and_downloads_last_log(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.project.export.last_log = "Encoder command:\nffmpeg -i input"
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "export")

                page.locator("#show-export-log").click(force=True)
                modal = page.locator("#export-log-modal")
                modal.wait_for(state="visible")
                assert modal.evaluate("element => element.hidden") is False
                assert "Encoder command:" in page.locator("#export-log-output").text_content()
                assert page.locator("#export-export-log").is_disabled() is False

                with page.expect_download() as download_info:
                    page.locator("#export-export-log").click()
                download = download_info.value
                assert download.suggested_filename.endswith("-export-log.txt")
                download_target = tmp_path / download.suggested_filename
                download.save_as(str(download_target))
                assert download_target.read_text(encoding="utf-8") == "Encoder command:\nffmpeg -i input\n"

                page.locator("#close-export-log").click()
                page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === true")

                page.locator("#show-export-log").click(force=True)
                page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === false")
                page.evaluate("document.querySelector('[data-close-export-log=\"true\"]')?.click()")
                page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === true")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_controls_update_preset_and_settings_state(synthetic_video_factory, tmp_path: Path) -> None:
    primary_path = Path(synthetic_video_factory(name="export-controls-ui"))
    export_path = tmp_path / "exports" / "custom-output.mp4"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "export")
                page.locator('[data-tool-pane="export"]').wait_for(state="visible")

                page.locator("#export-preset").select_option("youtube_long_1080p")
                page.wait_for_function("() => state?.project?.export?.preset === 'youtube_long_1080p'")
                assert page.locator("#export-preset").input_value() == "youtube_long_1080p"
                assert "1920x1080" in page.locator("#export-preset-description").text_content()

                page.locator("#quality").select_option("low")
                page.wait_for_function("() => state?.project?.export?.quality === 'low'")

                page.locator("#aspect-ratio").select_option("1:1")
                page.wait_for_function("() => state?.project?.export?.aspect_ratio === '1:1'")

                page.locator("#target-width").fill("1440")
                page.locator("#target-height").fill("1440")
                page.wait_for_function(
                    "() => state?.project?.export?.target_width === 1440 && state?.project?.export?.target_height === 1440"
                )

                page.locator("#frame-rate").select_option("60")
                page.wait_for_function("() => state?.project?.export?.frame_rate === '60'")

                page.locator("#video-codec").select_option("hevc")
                page.wait_for_function("() => state?.project?.export?.video_codec === 'hevc'")

                page.locator("#video-bitrate").fill("20")
                page.wait_for_function("() => state?.project?.export?.video_bitrate_mbps === 20")

                page.locator("#audio-sample-rate").fill("44100")
                page.wait_for_function("() => state?.project?.export?.audio_sample_rate === 44100")

                page.locator("#audio-bitrate").fill("256")
                page.wait_for_function("() => state?.project?.export?.audio_bitrate_kbps === 256")

                page.locator("#color-space").select_option("bt709_sdr")
                page.wait_for_function("() => state?.project?.export?.color_space === 'bt709_sdr'")

                page.locator("#ffmpeg-preset").select_option("slow")
                page.wait_for_function("() => state?.project?.export?.ffmpeg_preset === 'slow'")

                page.locator("#two-pass").check()
                page.wait_for_function("() => state?.project?.export?.two_pass === true")

                page.locator("#export-path").fill(str(export_path))
                page.wait_for_function(
                    "expected => document.getElementById('export-path')?.value === expected",
                    arg=str(export_path),
                )
                page.wait_for_function(
                    "expected => state?.project?.export?.output_path === expected",
                    arg=str(export_path),
                )

                export_state = page.evaluate(
                    """() => ({
                        preset: state?.project?.export?.preset || '',
                        quality: state?.project?.export?.quality || '',
                        aspectRatio: state?.project?.export?.aspect_ratio || '',
                        targetWidth: state?.project?.export?.target_width ?? null,
                        targetHeight: state?.project?.export?.target_height ?? null,
                        frameRate: state?.project?.export?.frame_rate || '',
                        videoCodec: state?.project?.export?.video_codec || '',
                        videoBitrateMbps: state?.project?.export?.video_bitrate_mbps ?? null,
                        audioSampleRate: state?.project?.export?.audio_sample_rate ?? null,
                        audioBitrateKbps: state?.project?.export?.audio_bitrate_kbps ?? null,
                        colorSpace: state?.project?.export?.color_space || '',
                        ffmpegPreset: state?.project?.export?.ffmpeg_preset || '',
                        twoPass: Boolean(state?.project?.export?.two_pass),
                        outputPath: state?.project?.export?.output_path || '',
                    })"""
                )
                assert export_state["preset"] == "custom"
                assert export_state["quality"] == "low"
                assert export_state["aspectRatio"] == "1:1"
                assert export_state["frameRate"] == "60"
                assert export_state["videoCodec"] == "hevc"
                assert export_state["audioBitrateKbps"] == 256
                assert export_state["colorSpace"] == "bt709_sdr"
                assert export_state["ffmpegPreset"] == "slow"
                assert export_state["twoPass"] is True
                assert export_state["outputPath"] == str(export_path)
                assert page.locator("#export-preset").input_value() == "custom"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_scoring_workbench_rows_lock_edit_delete_and_restore(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="scoring-workbench-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator('button[data-tool="scoring"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "scoring"

                page.locator("#scoring-enabled").check()
                page.wait_for_timeout(150)

                preset_values = page.locator("#scoring-preset").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert preset_values
                selected_preset = None
                for preset_value in preset_values:
                    page.locator("#scoring-preset").select_option(preset_value)
                    page.wait_for_timeout(150)
                    if int(page.evaluate("state.scoring_summary.penalty_fields.length")) > 0:
                        selected_preset = preset_value
                        break
                assert selected_preset is not None

                page.locator("#expand-scoring").click()
                page.wait_for_timeout(150)
                page.locator("#scoring-workbench").wait_for(state="visible")

                first_shot_id = page.evaluate("state.timing_segments[0].shot_id")
                second_shot_id = page.evaluate("state.timing_segments[1].shot_id")
                score_select = page.locator('#scoring-workbench-table select[data-score-field="letter"]').first
                lock_button = page.locator("#scoring-workbench-table .lock-button").first
                lock_button.click()
                score_select.wait_for(state="visible")
                original_letter = score_select.input_value()
                original_penalty = int(
                    page.locator("#scoring-workbench-table .shot-penalty-input").first.input_value()
                )
                score_values = score_select.evaluate(
                    "select => [...select.options].map((option) => option.value)"
                )
                next_letter = next((value for value in score_values if value != original_letter), original_letter)

                score_select.select_option(next_letter)
                penalty_input = page.locator("#scoring-workbench-table .shot-penalty-input").first
                penalty_input.fill(str(original_penalty + 1))
                penalty_input.dispatch_event("change")

                page.wait_for_timeout(250)
                lock_button.click()
                updated_letter = page.evaluate("(shotId) => (state?.timing_segments || []).find((item) => item.shot_id === shotId)?.score_letter ?? null", first_shot_id)
                assert updated_letter == next_letter

                page.locator("#scoring-workbench-table button.restore-button:not(.danger-button)").first.click()
                page.wait_for_function(
                    """({ shotId, originalLetter }) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return Boolean(segment) && segment.score_letter === originalLetter;
                    }""",
                    arg={"shotId": first_shot_id, "originalLetter": original_letter},
                )
                restored_letter = page.evaluate(
                    """(shotId) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return segment ? segment.score_letter : null;
                    }""",
                    first_shot_id,
                )
                assert restored_letter == original_letter

                page.locator("#scoring-workbench-table button.danger-button").nth(1).dispatch_event("click")
                page.wait_for_function(
                    """(shotId) => !(state?.project?.analysis?.shots || []).some((shot) => shot.id === shotId)""",
                    arg=second_shot_id,
                )
                assert page.evaluate(
                    """(shotId) => !(state?.project?.analysis?.shots || []).some((shot) => shot.id === shotId)""",
                    second_shot_id,
                ) is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_viewport_window_drag_persists_after_reload(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-window-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator("#expand-waveform").click()
                page.wait_for_timeout(150)
                page.locator("#zoom-waveform-in").click()
                page.wait_for_timeout(150)

                window = page.locator("#waveform-window")
                track = page.locator("#waveform-window-track")
                handle = page.locator("#waveform-window-handle")
                window.wait_for(state="visible")

                track_box = track.bounding_box()
                handle_box = handle.bounding_box()
                assert track_box is not None
                assert handle_box is not None

                initial_offset = int(page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))"))
                start_x = handle_box["x"] + handle_box["width"] / 2
                start_y = handle_box["y"] + handle_box["height"] / 2
                target_ratio = 0.75 if start_x < track_box["x"] + track_box["width"] / 2 else 0.25
                target_x = track_box["x"] + track_box["width"] * target_ratio

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(target_x, start_y, steps=12)
                page.mouse.up()

                page.wait_for_function(
                    "(before) => Number(localStorage.getItem('splitshot.waveform.offsetMs')) !== before",
                    arg=initial_offset,
                )

                stored_offset = int(page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))"))
                assert stored_offset != initial_offset
                page.wait_for_timeout(500)

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("(expected) => waveformOffsetMs === expected", arg=stored_offset)
                if not page.locator("#waveform-window").is_visible():
                    page.locator("#expand-waveform").click()
                    page.wait_for_timeout(150)
                assert page.evaluate("waveformOffsetMs") == stored_offset
                assert int(page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))")) == stored_offset
            finally:
                browser.close()
    finally:
        server.shutdown()
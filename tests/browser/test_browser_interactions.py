from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover - depends on local browser install
        pytest.skip(f"Playwright Chromium is unavailable: {exc}")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


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
                badge_box = text_box.bounding_box()
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
                assert after_box["quadrant"] == "custom"
                assert after_box["x"] != before_box["x"] or after_box["y"] != before_box["y"]
            finally:
                browser.close()
    finally:
        server.shutdown()
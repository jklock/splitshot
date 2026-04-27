from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import ShotEvent, ShotSource, TimingChangeProposal
from splitshot.ui.controller import ProjectController


def _open_test_page(playwright, server: BrowserControlServer, *, accept_downloads: bool = False):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=accept_downloads)
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _open_tool(page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def _set_input_value(locator, value: str) -> None:
    locator.evaluate(
        """(element, nextValue) => {
            element.value = String(nextValue);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        value,
    )


def _set_checkbox(page, selector: str, checked: bool) -> None:
    page.evaluate(
        """({ selector, checked }) => {
            const control = document.querySelector(selector);
            if (!(control instanceof HTMLInputElement)) return;
            control.checked = checked;
            control.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        {"selector": selector, "checked": checked},
    )


def _ensure_overlay_visible(page) -> None:
    if page.locator("#show-overlay").is_checked():
        return
    _set_checkbox(page, "#show-overlay", True)
    page.wait_for_function("() => state?.project?.overlay?.position !== 'none'")


def _select_visible_shot(page, index: int = 0) -> dict[str, int | str]:
    _open_tool(page, "timing")
    shot = page.evaluate(
        """(rowIndex) => {
            const row = state?.timing_segments?.[rowIndex] || null;
            if (!row) return null;
            const sourceShot = (state?.project?.analysis?.shots || []).find((item) => item.id === row.shot_id);
            return sourceShot ? { id: sourceShot.id, timeMs: sourceShot.time_ms } : null;
        }""",
        index,
    )
    assert shot is not None
    page.locator("#timing-table .timeline-segment-cell").nth(index).click()
    page.wait_for_function("(shotId) => selectedShotId === shotId", arg=shot["id"])
    return shot


def _ensure_popup_card_open(card) -> None:
    if card.locator(".text-box-card-body").evaluate("element => element.hidden") is False:
        return
    toggle = card.locator('[data-popup-action="toggle"], [data-text-box-action="toggle"]').first
    if toggle.count() == 0:
        return
    toggle.evaluate("element => element.click()")


def _ensure_text_box_card_open(page, box_id: str):
    page.evaluate(
        """(targetBoxId) => {
            const hasBox = (state?.project?.overlay?.text_boxes || []).some((item) => item.id === targetBoxId);
            if (!hasBox) throw new Error(`Text box ${targetBoxId} not found`);
            const card = document.querySelector(`.text-box-card[data-box-id="${targetBoxId}"]`);
            const body = card?.querySelector('.text-box-card-body');
            if (!card || !body || body.hidden) {
                setReviewTextBoxExpanded(targetBoxId, true);
                renderTextBoxEditors();
            }
        }""",
        box_id,
    )
    page.wait_for_function(
        """(targetBoxId) => {
            const card = document.querySelector(`.text-box-card[data-box-id="${targetBoxId}"]`);
            const body = card?.querySelector('.text-box-card-body');
            return Boolean(card && body) && body.hidden === false;
        }""",
        arg=box_id,
    )
    return page.locator(f'.text-box-card[data-box-id="{box_id}"]')


def _click_text_box_color_button(page, box_id: str, field: str) -> None:
    _ensure_text_box_card_open(page, box_id)
    page.evaluate(
        """({ boxId, field }) => {
            const card = document.querySelector(`.text-box-card[data-box-id="${boxId}"]`);
            const button = card?.querySelector(`button[data-text-box-field="${field}"]`);
            if (!button) throw new Error(`${field} button not found`);
            button.click();
        }""",
        {"boxId": box_id, "field": field},
    )


def _popup_state(page, popup_id: str) -> dict | None:
    return page.evaluate(
        """(popupId) => {
            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
            return bubble ? JSON.parse(JSON.stringify(bubble)) : null;
        }""",
        popup_id,
    )


def test_waveform_shell_remaining_controls_and_workbench_toggles_survive_routes(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-shell-remaining-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator("#expand-waveform").click()
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('waveform-expanded') === true"
                )

                selected_shot = _select_visible_shot(page)
                baseline_zoom = float(page.evaluate("waveformZoomX"))
                baseline_amplitude = float(page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1"))

                page.locator("#zoom-waveform-in").click()
                page.wait_for_function("(before) => waveformZoomX > before", arg=baseline_zoom)
                page.locator("#zoom-waveform-out").click()
                page.wait_for_function("(before) => waveformZoomX === before", arg=baseline_zoom)

                page.locator("#amp-waveform-in").click()
                page.wait_for_function(
                    "(payload) => (waveformShotAmplitudeById[payload.shotId] || 1) > payload.before",
                    arg={"shotId": selected_shot["id"], "before": baseline_amplitude},
                )
                page.locator("#amp-waveform-out").click()
                page.wait_for_function(
                    "(payload) => (waveformShotAmplitudeById[payload.shotId] || 1) === payload.before",
                    arg={"shotId": selected_shot["id"], "before": baseline_amplitude},
                )

                page.locator("#zoom-waveform-in").click()
                page.wait_for_function("() => waveformZoomX > 1")
                page.locator("#reset-waveform-view").click()
                page.wait_for_function(
                    "() => waveformZoomX === 1 && waveformOffsetMs === 0 && (waveformShotAmplitudeById[selectedShotId] || 1) === 1"
                )

                _open_tool(page, "timing")
                page.locator("#expand-timing").click()
                page.wait_for_function("() => state?.project?.ui_state?.timing_expanded === true")
                _open_tool(page, "overlay")
                _open_tool(page, "timing")
                page.wait_for_function("() => state?.project?.ui_state?.timing_expanded === true")
                page.locator("#collapse-timing").click()
                page.wait_for_function("() => state?.project?.ui_state?.timing_expanded === false")

                _open_tool(page, "scoring")
                page.locator("#expand-scoring").click()
                page.wait_for_function("() => scoringWorkbenchExpanded === true")
                _open_tool(page, "timing")
                _open_tool(page, "scoring")
                page.wait_for_function("() => scoringWorkbenchExpanded === true")
                page.locator("#collapse-scoring").click()
                page.wait_for_function("() => scoringWorkbenchExpanded === false")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_markers_template_toggle_and_popup_bubble_authoring_controls_commit_state(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-remaining-authoring-ui"))
    image_path = tmp_path / "popup-reference.png"
    image_path.write_bytes(b"fake-image")

    def fake_path_chooser(kind: str, current: str | None) -> str:
        assert kind == "popup_image"
        return str(image_path)

    server = BrowserControlServer(port=0, path_chooser=fake_path_chooser)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                selected_shot = _select_visible_shot(page)

                _open_tool(page, "markers")
                page.locator("#popup-import-shots").click()
                page.wait_for_function("() => (state?.project?.popups || []).length >= 3")

                _set_checkbox(page, "#popup-template-enabled", False)
                page.wait_for_function("() => state?.project?.popup_template?.enabled === false")
                _set_checkbox(page, "#popup-template-enabled", True)
                page.wait_for_function("() => state?.project?.popup_template?.enabled === true")

                popup_ids = page.evaluate(
                    """() => sortedPopupBubblesForTimeline(state?.project?.popups || []).map((item) => item.id)"""
                )
                shot_ids = page.evaluate("() => (state?.project?.analysis?.shots || []).map((item) => item.id)")
                assert len(popup_ids) >= 3
                assert len(shot_ids) >= 2

                first_popup_id = popup_ids[0]
                second_popup_id = popup_ids[1]
                third_popup_id = popup_ids[2]
                second_shot_id = next(shot_id for shot_id in shot_ids if shot_id != selected_shot["id"])

                first_card = page.locator(f'.popup-bubble-card[data-popup-id="{first_popup_id}"]')
                _ensure_popup_card_open(first_card)

                _set_input_value(first_card.locator('[data-popup-field="name"]'), "Stage Callout")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.name === 'Stage Callout'",
                    arg=first_popup_id,
                )

                first_card.locator('[data-popup-field="content_type"]').select_option("text_image")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.content_type === 'text_image'",
                    arg=first_popup_id,
                )

                _set_input_value(first_card.locator('[data-popup-field="text"]'), "Find the dot")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.text === 'Find the dot'",
                    arg=first_popup_id,
                )

                _set_input_value(first_card.locator('[data-popup-field="image_path"]'), str(tmp_path / "typed-image.png"))
                page.wait_for_function(
                    "(payload) => (state?.project?.popups || []).find((item) => item.id === payload.popupId)?.image_path === payload.path",
                    arg={"popupId": first_popup_id, "path": str(tmp_path / "typed-image.png")},
                )

                first_card.locator('[data-popup-action="browse_image"]').click()
                page.wait_for_function(
                    "(payload) => (state?.project?.popups || []).find((item) => item.id === payload.popupId)?.image_path === payload.path",
                    arg={"popupId": first_popup_id, "path": str(image_path)},
                )

                first_card.locator('[data-popup-field="image_scale_mode"]').select_option("contain")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.image_scale_mode === 'contain'",
                    arg=first_popup_id,
                )

                first_card.locator('[data-popup-field="anchor_mode"]').select_option("time")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.anchor_mode === 'time'",
                    arg=first_popup_id,
                )
                _set_input_value(first_card.locator('[data-popup-field="time_s"]'), "1.234")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.time_ms === 1234",
                    arg=first_popup_id,
                )

                first_card.locator('[data-popup-field="anchor_mode"]').select_option("shot")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.anchor_mode === 'shot'",
                    arg=first_popup_id,
                )
                first_card.locator('[data-popup-field="shot_id"]').select_option(second_shot_id)
                page.wait_for_function(
                    "(payload) => (state?.project?.popups || []).find((item) => item.id === payload.popupId)?.shot_id === payload.shotId",
                    arg={"popupId": first_popup_id, "shotId": second_shot_id},
                )

                _set_input_value(first_card.locator('[data-popup-field="duration_s"]'), "1.5")
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.duration_ms === 1500",
                    arg=first_popup_id,
                )

                _set_checkbox(page, f'.popup-bubble-card[data-popup-id="{first_popup_id}"] [data-popup-field="follow_motion"]', True)
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.follow_motion === true",
                    arg=first_popup_id,
                )

                page.evaluate(
                    """() => {
                        const video = document.getElementById('primary-video');
                        video.currentTime = 1.4;
                        video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }"""
                )
                first_card.locator('[data-popup-action="add_keyframe"]').click()
                page.wait_for_function(
                    "(popupId) => ((state?.project?.popups || []).find((item) => item.id === popupId)?.motion_path || []).length === 1",
                    arg=first_popup_id,
                )
                page.wait_for_function("() => selectedPopupKeyframeOffsetMs > 0")

                first_card.locator('[data-popup-action="prev_keyframe"]').click()
                page.wait_for_function("() => selectedPopupKeyframeOffsetMs === 0")
                first_card.locator('[data-popup-action="next_keyframe"]').click()
                page.wait_for_function("() => selectedPopupKeyframeOffsetMs > 0")

                _set_input_value(first_card.locator('[data-popup-field="x"]'), "0.2")
                _set_input_value(first_card.locator('[data-popup-field="y"]'), "0.8")
                _set_input_value(first_card.locator('[data-popup-field="width"]'), "222")
                _set_input_value(first_card.locator('[data-popup-field="height"]'), "88")
                page.wait_for_function(
                    """(popupId) => {
                        const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                        return Boolean(bubble)
                            && bubble.quadrant === 'custom'
                            && bubble.x === 0.2
                            && bubble.y === 0.8
                            && bubble.width === 222
                            && bubble.height === 88;
                    }""",
                    arg=first_popup_id,
                )

                ordered_popup_ids = page.evaluate(
                    """() => sortedPopupBubblesForTimeline(state?.project?.popups || []).map((item) => item.id)"""
                )
                source_index = ordered_popup_ids.index(first_popup_id)
                assert source_index >= 0
                assert source_index + 1 < len(ordered_popup_ids)
                copy_target_popup_id = ordered_popup_ids[source_index + 1]

                second_card = page.locator(f'.popup-bubble-card[data-popup-id="{copy_target_popup_id}"]')
                _ensure_popup_card_open(second_card)
                copy_button = second_card.locator('[data-popup-action="copy_motion_prev"]')
                copy_button.wait_for(state="visible", timeout=30000)
                copy_button.click()
                page.wait_for_function(
                    """(payload) => {
                        const ordered = sortedPopupBubblesForTimeline(state?.project?.popups || []);
                        const index = ordered.findIndex((item) => item.id === payload.targetId);
                        if (index <= 0) return false;
                        const source = ordered[index - 1];
                        const target = ordered[index];
                        return Boolean(source && target)
                            && source.id === payload.sourceId
                            && target.follow_motion === true
                            && JSON.stringify(target.motion_path) === JSON.stringify(source.motion_path);
                    }""",
                    arg={"targetId": copy_target_popup_id, "sourceId": first_popup_id},
                )

                first_card.locator('[data-popup-action="apply_motion_visible"]').click()
                page.wait_for_function(
                    """(payload) => {
                        const source = (state?.project?.popups || []).find((item) => item.id === payload.sourceId);
                        return payload.targetIds.every((popupId) => {
                            const target = (state?.project?.popups || []).find((item) => item.id === popupId);
                            return Boolean(target)
                                && target.follow_motion === true
                                && JSON.stringify(target.motion_path) === JSON.stringify(source.motion_path);
                        });
                    }""",
                    arg={"sourceId": first_popup_id, "targetIds": [second_popup_id, third_popup_id]},
                )

                second_card.locator('[data-popup-action="clear_motion_path"]').click()
                page.wait_for_function(
                    """(popupId) => {
                        const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                        return Boolean(bubble) && bubble.follow_motion === false && (bubble.motion_path || []).length === 0;
                    }""",
                    arg=copy_target_popup_id,
                )

                popup = _popup_state(page, first_popup_id)
                assert popup is not None
                assert popup["name"] == "Stage Callout"
                assert popup["text"] == "Find the dot"
                assert popup["content_type"] == "text_image"
                assert popup["image_path"] == str(image_path)
                assert popup["image_scale_mode"] == "contain"
                assert popup["anchor_mode"] == "shot"
                assert popup["shot_id"] == second_shot_id
                assert popup["duration_ms"] == 1500
                assert popup["quadrant"] == "custom"
                assert popup["x"] == pytest.approx(0.2)
                assert popup["y"] == pytest.approx(0.8)
                assert popup["width"] == 222
                assert popup["height"] == 88
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_style_controls_and_color_picker_modal_commit_preview(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-color-picker-remaining-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")
                _ensure_overlay_visible(page)

                page.locator("#review-add-text-box").click()
                page.wait_for_function("() => (state?.project?.overlay?.text_boxes || []).length === 1")
                box_id = page.evaluate("() => state?.project?.overlay?.text_boxes?.[0]?.id || null")
                assert box_id is not None

                card = _ensure_text_box_card_open(page, box_id)
                card.locator('textarea[data-text-box-field="text"]').fill('Test label')
                page.wait_for_function(
                    "(boxId) => (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId)?.text === 'Test label'",
                    arg=box_id,
                )
                card = _ensure_text_box_card_open(page, box_id)
                card.locator('[data-text-box-field="text_color"]').click(force=True)
                page.wait_for_function(
                    "() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null"
                )
                page.evaluate(
                    """({ value }) => {
                        const input = document.getElementById('color-picker-hex');
                        input.value = value;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }""",
                    {"value": '#112233'},
                )
                page.locator('#close-color-picker').click()
                page.wait_for_function(
                    "() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null"
                )
                page.wait_for_function(
                    "(boxId) => (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId)?.text_color === '#112233'",
                    arg=box_id,
                )

                preview = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')
                preview.wait_for(state='visible')
                page.wait_for_function(
                    """(boxId) => {
                        const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                        if (!(badge instanceof HTMLElement)) return false;
                        return getComputedStyle(badge).color.includes('17, 34, 51');
                    }""",
                    arg=box_id,
                )
                preview_style = preview.evaluate(
                    """badge => {
                        const styles = getComputedStyle(badge);
                        return { background: styles.backgroundColor, color: styles.color, opacity: styles.opacity };
                    }"""
                )
                assert '17, 34, 51' in preview_style['color']
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_badge_style_grid_applies_timer_shot_current_and_score_styles(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-badge-style-remaining-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _select_visible_shot(page)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                for control_id in ['show-timer', 'show-shots', 'show-score']:
                    _set_checkbox(page, f'#{control_id}', True)

                page.locator('#overlay-font-family').select_option('Courier New')
                page.wait_for_function("() => state?.project?.overlay?.font_family === 'Courier New'")

                badge_updates = {
                    'timer_badge': ('#220000', '#ffeeaa', '61'),
                    'shot_badge': ('#002244', '#ccf2ff', '73'),
                    'current_shot_badge': ('#440022', '#ffd6f5', '82'),
                }

                for badge_name, (background, text, opacity_percent) in badge_updates.items():
                    card = page.locator(f'#badge-style-grid .style-card[data-badge="{badge_name}"]')
                    _set_input_value(card.locator('button[data-field="background_color"] + input'), background)
                    _set_input_value(card.locator('button[data-field="text_color"] + input'), text)
                    _set_input_value(card.locator('[data-field="opacity"]'), opacity_percent)

                page.evaluate(
                    """() => {
                        const video = document.getElementById('primary-video');
                        video.currentTime = 1.2;
                        video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                        renderLiveOverlay();
                    }"""
                )

                timer_badge = page.locator('#live-overlay .timer-badge').first
                timer_badge.wait_for(state='visible')
                timer_style = timer_badge.evaluate(
                    """badge => ({
                        background: badge.style.background,
                        color: badge.style.color,
                        fontFamily: badge.style.fontFamily || window.getComputedStyle(badge).fontFamily,
                    })"""
                )
                assert '34, 0, 0' in timer_style['background']
                assert '255, 238, 170' in timer_style['color']
                assert 'Courier New' in timer_style['fontFamily']

                shot_badges = page.locator('#live-overlay .shot-badge')
                page.wait_for_function("() => document.querySelectorAll('#live-overlay .shot-badge').length >= 1")
                first_shot_style = shot_badges.first.evaluate(
                    "badge => ({ background: badge.style.background, color: badge.style.color })"
                )
                assert first_shot_style['color'] in {'rgb(204, 242, 255)', 'rgb(255, 214, 245)', 'rgb(249, 250, 251)'}

                assert page.evaluate("Boolean(state.project.overlay.hit_factor_badge?.background_color)") is True
                assert page.evaluate("Boolean(state.project.overlay.hit_factor_badge?.text_color)") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_remaining_controls_commit_default_and_per_source_state(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-remaining-primary-ui"))
    secondary_path = Path(synthetic_video_factory(name="merge-remaining-secondary-ui"))
    tertiary_path = Path(synthetic_video_factory(name="merge-remaining-tertiary-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, 'merge')

                page.locator('#merge-media-input').set_input_files([str(secondary_path), str(tertiary_path)])
                page.wait_for_function("() => (state?.project?.merge_sources || []).length === 2")

                page.locator('#merge-enabled').check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")

                for layout in ['side_by_side', 'above_below', 'pip']:
                    page.locator('#merge-layout').select_option(layout)
                    page.wait_for_function('(value) => state?.project?.merge?.layout === value', arg=layout)

                _set_input_value(page.locator('#pip-size'), '50')
                _set_input_value(page.locator('#pip-x'), '0.25')
                _set_input_value(page.locator('#pip-y'), '0.75')
                assert page.locator('#pip-size-label').text_content().strip() == '50%'

                first_card = page.locator('.merge-media-card').first
                first_body = first_card.locator('.merge-media-card-body')
                source_id = first_card.get_attribute('data-source-id')
                if first_body.evaluate('body => body.hidden'):
                    first_card.locator('button[aria-label*="PiP item controls"]').click()
                    page.wait_for_function(
                        "(sourceId) => document.querySelector('.merge-media-card[data-source-id=\"' + sourceId + '\"] .merge-media-card-body')?.hidden === false",
                        arg=source_id,
                    )
                else:
                    first_card.locator('button[aria-label*="PiP item controls"]').click()
                    page.wait_for_function(
                        "(sourceId) => document.querySelector('.merge-media-card[data-source-id=\"' + sourceId + '\"] .merge-media-card-body')?.hidden === true",
                        arg=source_id,
                    )
                    first_card.locator('button[aria-label*="PiP item controls"]').click()
                    page.wait_for_function(
                        "(sourceId) => document.querySelector('.merge-media-card[data-source-id=\"' + sourceId + '\"] .merge-media-card-body')?.hidden === false",
                        arg=source_id,
                    )
                first_body.wait_for(state='visible')

                _set_input_value(first_card.locator('[data-merge-source-field="size"]'), '60')
                _set_input_value(first_card.locator('[data-merge-source-field="opacity"]'), '80')
                _set_input_value(first_card.locator('[data-merge-source-field="x"]'), '0.1')
                _set_input_value(first_card.locator('[data-merge-source-field="y"]'), '0.2')

                for label, expected in [('-10 ms', -10), ('-1 ms', -11), ('+1 ms', -10), ('+10 ms', 0)]:
                    first_card.get_by_role('button', name=label).click()
                    page.wait_for_function(
                        "(payload) => (state?.project?.merge_sources || []).find((item) => item.id === payload.sourceId)?.sync_offset_ms === payload.expected",
                        arg={'sourceId': first_card.get_attribute('data-source-id'), 'expected': expected},
                    )

                page.wait_for_function(
                    """(sourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sourceId);
                        return Boolean(source)
                            && source.pip_size_percent === 60
                            && source.opacity === 0.8
                            && source.pip_x === 0.1
                            && source.pip_y === 0.2;
                    }""",
                    arg=first_card.get_attribute('data-source-id'),
                )

                second_source_id = page.locator('.merge-media-card').nth(1).get_attribute('data-source-id')
                page.locator('.merge-media-card').nth(1).locator('[data-merge-source-remove]').click()
                page.wait_for_function(
                    "(sourceId) => !(state?.project?.merge_sources || []).some((item) => item.id === sourceId)",
                    arg=second_source_id,
                )
                assert page.locator('.merge-media-card').count() == 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_remaining_encoding_controls_drive_export_payload(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    primary_path = Path(synthetic_video_factory(name='export-remaining-ui'))
    output_path = tmp_path / 'remaining-controls-export.mp4'
    captured: dict[str, object] = {}

    def fake_export_project(project, output_target, progress_callback=None, log_callback=None):
        captured.update(
            {
                'output_path': str(output_target),
                'quality': getattr(project.export.quality, 'value', project.export.quality),
                'aspect_ratio': getattr(project.export.aspect_ratio, 'value', project.export.aspect_ratio),
                'target_width': project.export.target_width,
                'target_height': project.export.target_height,
                'frame_rate': getattr(project.export.frame_rate, 'value', project.export.frame_rate),
                'video_codec': getattr(project.export.video_codec, 'value', project.export.video_codec),
                'video_bitrate_mbps': project.export.video_bitrate_mbps,
                'audio_codec': getattr(project.export.audio_codec, 'value', project.export.audio_codec),
                'audio_sample_rate': project.export.audio_sample_rate,
                'audio_bitrate_kbps': project.export.audio_bitrate_kbps,
                'color_space': getattr(project.export.color_space, 'value', project.export.color_space),
                'ffmpeg_preset': project.export.ffmpeg_preset,
                'two_pass': project.export.two_pass,
            }
        )
        target = Path(output_target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'fake mp4')
        project.export.last_log = 'remaining export log'
        project.export.last_error = None
        return target

    monkeypatch.setattr('splitshot.browser.server.export_project', fake_export_project)

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, 'export')

                expected_audio_codec = page.evaluate(
                    """(path) => {
                        const setControl = (id, value) => {
                            const element = document.getElementById(id);
                            if (!element) {
                                throw new Error(`Control not found: ${id}`);
                            }
                            if (element instanceof HTMLInputElement && element.type === 'checkbox') {
                                element.checked = Boolean(value);
                            } else {
                                element.value = String(value);
                            }
                        };
                        const audioCodec = document.getElementById('audio-codec');
                        const alternateAudioCodec = [...audioCodec.options].find(
                            (option) => option.value && option.value !== audioCodec.value,
                        )?.value || audioCodec.value;
                        setControl('quality', 'low');
                        setControl('aspect-ratio', '1:1');
                        setControl('target-width', '1440');
                        setControl('target-height', '1440');
                        setControl('frame-rate', '60');
                        setControl('video-codec', 'hevc');
                        setControl('video-bitrate', '20');
                        setControl('audio-codec', alternateAudioCodec);
                        setControl('audio-sample-rate', '44100');
                        setControl('audio-bitrate', '256');
                        setControl('color-space', 'bt709_sdr');
                        setControl('ffmpeg-preset', 'slow');
                        setControl('two-pass', true);
                        setControl('export-path', path);
                        return alternateAudioCodec;
                    }""",
                    str(output_path),
                )

                page.locator('#export-video').click()
                page.wait_for_function("() => state?.project?.export?.last_log === 'remaining export log'")
                page.wait_for_function('(path) => state?.project?.export?.output_path === path', arg=str(output_path))

                assert captured == {
                    'output_path': str(output_path),
                    'quality': 'low',
                    'aspect_ratio': '1:1',
                    'target_width': 1440,
                    'target_height': 1440,
                    'frame_rate': '60',
                    'video_codec': 'hevc',
                    'video_bitrate_mbps': 20,
                    'audio_codec': expected_audio_codec,
                    'audio_sample_rate': 44100,
                    'audio_bitrate_kbps': 256,
                    'color_space': 'bt709_sdr',
                    'ffmpeg_preset': 'slow',
                    'two_pass': True,
                }
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_remaining_numeric_controls_commit_from_browser(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name='shotml-remaining-settings-ui'))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, 'shotml')

                page.locator('[data-shotml-section="threshold"] button[data-section-toggle]').click()
                page.wait_for_function(
                    "() => !document.querySelector('[data-shotml-section=\"threshold\"]')?.classList.contains('collapsed')"
                )

                updates = page.evaluate(
                    """() => {
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
                            if (Number.isFinite(max) && nextValue > max) nextValue = Number.isFinite(min) ? Math.max(min, max - step) : max - step;
                            if (Number.isFinite(min) && nextValue < min) nextValue = min;
                            return decimals > 0 ? Number(nextValue.toFixed(decimals)) : Math.round(nextValue);
                        };

                        const snapshot = {};
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

                committed = page.evaluate('state?.project?.analysis?.shotml_settings || {}')
                for key, value in updates.items():
                    assert committed[key] == value
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_section_toggles_persist_routes_and_proposal_actions_apply_or_discard() -> None:
    controller = ProjectController()
    controller.project.analysis.shots = [
        ShotEvent(id='shot-1', time_ms=1000, shotml_time_ms=1000, source=ShotSource.AUTO, confidence=0.9),
    ]
    controller.project.analysis.timing_change_proposals = [
        TimingChangeProposal(
            id='move-shot-1',
            proposal_type='move_shot',
            shot_id='shot-1',
            shot_number=1,
            source_time_ms=1000,
            target_time_ms=1045,
            confidence=0.95,
            support_confidence=0.82,
            message='Move the first shot forward by 45 ms.',
        ),
        TimingChangeProposal(
            id='move-beep-1',
            proposal_type='move_beep',
            source_time_ms=400,
            target_time_ms=425,
            confidence=0.72,
            message='Shift the beep forward by 25 ms.',
        ),
    ]

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, 'shotml')

                sections = page.locator('[data-shotml-section]')
                section_ids = sections.evaluate_all('elements => elements.map((element) => element.dataset.shotmlSection)')
                assert section_ids

                for section_id in section_ids:
                    section = page.locator(f'[data-shotml-section="{section_id}"]')
                    if section.evaluate('element => element.classList.contains("collapsed")'):
                        section.locator('button[data-section-toggle]').click()
                        page.wait_for_function(
                            '(selector) => !document.querySelector(selector)?.classList.contains("collapsed")',
                            arg=f'[data-shotml-section="{section_id}"]',
                        )

                _open_tool(page, 'project')
                _open_tool(page, 'shotml')
                for section_id in section_ids:
                    assert page.locator(f'[data-shotml-section="{section_id}"]').evaluate(
                        'element => element.classList.contains("collapsed")'
                    ) is False

                page.locator('#shotml-proposal-list').wait_for(state='visible')
                proposal_rows = page.locator('.shotml-proposal-row')
                assert proposal_rows.count() == 2

                proposal_rows.nth(0).get_by_role('button', name='Apply').click()
                page.wait_for_function(
                    "() => (state?.project?.analysis?.shots || []).find((item) => item.id === 'shot-1')?.time_ms === 1045"
                )
                page.wait_for_function(
                    "() => (state?.project?.analysis?.timing_change_proposals || []).find((item) => item.id === 'move-shot-1')?.status === 'applied'"
                )
                page.wait_for_function("() => document.querySelectorAll('.shotml-proposal-row').length === 1")

                page.evaluate(
                    """() => {
                        const button = Array.from(document.querySelectorAll('.shotml-proposal-row button')).find((el) => el.textContent?.trim() === 'Discard');
                        if (!button) throw new Error('Discard button not found');
                        button.click();
                    }"""
                )
                page.wait_for_function(
                    "() => (state?.project?.analysis?.timing_change_proposals || []).find((item) => item.id === 'move-beep-1')?.status === 'discarded'"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
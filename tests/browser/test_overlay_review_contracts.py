from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest

from splitshot.browser.server import BrowserControlServer
from splitshot.overlay.render import OverlayRenderer
from splitshot.ui.controller import ProjectController


STATIC_ROOT = Path("src/splitshot/browser/static")


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def test_overlay_api_preserves_locked_coordinates_but_renderer_uses_stack() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "show_timer": True,
                "show_draw": False,
                "show_shots": False,
                "show_score": False,
                "timer_lock_to_stack": True,
                "timer_x": 0.24,
                "timer_y": 0.28,
            },
        )

        assert state["project"]["overlay"]["timer_lock_to_stack"] is True
        assert state["project"]["overlay"]["timer_x"] == pytest.approx(0.24)
        assert state["project"]["overlay"]["timer_y"] == pytest.approx(0.28)

        badges, positioned_badges, _score_marks = OverlayRenderer()._build_badges_with_positions(controller.project, 500)
        assert any(badge.text.startswith("Timer ") for badge in badges)
        assert not any(badge.text.startswith("Timer ") for badge, _x, _y in positioned_badges)

        state = _post_json(
            f"{server.url}api/overlay",
            {
                "timer_lock_to_stack": False,
                "timer_x": 0.24,
                "timer_y": 0.28,
            },
        )

        assert state["project"]["overlay"]["timer_lock_to_stack"] is False
        badges, positioned_badges, _score_marks = OverlayRenderer()._build_badges_with_positions(controller.project, 500)
        assert not any(badge.text.startswith("Timer ") for badge in badges)
        timer_badge = next(badge_tuple for badge_tuple in positioned_badges if badge_tuple[0].text.startswith("Timer "))
        assert timer_badge[1] == pytest.approx(0.24)
        assert timer_badge[2] == pytest.approx(0.28)
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    ("payload", "expected_x", "expected_y"),
    [
        ({"quadrant": "custom", "x": 0.25, "y": ""}, 0.25, 0.5),
        ({"quadrant": "custom", "x": "", "y": 0.75}, 0.5, 0.75),
        ({"quadrant": "top_left", "x": 0.1, "y": None}, 0.1, 0.5),
    ],
)
def test_overlay_api_defaults_partial_text_box_custom_coordinates_like_preview(
    payload: dict,
    expected_x: float,
    expected_y: float,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/overlay",
            {
                "review_boxes_lock_to_stack": False,
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
                        "source": "manual",
                        "text": "Review note",
                        "background_color": "#ff0000",
                        "text_color": "#ffffff",
                        "opacity": 1.0,
                        "width": 120,
                        "height": 40,
                        **payload,
                    }
                ],
            },
        )

        box = state["project"]["overlay"]["text_boxes"][0]
        assert box["quadrant"] == "custom"
        assert box["x"] == pytest.approx(expected_x)
        assert box["y"] == pytest.approx(expected_y)
    finally:
        server.shutdown()


def test_review_stack_lock_uses_stack_rendering_without_discarding_custom_coordinates() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "show_timer": False,
                "show_draw": False,
                "show_shots": False,
                "show_score": False,
                "review_boxes_lock_to_stack": True,
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
                        "source": "manual",
                        "text": "Review Box",
                        "quadrant": "custom",
                        "x": 0.7,
                        "y": 0.2,
                        "background_color": "#ff0000",
                        "text_color": "#ffffff",
                        "opacity": 1.0,
                        "width": 140,
                        "height": 44,
                    }
                ],
            },
        )

        box = state["project"]["overlay"]["text_boxes"][0]
        assert box["quadrant"] == "custom"
        assert box["x"] == pytest.approx(0.7)
        assert box["y"] == pytest.approx(0.2)

        badges, positioned_badges, _score_marks = OverlayRenderer()._build_badges_with_positions(controller.project, 0)
        assert any(badge.text == "Review Box" for badge in badges)
        assert not any(badge.text == "Review Box" for badge, _x, _y in positioned_badges)

        state = _post_json(f"{server.url}api/overlay", {"review_boxes_lock_to_stack": False})
        box = state["project"]["overlay"]["text_boxes"][0]
        assert box["quadrant"] == "custom"
        assert box["x"] == pytest.approx(0.7)
        assert box["y"] == pytest.approx(0.2)

        badges, positioned_badges, _score_marks = OverlayRenderer()._build_badges_with_positions(controller.project, 0)
        assert not any(badge.text == "Review Box" for badge in badges)
        assert not any(badge.text == "Review Box" for badge, _x, _y in positioned_badges)
    finally:
        server.shutdown()


def test_overlay_payload_keeps_review_text_boxes_and_legacy_custom_box_in_sync() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    match = re.search(r"function readOverlayPayload\(\) \{(?P<body>.*?)\n\}", js, re.S)

    assert match is not None
    body = match.group("body")
    assert "const textBoxes = overlayTextBoxes().map((box, index) => normalizeOverlayTextBox(box, index));" in body
    assert "const primaryTextBox = preferredLegacyTextBox(textBoxes);" in body
    assert "review_boxes_lock_to_stack: $(\"review-lock-to-stack\").checked" in body
    assert "text_boxes: textBoxes.map((box) => ({" in body
    assert "custom_box_mode: primaryTextBox?.source || \"manual\"" in body
    assert "custom_box_x: primaryTextBox?.x ?? \"\"" in body
    assert "custom_box_y: primaryTextBox?.y ?? \"\"" in body


def test_overlay_color_picker_previews_then_flushes_committed_color_payloads() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert "const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;" in js
    assert "function scheduleOverlayColorCommit() {" in js
    assert "overlayColorCommitTimer = window.setTimeout(() => {" in js
    assert "scheduleOverlayApply();" in js
    assert "function flushOverlayColorCommit() {" in js
    assert "clearOverlayColorCommitTimer();" in js
    assert "function closeColorPicker({ commit = true } = {}) {" in js
    assert "if (commit) flushOverlayColorCommit();" in js
    assert "applyColorControlValue(activeColorPickerControl, normalized, { queueCommit: true });" in js
    assert "if (commit) flushOverlayColorCommit();" in js


def test_overlay_review_drag_cleanup_is_bound_to_cancel_lost_capture_and_window_interruptions() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert "function cancelOverlayDragInteractions(reason = \"interrupted\") {" in js
    assert "overlayBadgeDrag = null;" in js
    assert "textBoxDrag = null;" in js
    assert 'document.addEventListener("pointercancel", endOverlayBadgeDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endOverlayBadgeDrag);' in js
    assert 'document.addEventListener("pointercancel", endTextBoxDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endTextBoxDrag);' in js
    assert 'window.addEventListener("blur", () => cancelOverlayDragInteractions("window.blur"));' in js
    assert 'document.addEventListener("visibilitychange", () => {' in js
    assert 'cancelOverlayDragInteractions("document.hidden");' in js


def test_overlay_drag_math_uses_client_preview_frame_rect() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert "function previewFrameClientRect(video, container) {" in js
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in js
    assert "const badgeRect = customBadge.getBoundingClientRect();" in js
    assert "const startY = clamp((badgeRect.top - frameRect.top + badgeRect.height / 2) / frameRect.height, 0, 1);" in js
    assert "const anchorRect = anchorBadge?.getBoundingClientRect() || overlay?.getBoundingClientRect() || badge.getBoundingClientRect();" in js


def test_imported_summary_defaults_and_above_final_contract_are_source_visible() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    controller_source = Path("src/splitshot/ui/controller.py").read_text(encoding="utf-8")

    assert 'quadrant: source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left"' in js
    assert 'const fallbackQuadrant = source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left";' in js
    assert 'if (box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE)' in js
    assert 'source="imported_summary",' in controller_source
    assert 'quadrant="above_final",' in controller_source
    assert "sync_overlay_legacy_custom_box_fields(self.project.overlay)" in controller_source

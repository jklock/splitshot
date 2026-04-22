from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import PopupBubble, PopupMotionPoint, ScoreLetter, ScoreMark, ShotEvent, ShotSource
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


def test_review_box_lock_preserves_custom_coordinates_but_renders_from_stack_anchor() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        payload = {
            "position": "top",
            "shot_quadrant": "top_left",
            "show_timer": False,
            "show_draw": False,
            "show_shots": False,
            "show_score": False,
            "text_boxes": [
                {
                    "id": "manual-box",
                    "enabled": True,
                    "lock_to_stack": True,
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
        }
        state = _post_json(
            f"{server.url}api/overlay",
            payload,
        )

        box = state["project"]["overlay"]["text_boxes"][0]
        assert box["lock_to_stack"] is True
        assert box["quadrant"] == "custom"
        assert box["x"] == pytest.approx(0.7)
        assert box["y"] == pytest.approx(0.2)

        def render_center() -> tuple[float, float]:
            image = QImage(320, 180, QImage.Format.Format_ARGB32)
            image.fill(QColor("#000000"))
            painter = QPainter(image)
            OverlayRenderer().paint(painter, controller.project, 0, 320, 180)
            painter.end()

            red_pixels: list[tuple[int, int]] = []
            for y in range(image.height()):
                for x in range(image.width()):
                    color = image.pixelColor(x, y)
                    if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                        red_pixels.append((x, y))

            assert red_pixels
            center_x = (min(x for x, _y in red_pixels) + max(x for x, _y in red_pixels)) / 2
            center_y = (min(y for _x, y in red_pixels) + max(y for _x, y in red_pixels)) / 2
            return center_x, center_y

        locked_center_x, locked_center_y = render_center()
        assert locked_center_x < 120
        assert locked_center_y < 80

        payload["text_boxes"][0]["lock_to_stack"] = False
        state = _post_json(f"{server.url}api/overlay", payload)
        box = state["project"]["overlay"]["text_boxes"][0]
        assert box["lock_to_stack"] is False
        assert box["quadrant"] == "custom"
        assert box["x"] == pytest.approx(0.7)
        assert box["y"] == pytest.approx(0.2)

        unlocked_center_x, unlocked_center_y = render_center()
        assert unlocked_center_x == pytest.approx(320 * 0.7, abs=3)
        assert unlocked_center_y == pytest.approx(180 * 0.2, abs=3)
    finally:
        server.shutdown()


def test_review_text_box_auto_size_is_independent_of_global_bubble_size() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "show_timer": False,
                "show_draw": False,
                "show_shots": False,
                "show_score": False,
                "bubble_width": 240,
                "bubble_height": 96,
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
                        "lock_to_stack": False,
                        "source": "manual",
                        "text": "Review Box",
                        "quadrant": "custom",
                        "x": 0.5,
                        "y": 0.5,
                        "background_color": "#ff0000",
                        "text_color": "#ffffff",
                        "opacity": 1.0,
                        "width": 0,
                        "height": 0,
                    }
                ],
            },
        )

        image = QImage(320, 180, QImage.Format.Format_ARGB32)
        image.fill(QColor("#000000"))
        painter = QPainter(image)
        OverlayRenderer().paint(painter, controller.project, 0, 320, 180)
        painter.end()

        red_pixels: list[tuple[int, int]] = []
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                    red_pixels.append((x, y))

        assert red_pixels
        min_x = min(x for x, _y in red_pixels)
        max_x = max(x for x, _y in red_pixels)
        min_y = min(y for _x, y in red_pixels)
        max_y = max(y for _x, y in red_pixels)
        assert max_x - min_x < 180
        assert max_y - min_y < 80
    finally:
        server.shutdown()


def test_popup_bubble_uses_exact_shot_time_and_auto_size() -> None:
    controller = ProjectController()
    controller.project.primary_video.fps = 10
    shot = ShotEvent(id="shot-one", time_ms=101, source=ShotSource.AUTO, confidence=0.9)
    controller.project.analysis.shots = [shot]
    controller.project.popups = [PopupBubble(
        id="popup-one",
        enabled=True,
        text="Popup",
        anchor_mode="shot",
        shot_id=shot.id,
        time_ms=0,
        duration_ms=1000,
        quadrant="middle_middle",
        x=0.5,
        y=0.5,
        background_color="#ff0000",
        text_color="#ffffff",
        opacity=1.0,
        width=0,
        height=0,
    )]
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(
            f"{server.url}api/overlay",
            {
                "position": "none",
                "show_timer": False,
                "show_draw": False,
                "show_shots": False,
                "show_score": False,
            },
        )
        _post_json(
            f"{server.url}api/popups",
            {
                "popups": [
                    {
                        "id": "popup-one",
                        "enabled": True,
                        "text": "Popup",
                        "anchor_mode": "shot",
                        "shot_id": shot.id,
                        "time_ms": 0,
                        "duration_ms": 1000,
                        "quadrant": "middle_middle",
                        "x": 0.5,
                        "y": 0.5,
                        "background_color": "#ff0000",
                        "text_color": "#ffffff",
                        "opacity": 1.0,
                        "width": 0,
                        "height": 0,
                    }
                ],
            },
        )

        def render_popup(position_ms: int) -> list[tuple[int, int]]:
            image = QImage(320, 180, QImage.Format.Format_ARGB32)
            image.fill(QColor("#000000"))
            painter = QPainter(image)
            OverlayRenderer().paint(painter, controller.project, position_ms, 320, 180)
            painter.end()

            return [
                (x, y)
                for y in range(image.height())
                for x in range(image.width())
                if image.pixelColor(x, y).red() > 120
                and image.pixelColor(x, y).red() > image.pixelColor(x, y).green() + 40
                and image.pixelColor(x, y).red() > image.pixelColor(x, y).blue() + 40
            ]

        before_pixels = render_popup(100)
        on_time_pixels = render_popup(101)

        assert not before_pixels
        assert on_time_pixels
        min_x = min(x for x, _y in on_time_pixels)
        max_x = max(x for x, _y in on_time_pixels)
        min_y = min(y for _x, y in on_time_pixels)
        max_y = max(y for _x, y in on_time_pixels)
        assert max_x - min_x < 160
        assert max_y - min_y < 80
    finally:
        server.shutdown()


def test_popup_bubble_uses_shot_score_and_penalties_for_text() -> None:
    controller = ProjectController()
    controller.project.scoring.ruleset = "idpa_time_plus"
    controller.project.primary_video.fps = 10
    shot = ShotEvent(
        id="shot-score",
        time_ms=101,
        source=ShotSource.AUTO,
        confidence=0.9,
        score=ScoreMark(letter=ScoreLetter.DOWN_0, penalty_counts={"procedural_errors": 1}),
    )
    controller.project.analysis.shots = [shot]
    controller.project.popups = [PopupBubble(
        id="popup-score",
        enabled=True,
        text="",
        anchor_mode="shot",
        shot_id=shot.id,
        time_ms=0,
        duration_ms=1000,
        quadrant="middle_middle",
        x=0.5,
        y=0.5,
        background_color="#ff0000",
        text_color="#ffffff",
        opacity=1.0,
        width=0,
        height=0,
    )]

    image = QImage(320, 180, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    OverlayRenderer().paint(painter, controller.project, 101, 320, 180)
    painter.end()

    red_pixels = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).red() > 120
        and image.pixelColor(x, y).red() > image.pixelColor(x, y).green() + 40
        and image.pixelColor(x, y).red() > image.pixelColor(x, y).blue() + 40
    ]

    assert red_pixels


def test_popup_bubble_follow_motion_path_interpolates_between_points() -> None:
    controller = ProjectController()
    controller.project.popups = [PopupBubble(
        id="popup-motion",
        enabled=True,
        text="Popup",
        anchor_mode="time",
        time_ms=0,
        duration_ms=2000,
        quadrant="custom",
        x=0.25,
        y=0.25,
        follow_motion=True,
        motion_path=[PopupMotionPoint(offset_ms=1000, x=0.75, y=0.75)],
        background_color="#ff0000",
        text_color="#ffffff",
        opacity=1.0,
        width=80,
        height=40,
    )]

    def render_center(position_ms: int) -> tuple[float, float]:
        image = QImage(320, 180, QImage.Format.Format_ARGB32)
        image.fill(QColor("#000000"))
        painter = QPainter(image)
        OverlayRenderer().paint(painter, controller.project, position_ms, 320, 180)
        painter.end()

        red_pixels: list[tuple[int, int]] = []
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.red() > 120 and color.red() > color.green() + 40 and color.red() > color.blue() + 40:
                    red_pixels.append((x, y))

        assert red_pixels
        center_x = (min(x for x, _y in red_pixels) + max(x for x, _y in red_pixels)) / 2
        center_y = (min(y for _x, y in red_pixels) + max(y for _x, y in red_pixels)) / 2
        return center_x, center_y

    start_center_x, start_center_y = render_center(0)
    mid_center_x, mid_center_y = render_center(500)
    end_center_x, end_center_y = render_center(1000)

    assert start_center_x == pytest.approx(80, abs=8)
    assert start_center_y == pytest.approx(45, abs=8)
    assert mid_center_x == pytest.approx(160, abs=8)
    assert mid_center_y == pytest.approx(90, abs=8)
    assert end_center_x == pytest.approx(240, abs=8)
    assert end_center_y == pytest.approx(135, abs=8)


def test_overlay_payload_keeps_review_text_boxes_and_legacy_custom_box_in_sync() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    match = re.search(r"function readOverlayPayload\(\) \{(?P<body>.*?)\n\}", js, re.S)

    assert match is not None
    body = match.group("body")
    assert "const textBoxes = overlayTextBoxes().map((box, index) => normalizeOverlayTextBox(box, index));" in body
    assert "const primaryTextBox = preferredLegacyTextBox(textBoxes);" in body
    assert "text_boxes: textBoxes.map((box) => ({" in body
    assert "lock_to_stack: box.lock_to_stack" in body
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
    assert 'scoreLayer.style.left = `${frameRect.left}px`;' in js
    assert 'scoreLayer.style.top = `${frameRect.top}px`;' in js
    assert 'scoreLayer.style.width = `${frameRect.width}px`;' in js
    assert 'scoreLayer.style.height = `${frameRect.height}px`;' in js
    assert 'badge.style.left = `${clamp((x * frameRect.width) - (badgeWidth / 2), 0, Math.max(0, frameRect.width - badgeWidth))}px`;' in js
    assert 'badge.style.top = `${clamp((y * frameRect.height) - (badgeHeight / 2), 0, Math.max(0, frameRect.height - badgeHeight))}px`;' in js
    assert 'const effectiveKind = initialConfig?.lockId && $(initialConfig.lockId)?.checked ? "shots" : kind;' in js
    assert 'kind: effectiveKind,' in js
    assert 'sourceKind: kind,' in js
    assert '$(config.lockId).checked = false;' not in js


def test_imported_summary_defaults_and_above_final_contract_are_source_visible() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    controller_source = Path("src/splitshot/ui/controller.py").read_text(encoding="utf-8")
    renderer_source = Path("src/splitshot/overlay/render.py").read_text(encoding="utf-8")

    assert 'quadrant: source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left"' in js
    assert 'const fallbackQuadrant = source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left";' in js
    assert 'return box.text || state?.scoring_summary?.imported_overlay_text || "";' in js
    assert 'if (box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE)' in js
    assert 'textArea.disabled = false;' in js
    assert 'Leave blank to use the imported PractiScore stage summary after the final shot' in js
    assert 'return rawValue === importedSummaryDefault ? "" : rawValue;' in js
    assert 'function resolvedOverlayTextBoxSize(box) {' in js
    assert 'function overlayStackAnchorRect(overlay) {' in js
    assert 'function overlayStackTerminalRect(overlay) {' in js
    assert 'const frameClientRect = roundedRect(previewFrameClientRect(video, stage) || stage.getBoundingClientRect());' in js
    assert 'if (direction === "up") return candidateRect.top < selectedRect.top ? candidate : selected;' in js
    assert 'left = baseRect.left + (baseRect.width / 2) - (badgeRect.width / 2);' in js
    assert 'top = baseRect.top + (baseRect.height / 2) - (badgeRect.height / 2);' in js
    assert 'if (box.lock_to_stack && box.quadrant !== ABOVE_FINAL_TEXT_BOX_VALUE) {' in js
    assert 'const aboveFinalAnchorRect = box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE' in js
    assert '!(finalScoreBadge instanceof HTMLElement) && box.source === "imported_summary" ? stackAnchorRect : null' in js
    assert 'anchorBadge: box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE ? finalScoreBadge : null,' in js
    assert 'renderCustomOverlayBoxes(customOverlay, textBoxEntries, frameClientRect, overlayScale, size, finalScoreBadge, stackAnchorRect, stackTerminalRect);' in js
    assert "def _terminal_stack_rect(rects: list[QRectF], direction: str) -> QRectF | None:" in renderer_source
    assert 'rect_x = base_rect.center().x() - (badge_width / 2)' in renderer_source
    assert 'rect_y = base_rect.center().y() - (badge_height / 2)' in renderer_source
    assert 'source="imported_summary",' in controller_source
    assert 'quadrant="above_final",' in controller_source
    assert "sync_overlay_legacy_custom_box_fields(self.project.overlay)" in controller_source


def test_review_box_unlock_and_drag_preserve_rendered_position_contract() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'let textBoxRenderedPositionById = new Map();' in js
    assert 'function resolveNormalizedPointFromRect(rect, frameRect) {' in js
    assert 'function resolveRenderedTextBoxCoordinates(boxId, fallbackBox = null) {' in js
    assert 'function unlockedOverlayTextBox(box, coordinates = null) {' in js
    assert 'function syncLockedTextBoxEditorCoordinates() {' in js
    assert 'if (!locked && box.lock_to_stack && box.quadrant !== ABOVE_FINAL_TEXT_BOX_VALUE) {' in js
    assert 'return unlockedOverlayTextBox(box);' in js
    assert 'const unlockedBox = unlockedOverlayTextBox(box, resolveNormalizedPointFromRect(badgeRect, frameRect));' in js
    assert 'textBoxRenderedPositionById = nextRenderedPositions;' in js
    assert 'syncLockedTextBoxEditorCoordinates();' in js
    assert 'setReviewTextBoxExpanded(box.id, !isReviewTextBoxExpanded(box.id));' in js
    assert 'card.querySelector(".text-box-card-header")?.addEventListener("click", (event) => {' in js


def test_overlay_mode_switches_seed_from_rendered_baselines_contract() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'function resolveRenderedOverlayBadgeCoordinates(kind) {' in js
    assert 'function resetOverlayPlacementBaseline(controlId) {' in js
    assert 'function syncOverlayBadgeCoordinateControlValues() {' in js
    assert 'const seededCoordinates = resolveRenderedOverlayBadgeCoordinates("shots") || { x: 0.5, y: 0.5 };' in js
    assert 'const renderedCoordinates = resolveRenderedTextBoxCoordinates(box.id, box) || {' in js
    assert 'if (locked && !box.lock_to_stack && box.quadrant !== ABOVE_FINAL_TEXT_BOX_VALUE) {' in js
    assert 'const coords = resolveRenderedOverlayBadgeCoordinates(kind);' in js
    assert 'syncControlValue($(config.xId), coords.x);' in js
    assert 'syncControlValue($(config.yId), coords.y);' in js
    assert 'const effectiveKind = initialConfig?.lockId && $(initialConfig.lockId)?.checked ? "shots" : kind;' in js
    assert 'resetOverlayPlacementBaseline(id);' in js
    assert 'syncOverlayBadgeCoordinateControlValues();' in js
    assert '["timer-x", "timer-y", "draw-x", "draw-y"]' not in js

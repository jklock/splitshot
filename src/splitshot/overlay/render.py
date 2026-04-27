from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from splitshot.domain.models import BadgeSize, BadgeStyle, OverlayPosition, Project, overlay_text_boxes_for_render
from splitshot.presentation.popups import (
    popup_bubble_content_type,
    popup_bubble_display_text,
    popup_bubble_image_path,
    popup_bubble_image_scale_mode,
    popup_bubble_is_visible_at,
    popup_bubble_point,
)
from splitshot.scoring.logic import (
    calculate_scoring_summary,
    current_shot_index,
    format_imported_stage_overlay_text,
    shot_display_time_ms,
)
from splitshot.timeline.model import compute_split_rows, draw_time_ms, raw_time_ms, sort_shots


@dataclass(slots=True)
class Badge:
    text: str
    style: BadgeStyle
    text_color: str | None = None
    background_color: str | None = None
    width: int | None = None
    height: int | None = None
    text_runs: tuple[tuple[str, str | None], ...] | None = None
    text_bias: str = "center"
    image_path: str = ""
    image_scale_mode: str = "contain"


_FONT_SIZE = {
    BadgeSize.XS: 10,
    BadgeSize.S: 12,
    BadgeSize.M: 14,
    BadgeSize.L: 16,
    BadgeSize.XL: 20,
}

_BADGE_PADDING_X_PX = 10
_BADGE_PADDING_Y_PX = 5
_FIRST_SCORE_TOKEN_GAP = "  "

_PENALTY_LABELS = {
    "procedural_errors": "PE",
    "manual_no_shoots": "NS",
    "manual_misses": "M",
    "non_threats": "NT",
    "flagrant_penalties": "FP",
    "failures_to_do_right": "FTDR",
    "finger_pe": "FPE",
    "steel_misses": "PM",
    "stop_plate_failures": "SPF",
    "steel_not_down": "SND",
}

_ABOVE_FINAL_TEXT_BOX_QUADRANT = "above_final"

def _combined_rect(rects: list[QRectF]) -> QRectF | None:
    if not rects:
        return None
    left = min(rect.left() for rect in rects)
    top = min(rect.top() for rect in rects)
    right = max(rect.right() for rect in rects)
    bottom = max(rect.bottom() for rect in rects)
    return QRectF(left, top, max(0.0, right - left), max(0.0, bottom - top))


def _terminal_stack_rect(rects: list[QRectF], direction: str) -> QRectF | None:
    if not rects:
        return None
    if direction == "left":
        return min(rects, key=lambda rect: rect.left())
    if direction == "up":
        return min(rects, key=lambda rect: rect.top())
    if direction == "down":
        return max(rects, key=lambda rect: rect.bottom())
    return max(rects, key=lambda rect: rect.right())


def _score_token_color(project: Project, token: str) -> str | None:
    normalized_token = str(token).strip()
    if not normalized_token:
        return None
    return project.overlay.scoring_colors.get(normalized_token)


def _shot_badge_base_text(shot_number: int, split_text: str, interval_label: str | None) -> str:
    normalized_label = str(interval_label or "").strip()
    if not normalized_label or normalized_label == "Split":
        return f"Shot {shot_number} {split_text}"
    return f"Shot {shot_number} {normalized_label} {split_text}"


def _shot_score_badge_content(project: Project, shot: object, base_text: str) -> tuple[str, tuple[tuple[str, str | None], ...] | None]:
    score = getattr(shot, "score", None)
    if not project.scoring.enabled or score is None:
        return base_text, None

    text_parts: list[tuple[str, str | None]] = [
        (base_text, None),
        (_FIRST_SCORE_TOKEN_GAP, None),
        (score.letter.value, _score_token_color(project, score.letter.value)),
    ]
    plain_text = f"{base_text}{_FIRST_SCORE_TOKEN_GAP}{score.letter.value}"
    for field_id, value in score.penalty_counts.items():
        numeric = max(0.0, float(value))
        if numeric <= 0:
            continue
        label = _PENALTY_LABELS.get(field_id, field_id.replace("_", " "))
        count_text = f" x{_format_penalty_count(numeric)}"
        plain_text = f"{plain_text} {label}{count_text}"
        text_parts.extend([
            (" ", None),
            (label, _score_token_color(project, label)),
            (count_text, None),
        ])
    return plain_text, tuple(text_parts)


def _format_split_seconds(value_ms: int) -> str:
    return f"{value_ms / 1000.0:.2f}s"


def _format_elapsed_seconds(value_ms: int | None) -> str:
    if value_ms is None:
        return "--.--"
    return f"{value_ms / 1000.0:.2f}"


def _format_penalty_count(value: float) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else f"{numeric:.1f}"


def _format_penalty_counts(penalty_counts: dict[str, float]) -> str:
    parts: list[str] = []
    for field_id, value in penalty_counts.items():
        numeric = float(value)
        if numeric <= 0:
            continue
        label = _PENALTY_LABELS.get(field_id, field_id.replace("_", " "))
        parts.append(f"{label} x{_format_penalty_count(numeric)}")
    return ", ".join(parts)


def _text_bias_for_direction(direction: str | None) -> str:
    if direction == "left":
        return "right"
    if direction == "right":
        return "left"
    return "center"


def _standard_badge_texts(project: Project) -> tuple[str, ...]:
    texts: list[str] = []
    shots = sort_shots(project.analysis.shots)
    split_row_by_shot_id = {
        row.shot_id: row
        for row in compute_split_rows(project)
        if row.shot_id is not None
    }

    if project.overlay.show_timer:
        texts.append(f"Timer {_format_elapsed_seconds(raw_time_ms(project))}")

    draw_value = draw_time_ms(project)
    if project.overlay.show_draw and draw_value is not None:
        texts.append(f"Draw {_format_elapsed_seconds(draw_value)}")

    if project.overlay.show_shots:
        for index, shot in enumerate(shots, start=1):
            split_row = split_row_by_shot_id.get(shot.id)
            split_ms = None if split_row is None else split_row.split_ms
            split_text = _format_split_seconds(max(0, split_ms or 0))
            base_text = _shot_badge_base_text(
                index,
                split_text,
                None if split_row is None else split_row.interval_label,
            )
            score_text, _score_runs = _shot_score_badge_content(project, shot, base_text)
            texts.append(score_text)

    if project.overlay.show_score and project.scoring.enabled:
        summary = calculate_scoring_summary(project)
        if summary["display_value"] != "--":
            texts.append(f"{summary['display_label']} {summary['display_value']}")

    return tuple(texts)


def _auto_badge_size(texts: tuple[str, ...], metrics, line_height: int | None = None) -> tuple[int, int] | None:
    if not texts:
        return None
    text_width = 0
    text_height = 0
    resolved_line_height = max(1, int(line_height or metrics.height()))
    for text in texts:
        lines = str(text or "").splitlines() or [""]
        text_width = max(text_width, max(metrics.horizontalAdvance(line or " ") for line in lines))
        text_height = max(text_height, resolved_line_height * max(1, len(lines)))
    if text_width <= 0 or text_height <= 0:
        return None
    return (
        text_width + (_BADGE_PADDING_X_PX * 2),
        text_height + (_BADGE_PADDING_Y_PX * 2),
    )


def _badge_line_height(font: QFont, metrics) -> int:
    pixel_size = font.pixelSize()
    if pixel_size > 0:
        return max(1, int(pixel_size))
    return max(1, int(metrics.height()))


class OverlayRenderer:
    def build_badges(
        self,
        project: Project,
        position_ms: int,
    ) -> tuple[list[Badge], list[tuple[str, float, float, float]]]:
        badges, positioned_badges, score_marks = self._build_badges_with_positions(project, position_ms)
        return badges + [badge for badge, _x, _y in positioned_badges], score_marks

    def _build_badges_with_positions(
        self,
        project: Project,
        position_ms: int,
    ) -> tuple[list[Badge], list[tuple[Badge, float, float]], list[tuple[str, float, float, float]]]:
        if project.overlay.position == OverlayPosition.NONE:
            return [], [], []
        shots = sort_shots(project.analysis.shots)
        current_index = current_shot_index(project, position_ms)
        badges: list[Badge] = []
        positioned_badges: list[tuple[Badge, float, float]] = []
        split_rows = compute_split_rows(project)
        split_row_by_shot_id = {
            row.shot_id: row
            for row in split_rows
            if row.shot_id is not None
        }

        def append_badge(badge: Badge, x: float | None = None, y: float | None = None) -> None:
            if x is not None and y is not None:
                positioned_badges.append((badge, x, y))
                return
            badges.append(badge)

        beep_time = project.analysis.beep_time_ms_primary
        elapsed = max(0, position_ms - beep_time) if beep_time is not None else position_ms
        if beep_time is not None and shots:
            elapsed = min(elapsed, max(0, shots[-1].time_ms - beep_time))
        if project.overlay.show_timer:
            append_badge(
                Badge(f"Timer {_format_elapsed_seconds(elapsed)}", project.overlay.timer_badge),
                None if project.overlay.timer_lock_to_stack else project.overlay.timer_x,
                None if project.overlay.timer_lock_to_stack else project.overlay.timer_y,
            )

        draw_value = draw_time_ms(project)
        first_shot_time = None if not shots else shot_display_time_ms(project, shots[0].time_ms)
        if (
            project.overlay.show_draw
            and draw_value is not None
            and first_shot_time is not None
            and position_ms < first_shot_time
        ):
            append_badge(
                Badge(f"Draw {_format_elapsed_seconds(draw_value)}", project.overlay.shot_badge),
                None if project.overlay.draw_lock_to_stack else project.overlay.draw_x,
                None if project.overlay.draw_lock_to_stack else project.overlay.draw_y,
            )

        final_shot_time = None if not shots else shot_display_time_ms(project, shots[-1].time_ms)
        final_shot_reached = final_shot_time is not None and position_ms >= final_shot_time

        if project.overlay.show_shots and current_index is not None:
            max_visible = max(1, int(project.overlay.max_visible_shots))
            start = max(0, current_index - max_visible + 1)
            for index in range(start, current_index + 1):
                shot = shots[index]
                split_row = split_row_by_shot_id.get(shot.id)
                split_ms = None if split_row is None else split_row.split_ms
                split_text = _format_split_seconds(max(0, split_ms or 0))
                style = (
                    project.overlay.current_shot_badge if index == current_index else project.overlay.shot_badge
                )
                base_text = _shot_badge_base_text(
                    index + 1,
                    split_text,
                    None if split_row is None else split_row.interval_label,
                )
                score_text, score_runs = _shot_score_badge_content(project, shot, base_text)
                badges.append(
                    Badge(
                        score_text,
                        style,
                        style.text_color,
                        None,
                        text_runs=score_runs,
                        text_bias=_text_bias_for_direction(project.overlay.shot_direction),
                    )
                )

        if final_shot_reached and project.scoring.enabled and project.overlay.show_score:
            summary = calculate_scoring_summary(project)
            if summary["display_value"] != "--":
                append_badge(
                    Badge(
                        f"{summary['display_label']} {summary['display_value']}",
                        project.overlay.hit_factor_badge,
                    ),
                    None if project.overlay.score_lock_to_stack else project.overlay.score_x,
                    None if project.overlay.score_lock_to_stack else project.overlay.score_y,
                )

        score_marks: list[tuple[str, float, float, float]] = []

        return badges, positioned_badges, score_marks

    @staticmethod
    def _text_box_text(project: Project, position_ms: int, source: str, text: str, enabled: bool) -> str:
        if not enabled:
            return ""
        if source == "imported_summary":
            final_shot_time = (
                shot_display_time_ms(project, project.analysis.shots[-1].time_ms)
                if project.analysis.shots
                else None
            )
            if final_shot_time is None or position_ms < final_shot_time:
                return ""
            override_text = text.strip()
            if override_text:
                return override_text
            return format_imported_stage_overlay_text(project.scoring.imported_stage).strip()
        return text.strip()

    def paint(self, painter: QPainter, project: Project, position_ms: int, width: int, height: int) -> None:
        has_visible_popup = any(
            popup.enabled
            and popup_bubble_display_text(project, popup).strip()
            and popup_bubble_is_visible_at(project, popup, position_ms)
            for popup in project.popups
        )
        if project.overlay.position == OverlayPosition.NONE and not has_visible_popup:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        font_size = project.overlay.font_size or _FONT_SIZE[project.overlay.badge_size]
        font = QFont(project.overlay.font_family or "Helvetica Neue")
        font.setPixelSize(max(1, int(font_size)))
        font.setBold(project.overlay.font_bold)
        font.setItalic(project.overlay.font_italic)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = _badge_line_height(font, metrics)
        auto_badge_size = _auto_badge_size(_standard_badge_texts(project), metrics, line_height=line_height)

        badges, positioned_badges, score_marks = self._build_badges_with_positions(project, position_ms)
        final_shot_time = None if not project.analysis.shots else shot_display_time_ms(project, project.analysis.shots[-1].time_ms)
        final_shot_reached = final_shot_time is not None and position_ms >= final_shot_time
        score_summary = calculate_scoring_summary(project) if project.scoring.enabled else None
        has_final_score_badge = (
            final_shot_reached
            and project.overlay.show_score
            and project.scoring.enabled
            and score_summary is not None
            and score_summary["display_value"] != "--"
        )

        final_score_rect: QRectF | None = None
        badge_rects = self._paint_badges(painter, badges, project, width, height, auto_badge_size=auto_badge_size)
        stack_anchor_rect = _combined_rect(badge_rects)
        stack_terminal_rect = _terminal_stack_rect(badge_rects, project.overlay.shot_direction)
        if has_final_score_badge and project.overlay.score_lock_to_stack and badge_rects:
            final_score_rect = badge_rects[-1]
        for index, (badge, x, y) in enumerate(positioned_badges):
            rects = self._paint_badges(
                painter,
                [badge],
                project,
                width,
                height,
                quadrant="custom",
                custom_x=x,
                custom_y=y,
                auto_badge_size=auto_badge_size,
            )
            if has_final_score_badge and not project.overlay.score_lock_to_stack and index == len(positioned_badges) - 1 and rects:
                final_score_rect = rects[-1]
        text_boxes = [] if project.overlay.position == OverlayPosition.NONE else overlay_text_boxes_for_render(project.overlay)
        for text_box in text_boxes:
            text_value = self._text_box_text(
                project,
                position_ms,
                text_box.source,
                text_box.text,
                text_box.enabled,
            )
            if not text_value:
                continue
            custom_style = BadgeStyle(
                background_color=text_box.background_color or project.overlay.hit_factor_badge.background_color,
                text_color=text_box.text_color or project.overlay.hit_factor_badge.text_color,
                opacity=text_box.opacity,
            )
            text_box_auto_size = _auto_badge_size((text_value,), metrics, line_height=line_height)
            if text_box.lock_to_stack and text_box.quadrant != _ABOVE_FINAL_TEXT_BOX_QUADRANT:
                rects = self._paint_badges(
                    painter,
                    [
                        Badge(
                            text_value,
                            custom_style,
                            width=text_box.width or None,
                            height=text_box.height or None,
                        )
                    ],
                    project,
                    width,
                    height,
                    quadrant=project.overlay.shot_quadrant,
                    anchor_rect=None,
                    after_rect=stack_terminal_rect,
                    auto_badge_size=text_box_auto_size,
                    use_project_bubble_size=False,
                )
                if rects:
                    stack_terminal_rect = rects[-1]
                continue
            text_box_quadrant = text_box.quadrant
            anchor_rect = final_score_rect
            if (
                text_box_quadrant == _ABOVE_FINAL_TEXT_BOX_QUADRANT
                and anchor_rect is None
                and getattr(text_box, "source", "") == "imported_summary"
            ):
                anchor_rect = stack_anchor_rect
            if text_box_quadrant == _ABOVE_FINAL_TEXT_BOX_QUADRANT and anchor_rect is None:
                text_box_quadrant = "top_middle"
            self._paint_badges(
                painter,
                [
                    Badge(
                        text_value,
                        custom_style,
                        width=text_box.width or None,
                        height=text_box.height or None,
                    )
                ],
                project,
                width,
                height,
                quadrant=text_box_quadrant,
                custom_x=text_box.x,
                custom_y=text_box.y,
                anchor_rect=anchor_rect,
                auto_badge_size=text_box_auto_size,
                use_project_bubble_size=False,
            )
        for popup in project.popups:
            popup_text = popup_bubble_display_text(project, popup)
            popup_content_type = popup_bubble_content_type(popup)
            popup_image_path = popup_bubble_image_path(popup)
            popup_has_text = popup_content_type in {"text", "text_image"} and bool(popup_text.strip())
            popup_has_image = popup_content_type in {"image", "text_image"} and bool(popup_image_path)
            if (
                not popup.enabled
                or (not popup_has_text and not popup_has_image)
                or not popup_bubble_is_visible_at(project, popup, position_ms)
            ):
                continue
            popup_style = BadgeStyle(
                background_color=popup.background_color,
                text_color=popup.text_color,
                opacity=popup.opacity,
            )
            popup_auto_size = _auto_badge_size((popup_text,), metrics, line_height=line_height)
            popup_x, popup_y = popup_bubble_point(project, popup, position_ms)
            self._paint_badges(
                painter,
                [
                    Badge(
                        popup_text if popup_has_text else "",
                        popup_style,
                        width=popup.width or None,
                        height=popup.height or None,
                        image_path=popup_image_path,
                        image_scale_mode=popup_bubble_image_scale_mode(popup),
                    )
                ],
                project,
                width,
                height,
                quadrant="custom",
                custom_x=popup_x,
                custom_y=popup_y,
                auto_badge_size=popup_auto_size,
                use_project_bubble_size=False,
            )
        self._paint_scores(painter, project, score_marks, width, height)

        painter.restore()

    def _paint_badges(
        self,
        painter: QPainter,
        badges: list[Badge],
        project: Project,
        width: int,
        height: int,
        quadrant: str | None = None,
        custom_x: float | None = None,
        custom_y: float | None = None,
        auto_badge_size: tuple[int, int] | None = None,
        anchor_rect: QRectF | None = None,
        after_rect: QRectF | None = None,
        use_project_bubble_size: bool = True,
    ) -> list[QRectF]:
        if not badges:
            return []

        position = project.overlay.position
        font_size = project.overlay.font_size or _FONT_SIZE[project.overlay.badge_size]
        font = QFont(project.overlay.font_family or "Helvetica Neue")
        font.setPixelSize(max(1, int(font_size)))
        font.setBold(project.overlay.font_bold)
        font.setItalic(project.overlay.font_italic)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = _badge_line_height(font, metrics)
        padding_y = _BADGE_PADDING_Y_PX
        padding_x = _BADGE_PADDING_X_PX
        gap = max(0, int(project.overlay.spacing))
        frame_padding = max(0, int(project.overlay.margin))
        quadrant_value = quadrant or project.overlay.shot_quadrant

        x_override = project.overlay.custom_x if custom_x is None and quadrant_value == "custom" else custom_x
        y_override = project.overlay.custom_y if custom_y is None and quadrant_value == "custom" else custom_y
        if quadrant_value == "custom":
            if x_override is None:
                x_override = 0.5
            if y_override is None:
                y_override = 0.5

        previous_rect: QRectF | None = None
        painted_rects: list[QRectF] = []
        for index, badge in enumerate(badges):
            lines = badge.text.splitlines() or [""]
            image = QImage(badge.image_path) if badge.image_path else QImage()
            has_image = not image.isNull()
            if badge.text_runs:
                text_width = sum(metrics.horizontalAdvance(segment_text) for segment_text, _segment_color in badge.text_runs)
            else:
                text_width = max(
                    max(metrics.horizontalAdvance(line) for line in lines),
                    self._minimum_badge_text_width(metrics, badge.text),
                )
            text_height = line_height * max(1, len(lines))
            explicit_width = int(badge.width or (project.overlay.bubble_width if use_project_bubble_size else 0) or 0)
            explicit_height = int(badge.height or (project.overlay.bubble_height if use_project_bubble_size else 0) or 0)
            fallback_width = text_width + (padding_x * 2)
            fallback_height = text_height + (padding_y * 2)
            if has_image:
                fallback_width = max(fallback_width, min(320, max(220, image.width())))
                image_height = min(220, max(124, image.height()))
                fallback_height = max(
                    fallback_height,
                    image_height if not badge.text else image_height + text_height + 14,
                )
            badge_width = explicit_width if explicit_width > 0 else (auto_badge_size[0] if auto_badge_size else fallback_width)
            badge_height = explicit_height if explicit_height > 0 else (auto_badge_size[1] if auto_badge_size else fallback_height)
            base_rect = previous_rect or after_rect
            if base_rect is None:
                if quadrant_value == "custom":
                    rect_x = (max(0.0, min(1.0, float(x_override))) * width) - (badge_width / 2)
                    rect_y = (max(0.0, min(1.0, float(y_override))) * height) - (badge_height / 2)
                elif quadrant_value == _ABOVE_FINAL_TEXT_BOX_QUADRANT and anchor_rect is not None:
                    rect_x = anchor_rect.center().x() - (badge_width / 2)
                    rect_y = anchor_rect.top() - gap - badge_height
                else:
                    rect_x, rect_y = self._first_badge_position(
                        width,
                        height,
                        badge_width,
                        badge_height,
                        frame_padding,
                        quadrant_value,
                    )
                rect_x = max(0.0, min(rect_x, max(0.0, width - badge_width)))
                rect_y = max(0.0, min(rect_y, max(0.0, height - badge_height)))
            else:
                center_on_base = after_rect is not None
                rect_x = base_rect.x()
                rect_y = base_rect.y()
                if project.overlay.shot_direction == "right":
                    rect_x = base_rect.x() + base_rect.width() + gap
                    if center_on_base:
                        rect_y = base_rect.center().y() - (badge_height / 2)
                elif project.overlay.shot_direction == "left":
                    rect_x = base_rect.x() - badge_width - gap
                    if center_on_base:
                        rect_y = base_rect.center().y() - (badge_height / 2)
                elif project.overlay.shot_direction == "up":
                    if center_on_base:
                        rect_x = base_rect.center().x() - (badge_width / 2)
                    rect_y = base_rect.y() - badge_height - gap
                else:
                    if center_on_base:
                        rect_x = base_rect.center().x() - (badge_width / 2)
                    rect_y = base_rect.y() + base_rect.height() + gap
                if center_on_base:
                    rect_x = max(0.0, min(rect_x, max(0.0, width - badge_width)))
                    rect_y = max(0.0, min(rect_y, max(0.0, height - badge_height)))
            rect = QRectF(rect_x, rect_y, badge_width, badge_height)
            previous_rect = rect
            painted_rects.append(rect)
            text_bias = badge.text_bias or "center"

            background = QColor(badge.background_color or badge.style.background_color)
            background.setAlphaF(badge.style.opacity)
            painter.setPen(Qt.NoPen)
            painter.setBrush(background)
            if project.overlay.style_type == "bubble":
                radius = rect.height() / 2
            elif project.overlay.style_type == "rounded":
                radius = 16
            else:
                radius = 0
            if radius:
                painter.drawRoundedRect(rect, radius, radius)
            else:
                painter.drawRect(rect)
            text_rect = rect.adjusted(padding_x, padding_y, -padding_x, -padding_y)
            if has_image:
                image_rect = QRectF(text_rect)
                if badge.text:
                    image_rect.setBottom(max(image_rect.top(), image_rect.bottom() - line_height - 6))
                source_rect = QRectF(0.0, 0.0, float(image.width()), float(image.height()))
                if badge.image_scale_mode == "cover" and image_rect.width() > 0 and image_rect.height() > 0:
                    source_ratio = image.width() / max(1.0, image.height())
                    target_ratio = image_rect.width() / max(1.0, image_rect.height())
                    if source_ratio > target_ratio:
                        cropped_width = image.height() * target_ratio
                        source_rect.setLeft((image.width() - cropped_width) / 2.0)
                        source_rect.setWidth(cropped_width)
                    else:
                        cropped_height = image.width() / max(0.0001, target_ratio)
                        source_rect.setTop((image.height() - cropped_height) / 2.0)
                        source_rect.setHeight(cropped_height)
                painter.drawImage(image_rect, image, source_rect)
            if badge.text_runs:
                default_color = QColor(badge.text_color or badge.style.text_color)
                total_text_width = sum(metrics.horizontalAdvance(segment_text) for segment_text, _segment_color in badge.text_runs)
                if text_bias == "left":
                    start_x = text_rect.left()
                elif text_bias == "right":
                    start_x = text_rect.right() - total_text_width
                else:
                    start_x = text_rect.left() + max(0.0, (text_rect.width() - total_text_width) / 2)
                baseline_y = text_rect.top() + max(0.0, (text_rect.height() - metrics.height()) / 2) + metrics.ascent()
                cursor_x = start_x
                for segment_text, segment_color in badge.text_runs:
                    if not segment_text:
                        continue
                    painter.setPen(QColor(segment_color) if segment_color else default_color)
                    painter.drawText(QPointF(cursor_x, baseline_y), segment_text)
                    cursor_x += metrics.horizontalAdvance(segment_text)
            else:
                painter.setPen(QColor(badge.text_color or badge.style.text_color))
                if len(lines) > 1:
                    total_text_height = line_height * len(lines)
                    line_top = text_rect.top() + max(0.0, (text_rect.height() - total_text_height) / 2)
                    baseline_offset = min(metrics.ascent(), line_height)
                    painter.save()
                    painter.setClipRect(text_rect)
                    for line_index, line in enumerate(lines):
                        line_text = line or " "
                        line_width = metrics.horizontalAdvance(line_text)
                        if text_bias == "left":
                            line_x = text_rect.left()
                        elif text_bias == "right":
                            line_x = text_rect.right() - line_width
                        else:
                            line_x = text_rect.left() + max(0.0, (text_rect.width() - line_width) / 2)
                        baseline_y = line_top + (line_index * line_height) + baseline_offset
                        painter.drawText(QPointF(line_x, baseline_y), line)
                    painter.restore()
                else:
                    text_flags = Qt.AlignVCenter
                    if text_bias == "left":
                        text_flags |= Qt.AlignLeft
                    elif text_bias == "right":
                        text_flags |= Qt.AlignRight
                    else:
                        text_flags |= Qt.AlignHCenter
                    painter.drawText(
                        text_rect,
                        text_flags,
                        badge.text,
                    )
        return painted_rects

    @staticmethod
    def _first_badge_position(
        width: int,
        height: int,
        badge_width: int,
        badge_height: int,
        margin: int,
        quadrant: str,
    ) -> tuple[float, float]:
        vertical, horizontal = quadrant.split("_", 1) if "_" in quadrant else ("bottom", "left")
        x_map = {
            "left": float(margin),
            "middle": max(0.0, (width - badge_width) / 2),
            "right": max(0.0, width - badge_width - margin),
        }
        y_map = {
            "top": float(margin),
            "middle": max(0.0, (height - badge_height) / 2),
            "bottom": max(0.0, height - badge_height - margin),
        }
        return x_map.get(horizontal, float(margin)), y_map.get(vertical, float(margin))

    @staticmethod
    def _minimum_badge_text_width(metrics, text: str) -> int:
        if text.startswith("Timer"):
            return metrics.horizontalAdvance("Timer 00.00")
        if text.startswith("Draw"):
            return metrics.horizontalAdvance("Draw 00.00")
        if text.startswith("Hit Factor"):
            return metrics.horizontalAdvance("Hit Factor 00.00")
        if text.startswith("Final"):
            return metrics.horizontalAdvance("Final 00.00")
        return 0

    def _paint_scores(
        self,
        painter: QPainter,
        project: Project,
        score_marks: list[tuple[str, float, float, float]],
        width: int,
        height: int,
    ) -> None:
        if not score_marks:
            return

        for letter, x_norm, y_norm, alpha in score_marks:
            color = QColor(project.overlay.scoring_colors.get(letter, "#FFFFFF"))
            color.setAlphaF(alpha)
            painter.setPen(color)
            font = QFont("Helvetica Neue")
            font.setPixelSize(28)
            font.setBold(True)
            painter.setFont(font)
            point = QPointF(x_norm * width, y_norm * height)
            painter.drawText(point, letter)

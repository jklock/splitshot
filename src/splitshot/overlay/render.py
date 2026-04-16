from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from splitshot.domain.models import BadgeSize, BadgeStyle, OverlayPosition, Project, overlay_text_boxes_for_render
from splitshot.scoring.logic import calculate_scoring_summary, format_imported_stage_overlay_text
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


_FONT_SIZE = {
    BadgeSize.XS: 10,
    BadgeSize.S: 12,
    BadgeSize.M: 14,
    BadgeSize.L: 16,
    BadgeSize.XL: 20,
}

_BADGE_PADDING_X_PX = 10
_BADGE_PADDING_Y_PX = 5

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

    text_parts: list[tuple[str, str | None]] = [(base_text, None), (" ", None), (score.letter.value, _score_token_color(project, score.letter.value))]
    plain_text = f"{base_text} {score.letter.value}"
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


def _auto_badge_size(texts: tuple[str, ...], metrics) -> tuple[int, int] | None:
    if not texts:
        return None
    text_width = 0
    text_height = 0
    for text in texts:
        lines = str(text or "").splitlines() or [""]
        text_width = max(text_width, max(metrics.horizontalAdvance(line or " ") for line in lines))
        text_height = max(text_height, metrics.height() * max(1, len(lines)))
    if text_width <= 0 or text_height <= 0:
        return None
    return (
        text_width + (_BADGE_PADDING_X_PX * 2),
        text_height + (_BADGE_PADDING_Y_PX * 2),
    )


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
        shots = sort_shots(project.analysis.shots)
        current_index = None
        for index, shot in enumerate(shots):
            if shot.time_ms <= position_ms:
                current_index = index
            else:
                break
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
                project.overlay.timer_x,
                project.overlay.timer_y,
            )

        draw_value = draw_time_ms(project)
        first_shot_time = None if not shots else shots[0].time_ms
        if (
            project.overlay.show_draw
            and draw_value is not None
            and first_shot_time is not None
            and position_ms < first_shot_time
        ):
            append_badge(
                Badge(f"Draw {_format_elapsed_seconds(draw_value)}", project.overlay.shot_badge),
                project.overlay.draw_x,
                project.overlay.draw_y,
            )

        final_shot_time = None if not shots else shots[-1].time_ms
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
                    project.overlay.score_x,
                    project.overlay.score_y,
                )

        score_marks: list[tuple[str, float, float, float]] = []

        return badges, positioned_badges, score_marks

    @staticmethod
    def _text_box_text(project: Project, position_ms: int, source: str, text: str, enabled: bool) -> str:
        if not enabled:
            return ""
        if source == "imported_summary":
            final_shot_time = project.analysis.shots[-1].time_ms if project.analysis.shots else None
            if final_shot_time is None or position_ms < final_shot_time:
                return ""
            return format_imported_stage_overlay_text(project.scoring.imported_stage).strip()
        return text.strip()

    def paint(self, painter: QPainter, project: Project, position_ms: int, width: int, height: int) -> None:
        if project.overlay.position == OverlayPosition.NONE:
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
        auto_badge_size = _auto_badge_size(_standard_badge_texts(project), painter.fontMetrics())

        badges, positioned_badges, score_marks = self._build_badges_with_positions(project, position_ms)
        self._paint_badges(painter, badges, project, width, height, auto_badge_size=auto_badge_size)
        for badge, x, y in positioned_badges:
            self._paint_badges(
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
        for text_box in overlay_text_boxes_for_render(project.overlay):
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
                quadrant=text_box.quadrant,
                custom_x=text_box.x,
                custom_y=text_box.y,
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
    ) -> None:
        if not badges:
            return

        position = project.overlay.position
        font_size = project.overlay.font_size or _FONT_SIZE[project.overlay.badge_size]
        font = QFont(project.overlay.font_family or "Helvetica Neue")
        font.setPixelSize(max(1, int(font_size)))
        font.setBold(project.overlay.font_bold)
        font.setItalic(project.overlay.font_italic)
        painter.setFont(font)
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
        for index, badge in enumerate(badges):
            metrics = painter.fontMetrics()
            lines = badge.text.splitlines() or [""]
            if badge.text_runs:
                text_width = sum(metrics.horizontalAdvance(segment_text) for segment_text, _segment_color in badge.text_runs)
            else:
                text_width = max(
                    max(metrics.horizontalAdvance(line) for line in lines),
                    self._minimum_badge_text_width(metrics, badge.text),
                )
            text_height = metrics.height() * max(1, len(lines))
            explicit_width = int(badge.width or project.overlay.bubble_width or 0)
            explicit_height = int(badge.height or project.overlay.bubble_height or 0)
            badge_width = explicit_width if explicit_width > 0 else (auto_badge_size[0] if auto_badge_size else text_width + (padding_x * 2))
            badge_height = explicit_height if explicit_height > 0 else (auto_badge_size[1] if auto_badge_size else text_height + (padding_y * 2))
            if previous_rect is None:
                if quadrant_value == "custom":
                    rect_x = (max(0.0, min(1.0, float(x_override))) * width) - (badge_width / 2)
                    rect_y = (max(0.0, min(1.0, float(y_override))) * height) - (badge_height / 2)
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
                rect_x = previous_rect.x()
                rect_y = previous_rect.y()
                if project.overlay.shot_direction == "right":
                    rect_x = previous_rect.x() + previous_rect.width() + gap
                elif project.overlay.shot_direction == "left":
                    rect_x = previous_rect.x() - badge_width - gap
                elif project.overlay.shot_direction == "up":
                    rect_y = previous_rect.y() - badge_height - gap
                else:
                    rect_y = previous_rect.y() + previous_rect.height() + gap
            rect = QRectF(rect_x, rect_y, badge_width, badge_height)
            previous_rect = rect

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
                text_flags = Qt.AlignCenter
                if "\n" in badge.text:
                    text_flags |= Qt.TextWordWrap
                painter.drawText(
                    text_rect,
                    text_flags,
                    badge.text,
                )

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

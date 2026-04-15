from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from splitshot.domain.models import BadgeSize, BadgeStyle, OverlayPosition, Project
from splitshot.scoring.logic import calculate_scoring_summary, format_imported_stage_overlay_text
from splitshot.timeline.model import draw_time_ms


@dataclass(slots=True)
class Badge:
    text: str
    style: BadgeStyle
    text_color: str | None = None
    width: int | None = None
    height: int | None = None


_FONT_SIZE = {
    BadgeSize.XS: 10,
    BadgeSize.S: 12,
    BadgeSize.M: 14,
    BadgeSize.L: 16,
    BadgeSize.XL: 20,
}

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
        shots = sorted(project.analysis.shots, key=lambda shot: shot.time_ms)
        current_index = None
        for index, shot in enumerate(shots):
            if shot.time_ms <= position_ms:
                current_index = index
            else:
                break
        badges: list[Badge] = []
        positioned_badges: list[tuple[Badge, float, float]] = []

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
                if index == 0:
                    split_text = _format_split_seconds(shot.time_ms - (beep_time or 0))
                else:
                    split_text = _format_split_seconds(shot.time_ms - shots[index - 1].time_ms)
                style = (
                    project.overlay.current_shot_badge if index == current_index else project.overlay.shot_badge
                )
                score_text = ""
                if project.scoring.enabled and shot.score:
                    score_text = f" {shot.score.letter.value}"
                    penalty_text = _format_penalty_counts(shot.score.penalty_counts)
                    if penalty_text:
                        score_text = f"{score_text} {penalty_text}"
                score_color = (
                    project.overlay.scoring_colors.get(shot.score.letter.value)
                    if project.scoring.enabled and shot.score
                    else None
                )
                badges.append(Badge(f"Shot {index + 1} {split_text}{score_text}", style, score_color))

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
    def _custom_box_text(project: Project, position_ms: int) -> str:
        if not project.overlay.custom_box_enabled:
            return ""

        if project.overlay.custom_box_mode == "imported_summary":
            final_shot_time = project.analysis.shots[-1].time_ms if project.analysis.shots else None
            if final_shot_time is None or position_ms < final_shot_time:
                return ""
            return format_imported_stage_overlay_text(project.scoring.imported_stage).strip()

        return project.overlay.custom_box_text.strip()

    def paint(self, painter: QPainter, project: Project, position_ms: int, width: int, height: int) -> None:
        if project.overlay.position == OverlayPosition.NONE:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        badges, positioned_badges, score_marks = self._build_badges_with_positions(project, position_ms)
        self._paint_badges(painter, badges, project, width, height)
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
            )
        custom_box_text = self._custom_box_text(project, position_ms)
        if custom_box_text:
            custom_style = BadgeStyle(
                background_color=project.overlay.custom_box_background_color or project.overlay.hit_factor_badge.background_color,
                text_color=project.overlay.custom_box_text_color or project.overlay.hit_factor_badge.text_color,
                opacity=project.overlay.custom_box_opacity,
            )
            self._paint_badges(
                painter,
                [
                    Badge(
                        custom_box_text,
                        custom_style,
                        width=project.overlay.custom_box_width or None,
                        height=project.overlay.custom_box_height or None,
                    )
                ],
                project,
                width,
                height,
                quadrant=project.overlay.custom_box_quadrant,
                custom_x=project.overlay.custom_box_x,
                custom_y=project.overlay.custom_box_y,
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
        padding_y = max(2, int(project.overlay.spacing))
        padding_x = max(6, int(project.overlay.spacing * 1.5))
        gap = max(0, int(project.overlay.margin))
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
            text_width = max(
                max(metrics.horizontalAdvance(line) for line in lines),
                self._minimum_badge_text_width(metrics, badge.text),
            )
            text_height = metrics.height() * max(1, len(lines))
            explicit_width = int(badge.width or project.overlay.bubble_width or 0)
            explicit_height = int(badge.height or project.overlay.bubble_height or 0)
            badge_width = explicit_width if explicit_width > 0 else text_width + (padding_x * 2)
            badge_height = explicit_height if explicit_height > 0 else text_height + (padding_y * 2)
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
                        gap,
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

            background = QColor(badge.style.background_color)
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
            painter.setPen(QColor(badge.text_color or badge.style.text_color))
            text_flags = Qt.AlignCenter
            if "\n" in badge.text:
                text_flags |= Qt.TextWordWrap
            painter.drawText(
                rect.adjusted(padding_x, padding_y, -padding_x, -padding_y),
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

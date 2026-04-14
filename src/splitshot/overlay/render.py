from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from splitshot.domain.models import BadgeSize, BadgeStyle, OverlayPosition, Project
from splitshot.scoring.logic import calculate_scoring_summary, current_shot_index, format_imported_stage_overlay_text
from splitshot.timeline.model import draw_time_ms
from splitshot.utils.time import format_time_ms


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


def _format_split_seconds(value_ms: int) -> str:
    return f"{value_ms / 1000.0:.2f}s"


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
        current_index = current_shot_index(project, position_ms)
        shots = project.analysis.shots
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
                Badge(f"Timer {format_time_ms(elapsed)}", project.overlay.timer_badge),
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
                Badge(f"Draw {format_time_ms(draw_value)}", project.overlay.shot_badge),
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
                score_text = f" {shot.score.letter.value}" if project.scoring.enabled and shot.score else ""
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
        font = QFont(project.overlay.font_family or "Helvetica Neue", font_size)
        font.setBold(project.overlay.font_bold)
        font.setItalic(project.overlay.font_italic)
        painter.setFont(font)
        padding_y = max(2, int(project.overlay.spacing))
        padding_x = max(6, int(project.overlay.spacing * 1.5))
        gap = max(0, int(project.overlay.margin))
        quadrant_value = quadrant or project.overlay.shot_quadrant
        cursor_x, cursor_y = self._start_position(project, width, height, quadrant_value)

        x_override = project.overlay.custom_x if custom_x is None and quadrant_value == "custom" else custom_x
        y_override = project.overlay.custom_y if custom_y is None and quadrant_value == "custom" else custom_y
        if quadrant_value == "custom":
            if x_override is None:
                x_override = 0.5
            if y_override is None:
                y_override = 0.5
        if x_override is not None:
            cursor_x = int(x_override * width)
        if y_override is not None:
            cursor_y = int(y_override * height)

        previous_rect: QRectF | None = None
        for index, badge in enumerate(badges):
            metrics = painter.fontMetrics()
            lines = badge.text.splitlines() or [""]
            text_width = max(
                max(metrics.horizontalAdvance(line) for line in lines),
                self._minimum_badge_text_width(metrics, badge.text),
            )
            text_height = metrics.height() * max(1, len(lines))
            badge_width = max(text_width + (padding_x * 2), int(badge.width or project.overlay.bubble_width))
            badge_height = max(text_height + (padding_y * 2), int(badge.height or project.overlay.bubble_height))
            if previous_rect is None:
                rect_x = float(cursor_x)
                rect_y = float(cursor_y)
                if quadrant_value == "custom":
                    rect_x -= badge_width / 2
                    rect_y -= badge_height / 2
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
            painter.drawText(
                rect.adjusted(padding_x, padding_y, -padding_x, -padding_y),
                Qt.AlignCenter | Qt.TextWordWrap,
                badge.text,
            )

    @staticmethod
    def _start_position(project: Project, width: int, height: int, quadrant_override: str | None = None) -> tuple[int, int]:
        margin = max(0, int(project.overlay.margin))
        quadrant = quadrant_override or project.overlay.shot_quadrant
        if quadrant == "custom":
            return width // 2, height // 2
        x_map = {
            "left": margin,
            "middle": width // 2,
            "right": max(0, width - 220 - margin),
        }
        y_map = {
            "top": margin,
            "middle": height // 2,
            "bottom": max(0, height - 48 - margin),
        }
        vertical, horizontal = quadrant.split("_", 1) if "_" in quadrant else ("bottom", "left")
        return x_map.get(horizontal, margin), y_map.get(vertical, margin)

    @staticmethod
    def _minimum_badge_text_width(metrics, text: str) -> int:
        if text.startswith("Timer"):
            return metrics.horizontalAdvance("Timer 00:00.000")
        if text.startswith("Draw"):
            return metrics.horizontalAdvance("Draw 00:00.000")
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
            font = QFont("Helvetica Neue", 28)
            font.setBold(True)
            painter.setFont(font)
            point = QPointF(x_norm * width, y_norm * height)
            painter.drawText(point, letter)

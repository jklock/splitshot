from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from splitshot.domain.models import BadgeSize, BadgeStyle, OverlayPosition, Project
from splitshot.scoring.logic import calculate_scoring_summary, current_shot_index
from splitshot.timeline.model import draw_time_ms
from splitshot.utils.time import format_time_ms


@dataclass(slots=True)
class Badge:
    text: str
    style: BadgeStyle
    text_color: str | None = None


_FONT_SIZE = {
    BadgeSize.XS: 10,
    BadgeSize.S: 12,
    BadgeSize.M: 14,
    BadgeSize.L: 16,
    BadgeSize.XL: 20,
}


class OverlayRenderer:
    def build_badges(self, project: Project, position_ms: int) -> tuple[list[Badge], list[tuple[str, float, float, float]]]:
        current_index = current_shot_index(project, position_ms)
        badges: list[Badge] = []

        beep_time = project.analysis.beep_time_ms_primary
        elapsed = max(0, position_ms - beep_time) if beep_time is not None else position_ms
        if project.overlay.show_timer:
            badges.append(Badge(f"Timer {format_time_ms(elapsed)}", project.overlay.timer_badge))

        draw_value = draw_time_ms(project)
        if project.overlay.show_draw and draw_value is not None:
            badges.append(Badge(f"Draw {format_time_ms(draw_value)}", project.overlay.shot_badge))

        if project.overlay.show_shots and current_index is not None:
            shots = project.analysis.shots
            max_visible = max(1, int(project.overlay.max_visible_shots))
            start = max(0, current_index - max_visible + 1)
            for index in range(start, current_index + 1):
                shot = shots[index]
                if index == 0:
                    split_text = format_time_ms(shot.time_ms - (beep_time or 0))
                else:
                    split_text = format_time_ms(shot.time_ms - shots[index - 1].time_ms)
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

        if project.scoring.enabled and project.overlay.show_score:
            summary = calculate_scoring_summary(project)
            if summary["display_value"] != "--":
                badges.append(
                    Badge(
                        f"{summary['display_label']} {summary['display_value']}",
                        project.overlay.hit_factor_badge,
                    )
                )

        score_marks: list[tuple[str, float, float, float]] = []

        return badges, score_marks

    def paint(self, painter: QPainter, project: Project, position_ms: int, width: int, height: int) -> None:
        if project.overlay.position == OverlayPosition.NONE:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        badges, score_marks = self.build_badges(project, position_ms)
        self._paint_badges(painter, badges, project, width, height)
        if project.overlay.custom_box_enabled and project.overlay.custom_box_text.strip():
            self._paint_badges(
                painter,
                [Badge(project.overlay.custom_box_text.strip(), project.overlay.hit_factor_badge)],
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
        cursor_x, cursor_y = self._start_position(project, width, height, quadrant)

        x_override = project.overlay.custom_x if custom_x is None else custom_x
        y_override = project.overlay.custom_y if custom_y is None else custom_y
        if x_override is not None:
            cursor_x = int(x_override * width)
        if y_override is not None:
            cursor_y = int(y_override * height)

        for badge in badges:
            metrics = painter.fontMetrics()
            text_width = max(metrics.horizontalAdvance(badge.text), self._minimum_badge_text_width(metrics, badge.text))
            text_height = metrics.height()
            badge_width = max(text_width + (padding_x * 2), int(project.overlay.bubble_width))
            badge_height = max(text_height + (padding_y * 2), int(project.overlay.bubble_height))
            rect = QRectF(cursor_x, cursor_y, badge_width, badge_height)

            if project.overlay.shot_direction == "right":
                cursor_x += rect.width() + gap
            elif project.overlay.shot_direction == "left":
                cursor_x -= rect.width() + gap
            elif project.overlay.shot_direction == "up":
                cursor_y -= rect.height() + gap
            else:
                cursor_y += rect.height() + gap

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
                Qt.AlignCenter,
                badge.text,
            )

    @staticmethod
    def _start_position(project: Project, width: int, height: int, quadrant_override: str | None = None) -> tuple[int, int]:
        margin = max(0, int(project.overlay.margin))
        quadrant = quadrant_override or project.overlay.shot_quadrant
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
        if text.startswith("Final Time"):
            return metrics.horizontalAdvance("Final Time 00:00.000")
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

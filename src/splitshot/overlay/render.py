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
        badges.append(Badge(f"Timer {format_time_ms(elapsed)}", project.overlay.timer_badge))

        draw_value = draw_time_ms(project)
        if draw_value is not None:
            badges.append(Badge(f"Draw {format_time_ms(draw_value)}", project.overlay.shot_badge))

        if current_index is not None:
            shots = project.analysis.shots
            start = max(0, current_index - 3)
            for index in range(start, current_index + 1):
                shot = shots[index]
                if index == 0:
                    split_text = format_time_ms(shot.time_ms - (beep_time or 0))
                else:
                    split_text = format_time_ms(shot.time_ms - shots[index - 1].time_ms)
                style = (
                    project.overlay.current_shot_badge if index == current_index else project.overlay.shot_badge
                )
                badges.append(Badge(f"Shot {index + 1} {split_text}", style))

        if project.scoring.enabled:
            summary = calculate_scoring_summary(project)
            if summary["display_value"] != "--":
                badges.append(
                    Badge(
                        f"{summary['display_label']} {summary['display_value']}",
                        project.overlay.hit_factor_badge,
                    )
                )

        score_marks: list[tuple[str, float, float, float]] = []
        if project.scoring.enabled:
            for shot in project.analysis.shots:
                if shot.score is None:
                    continue
                elapsed_since = position_ms - shot.time_ms
                if 0 <= elapsed_since <= 1200:
                    alpha = max(0.2, 1.0 - (elapsed_since / 1200.0))
                    score_marks.append((shot.score.letter.value, shot.score.x_norm, shot.score.y_norm, alpha))

        return badges, score_marks

    def paint(self, painter: QPainter, project: Project, position_ms: int, width: int, height: int) -> None:
        if project.overlay.position == OverlayPosition.NONE:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        badges, score_marks = self.build_badges(project, position_ms)
        self._paint_badges(painter, badges, project, width, height)
        self._paint_scores(painter, project, score_marks, width, height)

        painter.restore()

    def _paint_badges(
        self,
        painter: QPainter,
        badges: list[Badge],
        project: Project,
        width: int,
        height: int,
    ) -> None:
        if not badges:
            return

        position = project.overlay.position
        font = QFont("Helvetica Neue", _FONT_SIZE[project.overlay.badge_size])
        painter.setFont(font)
        padding_y = max(2, int(project.overlay.spacing))
        padding_x = max(6, int(project.overlay.spacing * 1.5))
        gap = max(0, int(project.overlay.margin))
        cursor_x = max(0, int(project.overlay.margin))
        cursor_y = max(0, int(project.overlay.margin))

        if position == OverlayPosition.BOTTOM:
            cursor_y = max(0, height - 48 - max(0, int(project.overlay.margin)))
        elif position == OverlayPosition.RIGHT:
            cursor_x = max(0, width - 220 - max(0, int(project.overlay.margin)))

        for badge in badges:
            metrics = painter.fontMetrics()
            text_width = max(metrics.horizontalAdvance(badge.text), self._minimum_badge_text_width(metrics, badge.text))
            text_height = metrics.height()
            rect = QRectF(cursor_x, cursor_y, text_width + (padding_x * 2), text_height + (padding_y * 2))

            if position in {OverlayPosition.TOP, OverlayPosition.BOTTOM}:
                cursor_x += rect.width() + gap
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
            painter.setPen(QColor(badge.style.text_color))
            painter.drawText(
                rect.adjusted(padding_x, padding_y, -padding_x, -padding_y),
                Qt.AlignCenter,
                badge.text,
            )

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

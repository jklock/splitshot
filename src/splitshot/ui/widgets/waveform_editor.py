from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from splitshot.domain.models import ShotEvent


@dataclass(slots=True)
class WaveformState:
    duration_ms: int = 1
    waveform: list[float] | None = None
    secondary_waveform: list[float] | None = None
    shots: list[ShotEvent] | None = None
    beep_time_ms: int | None = None
    secondary_beep_time_ms: int | None = None
    playhead_ms: int = 0
    zoom: float = 1.0
    offset_ms: int = 0
    selected_shot_id: str | None = None
    frame_nudge_ms: int = 33


class WaveformEditor(QWidget):
    shot_added = Signal(int)
    shot_moved = Signal(str, int)
    shot_deleted = Signal(str)
    beep_moved = Signal(int)
    seek_requested = Signal(int)
    shot_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setFocusPolicy(Qt.StrongFocus)
        self.state = WaveformState()
        self._dragging_shot_id: str | None = None
        self._dragging_beep = False
        self._panning = False
        self._last_mouse_x = 0.0

    def set_state(self, state: WaveformState) -> None:
        self.state = state
        self.update()

    def visible_range_ms(self) -> tuple[int, int]:
        duration = max(1, self.state.duration_ms)
        visible = int(duration / max(1.0, self.state.zoom))
        start = max(0, min(self.state.offset_ms, duration - visible))
        return start, start + visible

    def _time_to_x(self, time_ms: int) -> float:
        start, end = self.visible_range_ms()
        span = max(1, end - start)
        return ((time_ms - start) / span) * self.width()

    def _x_to_time(self, x: float) -> int:
        start, end = self.visible_range_ms()
        span = max(1, end - start)
        return int(start + (x / max(1, self.width())) * span)

    def _marker_at(self, x: float) -> str | None:
        shots = self.state.shots or []
        for shot in shots:
            shot_x = self._time_to_x(shot.time_ms)
            if abs(shot_x - x) <= 8:
                return shot.id
        return None

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#18243B"))
        painter.setRenderHint(QPainter.Antialiasing, True)

        waveform = self.state.waveform or []
        if waveform:
            self._paint_waveform(painter, waveform, QColor("#3B82F6"), 0.5, 0.42)
        if self.state.secondary_waveform:
            self._paint_waveform(
                painter,
                self.state.secondary_waveform,
                QColor("#60A5FA"),
                0.76,
                0.18,
            )
        self._paint_markers(painter)
        self._paint_playhead(painter)

    def _paint_waveform(
        self,
        painter: QPainter,
        waveform: list[float],
        color: QColor,
        center_ratio: float,
        amplitude_ratio: float,
    ) -> None:
        width = self.width()
        height = self.height()
        mid_y = height * center_ratio
        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        start_ms, end_ms = self.visible_range_ms()
        start_index = int((start_ms / max(1, self.state.duration_ms)) * len(waveform))
        end_index = max(start_index + 1, int((end_ms / max(1, self.state.duration_ms)) * len(waveform)))
        visible = waveform[start_index:end_index]
        if not visible:
            return
        step = width / max(1, len(visible))
        for index, value in enumerate(visible):
            x = index * step
            amplitude = value * (height * amplitude_ratio)
            painter.drawLine(QPointF(x, mid_y - amplitude), QPointF(x, mid_y + amplitude))

    def _paint_markers(self, painter: QPainter) -> None:
        shots = self.state.shots or []
        for index, shot in enumerate(shots, start=1):
            x = self._time_to_x(shot.time_ms)
            color = QColor("#22C55E" if shot.id != self.state.selected_shot_id else "#A3E635")
            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            painter.drawText(int(x + 4), 18, str(index))

        if self.state.beep_time_ms is not None:
            x = self._time_to_x(self.state.beep_time_ms)
            pen = QPen(QColor("#F97316"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            painter.drawText(int(x + 6), 18, "BEEP")

        if self.state.secondary_beep_time_ms is not None:
            x = self._time_to_x(self.state.secondary_beep_time_ms)
            pen = QPen(QColor("#FB923C"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(QPointF(x, self.height() * 0.58), QPointF(x, self.height()))

    def _paint_playhead(self, painter: QPainter) -> None:
        x = self._time_to_x(self.state.playhead_ms)
        pen = QPen(QColor("#EF4444"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._last_mouse_x = event.position().x()
        marker_id = self._marker_at(self._last_mouse_x)
        if event.button() == Qt.RightButton and marker_id is not None:
            self.shot_deleted.emit(marker_id)
            return
        beep_x = None if self.state.beep_time_ms is None else self._time_to_x(self.state.beep_time_ms)
        if (
            event.modifiers() & Qt.ShiftModifier
            and self.state.beep_time_ms is not None
            and beep_x is not None
            and abs(beep_x - event.position().x()) <= 12
        ):
            self._dragging_beep = True
            self.beep_moved.emit(self._x_to_time(event.position().x()))
            return
        if marker_id is not None:
            self._dragging_shot_id = marker_id
            self.shot_selected.emit(marker_id)
            return
        if event.button() == Qt.LeftButton:
            self._panning = event.modifiers() & Qt.AltModifier == Qt.AltModifier

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        current_x = event.position().x()
        if self._dragging_shot_id is not None:
            self.shot_moved.emit(self._dragging_shot_id, self._x_to_time(current_x))
            return
        if self._dragging_beep:
            self.beep_moved.emit(self._x_to_time(current_x))
            return
        if self._panning:
            delta_x = current_x - self._last_mouse_x
            start_ms, end_ms = self.visible_range_ms()
            span = max(1, end_ms - start_ms)
            delta_ms = int(-(delta_x / max(1, self.width())) * span)
            self.state.offset_ms = max(0, min(self.state.duration_ms - span, self.state.offset_ms + delta_ms))
            self._last_mouse_x = current_x
            self.update()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        time_ms = self._x_to_time(event.position().x())
        self.seek_requested.emit(time_ms)

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else (1 / 1.15)
        self.state.zoom = max(1.0, min(32.0, self.state.zoom * factor))
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self.state.selected_shot_id is None:
            return
        if event.key() == Qt.Key_Delete:
            self.shot_deleted.emit(self.state.selected_shot_id)
            return
        if event.key() == Qt.Key_Left:
            if event.modifiers() & Qt.AltModifier:
                delta = -self.state.frame_nudge_ms
            else:
                delta = -10 if event.modifiers() & Qt.ShiftModifier else -1
            self.shot_moved.emit(self.state.selected_shot_id, self._selected_time() + delta)
            return
        if event.key() == Qt.Key_Right:
            if event.modifiers() & Qt.AltModifier:
                delta = self.state.frame_nudge_ms
            else:
                delta = 10 if event.modifiers() & Qt.ShiftModifier else 1
            self.shot_moved.emit(self.state.selected_shot_id, self._selected_time() + delta)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        was_dragging_shot = self._dragging_shot_id is not None
        was_dragging_beep = self._dragging_beep
        was_panning = self._panning
        if (
            event.button() == Qt.LeftButton
            and not was_dragging_shot
            and not was_dragging_beep
            and not was_panning
        ):
            marker_id = self._marker_at(event.position().x())
            if marker_id is None and not (event.modifiers() & Qt.AltModifier):
                self.shot_added.emit(self._x_to_time(event.position().x()))
        self._dragging_shot_id = None
        self._dragging_beep = False
        self._panning = False

    def _selected_time(self) -> int:
        for shot in self.state.shots or []:
            if shot.id == self.state.selected_shot_id:
                return shot.time_ms
        return 0

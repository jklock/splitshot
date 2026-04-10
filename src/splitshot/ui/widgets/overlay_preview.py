from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from splitshot.domain.models import AspectRatio
from splitshot.export.pipeline import compute_crop_box
from splitshot.overlay.render import OverlayRenderer


class OverlayPreview(QWidget):
    score_position_selected = Signal(float, float)
    crop_center_selected = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.renderer = OverlayRenderer()
        self.project = None
        self.position_ms = 0
        self.placement_mode = False
        self.crop_mode = False

    def set_state(self, project, position_ms: int) -> None:
        self.project = project
        self.position_ms = position_ms
        self.update()

    def set_placement_mode(self, enabled: bool) -> None:
        self.placement_mode = enabled
        self.setCursor(Qt.CrossCursor if enabled or self.crop_mode else Qt.ArrowCursor)

    def set_crop_mode(self, enabled: bool) -> None:
        self.crop_mode = enabled
        self.setCursor(Qt.CrossCursor if enabled or self.placement_mode else Qt.ArrowCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self.project is None:
            return
        painter = QPainter(self)
        self.renderer.paint(painter, self.project, self.position_ms, self.width(), self.height())
        self._paint_crop_box(painter)

    def _paint_crop_box(self, painter: QPainter) -> None:
        if self.project is None or self.project.export.aspect_ratio == AspectRatio.ORIGINAL:
            return
        left, top, crop_width, crop_height = compute_crop_box(
            self.width(),
            self.height(),
            self.project.export.aspect_ratio,
            self.project.export.crop_center_x,
            self.project.export.crop_center_y,
        )
        pen = QPen(QColor("#F8FAFC"))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(left, top, crop_width, crop_height))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.project is None:
            event.ignore()
            return
        if self.placement_mode:
            x_norm = min(1.0, max(0.0, event.position().x() / max(1, self.width())))
            y_norm = min(1.0, max(0.0, event.position().y() / max(1, self.height())))
            self.score_position_selected.emit(x_norm, y_norm)
            event.accept()
            return
        if self.crop_mode:
            self._emit_crop_center(event.position().x(), event.position().y())
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.crop_mode and event.buttons() & Qt.LeftButton:
            self._emit_crop_center(event.position().x(), event.position().y())
            event.accept()
            return
        event.ignore()

    def _emit_crop_center(self, x_pos: float, y_pos: float) -> None:
        x_norm = min(1.0, max(0.0, x_pos / max(1, self.width())))
        y_norm = min(1.0, max(0.0, y_pos / max(1, self.height())))
        self.crop_center_selected.emit(x_norm, y_norm)

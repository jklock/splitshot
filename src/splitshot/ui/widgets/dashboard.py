from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def format_seconds_short(time_ms: int | None) -> str:
    if time_ms is None:
        return "--.--"
    return f"{time_ms / 1000:.2f}"


@dataclass(slots=True)
class SplitCardData:
    shot_id: str
    title: str
    value: str
    subtitle: str
    meta: str = ""


class SectionCard(QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionCard")

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("sectionSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("sectionMeta")
        self.meta_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.meta_label.setVisible(False)

        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        header_layout.addLayout(title_layout, stretch=1)
        header_layout.addWidget(self.meta_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(20)
        layout.addLayout(header_layout)
        layout.addWidget(self.content_widget)

    def set_meta_text(self, text: str) -> None:
        self.meta_label.setVisible(bool(text))
        self.meta_label.setText(text)

    def set_subtitle_text(self, text: str) -> None:
        self.subtitle_label.setVisible(bool(text))
        self.subtitle_label.setText(text)


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "--", subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("statSubtitle")
        self.subtitle_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch(1)

    def set_content(self, title: str, value: str, subtitle: str) -> None:
        self.title_label.setText(title)
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)


class UploadDropZone(QFrame):
    upload_requested = Signal()
    file_dropped = Signal(str)

    def __init__(
        self,
        title: str,
        description: str,
        button_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("uploadDropZone")
        self.setAcceptDrops(True)

        title_label = QLabel(title)
        title_label.setObjectName("uploadTitle")
        title_label.setWordWrap(True)

        description_label = QLabel(description)
        description_label.setObjectName("uploadDescription")
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignCenter)

        action_button = QPushButton(button_text)
        action_button.setProperty("primary", True)
        action_button.clicked.connect(self.upload_requested.emit)

        hint_label = QLabel("Drag and drop a video file here or choose one manually.")
        hint_label.setObjectName("uploadHint")
        hint_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch(1)
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addWidget(description_label)
        layout.addWidget(action_button, alignment=Qt.AlignCenter)
        layout.addWidget(hint_label)
        layout.addStretch(1)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()


class LegendItem(QWidget):
    def __init__(self, label: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        dot = QFrame(self)
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background: {color}; border-radius: 7px;")

        text = QLabel(label)
        text.setObjectName("legendLabel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(dot)
        layout.addWidget(text)


class SplitCard(QFrame):
    clicked = Signal(str)

    def __init__(self, data: SplitCardData, selected: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data = data
        self.shot_id = data.shot_id
        self.setObjectName("shotCard")
        self.setProperty("selected", selected)
        self.setCursor(Qt.PointingHandCursor)

        title_label = QLabel(data.title)
        title_label.setObjectName("shotCardTitle")

        value_label = QLabel(data.value)
        value_label.setObjectName("shotCardValue")

        subtitle_label = QLabel(data.subtitle)
        subtitle_label.setObjectName("shotCardSubtitle")

        meta_label = QLabel(data.meta)
        meta_label.setObjectName("shotCardMeta")
        meta_label.setVisible(bool(data.meta))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(meta_label)
        layout.addStretch(1)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.shot_id)
            event.accept()
            return
        super().mousePressEvent(event)


class SplitCardGrid(QScrollArea):
    shot_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self._cards: dict[str, SplitCard] = {}

        self._container = QWidget(self)
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._grid.setColumnStretch(0, 1)
        self.setWidget(self._container)

        self._show_empty_state()

    def set_cards(self, cards: list[SplitCardData], selected_shot_id: str | None) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._cards = {}
        if not cards:
            self._show_empty_state()
            return

        columns = 4
        for index, data in enumerate(cards):
            card = SplitCard(data, selected=data.shot_id == selected_shot_id)
            card.clicked.connect(self.shot_selected.emit)
            row = index // columns
            column = index % columns
            self._grid.addWidget(card, row, column)
            self._cards[data.shot_id] = card

        for column in range(columns):
            self._grid.setColumnStretch(column, 1)
        self._grid.setRowStretch((len(cards) // columns) + 1, 1)

    def set_selected_shot(self, shot_id: str | None) -> None:
        for current_id, card in self._cards.items():
            card.set_selected(current_id == shot_id)

    def _show_empty_state(self) -> None:
        empty_label = QLabel("Shot detections will appear here after analysis.")
        empty_label.setObjectName("emptyGridLabel")
        empty_label.setAlignment(Qt.AlignCenter)
        self._grid.addWidget(empty_label, 0, 0)

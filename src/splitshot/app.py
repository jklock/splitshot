from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from splitshot.ui.controller import ProjectController
from splitshot.ui.main_window import MainWindow


def _build_stylesheet() -> str:
    return """
    QWidget {
        background: #0B0E13;
        color: #F4F7FB;
        font-family: "Avenir Next", "Helvetica Neue";
        font-size: 14px;
    }
    QMainWindow::separator {
        background: #0B0E13;
        width: 1px;
        height: 1px;
    }
    QMenuBar, QMenu {
        background: #11151C;
        color: #F4F7FB;
        border: 1px solid #202632;
    }
    QMenu::item:selected {
        background: #1D2430;
    }
    QFrame#navigationRail, QFrame#inspectorShell, QFrame#topHeader, QFrame#sectionCard, QFrame#statCard, QFrame#uploadDropZone, QFrame#panelCard, QFrame#shotCard, QWidget#previewSurface {
        background: #151922;
        border: 1px solid #242B37;
        border-radius: 18px;
    }
    QWidget#previewSurface {
        background: #050608;
    }
    QLabel#brandLabel {
        font-size: 24px;
        font-weight: 700;
    }
    QLabel#brandSubLabel {
        color: #92A0B5;
        font-size: 12px;
    }
    QPushButton[navButton="true"] {
        text-align: left;
        padding: 14px 16px;
        border: 1px solid transparent;
        border-radius: 14px;
        background: transparent;
        color: #AEB9C9;
        font-weight: 600;
    }
    QPushButton[navButton="true"]:checked {
        background: #1B2230;
        border-color: #303A4B;
        color: #F4F7FB;
    }
    QPushButton[navButton="true"]:disabled {
        color: #586274;
    }
    QPushButton, QComboBox, QSpinBox {
        background: #1B2230;
        border: 1px solid #303A4B;
        border-radius: 12px;
        padding: 10px 12px;
    }
    QPushButton:hover, QComboBox:hover, QSpinBox:hover {
        border-color: #45556E;
    }
    QPushButton[primary="true"] {
        background: #1387F5;
        border-color: #1387F5;
        color: white;
        font-weight: 700;
    }
    QPushButton[danger="true"] {
        background: #301A1C;
        border-color: #5A2E34;
        color: #FFCDD3;
    }
    QLabel#projectTitle {
        font-size: 28px;
        font-weight: 700;
    }
    QLabel#projectDetail {
        color: #91A0B4;
    }
    QLabel#statusPill {
        background: #1D2430;
        border: 1px solid #2F394A;
        border-radius: 14px;
        padding: 10px 14px;
        color: #D6DEEA;
        min-width: 280px;
    }
    QLabel#sectionTitle {
        font-size: 18px;
        font-weight: 700;
    }
    QLabel#sectionSubtitle, QLabel#panelInfo, QLabel#legendLabel, QLabel#emptyGridLabel {
        color: #95A2B5;
    }
    QLabel#sectionMeta {
        color: #D2D9E6;
        font-size: 16px;
        font-weight: 700;
    }
    QLabel#statTitle {
        color: #B5C0D0;
        font-size: 13px;
        font-weight: 600;
    }
    QLabel#statValue {
        font-size: 42px;
        font-weight: 700;
    }
    QLabel#statSubtitle {
        color: #8E9AB0;
    }
    QLabel#uploadTitle {
        font-size: 32px;
        font-weight: 700;
    }
    QLabel#uploadDescription, QLabel#uploadHint {
        color: #9AA7B9;
        font-size: 15px;
    }
    QLabel#timelineTime {
        color: #C8D0DB;
        min-width: 72px;
    }
    QSlider::groove:horizontal {
        background: #283244;
        border-radius: 4px;
        height: 8px;
    }
    QSlider::handle:horizontal {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        width: 18px;
        margin: -6px 0;
        border-radius: 9px;
    }
    QCheckBox {
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    QCheckBox::indicator:unchecked {
        border: 1px solid #45556E;
        border-radius: 5px;
        background: #1B2230;
    }
    QCheckBox::indicator:checked {
        border: 1px solid #1387F5;
        border-radius: 5px;
        background: #1387F5;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QFrame#shotCard[selected="true"] {
        border: 1px solid #1387F5;
        background: #182437;
    }
    QLabel#shotCardTitle {
        color: #AAB6C8;
        font-size: 12px;
        font-weight: 600;
    }
    QLabel#shotCardValue {
        font-size: 30px;
        font-weight: 700;
    }
    QLabel#shotCardSubtitle, QLabel#shotCardMeta {
        color: #91A0B5;
    }
    """


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("SplitShot")
    app.setOrganizationName("SplitShot")
    app.setStyleSheet(_build_stylesheet())
    return app


def run(project_path: str | None = None) -> int:
    app = create_application()
    controller = ProjectController()
    if project_path is not None:
        controller.open_project(project_path)
    window = MainWindow(controller)
    window.show()
    return app.exec()

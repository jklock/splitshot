from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from splitshot.ui.controller import ProjectController
from splitshot.ui.main_window import MainWindow


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("SplitShot")
    app.setOrganizationName("SplitShot")
    return app


def run() -> int:
    app = create_application()
    controller = ProjectController()
    window = MainWindow(controller)
    window.show()
    return app.exec()

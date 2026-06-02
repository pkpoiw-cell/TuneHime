"""AI Live Tuner — application entry point."""

from __future__ import annotations

import sys


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    from .qt_ui import MainWindow
    from .qt_ui.theme import STYLESHEET

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()

    # Busy-wait event loop (app.exec() has issues on Python 3.14)
    while window.isVisible():
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

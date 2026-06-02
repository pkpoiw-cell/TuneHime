"""Launch AI Live Tuner with proper error handling."""

import sys
import os

# Add src to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)

try:
    from PyQt6.QtWidgets import QApplication
    from ai_live_tuner.qt_ui.main_window import MainWindow
    from ai_live_tuner.qt_ui.theme import STYLESHEET

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()

    # Busy-wait event loop (app.exec() has issues on Python 3.14)
    while window.isVisible():
        app.processEvents()
except Exception as e:
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core import APP_NAME, __version__
from core.i18n import set_language, detect_system_language
from core.settings import settings


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    if os.name == "nt":
        try:  # own taskbar icon/group instead of python.exe's
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"WaveSmith.App.{__version__}")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(resource_path(os.path.join("assets", "app_icon.ico"))))

    lang = settings().value("language", "", type=str) or detect_system_language()
    set_language(lang)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    # Files/folders passed on the command line (e.g. "Open with…" or dropped onto the .exe)
    paths = [p for p in sys.argv[1:] if os.path.exists(p)]
    if paths:
        window.tabs.setCurrentIndex(0)
        window.c_queue.add_paths(paths)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

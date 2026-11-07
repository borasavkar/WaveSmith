"""
Portable settings: stored in WaveSmith.ini next to the executable (or the
project folder when running from source). Nothing is written to the registry.
Falls back to the per-user config folder if the app folder is read-only.
"""
import os
import sys

from PyQt6.QtCore import QSettings, QStandardPaths


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ini_path():
    primary = os.path.join(app_dir(), "WaveSmith.ini")
    try:
        with open(primary, "a", encoding="utf-8"):
            pass
        return primary
    except OSError:
        cfg = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        os.makedirs(cfg, exist_ok=True)
        return os.path.join(cfg, "WaveSmith.ini")


_settings = None


def settings():
    global _settings
    if _settings is None:
        _settings = QSettings(_ini_path(), QSettings.Format.IniFormat)
    return _settings

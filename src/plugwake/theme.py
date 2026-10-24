from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QWindow

# Windows 11 22H2 is the first build with the documented system backdrop attribute.
MICA_MIN_BUILD = 22621
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW = 2


class Margins(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int) for name in ("left", "right", "top", "bottom")]


def mica_supported() -> bool:
    return sys.platform == "win32" and sys.getwindowsversion().build >= MICA_MIN_BUILD


def is_dark(app: QGuiApplication) -> bool:
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Unknown:
        return app.palette().window().color().lightness() < 128
    return scheme == Qt.ColorScheme.Dark


def enable_mica(window: QWindow) -> bool:
    if not mica_supported():
        return False
    try:
        hwnd = ctypes.c_void_p(int(window.winId()))
        result = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(Margins(-1, -1, -1, -1)))
    except (AttributeError, OSError):
        return False
    if result != 0:
        return False
    return set_dwm_attribute(window, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MAINWINDOW)


def follow_color_scheme(app: QGuiApplication, window: QWindow) -> None:
    """Keep the Windows title bar and Mica tint in step with the system light or dark theme."""
    if sys.platform != "win32":
        return

    def apply() -> None:
        set_dwm_attribute(window, DWMWA_USE_IMMERSIVE_DARK_MODE, int(is_dark(app)))

    apply()
    app.styleHints().colorSchemeChanged.connect(lambda _scheme: apply())


def set_dwm_attribute(window: QWindow, attribute: int, value: int) -> bool:
    try:
        hwnd = ctypes.c_void_p(int(window.winId()))
        data = ctypes.c_int(value)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
    except (AttributeError, OSError):
        return False
    return result == 0

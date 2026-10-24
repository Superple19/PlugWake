from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

# Windows 11 22H2 is the first build with the documented system backdrop attribute.
MICA_MIN_BUILD = 22621
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW = 2


@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    container: str
    container_high: str
    on_surface: str
    on_surface_variant: str
    outline: str
    outline_variant: str
    primary: str
    on_primary: str
    tonal: str
    on_tonal: str
    success: str
    on_success: str
    error: str
    on_error: str
    error_text: str
    error_hover: str
    log: str


LIGHT = Palette(
    window="#f8f9fc",
    surface="rgba(255, 255, 255, 0.72)",
    container="#ffffff",
    container_high="#eef1f6",
    on_surface="#1a1c1e",
    on_surface_variant="#44474e",
    outline="#74777f",
    outline_variant="#c4c6d0",
    primary="#0b57d0",
    on_primary="#ffffff",
    tonal="#dde3ea",
    on_tonal="#161c22",
    success="#146c2e",
    on_success="#ffffff",
    error="#b3261e",
    on_error="#ffffff",
    error_text="#b3261e",
    error_hover="#fce8e6",
    log="#f1f3f8",
)

DARK = Palette(
    window="#131417",
    surface="rgba(32, 33, 36, 0.72)",
    container="#1e1f23",
    container_high="#2a2c31",
    on_surface="#e3e2e6",
    on_surface_variant="#c4c6d0",
    outline="#8e9099",
    outline_variant="#44474e",
    primary="#a8c7fa",
    on_primary="#062e6f",
    tonal="#333840",
    on_tonal="#dde3ea",
    success="#1e7e34",
    on_success="#ffffff",
    error="#c5221f",
    on_error="#ffffff",
    error_text="#f2b8b5",
    error_hover="#3d1f1e",
    log="#17181b",
)


def is_dark(app: QApplication) -> bool:
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Unknown:
        return app.palette().window().color().lightness() < 128
    return scheme == Qt.ColorScheme.Dark


def mica_supported() -> bool:
    return sys.platform == "win32" and sys.getwindowsversion().build >= MICA_MIN_BUILD


def stylesheet(p: Palette, mica: bool) -> str:
    window = "transparent" if mica else p.window
    pane = p.surface if mica else p.window
    return f"""
QWidget {{
  color: {p.on_surface};
  font-size: 10pt;
}}
QMainWindow, QDialog, QMessageBox, QInputDialog {{
  background: {p.window};
}}
QMainWindow#mainWindow {{
  background: {window};
}}
QTabWidget::pane {{
  background: {pane};
  border: none;
  border-top: 1px solid {p.outline_variant};
}}
QTabWidget > QWidget, QTabWidget QStackedWidget > QWidget,
QScrollArea, QScrollArea > QWidget > QWidget {{
  background: transparent;
}}
QTabBar::tab {{
  background: transparent;
  color: {p.on_surface_variant};
  border: none;
  border-bottom: 3px solid transparent;
  padding: 10px 18px;
  font-weight: 600;
}}
QTabBar::tab:selected {{
  color: {p.primary};
  border-bottom: 3px solid {p.primary};
}}
QTabBar::tab:hover:!selected {{
  color: {p.on_surface};
}}
QLabel {{
  background: transparent;
}}
QLabel#status {{
  color: {p.on_surface_variant};
  font-size: 11pt;
  font-weight: 600;
  padding: 2px 4px;
}}
QGroupBox {{
  background: {p.container};
  border: 1px solid {p.outline_variant};
  border-radius: 12px;
  margin-top: 22px;
  padding: 14px 12px 10px 12px;
  font-weight: 600;
}}
QGroupBox::title {{
  subcontrol-origin: margin;
  left: 12px;
  padding: 0 4px;
  color: {p.on_surface_variant};
}}
QGroupBox QLabel {{
  font-weight: 400;
  color: {p.on_surface_variant};
}}
QPushButton {{
  background: {p.tonal};
  color: {p.on_tonal};
  border: none;
  border-radius: 18px;
  padding: 8px 18px;
  min-height: 20px;
  font-weight: 600;
}}
QPushButton:hover {{
  background: {p.container_high};
}}
QPushButton:pressed {{
  background: {p.outline_variant};
}}
QPushButton#primaryOn, QPushButton#primaryOff {{
  min-height: 30px;
  border-radius: 23px;
  font-size: 11pt;
}}
QPushButton#primaryOn {{
  background: {p.success};
  color: {p.on_success};
}}
QPushButton#primaryOff {{
  background: {p.error};
  color: {p.on_error};
}}
QPushButton#danger {{
  background: transparent;
  color: {p.error_text};
  border: 1px solid {p.error_text};
}}
QPushButton#danger:hover {{
  background: {p.error_hover};
}}
QLineEdit, QComboBox {{
  background: {p.container_high};
  color: {p.on_surface};
  border: 1px solid {p.outline_variant};
  border-radius: 8px;
  padding: 6px 10px;
  selection-background-color: {p.primary};
  selection-color: {p.on_primary};
}}
QLineEdit:focus, QComboBox:focus {{
  border: 2px solid {p.primary};
  padding: 5px 9px;
}}
QComboBox::drop-down {{
  border: none;
  width: 24px;
}}
QComboBox QAbstractItemView {{
  background: {p.container};
  color: {p.on_surface};
  border: 1px solid {p.outline_variant};
  selection-background-color: {p.tonal};
  selection-color: {p.on_tonal};
}}
QPlainTextEdit {{
  background: {p.log};
  color: {p.on_surface};
  border: 1px solid {p.outline_variant};
  border-radius: 12px;
  padding: 8px;
  font-family: Consolas, "DejaVu Sans Mono", monospace;
  selection-background-color: {p.primary};
  selection-color: {p.on_primary};
}}
QScrollBar:vertical {{
  background: transparent;
  width: 10px;
  margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
  background: {p.outline_variant};
  border-radius: 3px;
  min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
  height: 0;
}}
"""


def apply_theme(app: QApplication, window: QWidget, mica: bool) -> None:
    dark = is_dark(app)
    app.setStyleSheet(stylesheet(DARK if dark else LIGHT, mica))
    if sys.platform == "win32":
        set_dwm_attribute(window, DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))


def enable_mica(window: QWidget) -> bool:
    if not mica_supported():
        return False
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    if not extend_frame_into_client_area(window):
        return False
    return set_dwm_attribute(window, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MAINWINDOW)


class Margins(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int) for name in ("left", "right", "top", "bottom")]


def extend_frame_into_client_area(window: QWidget) -> bool:
    try:
        hwnd = ctypes.c_void_p(int(window.winId()))
        result = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(Margins(-1, -1, -1, -1)))
    except (AttributeError, OSError):
        return False
    return result == 0


def set_dwm_attribute(window: QWidget, attribute: int, value: int) -> bool:
    try:
        hwnd = ctypes.c_void_p(int(window.winId()))
        data = ctypes.c_int(value)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
    except (AttributeError, OSError):
        return False
    return result == 0

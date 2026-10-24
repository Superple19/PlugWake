from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle

from .actions import (
    ActionCancelled,
    CancelToken,
    cancellable,
    remote_hard_reboot,
    remote_off,
    remote_on,
    remote_reboot,
    test_home_assistant,
    test_rdp_host,
)
from .config import FIELDS, ROOT, load_config, load_env, save_env
from .theme import enable_mica, follow_color_scheme, mica_supported

QML_DIR = Path(__file__).with_name("qml")

# id: (label, action, needs_password, confirmation)
ACTIONS: dict[str, tuple[str, Callable, bool, str]] = {
    "on": ("Remote On", remote_on, False, ""),
    "off": ("Remote Off", remote_off, True, "Shut down the target PC and turn the smart plug off?"),
    "reboot": ("Soft Reboot", remote_reboot, True, "Reboot the target PC over SSH?"),
    "hard-reboot": (
        "Hard Reboot",
        remote_hard_reboot,
        True,
        "Shut down the target PC, cut plug power, turn it back on, and open RDP?",
    ),
    "test-ha": ("Test Home Assistant", test_home_assistant, False, ""),
    "test-rdp": ("Test RDP Port", test_rdp_host, False, ""),
}

SETTING_GROUPS = [
    ("Home Assistant", ["HA_URL", "HA_TOKEN", "PLUG_ENTITY", "WATT_ENTITY"]),
    ("Target PC", ["RDP_HOST", "PC_SSH_TARGET", "TARGET_OS"]),
    (
        "Power Safety",
        [
            "POWER_THRESHOLD_W",
            "RDP_WAIT_SECONDS",
            "SHUTDOWN_WAIT_SECONDS",
            "PLUG_OFF_SECONDS",
            "POWER_ON_LOW_CONFIRMATIONS",
            "POWER_OFF_LOW_CONFIRMATIONS",
        ],
    ),
]

PLACEHOLDERS = {
    "HA_URL": "http://ha.example.local:8123",
    "HA_TOKEN": "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE",
    "PLUG_ENTITY": "switch.smart_plug",
    "WATT_ENTITY": "sensor.smart_plug_power",
    "RDP_HOST": "target-pc",
    "PC_SSH_TARGET": "user@target-pc",
    "TARGET_OS": "windows",
    "POWER_THRESHOLD_W": "5",
    "RDP_WAIT_SECONDS": "180",
    "SHUTDOWN_WAIT_SECONDS": "300",
    "PLUG_OFF_SECONDS": "10",
    "POWER_ON_LOW_CONFIRMATIONS": "3",
    "POWER_OFF_LOW_CONFIRMATIONS": "4",
}

SECRET_FIELDS = {"HA_TOKEN"}
CHOICES = {"TARGET_OS": ["windows", "linux"]}


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class ActionWorker(QThread):
    line = Signal(str)
    done = Signal(int)
    password_requested = Signal(str)

    def __init__(self, action: Callable[[Callable[[str], None]], None]) -> None:
        super().__init__()
        self.action = action
        self.password: str | None = None
        self.token = CancelToken()

    def run(self) -> None:
        try:
            with cancellable(self.token):
                self.action(self.line.emit)
        except ActionCancelled as exc:
            self.line.emit(f"{exc}.")
            self.done.emit(2)
            return
        except Exception as exc:
            self.line.emit(f"Error: {exc}")
            self.done.emit(1)
            return
        self.done.emit(0)

    def prompt_password(self, target: str) -> str | None:
        self.password = None
        self.password_requested.emit(target)
        while self.password is None:
            if self.token.requested:
                return ""
            self.msleep(50)
        return self.password


class Backend(QObject):
    logLine = Signal(str)
    passwordRequested = Signal(str)
    statusChanged = Signal()
    runningChanged = Signal()
    cancellingChanged = Signal()
    valuesChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "Ready"
        self._running = False
        self._cancelling = False
        self._label = ""
        self._worker: ActionWorker | None = None
        self._values: dict[str, str] = {}
        self.loadSettings()

    def _get_status(self) -> str:
        return self._status

    def _get_running(self) -> bool:
        return self._running

    def _get_cancelling(self) -> bool:
        return self._cancelling

    def _get_values(self) -> dict[str, str]:
        return self._values

    def _get_setting_groups(self) -> list[dict]:
        return [
            {
                "title": title,
                "fields": [
                    {
                        "key": key,
                        "placeholder": PLACEHOLDERS.get(key, ""),
                        "secret": key in SECRET_FIELDS,
                        "choices": CHOICES.get(key, []),
                    }
                    for key in keys
                ],
            }
            for title, keys in SETTING_GROUPS
        ]

    status = Property(str, _get_status, notify=statusChanged)
    running = Property(bool, _get_running, notify=runningChanged)
    cancelling = Property(bool, _get_cancelling, notify=cancellingChanged)
    values = Property("QVariantMap", _get_values, notify=valuesChanged)
    settingGroups = Property("QVariantList", _get_setting_groups, constant=True)

    def log(self, text: str) -> None:
        self.logLine.emit(f"[{timestamp()}] {text}")

    def _set_status(self, text: str) -> None:
        self._status = text
        self.statusChanged.emit()

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.runningChanged.emit()

    def _set_cancelling(self, cancelling: bool) -> None:
        self._cancelling = cancelling
        self.cancellingChanged.emit()

    @Slot(str, result=str)
    def confirmText(self, action_id: str) -> str:
        return ACTIONS[action_id][3]

    @Slot(str, result=str)
    def actionLabel(self, action_id: str) -> str:
        return ACTIONS[action_id][0]

    @Slot(str)
    def run(self, action_id: str) -> None:
        if self._running:
            return
        label, action, needs_password, _confirm = ACTIONS[action_id]
        try:
            config = load_config()
        except RuntimeError as exc:
            self.log(f"Error: {exc}")
            self._set_status(f"{label} failed")
            return

        self._label = label
        self.log(f"Running {label}.")
        self._set_status(f"Running {label}")
        if needs_password:
            worker = ActionWorker(lambda log: action(config, log, worker.prompt_password))
        else:
            worker = ActionWorker(lambda log: action(config, log))
        worker.line.connect(self._on_line)
        worker.password_requested.connect(self.passwordRequested)
        worker.done.connect(self._on_done)
        self._worker = worker
        self._set_running(True)
        worker.start()

    @Slot(str)
    def _on_line(self, text: str) -> None:
        self.log(text)

    @Slot()
    def cancel(self) -> None:
        if not self._running or self._cancelling or self._worker is None:
            return
        self._worker.token.cancel()
        self._set_cancelling(True)
        self.log("Cancel requested. Stopping at the next safe point.")
        self._set_status(f"Cancelling {self._label}")

    @Slot(int)
    def _on_done(self, code: int) -> None:
        outcome = {0: "completed", 2: "cancelled"}.get(code, "failed")
        self.log(f"{self._label} {outcome}.")
        self._set_status(f"{self._label} {outcome}")
        self._set_cancelling(False)
        self._set_running(False)

    @Slot(str, bool)
    def providePassword(self, password: str, ok: bool) -> None:
        if self._worker is not None:
            self._worker.password = password if ok else ""

    @Slot(str, str)
    def setValue(self, key: str, value: str) -> None:
        self._values[key] = value

    @Slot()
    def loadSettings(self) -> None:
        env = load_env()
        values = {key: env.get(key, "") for key in FIELDS}
        if values["TARGET_OS"] not in CHOICES["TARGET_OS"]:
            values["TARGET_OS"] = "windows"
        self._values = values
        self.valuesChanged.emit()

    @Slot()
    def saveSettings(self) -> None:
        save_env({key: self._values.get(key, "").strip() for key in FIELDS})
        self.log("Saved .env.")

    @Slot()
    def resetDefaults(self) -> None:
        self._values = {key: PLACEHOLDERS.get(key, "") for key in FIELDS}
        self.valuesChanged.emit()
        self.log("Reset settings fields to defaults. Save .env to apply.")


def main() -> None:
    os.chdir(ROOT)
    QQuickStyle.setStyle("FluentWinUI3")
    mica = mica_supported()
    if mica:
        # The default Direct3D 11 swap chain is opaque, so Mica only shows through with OpenGL.
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
        QQuickWindow.setDefaultAlphaBuffer(True)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("PlugWake")
    icon = ROOT / "assets" / "icons" / "plugwake.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("micaRequested", mica)
    engine.rootContext().setContextProperty("appIconUrl", QUrl.fromLocalFile(str(icon)) if icon.exists() else QUrl())
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        raise SystemExit(1)

    window = engine.rootObjects()[0]
    if mica and not enable_mica(window):
        window.setProperty("micaActive", False)
    follow_color_scheme(app, window)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()

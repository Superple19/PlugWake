from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle

from .actions import (
    ActionCancelled,
    CancelToken,
    cancellable,
    read_status,
    remote_hard_reboot,
    remote_off,
    remote_on,
    remote_reboot,
    test_home_assistant,
    test_rdp_host,
)
from .config import FIELDS, ROOT, Config, config_from_values, load_config, load_env, save_env
from .theme import enable_mica, follow_color_scheme, mica_supported

QML_DIR = Path(__file__).with_name("qml")
STATUS_POLL_MS = 15_000

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

# key: (label, description, kind). kind is text, secret, choice, int, or float.
SETTINGS: dict[str, tuple[str, str, str]] = {
    "HA_URL": ("Home Assistant URL", "Base address, for example http://ha.example.local:8123.", "text"),
    "HA_TOKEN": ("Access token", "Long-lived access token from your Home Assistant profile.", "secret"),
    "PLUG_ENTITY": ("Smart plug entity", "Switch entity that powers the target PC.", "text"),
    "WATT_ENTITY": ("Power sensor entity", "Sensor that reports the plug's power draw in watts.", "text"),
    "RDP_HOST": ("RDP host", "Host name or address of the target PC for Remote Desktop.", "text"),
    "PC_SSH_TARGET": ("SSH target", "user@host used to shut down or reboot the target PC.", "text"),
    "TARGET_OS": ("Target OS", "Operating system on the target PC.", "choice"),
    "POWER_THRESHOLD_W": ("Running threshold (W)", "Power at or above this value means the PC is running.", "float"),
    "RDP_WAIT_SECONDS": ("RDP wait (s)", "How long Remote On waits for RDP to answer.", "int"),
    "SHUTDOWN_WAIT_SECONDS": (
        "Shutdown wait (s)",
        "How long Remote Off waits for power to drop. Plug power is not cut on timeout.",
        "int",
    ),
    "PLUG_OFF_SECONDS": ("Plug off time (s)", "How long the plug stays off during a power cycle.", "int"),
    "POWER_ON_LOW_CONFIRMATIONS": (
        "Remote On low readings",
        "Low readings in a row before Remote On power-cycles an on plug.",
        "int",
    ),
    "POWER_OFF_LOW_CONFIRMATIONS": (
        "Remote Off low readings",
        "Low readings in a row before Remote Off cuts plug power.",
        "int",
    ),
}

# (title, keys, test action shown under the group)
SETTING_GROUPS = [
    ("Home Assistant", ["HA_URL", "HA_TOKEN", "PLUG_ENTITY", "WATT_ENTITY"], "test-ha"),
    ("Target PC", ["RDP_HOST", "PC_SSH_TARGET", "TARGET_OS"], "test-rdp"),
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
        "",
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


class StatusProbe(QThread):
    result = Signal("QVariantMap")

    def run(self) -> None:
        try:
            status = read_status(load_config())
        except Exception as exc:
            status = {"plug": "", "watt": None, "rdp": None, "error": str(exc)}
        status["updated"] = timestamp()
        self.result.emit(status)


class Backend(QObject):
    logLine = Signal(str)
    passwordRequested = Signal(str)
    statusChanged = Signal()
    runningChanged = Signal()
    cancellingChanged = Signal()
    pcStatusChanged = Signal()
    valuesChanged = Signal()
    dirtyChanged = Signal()
    noticeChanged = Signal()
    testResultsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "Ready"
        self._running = False
        self._cancelling = False
        self._label = ""
        self._worker: ActionWorker | None = None
        self._values: dict[str, str] = {}
        self._saved: dict[str, str] = {}
        self._dirty = False
        self._notice: dict[str, object] = {"text": "", "error": False}
        self._test_results: dict[str, dict[str, object]] = {}
        self._test_id = ""
        self._last_line = ""
        self._pc_status: dict[str, object] = {"plug": "", "watt": None, "rdp": None, "error": "", "updated": ""}
        self._probe: StatusProbe | None = None
        self._poll_timer: QTimer | None = None
        self.loadSettings()

    def _get_status(self) -> str:
        return self._status

    def _get_running(self) -> bool:
        return self._running

    def _get_cancelling(self) -> bool:
        return self._cancelling

    def _get_pc_status(self) -> dict[str, object]:
        return self._pc_status

    def _get_values(self) -> dict[str, str]:
        return self._values

    def _get_dirty(self) -> bool:
        return self._dirty

    def _get_notice(self) -> dict[str, object]:
        return self._notice

    def _get_test_results(self) -> dict[str, dict[str, object]]:
        return self._test_results

    def _get_setting_groups(self) -> list[dict]:
        return [
            {
                "title": title,
                "test": test,
                "testLabel": ACTIONS[test][0] if test else "",
                "fields": [
                    {
                        "key": key,
                        "label": SETTINGS[key][0],
                        "description": SETTINGS[key][1],
                        "kind": SETTINGS[key][2],
                        "placeholder": PLACEHOLDERS.get(key, ""),
                        "choices": CHOICES.get(key, []),
                    }
                    for key in keys
                ],
            }
            for title, keys, test in SETTING_GROUPS
        ]

    status = Property(str, _get_status, notify=statusChanged)
    running = Property(bool, _get_running, notify=runningChanged)
    cancelling = Property(bool, _get_cancelling, notify=cancellingChanged)
    pcStatus = Property("QVariantMap", _get_pc_status, notify=pcStatusChanged)
    values = Property("QVariantMap", _get_values, notify=valuesChanged)
    dirty = Property(bool, _get_dirty, notify=dirtyChanged)
    notice = Property("QVariantMap", _get_notice, notify=noticeChanged)
    testResults = Property("QVariantMap", _get_test_results, notify=testResultsChanged)
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
        label = ACTIONS[action_id][0]
        try:
            config = load_config()
        except RuntimeError as exc:
            self.log(f"Error: {exc}")
            self._set_status(f"{label} failed")
            return
        self._start(action_id, config)

    @Slot(str)
    def testSetting(self, action_id: str) -> None:
        """Run a connection test against the values in the Settings page, saved or not."""
        if self._running:
            return
        try:
            config = config_from_values(self._values)
        except RuntimeError as exc:
            self._set_test_result(action_id, str(exc), False)
            return
        self._set_test_result(action_id, "Testing...", True)
        self._test_id = action_id
        self._start(action_id, config)

    def _set_test_result(self, action_id: str, text: str, ok: bool) -> None:
        self._test_results = {**self._test_results, action_id: {"text": text, "ok": ok}}
        self.testResultsChanged.emit()

    def _start(self, action_id: str, config: Config) -> None:
        label, action, needs_password, _confirm = ACTIONS[action_id]
        self._label = label
        self._last_line = ""
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
        self._last_line = text
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
        if self._test_id:
            result = self._last_line.removeprefix("Error: ").rstrip(".") or outcome
            self._set_test_result(self._test_id, result, code == 0)
            self._test_id = ""
        self._set_cancelling(False)
        self._set_running(False)

    def startStatusPolling(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(STATUS_POLL_MS)
        self._poll_timer.timeout.connect(self.refreshStatus)
        self._poll_timer.start()
        self.refreshStatus()

    @Slot()
    def refreshStatus(self) -> None:
        if self._probe is not None and self._probe.isRunning():
            return
        probe = StatusProbe()
        probe.result.connect(self._on_status)
        self._probe = probe
        probe.start()

    @Slot("QVariantMap")
    def _on_status(self, status: dict[str, object]) -> None:
        self._pc_status = status
        self.pcStatusChanged.emit()

    @Slot(str, bool)
    def providePassword(self, password: str, ok: bool) -> None:
        if self._worker is not None:
            self._worker.password = password if ok else ""

    @Slot(str, str)
    def setValue(self, key: str, value: str) -> None:
        self._values[key] = value
        self._update_dirty()

    def _update_dirty(self) -> None:
        dirty = any(self._values.get(key, "") != self._saved.get(key, "") for key in FIELDS)
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirtyChanged.emit()

    def _set_notice(self, text: str, error: bool = False) -> None:
        self._notice = {"text": text, "error": error}
        self.noticeChanged.emit()

    @Slot()
    def loadSettings(self) -> None:
        env = load_env()
        values = {key: env.get(key, "") for key in FIELDS}
        if values["TARGET_OS"] not in CHOICES["TARGET_OS"]:
            values["TARGET_OS"] = "windows"
        self._values = values
        self._saved = dict(values)
        self.valuesChanged.emit()
        self._update_dirty()
        self._set_notice("")

    @Slot()
    def saveSettings(self) -> None:
        values = {key: self._values.get(key, "").strip() for key in FIELDS}
        try:
            config_from_values(values)
        except RuntimeError as exc:
            self._set_notice(f"Not saved: {exc}", error=True)
            return
        save_env(values)
        self._values = values
        self._saved = dict(values)
        self.valuesChanged.emit()
        self._update_dirty()
        self._set_notice("Saved.")
        self.log("Saved .env.")
        if self._poll_timer is not None:
            self.refreshStatus()

    @Slot()
    def resetDefaults(self) -> None:
        self._values = {key: PLACEHOLDERS.get(key, "") for key in FIELDS}
        self.valuesChanged.emit()
        self._update_dirty()
        self._set_notice("Example defaults filled in. Save to apply.")


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
    backend.startStatusPolling()
    if mica and not enable_mica(window):
        window.setProperty("micaActive", False)
    follow_color_scheme(app, window)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()

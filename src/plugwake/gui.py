from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .actions import remote_hard_reboot, remote_off, remote_on, remote_reboot, test_home_assistant, test_rdp_host
from .config import FIELDS, ROOT, load_config, load_env, save_env


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


STYLE = """
QWidget {
  background: #171717;
  color: #f5f5f5;
  font-size: 10pt;
}
QTabBar::tab {
  background: #222222;
  border: 1px solid #3a3a3a;
  border-bottom: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  padding: 8px 14px;
}
QTabBar::tab:selected {
  background: #2b2b2b;
}
QTabWidget::pane {
  border: 1px solid #3a3a3a;
  background: #171717;
}
QGroupBox {
  background: #1f1f1f;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  margin-top: 12px;
  padding: 10px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 4px;
}
QPushButton {
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  color: #f5f5f5;
  padding: 8px 12px;
}
QPushButton:hover {
  background: #333333;
}
QPushButton#primaryOn {
  background: #238636;
  border-color: #2ea043;
  color: #ffffff;
  font-weight: 600;
}
QPushButton#primaryOff {
  background: #da3633;
  border-color: #f85149;
  color: #ffffff;
  font-weight: 600;
}
QPushButton#danger {
  border-color: #f85149;
  color: #ff7b72;
}
QPushButton#danger:hover {
  background: #3d1d1d;
}
QLineEdit, QComboBox, QPlainTextEdit {
  background: #111827;
  border: 1px solid #374151;
  border-radius: 4px;
  color: #f9fafb;
  padding: 6px;
}
QPlainTextEdit {
  background: #0f172a;
  color: #e5e7eb;
  font-family: Consolas, monospace;
}
"""

PLACEHOLDERS = {
    "HA_URL": "http://ha.example.local:8123",
    "HA_TOKEN": "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE",
    "PLUG_ENTITY": "switch.smart_plug",
    "WATT_ENTITY": "sensor.smart_plug_power",
    "RDP_HOST": "target-pc",
    "PC_SSH_TARGET": "user@target-pc",
    "POWER_THRESHOLD_W": "5",
    "RDP_WAIT_SECONDS": "180",
    "SHUTDOWN_WAIT_SECONDS": "300",
    "PLUG_OFF_SECONDS": "10",
    "POWER_ON_LOW_CONFIRMATIONS": "3",
    "POWER_OFF_LOW_CONFIRMATIONS": "4",
}


class ActionWorker(QThread):
    line = Signal(str)
    done = Signal(int)
    password_requested = Signal(str)

    def __init__(self, action: Callable[[Callable[[str], None]], None]) -> None:
        super().__init__()
        self.action = action
        self.password: str | None = None

    def run(self) -> None:
        try:
            self.action(self.line.emit)
        except Exception as exc:
            self.line.emit(f"Error: {exc}")
            self.done.emit(1)
            return
        self.done.emit(0)

    def prompt_password(self, target: str) -> str | None:
        self.password = None
        self.password_requested.emit(target)
        while self.password is None:
            self.msleep(50)
        return self.password


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PlugWake")
        icon = ROOT / "assets" / "icons" / "plugwake.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(780, 560)
        self.setStyleSheet(STYLE)
        self.inputs: dict[str, QLineEdit | QComboBox] = {}
        self.worker: QThread | None = None
        self.status = QLabel("Ready")
        self.status.setStyleSheet("font-weight: 600; padding: 4px 0;")

        tabs = QTabWidget()
        tabs.addTab(self._control_tab(), "Control")
        tabs.addTab(self._settings_tab(), "Settings")
        self.setCentralWidget(tabs)
        self.load_settings()

    def _control_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        primary = QHBoxLayout()
        primary.setSpacing(10)

        on_button = QPushButton("Remote On")
        on_button.setObjectName("primaryOn")
        on_button.setMinimumHeight(44)
        on_button.clicked.connect(lambda: self.run_action("Remote On", remote_on))
        primary.addWidget(on_button)

        off_button = QPushButton("Remote Off")
        off_button.setObjectName("primaryOff")
        off_button.setMinimumHeight(44)
        off_button.clicked.connect(
            lambda: self.run_action(
                "Remote Off",
                remote_off,
                needs_password=True,
                confirm="Shut down the target PC and turn the smart plug off?",
            )
        )
        primary.addWidget(off_button)

        secondary = QHBoxLayout()
        secondary.setSpacing(10)
        reboot_group = QHBoxLayout()
        reboot_group.setSpacing(10)
        tool_group = QHBoxLayout()
        tool_group.setSpacing(10)

        soft_reboot = QPushButton("Soft Reboot")
        soft_reboot.clicked.connect(
            lambda: self.run_action(
                "Soft Reboot", remote_reboot, needs_password=True, confirm="Reboot the target PC over SSH?"
            )
        )
        reboot_group.addWidget(soft_reboot)

        hard_reboot = QPushButton("Hard Reboot")
        hard_reboot.setObjectName("danger")
        hard_reboot.clicked.connect(
            lambda: self.run_action(
                "Hard Reboot",
                remote_hard_reboot,
                needs_password=True,
                confirm="Shut down the target PC, cut plug power, turn it back on, and open RDP?",
            )
        )
        reboot_group.addWidget(hard_reboot)

        for label, fn in [
            ("Test Home Assistant", lambda: self.run_action("Test Home Assistant", test_home_assistant)),
            ("Test RDP Port", lambda: self.run_action("Test RDP Port", test_rdp_host)),
        ]:
            button = QPushButton(label)
            button.clicked.connect(fn)
            tool_group.addWidget(button)
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(lambda: self.log.clear())
        tool_group.addWidget(clear_button)
        secondary.addLayout(reboot_group)
        secondary.addStretch()
        secondary.addLayout(tool_group)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.status)
        layout.addLayout(primary)
        layout.addLayout(secondary)
        layout.addWidget(self.log)
        return root

    def _settings_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        for key in FIELDS:
            if key == "TARGET_OS":
                field = QComboBox()
                field.addItems(["windows", "linux"])
            else:
                field = QLineEdit()
                field.setPlaceholderText(PLACEHOLDERS.get(key, ""))
                if key == "HA_TOKEN":
                    field.setEchoMode(QLineEdit.EchoMode.Password)
            self.inputs[key] = field

        layout.addWidget(self._settings_group("Home Assistant", ["HA_URL", "HA_TOKEN", "PLUG_ENTITY", "WATT_ENTITY"]))
        layout.addWidget(self._settings_group("Target PC", ["RDP_HOST", "PC_SSH_TARGET", "TARGET_OS"]))
        layout.addWidget(
            self._settings_group(
                "Power Safety",
                [
                    "POWER_THRESHOLD_W",
                    "RDP_WAIT_SECONDS",
                    "SHUTDOWN_WAIT_SECONDS",
                    "PLUG_OFF_SECONDS",
                    "POWER_ON_LOW_CONFIRMATIONS",
                    "POWER_OFF_LOW_CONFIRMATIONS",
                ],
            )
        )

        save = QPushButton("Save .env")
        save.clicked.connect(self.save_settings)
        reload_button = QPushButton("Reload .env")
        reload_button.clicked.connect(self.load_settings)
        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self.reset_defaults)
        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(reload_button)
        buttons.addWidget(reset_button)
        layout.addLayout(buttons)
        layout.addStretch()
        return root

    def _settings_group(self, title: str, keys: list[str]) -> QGroupBox:
        group = QGroupBox(title)
        form = QFormLayout(group)
        for key in keys:
            form.addRow(key, self.inputs[key])
        return group

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(f"[{timestamp()}] {text}")

    def load_settings(self) -> None:
        values = load_env()
        for key, field in self.inputs.items():
            value = values.get(key, "")
            if isinstance(field, QComboBox):
                field.setCurrentText(value if value in ["windows", "linux"] else "windows")
            else:
                field.setText(value)

    def save_settings(self) -> None:
        save_env({key: self.input_value(field) for key, field in self.inputs.items()})
        self.append_log("Saved .env.")

    def reset_defaults(self) -> None:
        if (
            QMessageBox.question(
                self, "Reset Defaults", "Reset settings fields to example defaults? This will not save .env yet."
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        for key, field in self.inputs.items():
            if isinstance(field, QComboBox):
                field.setCurrentText("windows")
            else:
                field.setText(PLACEHOLDERS.get(key, ""))
        self.append_log("Reset settings fields to defaults. Save .env to apply.")

    def input_value(self, field: QLineEdit | QComboBox) -> str:
        if isinstance(field, QComboBox):
            return field.currentText()
        return field.text().strip()

    def run_action(
        self, label: str, action: Callable, needs_password: bool = False, confirm: str | None = None
    ) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "PlugWake", "A command is already running.")
            return
        if confirm and QMessageBox.question(self, label, confirm) != QMessageBox.StandardButton.Yes:
            return

        try:
            config = load_config()
        except RuntimeError as exc:
            self.append_log(f"Error: {exc}")
            self.status.setText(f"{label} failed")
            return
        self.append_log(f"Running {label}.")
        self.status.setText(f"Running {label}")
        if needs_password:
            worker = ActionWorker(lambda log: action(config, log, worker.prompt_password))
            worker.password_requested.connect(self.ask_password)
            self.worker = worker
        else:
            self.worker = ActionWorker(lambda log: action(config, log))
        self.worker.line.connect(self.append_log)
        self.worker.done.connect(lambda code: self.finish_action(label, code))
        self.worker.start()

    def finish_action(self, label: str, code: int) -> None:
        self.append_log(f"{label} exited with code {code}.")
        self.status.setText(f"{label} {'completed' if code == 0 else 'failed'}")

    def ask_password(self, target: str) -> None:
        assert isinstance(self.worker, ActionWorker)
        password, ok = QInputDialog.getText(self, "Password", f"Password for {target}", QLineEdit.EchoMode.Password)
        self.worker.password = password if ok else ""


def main() -> None:
    os.chdir(ROOT)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()

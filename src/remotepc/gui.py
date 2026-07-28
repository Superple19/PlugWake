from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from .actions import remote_off, remote_on
from .config import FIELDS, ROOT, load_config, load_env, save_env


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class CommandWorker(QThread):
    line = Signal(str)
    done = Signal(int)

    def __init__(self, args: list[str]) -> None:
        super().__init__()
        self.args = args

    def run(self) -> None:
        process = subprocess.Popen(self.args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        assert process.stdout is not None
        for line in process.stdout:
            self.line.emit(line.rstrip())
        self.done.emit(process.wait())


class ActionWorker(QThread):
    line = Signal(str)
    done = Signal(int)

    def __init__(self, action: Callable[[Callable[[str], None]], None]) -> None:
        super().__init__()
        self.action = action

    def run(self) -> None:
        try:
            self.action(self.line.emit)
        except Exception as exc:
            self.line.emit(f"Error: {exc}")
            self.done.emit(1)
            return
        self.done.emit(0)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RemotePC")
        self.resize(780, 560)
        self.inputs: dict[str, QLineEdit] = {}
        self.worker: QThread | None = None

        tabs = QTabWidget()
        tabs.addTab(self._control_tab(), "Control")
        tabs.addTab(self._settings_tab(), "Settings")
        self.setCentralWidget(tabs)
        self.load_settings()

    def _control_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        buttons = QHBoxLayout()

        on_button = QPushButton("Remote On")
        on_button.clicked.connect(lambda: self.run_action("Remote On", remote_on))
        buttons.addWidget(on_button)

        off_button = QPushButton("Remote Off")
        off_button.clicked.connect(lambda: self.run_action("Remote Off", remote_off))
        buttons.addWidget(off_button)

        boot_button = QPushButton("Boot Linux Once")
        boot_button.clicked.connect(lambda: self.run_command("Boot Linux Once", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "boot_linux_once.ps1")]))
        buttons.addWidget(boot_button)

        tests = QHBoxLayout()
        for label, fn in [("Test Home Assistant", self.test_ha), ("Test RDP Host", self.test_rdp), ("Show Boot Entries", self.show_boot_entries)]:
            button = QPushButton(label)
            button.clicked.connect(fn)
            tests.addWidget(button)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addLayout(buttons)
        layout.addLayout(tests)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log)
        return root

    def _settings_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()

        for key in FIELDS:
            field = QLineEdit()
            if key == "HA_TOKEN":
                field.setEchoMode(QLineEdit.EchoMode.Password)
            self.inputs[key] = field
            form.addRow(key, field)

        save = QPushButton("Save .env")
        save.clicked.connect(self.save_settings)
        reload_button = QPushButton("Reload .env")
        reload_button.clicked.connect(self.load_settings)
        layout.addLayout(form)
        layout.addWidget(save)
        layout.addWidget(reload_button)
        layout.addStretch()
        return root

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(f"[{timestamp()}] {text}")

    def load_settings(self) -> None:
        values = load_env()
        for key, field in self.inputs.items():
            field.setText(values.get(key, ""))

    def save_settings(self) -> None:
        save_env({key: field.text().strip() for key, field in self.inputs.items()})
        self.append_log("Saved .env")

    def run_command(self, label: str, args: list[str]) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "RemotePC", "A command is already running.")
            return

        self.append_log(f"Running {label}")
        self.worker = CommandWorker(args)
        self.worker.line.connect(self.append_log)
        self.worker.done.connect(lambda code: self.append_log(f"{label} exited with {code}"))
        self.worker.start()

    def run_action(self, label: str, action: Callable) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "RemotePC", "A command is already running.")
            return

        config = load_config()
        self.append_log(f"Running {label}")
        self.worker = ActionWorker(lambda log: action(config, log))
        self.worker.line.connect(self.append_log)
        self.worker.done.connect(lambda code: self.append_log(f"{label} exited with {code}"))
        self.worker.start()

    def test_ha(self) -> None:
        values = load_env()
        url = values.get("HA_URL", "").rstrip("/")
        token = values.get("HA_TOKEN", "")
        if not url or not token:
            self.append_log("Set HA_URL and HA_TOKEN first.")
            return

        request = urllib.request.Request(f"{url}/api/", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                self.append_log(f"Home Assistant OK: HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            self.append_log(f"Home Assistant HTTP error: {exc.code}")
        except OSError as exc:
            self.append_log(f"Home Assistant connection failed: {exc}")

    def test_rdp(self) -> None:
        host = load_env().get("RDP_HOST", "").strip()
        if not host:
            self.append_log("Set RDP_HOST first.")
            return
        try:
            with socket.create_connection((host, 3389), timeout=5):
                self.append_log(f"{host}:3389 is reachable.")
        except OSError as exc:
            self.append_log(f"{host}:3389 is not reachable: {exc}")

    def show_boot_entries(self) -> None:
        try:
            result = subprocess.run(["bcdedit", "/enum", "firmware"], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
        except OSError as exc:
            self.append_log(f"Failed to run bcdedit: {exc}")
            return
        output = result.stdout.strip() or result.stderr.strip()
        self.append_log(output if output else f"bcdedit exited with {result.returncode}")


def main() -> None:
    os.chdir(ROOT)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()

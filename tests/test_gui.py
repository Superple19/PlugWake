from __future__ import annotations

import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication

from plugwake import actions, gui


def test_setting_groups_cover_every_env_field_once() -> None:
    keys = [field["key"] for group in gui.Backend().settingGroups for field in group["fields"]]

    assert sorted(keys) == sorted(gui.FIELDS)


def test_backend_saves_edited_values(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[dict[str, str]] = []
    monkeypatch.setattr(gui, "load_env", lambda: {"HA_URL": "http://ha.example.local:8123"})
    monkeypatch.setattr(gui, "save_env", saved.append)

    backend = gui.Backend()
    backend.setValue("RDP_HOST", " target-pc ")
    backend.saveSettings()

    assert saved[0]["HA_URL"] == "http://ha.example.local:8123"
    assert saved[0]["RDP_HOST"] == "target-pc"
    assert saved[0]["TARGET_OS"] == "windows"
    assert set(saved[0]) == set(gui.FIELDS)


def test_backend_reports_config_errors_without_starting(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []

    def broken_config() -> None:
        raise RuntimeError("RDP_WAIT_SECONDS must be greater than zero")

    monkeypatch.setattr(gui, "load_config", broken_config)
    backend = gui.Backend()
    backend.logLine.connect(lines.append)

    backend.run("on")

    assert backend.running is False
    assert backend.status == "Remote On failed"
    assert lines[-1].endswith("Error: RDP_WAIT_SECONDS must be greater than zero")


def test_every_action_has_a_label_and_known_confirmation() -> None:
    backend = gui.Backend()

    assert backend.confirmText("on") == ""
    assert "Shut down" in backend.confirmText("off")
    assert all(backend.actionLabel(action_id) for action_id in gui.ACTIONS)


def test_worker_reports_cancellation_with_its_own_exit_code() -> None:
    codes: list[int] = []
    lines: list[str] = []

    def action(_log: object) -> None:
        worker.token.cancel()
        actions.pause(1)

    worker = gui.ActionWorker(action)
    worker.done.connect(codes.append)
    worker.line.connect(lines.append)
    worker.run()

    assert codes == [2]
    assert lines == ["Cancelled by user."]


def test_backend_cancel_stops_a_running_action(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    started = threading.Event()

    def slow_action(_config: object, _log: object) -> None:
        started.set()
        actions.pause(30)

    monkeypatch.setattr(gui, "load_config", lambda: None)
    monkeypatch.setitem(gui.ACTIONS, "on", ("Remote On", slow_action, False, ""))
    backend = gui.Backend()

    backend.run("on")
    assert started.wait(5)
    backend.cancel()
    deadline = time.monotonic() + 5
    while backend.running and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert backend.running is False
    assert backend.status == "Remote On cancelled"


def test_status_probe_reports_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    results: list[dict] = []

    def broken_config() -> None:
        raise RuntimeError("PLUG_OFF_SECONDS must be greater than zero")

    monkeypatch.setattr(gui, "load_config", broken_config)
    probe = gui.StatusProbe()
    probe.result.connect(results.append)
    probe.run()

    assert results[0]["error"] == "PLUG_OFF_SECONDS must be greater than zero"
    assert results[0]["updated"]


def test_backend_tracks_unsaved_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gui, "load_env", lambda: {"RDP_HOST": "target-pc"})
    monkeypatch.setattr(gui, "save_env", lambda _values: None)
    backend = gui.Backend()

    assert backend.dirty is False
    backend.setValue("RDP_HOST", "other-pc")
    assert backend.dirty is True
    backend.setValue("RDP_HOST", "target-pc")
    assert backend.dirty is False
    backend.setValue("RDP_HOST", "other-pc")
    backend.saveSettings()
    assert backend.dirty is False
    assert backend.notice == {"text": "Saved.", "error": False}


def test_backend_refuses_to_save_invalid_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[dict[str, str]] = []
    monkeypatch.setattr(gui, "load_env", lambda: {})
    monkeypatch.setattr(gui, "save_env", saved.append)
    backend = gui.Backend()

    backend.setValue("PLUG_OFF_SECONDS", "0")
    backend.saveSettings()

    assert saved == []
    assert backend.dirty is True
    assert backend.notice == {"text": "Not saved: PLUG_OFF_SECONDS must be greater than zero", "error": True}


def test_setting_test_uses_unsaved_values(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[tuple[str, str]] = []
    monkeypatch.setattr(gui, "load_env", lambda: {"RDP_HOST": "saved-pc"})
    monkeypatch.setattr(
        gui.Backend, "_start", lambda _self, action_id, config: started.append((action_id, config.rdp_host))
    )
    backend = gui.Backend()

    backend.setValue("RDP_HOST", "draft-pc")
    backend.testSetting("test-rdp")

    assert started == [("test-rdp", "draft-pc")]
    assert backend.testResults["test-rdp"] == {"text": "Testing...", "ok": True}


def test_setting_metadata_covers_every_field() -> None:
    assert set(gui.SETTINGS) == set(gui.FIELDS)
    assert all(kind in {"text", "secret", "choice", "int", "float"} for _label, _desc, kind in gui.SETTINGS.values())

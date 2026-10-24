from __future__ import annotations

import pytest

from plugwake import gui


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

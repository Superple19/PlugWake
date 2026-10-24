from __future__ import annotations

import pytest

from plugwake import actions
from plugwake.config import Config


def make_config(**overrides: object) -> Config:
    values: dict[str, object] = {
        "ha_url": "http://ha.example.local:8123",
        "ha_token": "test-token",
        "plug_entity": "switch.smart_plug",
        "watt_entity": "sensor.smart_plug_power",
        "rdp_host": "target-pc",
        "ssh_target": "user@target-pc",
        "target_os": "windows",
        "power_threshold_w": 5.0,
        "rdp_wait_seconds": 1,
        "power_on_low_confirmations": 3,
        "power_off_low_confirmations": 3,
    }
    values.update(overrides)
    return Config(**values)


def test_remote_off_requires_repeated_low_power_before_cutoff(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(power_off_low_confirmations=3)
    readings = ["0", "0", "0"]
    plug_actions: list[str] = []

    def state(_self: actions.HomeAssistant, entity: str) -> str:
        return "on" if entity == config.plug_entity else readings.pop(0)

    def set_plug(_self: actions.HomeAssistant, state: str) -> None:
        plug_actions.append(state)

    monkeypatch.setattr(actions.HomeAssistant, "state", state)
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", set_plug)
    monkeypatch.setattr(actions.time, "sleep", lambda _seconds: None)

    actions.remote_off(config, lambda _message: None)

    assert plug_actions == ["off"]
    assert readings == []


@pytest.mark.parametrize("reading", ["unavailable", "unknown", "nan", "inf", "-inf", "-1"])
def test_remote_off_rejects_invalid_power_readings(monkeypatch: pytest.MonkeyPatch, reading: str) -> None:
    config = make_config()
    plug_actions: list[str] = []

    def state(_self: actions.HomeAssistant, entity: str) -> str:
        return "on" if entity == config.plug_entity else reading

    def set_plug(_self: actions.HomeAssistant, state: str) -> None:
        plug_actions.append(state)

    monkeypatch.setattr(actions.HomeAssistant, "state", state)
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", set_plug)

    with pytest.raises(RuntimeError, match="Invalid power sensor state"):
        actions.remote_off(config, lambda _message: None)

    assert plug_actions == []


def test_hard_reboot_stops_when_remote_off_does_not_confirm_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config()
    plug_actions: list[str] = []
    rdp_opened: list[bool] = []

    monkeypatch.setattr(actions, "remote_off", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", lambda _self, state: plug_actions.append(state))
    monkeypatch.setattr(actions, "open_rdp", lambda *_args, **_kwargs: rdp_opened.append(True))

    with pytest.raises(actions.ActionFailed, match="shutdown was not confirmed"):
        actions.remote_hard_reboot(config, lambda _message: None)

    assert plug_actions == []
    assert rdp_opened == []

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
        if entity == config.plug_entity:
            return "off" if plug_actions else "on"
        return readings.pop(0)

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


def test_remote_off_fails_when_plug_does_not_confirm_off(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    plug_actions: list[str] = []

    def state(_self: actions.HomeAssistant, entity: str) -> str:
        return "on" if entity == config.plug_entity else "0"

    monkeypatch.setattr(actions.HomeAssistant, "state", state)
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", lambda _self, state: plug_actions.append(state))
    monkeypatch.setattr(actions.time, "monotonic", iter([0, 16]).__next__)
    monkeypatch.setattr(actions.time, "sleep", lambda _seconds: None)

    assert actions.remote_off(config, lambda _message: None) is False
    assert plug_actions == ["off"]


def test_remote_off_rejects_unknown_plug_state(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    plug_actions: list[str] = []

    monkeypatch.setattr(actions.HomeAssistant, "state", lambda _self, _entity: "unavailable")
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", lambda _self, state: plug_actions.append(state))

    with pytest.raises(actions.ActionFailed, match="Invalid smart plug state"):
        actions.remote_off(config, lambda _message: None)

    assert plug_actions == []


def test_remote_on_rejects_unknown_plug_state(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()

    monkeypatch.setattr(actions, "tailscale_connected", lambda: True)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(actions.HomeAssistant, "state", lambda _self, _entity: "unknown")

    with pytest.raises(actions.ActionFailed, match="Invalid smart plug state"):
        actions.remote_on(config, lambda _message: None)


def test_connect_ssh_rejects_unknown_host_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.policy = None

        def load_system_host_keys(self) -> None:
            pass

        def set_missing_host_key_policy(self, policy: object) -> None:
            self.policy = policy

        def connect(self, **_kwargs: object) -> None:
            pass

    client = FakeClient()
    monkeypatch.setattr(actions.paramiko, "SSHClient", lambda: client)

    connected, _password = actions.connect_ssh("user@target-pc", lambda _message: None, None)

    assert connected is client
    assert isinstance(client.policy, actions.paramiko.RejectPolicy)

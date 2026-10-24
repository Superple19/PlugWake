from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugwake import actions
from plugwake.config import Config


@pytest.fixture(autouse=True)
def reachable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions, "tailscale_connected", lambda: None)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: True)


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
        "shutdown_wait_seconds": 300,
        "plug_off_seconds": 10,
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

    with pytest.raises(actions.ActionFailed, match="Shutdown was not confirmed"):
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


def test_linux_rdp_detection_finds_existing_freerdp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions.sys, "platform", "linux")
    monkeypatch.setattr(actions.shutil, "which", lambda command: "/usr/bin/pgrep" if command == "pgrep" else None)
    monkeypatch.setattr(
        actions.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="1234 xfreerdp /v:target-pc\n", returncode=0),
    )

    assert actions.rdp_is_open("target-pc") is True


def test_windows_rdp_detection_does_not_interpolate_host_into_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    host = "target'; Write-Output 'unexpected"

    monkeypatch.setattr(actions.sys, "platform", "win32")
    monkeypatch.setattr(actions.shutil, "which", lambda _command: "powershell.exe")

    def run(*args: object, **kwargs: object) -> SimpleNamespace:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(actions.subprocess, "run", run)

    assert actions.rdp_is_open(host) is False
    command = captured["args"][0][3]
    environment = captured["kwargs"]["env"]
    assert host not in command
    assert environment["PLUGWAKE_RDP_HOST"] == host


class FakeClient:
    def __init__(self, fail_password: bool = False) -> None:
        self.policy = None
        self.closed = False
        self.fail_password = fail_password

    def load_system_host_keys(self) -> None:
        pass

    def set_missing_host_key_policy(self, policy: object) -> None:
        self.policy = policy

    def connect(self, **kwargs: object) -> None:
        if "password" not in kwargs or self.fail_password:
            raise actions.paramiko.AuthenticationException("auth failed")

    def close(self) -> None:
        self.closed = True


def test_connect_ssh_uses_a_new_client_for_each_password_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    clients = [FakeClient(), FakeClient(fail_password=True), FakeClient()]
    created = list(clients)
    monkeypatch.setattr(actions.paramiko, "SSHClient", lambda: created.pop(0))
    passwords = iter(["wrong", "right"])

    connected, password = actions.connect_ssh("user@target-pc", lambda _message: None, lambda _target: next(passwords))

    assert connected is clients[2]
    assert password == "right"
    assert clients[0].closed and clients[1].closed and not clients[2].closed


def fake_power_ssh(
    monkeypatch: pytest.MonkeyPatch, password: str | None, codes: list[int]
) -> list[tuple[str, str | None]]:
    commands: list[tuple[str, str | None]] = []
    client = FakeClient()

    def exec_ssh(_client: object, command: str, _log: object, stdin_text: str | None = None) -> int:
        commands.append((command, stdin_text))
        return codes.pop(0)

    monkeypatch.setattr(actions, "connect_ssh", lambda *_args: (client, password))
    monkeypatch.setattr(actions, "exec_ssh", exec_ssh)
    return commands


def test_linux_power_command_skips_password_prompt_when_sudo_needs_none(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(target_os="linux")
    commands = fake_power_ssh(monkeypatch, None, [0])
    prompts: list[str] = []

    def prompt(target: str) -> str:
        prompts.append(target)
        return "secret"

    assert actions.ssh_shutdown(config, lambda _message: None, prompt) is True
    assert commands == [("sudo -n systemctl poweroff", None)]
    assert prompts == []


def test_linux_power_command_prompts_when_sudo_requires_password(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(target_os="linux")
    commands = fake_power_ssh(monkeypatch, None, [1, 0])

    assert actions.ssh_shutdown(config, lambda _message: None, lambda _target: "secret") is True
    assert commands == [
        ("sudo -n systemctl poweroff", None),
        ("sudo -S -p '' systemctl poweroff", "secret"),
    ]


def test_linux_power_command_reuses_ssh_password_for_sudo(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(target_os="linux")
    commands = fake_power_ssh(monkeypatch, "secret", [0])

    assert actions.ssh_shutdown(config, lambda _message: None, None) is True
    assert commands == [("sudo -S -p '' systemctl poweroff", "secret")]


@pytest.mark.parametrize(("code", "sent"), [(0, True), (actions.SSH_NO_EXIT_STATUS, True), (1, False)])
def test_power_command_treats_dropped_connection_as_sent(
    monkeypatch: pytest.MonkeyPatch, code: int, sent: bool
) -> None:
    config = make_config(target_os="windows")
    fake_power_ssh(monkeypatch, None, [code])

    assert actions.ssh_shutdown(config, lambda _message: None, None) is sent


def test_remote_on_stops_when_plug_does_not_confirm_on(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    plug_actions: list[str] = []
    rdp_opened: list[bool] = []

    def state(_self: actions.HomeAssistant, entity: str) -> str:
        return "off" if entity == config.plug_entity else "0"

    monkeypatch.setattr(actions, "tailscale_connected", lambda: True)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(actions.HomeAssistant, "state", state)
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", lambda _self, state: plug_actions.append(state))
    monkeypatch.setattr(actions, "open_rdp", lambda *_args, **_kwargs: rdp_opened.append(True))
    monkeypatch.setattr(actions.time, "monotonic", iter([0, 16]).__next__)
    monkeypatch.setattr(actions.time, "sleep", lambda _seconds: None)

    with pytest.raises(actions.ActionFailed, match="did not confirm the on state"):
        actions.remote_on(config, lambda _message: None)

    assert plug_actions == ["on"]
    assert rdp_opened == []


def test_remote_on_fails_when_home_assistant_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions, "tailscale_connected", lambda: True)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: False)

    with pytest.raises(actions.ActionFailed, match="Home Assistant is not reachable"):
        actions.remote_on(make_config(), lambda _message: None)


def test_open_rdp_fails_when_host_never_comes_online(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions, "rdp_is_open", lambda _host: False)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(actions.time, "monotonic", iter([0, 0, 2]).__next__)
    monkeypatch.setattr(actions.time, "sleep", lambda _seconds: None)

    with pytest.raises(actions.ActionFailed, match="was not ready within"):
        actions.open_rdp(make_config(rdp_wait_seconds=1), lambda _message: None)


def test_test_rdp_host_fails_when_port_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: False)

    with pytest.raises(actions.ActionFailed, match="not reachable"):
        actions.test_rdp_host(make_config(), lambda _message: None)


@pytest.mark.parametrize(
    ("code", "message"),
    [(401, "rejected the token"), (404, "entity not found: switch.smart_plug"), (500, "HTTP 500")],
)
def test_home_assistant_http_errors_are_explained(monkeypatch: pytest.MonkeyPatch, code: int, message: str) -> None:
    def urlopen(request: object, timeout: float) -> None:
        raise actions.urllib.error.HTTPError("http://ha", code, "reason", {}, None)

    monkeypatch.setattr(actions.urllib.request, "urlopen", urlopen)

    with pytest.raises(actions.ActionFailed, match=message):
        actions.HomeAssistant(make_config()).state("switch.smart_plug")


def test_remote_on_continues_when_tailscale_is_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    lines: list[str] = []
    rdp_opened: list[bool] = []

    monkeypatch.setattr(actions, "tailscale_connected", lambda: False)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(actions.HomeAssistant, "state", lambda _self, _entity: "on")
    monkeypatch.setattr(actions.HomeAssistant, "watt", lambda _self: 60.0)
    monkeypatch.setattr(actions, "open_rdp", lambda *_args, **_kwargs: rdp_opened.append(True))

    actions.remote_on(config, lines.append)

    assert any(line.startswith("Warning: Tailscale is not connected") for line in lines)
    assert rdp_opened == [True]


def test_remote_on_mentions_tailscale_when_home_assistant_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(actions, "tailscale_connected", lambda: False)
    monkeypatch.setattr(actions, "tcp_open", lambda *_args, **_kwargs: False)

    with pytest.raises(actions.ActionFailed, match="Tailscale is also not connected"):
        actions.remote_on(make_config(), lambda _message: None)


def fake_plug(monkeypatch: pytest.MonkeyPatch, watts: list[float]) -> list[str]:
    events: list[str] = []
    plug = {"state": "on"}

    def set_plug(_self: actions.HomeAssistant, state: str) -> None:
        events.append(f"plug {state}")
        plug["state"] = state

    monkeypatch.setattr(actions.HomeAssistant, "state", lambda _self, _entity: plug["state"])
    monkeypatch.setattr(actions.HomeAssistant, "watt", lambda _self: watts.pop(0))
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", set_plug)
    monkeypatch.setattr(actions.time, "sleep", lambda seconds: events.append(f"sleep {seconds}"))
    monkeypatch.setattr(actions, "open_rdp", lambda *_args, **_kwargs: events.append("rdp"))
    return events


def test_remote_on_power_cycle_waits_with_plug_off(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(power_on_low_confirmations=2, plug_off_seconds=12)
    events = fake_plug(monkeypatch, [1.0, 1.0])
    monkeypatch.setattr(actions, "tcp_open", lambda host, *_args, **_kwargs: host != config.rdp_host)

    actions.remote_on(config, lambda _message: None)

    assert events == ["sleep 5", "plug off", "sleep 12", "plug on", "rdp"]


def test_remote_on_power_cycle_stops_when_plug_does_not_confirm_off(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(power_on_low_confirmations=1)
    events = fake_plug(monkeypatch, [1.0])
    monkeypatch.setattr(actions.HomeAssistant, "set_plug", lambda _self, state: events.append(f"plug {state}"))
    monkeypatch.setattr(actions, "tcp_open", lambda host, *_args, **_kwargs: host != config.rdp_host)
    monkeypatch.setattr(actions.time, "monotonic", iter([0, 16]).__next__)

    with pytest.raises(actions.ActionFailed, match="did not confirm the off state"):
        actions.remote_on(config, lambda _message: None)

    assert "plug on" not in events


def test_hard_reboot_waits_with_plug_off_before_turning_on(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(plug_off_seconds=12)
    events = fake_plug(monkeypatch, [])
    monkeypatch.setattr(actions, "remote_off", lambda *_args, **_kwargs: events.append("off") or True)

    actions.remote_hard_reboot(config, lambda _message: None)

    assert events == ["off", "sleep 12", "plug on", "rdp"]


def test_remote_off_ssh_failure_mentions_disconnected_tailscale(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_plug(monkeypatch, [60.0])
    monkeypatch.setattr(actions, "tailscale_connected", lambda: False)
    monkeypatch.setattr(actions, "ssh_shutdown", lambda *_args: False)

    with pytest.raises(actions.ActionFailed, match="SSH shutdown failed. Tailscale is also not connected"):
        actions.remote_off(make_config(), lambda _message: None)

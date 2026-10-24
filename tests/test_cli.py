from __future__ import annotations

import sys

import pytest

from plugwake import actions, cli


def test_cli_off_exits_with_error_when_plug_power_is_not_cut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["plugwake-cli", "off"])
    monkeypatch.setattr(cli, "load_config", lambda: None)
    lines: list[str] = []

    def remote_off(*_args: object) -> None:
        raise actions.ActionFailed("Power recovered to 60 W. Not cutting plug power")

    monkeypatch.setattr(cli, "remote_off", remote_off)
    monkeypatch.setattr(cli, "log", lines.append)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    assert lines == ["Error: Power recovered to 60 W. Not cutting plug power"]


def test_cli_reports_config_errors_without_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []

    def broken_config() -> None:
        raise RuntimeError("RDP_WAIT_SECONDS must be greater than zero")

    monkeypatch.setattr(sys, "argv", ["plugwake-cli", "on"])
    monkeypatch.setattr(cli, "load_config", broken_config)
    monkeypatch.setattr(cli, "log", lines.append)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    assert lines == ["Error: RDP_WAIT_SECONDS must be greater than zero"]

from __future__ import annotations

import sys

import pytest

from plugwake import cli


def test_cli_off_exits_with_error_when_plug_power_is_not_cut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["plugwake-cli", "off"])
    monkeypatch.setattr(cli, "load_config", lambda: None)
    monkeypatch.setattr(cli, "remote_off", lambda *_args: False)
    monkeypatch.setattr(cli, "log", lambda _text: None)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1

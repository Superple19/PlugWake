from __future__ import annotations

import pytest

from plugwake import config


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("RDP_WAIT_SECONDS", "0"),
        ("SHUTDOWN_WAIT_SECONDS", "0"),
        ("SHUTDOWN_WAIT_SECONDS", "abc"),
        ("PLUG_OFF_SECONDS", "0"),
        ("POWER_ON_LOW_CONFIRMATIONS", "0"),
        ("POWER_OFF_LOW_CONFIRMATIONS", "-1"),
        ("POWER_THRESHOLD_W", "nan"),
    ],
)
def test_load_config_rejects_unsafe_numeric_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path, key: str, value: str
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"{key}={value}\n", encoding="utf-8")
    monkeypatch.setattr(config, "ENV_FILE", env_file)

    with pytest.raises(RuntimeError):
        config.load_config()


def test_load_config_uses_defaults_without_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / ".env")

    loaded = config.load_config()

    assert loaded.target_os == "windows"
    assert loaded.power_threshold_w == 5
    assert loaded.rdp_wait_seconds == 180
    assert loaded.shutdown_wait_seconds == 300
    assert loaded.plug_off_seconds == 10
    assert loaded.power_on_low_confirmations == 3
    assert loaded.power_off_low_confirmations == 4


def test_load_config_reads_values_from_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nHA_URL=http://ha.example.local:8123/\nTARGET_OS= Linux \nSHUTDOWN_WAIT_SECONDS=120\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_FILE", env_file)

    loaded = config.load_config()

    assert loaded.ha_url == "http://ha.example.local:8123"
    assert loaded.target_os == "linux"
    assert loaded.shutdown_wait_seconds == 120

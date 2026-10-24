from __future__ import annotations

import pytest

from plugwake import config


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("RDP_WAIT_SECONDS", "0"),
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

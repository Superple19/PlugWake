from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"

FIELDS = [
    "HA_URL",
    "HA_TOKEN",
    "PLUG_ENTITY",
    "WATT_ENTITY",
    "RDP_HOST",
    "PC_SSH_TARGET",
    "TARGET_OS",
    "POWER_THRESHOLD_W",
    "RDP_WAIT_SECONDS",
    "SHUTDOWN_WAIT_SECONDS",
    "POWER_ON_LOW_CONFIRMATIONS",
    "POWER_OFF_LOW_CONFIRMATIONS",
]

DEFAULTS = {
    "TARGET_OS": "windows",
    "POWER_THRESHOLD_W": "5",
    "RDP_WAIT_SECONDS": "180",
    "SHUTDOWN_WAIT_SECONDS": "300",
    "POWER_ON_LOW_CONFIRMATIONS": "3",
    "POWER_OFF_LOW_CONFIRMATIONS": "4",
}


@dataclass(frozen=True)
class Config:
    ha_url: str
    ha_token: str
    plug_entity: str
    watt_entity: str
    rdp_host: str
    ssh_target: str
    target_os: str
    power_threshold_w: float
    rdp_wait_seconds: int
    shutdown_wait_seconds: int
    power_on_low_confirmations: int
    power_off_low_confirmations: int


def load_env() -> dict[str, str]:
    values = dict(DEFAULTS)
    if not ENV_FILE.exists():
        return values

    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def save_env(values: dict[str, str]) -> None:
    current = load_env()
    current.update(values)
    lines = [f"{key}={current.get(key, '')}" for key in FIELDS]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_config() -> Config:
    values = load_env()
    try:
        power_threshold_w = float(values.get("POWER_THRESHOLD_W", "5"))
        rdp_wait_seconds = int(values.get("RDP_WAIT_SECONDS", "180"))
        shutdown_wait_seconds = int(values.get("SHUTDOWN_WAIT_SECONDS", "300"))
        power_on_low_confirmations = int(values.get("POWER_ON_LOW_CONFIRMATIONS", "3"))
        power_off_low_confirmations = int(values.get("POWER_OFF_LOW_CONFIRMATIONS", "4"))
    except ValueError as exc:
        raise RuntimeError("Numeric settings in .env are invalid") from exc

    if not math.isfinite(power_threshold_w) or power_threshold_w < 0:
        raise RuntimeError("POWER_THRESHOLD_W must be a finite non-negative number")
    if rdp_wait_seconds <= 0:
        raise RuntimeError("RDP_WAIT_SECONDS must be greater than zero")
    if shutdown_wait_seconds <= 0:
        raise RuntimeError("SHUTDOWN_WAIT_SECONDS must be greater than zero")
    if power_on_low_confirmations < 1:
        raise RuntimeError("POWER_ON_LOW_CONFIRMATIONS must be at least 1")
    if power_off_low_confirmations < 1:
        raise RuntimeError("POWER_OFF_LOW_CONFIRMATIONS must be at least 1")

    return Config(
        ha_url=values.get("HA_URL", "").rstrip("/"),
        ha_token=values.get("HA_TOKEN", ""),
        plug_entity=values.get("PLUG_ENTITY", ""),
        watt_entity=values.get("WATT_ENTITY", ""),
        rdp_host=values.get("RDP_HOST", ""),
        ssh_target=values.get("PC_SSH_TARGET", ""),
        target_os=values.get("TARGET_OS", "windows").strip().lower(),
        power_threshold_w=power_threshold_w,
        rdp_wait_seconds=rdp_wait_seconds,
        shutdown_wait_seconds=shutdown_wait_seconds,
        power_on_low_confirmations=power_on_low_confirmations,
        power_off_low_confirmations=power_off_low_confirmations,
    )

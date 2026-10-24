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
    "PLUG_OFF_SECONDS",
    "POWER_ON_LOW_CONFIRMATIONS",
    "POWER_OFF_LOW_CONFIRMATIONS",
]

DEFAULTS = {
    "TARGET_OS": "windows",
    "POWER_THRESHOLD_W": "5",
    "RDP_WAIT_SECONDS": "180",
    "SHUTDOWN_WAIT_SECONDS": "300",
    "PLUG_OFF_SECONDS": "10",
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
    plug_off_seconds: int
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
    return config_from_values(load_env())


def number(values: dict[str, str], key: str, kind: type[int] | type[float]) -> int | float:
    raw = (values.get(key) or DEFAULTS[key]).strip()
    try:
        return kind(raw)
    except ValueError as exc:
        raise RuntimeError(f"{key} must be a number") from exc


def config_from_values(values: dict[str, str]) -> Config:
    power_threshold_w = number(values, "POWER_THRESHOLD_W", float)
    rdp_wait_seconds = number(values, "RDP_WAIT_SECONDS", int)
    shutdown_wait_seconds = number(values, "SHUTDOWN_WAIT_SECONDS", int)
    plug_off_seconds = number(values, "PLUG_OFF_SECONDS", int)
    power_on_low_confirmations = number(values, "POWER_ON_LOW_CONFIRMATIONS", int)
    power_off_low_confirmations = number(values, "POWER_OFF_LOW_CONFIRMATIONS", int)

    if not math.isfinite(power_threshold_w) or power_threshold_w < 0:
        raise RuntimeError("POWER_THRESHOLD_W must be a finite non-negative number")
    if rdp_wait_seconds <= 0:
        raise RuntimeError("RDP_WAIT_SECONDS must be greater than zero")
    if shutdown_wait_seconds <= 0:
        raise RuntimeError("SHUTDOWN_WAIT_SECONDS must be greater than zero")
    if plug_off_seconds <= 0:
        raise RuntimeError("PLUG_OFF_SECONDS must be greater than zero")
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
        target_os=(values.get("TARGET_OS") or "windows").strip().lower(),
        power_threshold_w=power_threshold_w,
        rdp_wait_seconds=rdp_wait_seconds,
        shutdown_wait_seconds=shutdown_wait_seconds,
        plug_off_seconds=plug_off_seconds,
        power_on_low_confirmations=power_on_low_confirmations,
        power_off_low_confirmations=power_off_low_confirmations,
    )

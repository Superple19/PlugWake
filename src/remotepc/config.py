from __future__ import annotations

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
    "LINUX_BOOT_ID",
    "POWER_THRESHOLD_W",
    "RDP_WAIT_SECONDS",
    "POWER_ON_LOW_CONFIRMATIONS",
    "POWER_OFF_LOW_CONFIRMATIONS",
]

DEFAULTS = {
    "POWER_THRESHOLD_W": "5",
    "RDP_WAIT_SECONDS": "180",
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
    linux_boot_id: str
    power_threshold_w: float
    rdp_wait_seconds: int
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
    return Config(
        ha_url=values.get("HA_URL", "").rstrip("/"),
        ha_token=values.get("HA_TOKEN", ""),
        plug_entity=values.get("PLUG_ENTITY", ""),
        watt_entity=values.get("WATT_ENTITY", ""),
        rdp_host=values.get("RDP_HOST", ""),
        ssh_target=values.get("PC_SSH_TARGET", ""),
        linux_boot_id=values.get("LINUX_BOOT_ID", ""),
        power_threshold_w=float(values.get("POWER_THRESHOLD_W", "5")),
        rdp_wait_seconds=int(values.get("RDP_WAIT_SECONDS", "180")),
        power_on_low_confirmations=int(values.get("POWER_ON_LOW_CONFIRMATIONS", "3")),
        power_off_low_confirmations=int(values.get("POWER_OFF_LOW_CONFIRMATIONS", "4")),
    )

# RemotePC

Small Windows scripts for powering on a remote PC through Home Assistant and opening RDP over Tailscale.

## Setup

1. Copy `.env.example` to `.env`.
2. Set `HA_TOKEN` to a Home Assistant long-lived access token.
3. Run `power_on_pc.bat` or `power_off_pc.bat`.

`.env` is intentionally ignored by Git.

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Callable

import paramiko

from .config import Config

Log = Callable[[str], None]
PasswordPrompt = Callable[[str], str | None]


class HomeAssistant:
    def __init__(self, config: Config) -> None:
        self.config = config

    def request(self, path: str, method: str = "GET", body: dict[str, str] | None = None) -> dict:
        if not self.config.ha_token:
            raise RuntimeError("Home Assistant token is not configured")

        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.ha_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.config.ha_token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8") or "{}")

    def state(self, entity: str) -> str:
        return str(self.request(f"/api/states/{entity}")["state"])

    def watt(self) -> float:
        state = self.state(self.config.watt_entity)
        try:
            return float(state)
        except ValueError as exc:
            raise RuntimeError(f"Invalid power sensor state: {state}") from exc

    def set_plug(self, state: str) -> None:
        service = "turn_on" if state == "on" else "turn_off"
        self.request(f"/api/services/switch/{service}", method="POST", body={"entity_id": self.config.plug_entity})


class ActionFailed(RuntimeError):
    pass


def tcp_open(host: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def test_home_assistant(config: Config, log: Log) -> None:
    require_config(config, ["ha_url", "ha_token"])
    HomeAssistant(config).request("/api/")
    log("Home Assistant is reachable.")


def test_rdp_host(config: Config, log: Log) -> None:
    require_config(config, ["rdp_host"])
    if tcp_open(config.rdp_host, 3389, timeout=5):
        log(f"{config.rdp_host}:3389 is reachable.")
    else:
        log(f"{config.rdp_host}:3389 is not reachable within 5 seconds.")


def tailscale_connected() -> bool | None:
    if not shutil.which("tailscale"):
        return None
    result = subprocess.run(["tailscale", "status"], text=True, capture_output=True, encoding="utf-8", errors="replace")
    text = result.stdout + result.stderr
    if result.returncode != 0:
        return False
    return not any(marker in text for marker in ["Tailscale is stopped", "Logged out", "not connected"])


def rdp_is_open(host: str) -> bool:
    if not shutil.which("powershell"):
        return False
    command = (
        "Get-CimInstance Win32_Process -Filter \"name = 'mstsc.exe'\" "
        f"| Where-Object {{ $_.CommandLine -like '*{host}*' }}"
    )
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            command,
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return bool(result.stdout.strip())


def open_rdp(config: Config, log: Log) -> None:
    if rdp_is_open(config.rdp_host):
        log(f"RDP is already open for {config.rdp_host}.")
        return

    log(f"Waiting for {config.rdp_host} to come online.")
    deadline = time.monotonic() + config.rdp_wait_seconds
    attempt = 1
    while time.monotonic() < deadline:
        if tcp_open(config.rdp_host, 3389):
            command = rdp_command(config.rdp_host)
            if command is None:
                log("No supported RDP client was found. Install xfreerdp on Linux.")
                return
            log(f"{config.rdp_host} is online. Opening RDP.")
            subprocess.Popen(command)
            return
        log(f"{config.rdp_host} is not ready yet. Retrying in 5 seconds. Attempt {attempt}.")
        attempt += 1
        time.sleep(5)
    log(f"{config.rdp_host} did not come online within {config.rdp_wait_seconds} seconds")


def rdp_command(host: str) -> list[str] | None:
    if sys.platform == "win32":
        return ["mstsc.exe", f"/v:{host}", "/f"]

    if sys.platform.startswith("linux"):
        for command in ["xfreerdp", "xfreerdp3"]:
            if shutil.which(command):
                return [command, f"/v:{host}", "/f", "/network:auto"]
    return None


def remote_on(config: Config, log: Log) -> None:
    require_config(config, ["ha_url", "ha_token", "plug_entity", "watt_entity", "rdp_host"])

    tailscale = tailscale_connected()
    if tailscale is False:
        log("Tailscale is not connected.")
        return
    if tailscale is None:
        log("Tailscale CLI was not found. Skipping direct Tailscale check.")

    if not tcp_open(url_host(config.ha_url), url_port(config.ha_url)):
        log("Home Assistant is not reachable.")
        return

    ha = HomeAssistant(config)
    log(f"Reading plug state: {config.plug_entity}")
    plug = ha.state(config.plug_entity)
    log(f"Reading power sensor: {config.watt_entity}")
    watt = ha.watt()
    log(f"Plug={plug}, Power={watt:g} W")

    if plug == "off":
        log("Decision: plug is off, so turning it on.")
        ha.set_plug("on")
        open_rdp(config, log)
        return

    if watt >= config.power_threshold_w:
        log(f"Decision: power is at or above {config.power_threshold_w:g} W, so PC is already on.")
        open_rdp(config, log)
        return

    log(f"Decision: plug is on but power is below {config.power_threshold_w:g} W. Watching for sustained low power.")
    if tcp_open(config.rdp_host, 3389):
        log(f"{config.rdp_host} is online despite low power. Treating PC as already on.")
        open_rdp(config, log)
        return

    low_count = 1
    log(f"Low power confirmation {low_count}/{config.power_on_low_confirmations}.")
    while low_count < config.power_on_low_confirmations:
        time.sleep(5)
        watt = ha.watt()
        log(f"Power={watt:g} W")
        if watt < config.power_threshold_w:
            low_count += 1
            log(f"Low power confirmation {low_count}/{config.power_on_low_confirmations}.")
        else:
            log("Power recovered. PC is already on.")
            open_rdp(config, log)
            return

    log(f"Decision: power stayed below {config.power_threshold_w:g} W, so power cycling plug.")
    ha.set_plug("off")
    time.sleep(3)
    ha.set_plug("on")
    open_rdp(config, log)


def remote_off(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> None:
    require_config(config, ["ha_url", "ha_token", "plug_entity", "watt_entity", "ssh_target"])

    ha = HomeAssistant(config)
    log(f"Reading plug state: {config.plug_entity}")
    plug = ha.state(config.plug_entity)
    log(f"Reading power sensor: {config.watt_entity}")
    watt = ha.watt()
    log(f"Plug={plug}, Power={watt:g} W")

    if plug == "off":
        log("Decision: plug is already off.")
        return

    if watt >= config.power_threshold_w:
        log(f"Decision: PC appears to be running. Sending shutdown over SSH to {config.ssh_target}.")
        if not ssh_shutdown(config, log, password_prompt):
            raise ActionFailed("SSH shutdown failed")

        log(f"SSH shutdown sent. Waiting for power to drop below {config.power_threshold_w:g} W.")
        deadline = time.monotonic() + 300
        low_count = 0
        while time.monotonic() < deadline:
            time.sleep(5)
            watt = ha.watt()
            log(f"Power={watt:g} W")
            if watt < config.power_threshold_w:
                low_count += 1
                log(f"Low power confirmation {low_count}/{config.power_off_low_confirmations}.")
                if low_count >= config.power_off_low_confirmations:
                    log(f"Power stayed below {config.power_threshold_w:g} W.")
                    break
            else:
                low_count = 0

        if low_count < config.power_off_low_confirmations:
            log("Timed out waiting for shutdown. Not cutting power.")
            return

    log(f"Decision: power is below {config.power_threshold_w:g} W, so turning plug off.")
    ha.set_plug("off")


def url_host(url: str) -> str:
    return urllib.parse.urlparse(url).hostname or ""


def url_port(url: str) -> int:
    parsed = urllib.parse.urlparse(url)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def require_config(config: Config, names: list[str]) -> None:
    missing = [name.upper() for name in names if not str(getattr(config, name)).strip()]
    if missing:
        raise RuntimeError(f"Missing required settings: {', '.join(missing)}")


def parse_ssh_target(target: str) -> tuple[str, str]:
    if "@" not in target:
        return "", target
    username, host = target.split("@", 1)
    return username, host


def ssh_shutdown(config: Config, log: Log, password_prompt: PasswordPrompt | None) -> bool:
    result = run_ssh_command(config, shutdown_command(config), log, password_prompt)
    return result == 0


def shutdown_command(config: Config) -> str:
    if config.target_os == "windows":
        return "shutdown /s /t 0"
    if config.target_os == "linux":
        return "sudo -S -p '' systemctl poweroff"
    raise RuntimeError(f"Unsupported TARGET_OS: {config.target_os}")


def reboot_command(config: Config) -> str:
    if config.target_os == "windows":
        return "shutdown /r /t 0"
    if config.target_os == "linux":
        return "sudo -S -p '' systemctl reboot"
    raise RuntimeError(f"Unsupported TARGET_OS: {config.target_os}")


def run_ssh_command(config: Config, command: str, log: Log, password_prompt: PasswordPrompt | None) -> int | None:
    client, password = connect_ssh(config.ssh_target, log, password_prompt)
    if client is None:
        return None

    try:
        stdin, stdout, stderr = client.exec_command(command)
        if config.target_os == "linux":
            if password is None and password_prompt is not None:
                password = password_prompt(config.ssh_target)
            if password:
                stdin.write(password + "\n")
                stdin.flush()
            stdin.channel.shutdown_write()
        output = stdout.read().decode("utf-8", errors="replace").strip()
        error = stderr.read().decode("utf-8", errors="replace").strip()
        if output:
            log(output)
        if error:
            log(error)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


def connect_ssh(
    target: str, log: Log, password_prompt: PasswordPrompt | None
) -> tuple[paramiko.SSHClient | None, str | None]:
    username, host = parse_ssh_target(target)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    try:
        client.connect(hostname=host, username=username or None, timeout=10, auth_timeout=15)
    except (paramiko.AuthenticationException, paramiko.SSHException) as exc:
        if "No authentication methods available" not in str(exc) and not isinstance(
            exc, paramiko.AuthenticationException
        ):
            log(f"SSH connection failed: {exc}")
            return None, None

        if password_prompt is None:
            log("SSH authentication failed. Password prompt is unavailable for this command.")
            return None, None

        for attempt in range(1, 4):
            password = password_prompt(target)
            if not password:
                log("SSH password was not provided.")
                return None, None

            try:
                client.connect(
                    hostname=host,
                    username=username or None,
                    password=password,
                    timeout=10,
                    auth_timeout=15,
                    look_for_keys=False,
                    allow_agent=False,
                )
                break
            except paramiko.AuthenticationException:
                log(f"SSH password authentication failed. Attempt {attempt}/3.")
                if attempt == 3:
                    return None, None
            except Exception as exc:
                log(f"SSH password authentication failed: {exc}")
                return None, None
    except Exception as exc:
        log(f"SSH connection failed: {exc}")
        return None, None

    return client, locals().get("password")


def remote_reboot(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> None:
    require_config(config, ["ssh_target"])
    log(f"Rebooting remote PC over SSH: {config.ssh_target}")
    code = run_ssh_command(config, reboot_command(config), log, password_prompt)
    if code != 0:
        raise ActionFailed("Failed to reboot remote PC")


def remote_hard_reboot(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> None:
    log("Starting hard reboot.")
    remote_off(config, log, password_prompt)
    log("Turning plug back on.")
    HomeAssistant(config).set_plug("on")
    open_rdp(config, log)

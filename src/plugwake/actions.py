from __future__ import annotations

import json
import math
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

import paramiko

from .config import Config

Log = Callable[[str], None]
PasswordPrompt = Callable[[str], str | None]

SSH_NO_EXIT_STATUS = -1


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
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise ActionFailed("Home Assistant rejected the token (HTTP 401). Check HA_TOKEN") from None
            raise ActionFailed(f"Home Assistant request failed (HTTP {exc.code} {exc.reason})") from None
        except urllib.error.URLError as exc:
            raise ActionFailed(f"Home Assistant is not reachable ({exc.reason})") from None

    def state(self, entity: str) -> str:
        try:
            return str(self.request(f"/api/states/{entity}")["state"])
        except ActionFailed as exc:
            if "HTTP 404" in str(exc):
                raise ActionFailed(f"Home Assistant entity not found: {entity}") from None
            raise

    def watt(self) -> float:
        state = self.state(self.config.watt_entity)
        try:
            value = float(state)
        except ValueError as exc:
            raise RuntimeError(f"Invalid power sensor state: {state}") from exc
        if not math.isfinite(value) or value < 0:
            raise RuntimeError(f"Invalid power sensor state: {state}")
        return value

    def set_plug(self, state: str) -> None:
        service = "turn_on" if state == "on" else "turn_off"
        self.request(f"/api/services/switch/{service}", method="POST", body={"entity_id": self.config.plug_entity})


class ActionFailed(RuntimeError):
    pass


def require_plug_state(state: str) -> str:
    if state not in {"on", "off"}:
        raise ActionFailed(f"Invalid smart plug state: {state}")
    return state


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
    if not tcp_open(config.rdp_host, 3389, timeout=5):
        raise ActionFailed(f"RDP port 3389 on {config.rdp_host} is not reachable within 5 seconds")
    log(f"RDP port 3389 on {config.rdp_host} is reachable.")


def tailscale_connected() -> bool | None:
    if not shutil.which("tailscale"):
        return None
    result = subprocess.run(["tailscale", "status"], text=True, capture_output=True, encoding="utf-8", errors="replace")
    text = result.stdout + result.stderr
    if result.returncode != 0:
        return False
    return not any(marker in text for marker in ["Tailscale is stopped", "Logged out", "not connected"])


def rdp_is_open(host: str) -> bool:
    if sys.platform == "win32":
        if not shutil.which("powershell"):
            return False
        command = (
            "$hostName = [Environment]::GetEnvironmentVariable('PLUGWAKE_RDP_HOST'); "
            "Get-CimInstance Win32_Process -Filter \"name = 'mstsc.exe'\" "
            "| Where-Object { $_.CommandLine -like ('*' + $hostName + '*') }"
        )
        environment = os.environ.copy()
        environment["PLUGWAKE_RDP_HOST"] = host
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )
        return bool(result.stdout.strip())

    if sys.platform.startswith("linux") and shutil.which("pgrep"):
        for process in ["xfreerdp", "xfreerdp3"]:
            result = subprocess.run(
                ["pgrep", "-af", process],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            if any(host in line for line in result.stdout.splitlines()):
                return True
    return False


def open_rdp(config: Config, log: Log) -> None:
    if rdp_is_open(config.rdp_host):
        log(f"RDP is already open for {config.rdp_host}.")
        return

    log(f"Waiting for RDP on {config.rdp_host}. Checking every 5 seconds.")
    start = time.monotonic()
    while (elapsed := time.monotonic() - start) < config.rdp_wait_seconds:
        if tcp_open(config.rdp_host, 3389):
            command = rdp_command(config.rdp_host)
            if command is None:
                raise ActionFailed("No supported RDP client was found. Install FreeRDP on Linux")
            log(f"RDP on {config.rdp_host} is ready. Opening RDP.")
            subprocess.Popen(command)
            return
        log(f"RDP on {config.rdp_host} not ready ({elapsed:.0f}/{config.rdp_wait_seconds} s).")
        time.sleep(5)
    raise ActionFailed(f"RDP on {config.rdp_host} was not ready within {config.rdp_wait_seconds} seconds")


def rdp_command(host: str) -> list[str] | None:
    if sys.platform == "win32":
        return ["mstsc.exe", f"/v:{host}", "/f"]

    if sys.platform.startswith("linux"):
        for command in ["xfreerdp", "xfreerdp3"]:
            if shutil.which(command):
                return [command, f"/v:{host}", "/f", "/network:auto"]
    return None


def check_network(config: Config, log: Log, need_ha: bool = True) -> bool | None:
    tailscale = tailscale_connected()
    if tailscale is False:
        log("Warning: Tailscale is not connected. Continuing in case the network works without it.")
    if tailscale is None:
        log("Tailscale CLI was not found. Skipping Tailscale check.")

    if need_ha and not tcp_open(url_host(config.ha_url), url_port(config.ha_url)):
        if tailscale is False:
            raise ActionFailed("Home Assistant is not reachable. Tailscale is also not connected")
        raise ActionFailed("Home Assistant is not reachable")
    return tailscale


def ssh_failure(message: str, tailscale: bool | None) -> ActionFailed:
    if tailscale is False:
        return ActionFailed(f"{message}. Tailscale is also not connected")
    return ActionFailed(message)


def remote_on(config: Config, log: Log) -> None:
    require_config(config, ["ha_url", "ha_token", "plug_entity", "watt_entity", "rdp_host"])
    check_network(config, log)

    ha = HomeAssistant(config)
    log(f"Reading plug state: {config.plug_entity}")
    plug = require_plug_state(ha.state(config.plug_entity))
    log(f"Reading power sensor: {config.watt_entity}")
    watt = ha.watt()
    log(f"Plug {plug}, power {watt:g} W.")

    if plug == "off":
        log("Decision: plug is off, so turning it on.")
        turn_plug_on(ha, config, log)
        open_rdp(config, log)
        return

    if watt >= config.power_threshold_w:
        log(f"Decision: power is at or above {config.power_threshold_w:g} W, so PC is already on.")
        open_rdp(config, log)
        return

    log(
        f"Decision: plug is on but power is below {config.power_threshold_w:g} W. "
        "Checking for sustained low power every 5 seconds."
    )
    if tcp_open(config.rdp_host, 3389):
        log(f"{config.rdp_host} is online despite low power. Treating PC as already on.")
        open_rdp(config, log)
        return

    low_count = 1
    log(f"Power {watt:g} W, low ({low_count}/{config.power_on_low_confirmations}).")
    while low_count < config.power_on_low_confirmations:
        time.sleep(5)
        watt = ha.watt()
        if watt < config.power_threshold_w:
            low_count += 1
            log(f"Power {watt:g} W, low ({low_count}/{config.power_on_low_confirmations}).")
        else:
            log(f"Power {watt:g} W, recovered. PC is already on.")
            open_rdp(config, log)
            return

    log(f"Decision: power stayed below {config.power_threshold_w:g} W, so power-cycling the plug.")
    ha.set_plug("off")
    if not wait_for_plug_state(ha, config, "off", log):
        raise ActionFailed("Smart plug did not confirm the off state")
    wait_with_plug_off(config, log)
    turn_plug_on(ha, config, log)
    open_rdp(config, log)


def remote_off(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> bool:
    require_config(config, ["ha_url", "ha_token", "plug_entity", "watt_entity", "ssh_target"])
    tailscale = check_network(config, log)

    ha = HomeAssistant(config)
    log(f"Reading plug state: {config.plug_entity}")
    plug = require_plug_state(ha.state(config.plug_entity))
    log(f"Reading power sensor: {config.watt_entity}")
    watt = ha.watt()
    log(f"Plug {plug}, power {watt:g} W.")

    if plug == "off":
        log("Decision: plug is already off.")
        return True

    if watt >= config.power_threshold_w:
        log(f"Decision: PC appears to be running. Sending shutdown over SSH to {config.ssh_target}.")
        if not ssh_shutdown(config, log, password_prompt):
            raise ssh_failure("SSH shutdown failed", tailscale)

        log(
            f"SSH shutdown sent. Waiting for power to drop below {config.power_threshold_w:g} W. "
            "Checking every 5 seconds."
        )
        start = time.monotonic()
        low_count = 0
        while time.monotonic() - start < config.shutdown_wait_seconds:
            time.sleep(5)
            elapsed = time.monotonic() - start
            watt = ha.watt()
            if watt < config.power_threshold_w:
                low_count += 1
                log(f"Power {watt:g} W, low ({low_count}/{config.power_off_low_confirmations}).")
                if low_count >= config.power_off_low_confirmations:
                    break
            else:
                low_count = 0
                log(f"Power {watt:g} W, waiting for shutdown ({elapsed:.0f}/{config.shutdown_wait_seconds} s).")

        if low_count < config.power_off_low_confirmations:
            log("Timed out waiting for shutdown. Not cutting power.")
            return False
    else:
        low_count = 1
        log(f"Power {watt:g} W, low ({low_count}/{config.power_off_low_confirmations}).")
        while low_count < config.power_off_low_confirmations:
            time.sleep(5)
            watt = ha.watt()
            if watt < config.power_threshold_w:
                low_count += 1
                log(f"Power {watt:g} W, low ({low_count}/{config.power_off_low_confirmations}).")
            else:
                log(f"Power {watt:g} W, recovered. Not cutting power.")
                return False

    log(f"Decision: power is below {config.power_threshold_w:g} W, so turning plug off.")
    ha.set_plug("off")
    if not wait_for_plug_state(ha, config, "off", log):
        log("Smart plug did not confirm the off state. Not continuing.")
        return False
    return True


def wait_with_plug_off(config: Config, log: Log) -> None:
    log(f"Plug is off. Waiting {config.plug_off_seconds} seconds before turning it back on.")
    time.sleep(config.plug_off_seconds)


def turn_plug_on(ha: HomeAssistant, config: Config, log: Log) -> None:
    ha.set_plug("on")
    if not wait_for_plug_state(ha, config, "on", log):
        raise ActionFailed("Smart plug did not confirm the on state")


def wait_for_plug_state(ha: HomeAssistant, config: Config, expected: str, log: Log) -> bool:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if ha.state(config.plug_entity) == expected:
            return True
        time.sleep(1)
    log(f"Smart plug did not reach state {expected} within 15 seconds.")
    return False


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
    return run_power_command(config, shutdown_command(config), log, password_prompt)


def shutdown_command(config: Config) -> str:
    if config.target_os == "windows":
        return "shutdown /s /t 0"
    if config.target_os == "linux":
        return "systemctl poweroff"
    raise RuntimeError(f"Unsupported TARGET_OS: {config.target_os}")


def reboot_command(config: Config) -> str:
    if config.target_os == "windows":
        return "shutdown /r /t 0"
    if config.target_os == "linux":
        return "systemctl reboot"
    raise RuntimeError(f"Unsupported TARGET_OS: {config.target_os}")


def run_power_command(config: Config, command: str, log: Log, password_prompt: PasswordPrompt | None) -> bool:
    client, password = connect_ssh(config.ssh_target, log, password_prompt)
    if client is None:
        return False

    try:
        if config.target_os != "linux":
            return power_command_sent(exec_ssh(client, command, log), log)

        if password is None:
            code = exec_ssh(client, f"sudo -n {command}", log)
            if code in {0, SSH_NO_EXIT_STATUS}:
                return power_command_sent(code, log)
            if password_prompt is None:
                log("sudo requires a password, but password prompt is unavailable for this command.")
                return False
            log("sudo requires a password.")
            password = password_prompt(config.ssh_target)
            if not password:
                log("sudo password was not provided.")
                return False

        return power_command_sent(exec_ssh(client, f"sudo -S -p '' {command}", log, password), log)
    finally:
        client.close()


def power_command_sent(code: int, log: Log) -> bool:
    if code == SSH_NO_EXIT_STATUS:
        log("SSH connection closed before an exit status was returned. Assuming the command was sent.")
        return True
    return code == 0


def exec_ssh(client: paramiko.SSHClient, command: str, log: Log, stdin_text: str | None = None) -> int:
    stdin, stdout, stderr = client.exec_command(command)
    if stdin_text is not None:
        stdin.write(stdin_text + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    output = stdout.read().decode("utf-8", errors="replace").strip()
    error = stderr.read().decode("utf-8", errors="replace").strip()
    if output:
        log(output)
    if error:
        log(error)
    return stdout.channel.recv_exit_status()


def new_ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    return client


def connect_ssh(
    target: str, log: Log, password_prompt: PasswordPrompt | None
) -> tuple[paramiko.SSHClient | None, str | None]:
    username, host = parse_ssh_target(target)
    client = new_ssh_client()

    try:
        client.connect(hostname=host, username=username or None, timeout=10, auth_timeout=15)
        return client, None
    except (paramiko.AuthenticationException, paramiko.SSHException) as exc:
        client.close()
        if "No authentication methods available" not in str(exc) and not isinstance(
            exc, paramiko.AuthenticationException
        ):
            log(f"SSH connection failed: {exc}")
            return None, None
    except Exception as exc:
        client.close()
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

        client = new_ssh_client()
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
            return client, password
        except paramiko.AuthenticationException:
            client.close()
            log(f"SSH password authentication failed ({attempt}/3).")
        except Exception as exc:
            client.close()
            log(f"SSH password authentication failed: {exc}")
            return None, None
    return None, None


def remote_reboot(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> None:
    require_config(config, ["ssh_target"])
    tailscale = check_network(config, log, need_ha=False)
    log(f"Rebooting target PC over SSH: {config.ssh_target}")
    if not run_power_command(config, reboot_command(config), log, password_prompt):
        raise ssh_failure("Failed to reboot target PC", tailscale)


def remote_hard_reboot(config: Config, log: Log, password_prompt: PasswordPrompt | None = None) -> None:
    log("Starting hard reboot.")
    if not remote_off(config, log, password_prompt):
        raise ActionFailed("Shutdown was not confirmed")
    wait_with_plug_off(config, log)
    log("Turning plug back on.")
    turn_plug_on(HomeAssistant(config), config, log)
    open_rdp(config, log)

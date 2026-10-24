from __future__ import annotations

import re

import pytest

from plugwake import gui, i18n


def qml_strings() -> set[str]:
    strings: set[str] = set()
    for path in gui.QML_DIR.glob("*.qml"):
        for call in re.findall(r"\bt\(([^()]*)\)", path.read_text(encoding="utf-8")):
            for match in re.finditer(r'"([^"]*)"', call):
                # Skip values being compared, such as plug === "on".
                if not call[: match.start()].rstrip().endswith("==="):
                    strings.add(match.group(1))
    return strings


def python_strings() -> set[str]:
    strings = {"Ready", "Running {label}", "Cancelling {label}", "Saved.", "Not saved: {reason}"}
    strings |= {f"{{label}} {outcome}" for outcome in ("completed", "failed", "cancelled")}
    strings.add("Example defaults filled in. Save to apply.")
    for label, _action, _password, confirm in gui.ACTIONS.values():
        strings.add(label)
        if confirm:
            strings.add(confirm)
    for title, _keys, _test in gui.SETTING_GROUPS:
        strings.add(title)
    for label, description, _kind in gui.SETTINGS.values():
        strings |= {label, description}
    return strings


def test_every_qml_string_has_a_korean_translation() -> None:
    strings = qml_strings()

    assert "Remote On" in strings
    assert sorted(strings - set(i18n.KO)) == []


def test_every_backend_string_has_a_korean_translation() -> None:
    assert sorted(python_strings() - set(i18n.KO)) == []


def test_korean_keeps_placeholders() -> None:
    for english, korean in i18n.KO.items():
        assert re.findall(r"\{\w+\}|%\d", english) == re.findall(r"\{\w+\}|%\d", korean), english


def test_backend_translates_status_and_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_config() -> None:
        raise RuntimeError("RDP_WAIT_SECONDS must be greater than zero")

    monkeypatch.setattr(gui, "load_config", broken_config)
    backend = gui.Backend(language="ko")

    assert backend.status == "준비됨"
    backend.run("on")
    assert backend.status == "원격 켜기 실패"
    assert backend.settingGroups[1]["title"] == "대상 PC"

    backend.setLanguage("en")

    assert backend.status == "Remote On failed"
    assert backend.settingGroups[1]["title"] == "Target PC"
    assert backend.strings == {}


def test_system_language_resolves_to_a_supported_language() -> None:
    assert i18n.resolve("system") in {"en", "ko"}
    assert i18n.resolve("ko") == "ko"

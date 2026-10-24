from __future__ import annotations

from PySide6.QtCore import QLocale

LANGUAGE_CHOICES = ["system", "en", "ko"]

# English source text -> Korean. Keys must match the English text in gui.py and the QML t() calls exactly.
KO: dict[str, str] = {
    # Navigation and Home
    "Home": "홈",
    "Settings": "설정",
    "Smart plug": "스마트 플러그",
    "Remote desktop": "원격 데스크톱",
    "On": "켜짐",
    "On (%1 W)": "켜짐 (%1 W)",
    "On (%1 W · PC off)": "켜짐 (%1 W · PC 꺼짐)",
    "Off": "꺼짐",
    "Unknown": "알 수 없음",
    "Ready": "준비됨",
    "Not reachable": "연결 안 됨",
    "Updated %1": "%1 업데이트",
    "Checking...": "확인 중...",
    "Refresh": "새로 고침",
    "Cancel": "취소",
    "Cancelling...": "취소 중...",
    "Power controls": "전원 제어",
    "Log": "로그",
    "Clear": "지우기",
    # Actions
    "Remote On": "원격 켜기",
    "Remote Off": "원격 끄기",
    "Soft Reboot": "소프트 재부팅",
    "Hard Reboot": "하드 재부팅",
    "Test Home Assistant": "Home Assistant 테스트",
    "Test RDP Port": "RDP 포트 테스트",
    "Shut down the target PC and turn the smart plug off?": "대상 PC를 종료하고 스마트 플러그를 끌까요?",
    "Reboot the target PC over SSH?": "SSH로 대상 PC를 재부팅할까요?",
    "Shut down the target PC, cut plug power, turn it back on, and open RDP?": (
        "대상 PC를 종료하고, 플러그 전원을 끊었다가 다시 켠 뒤 RDP를 열까요?"
    ),
    # Status
    "Running {label}": "{label} 실행 중",
    "{label} completed": "{label} 완료",
    "{label} failed": "{label} 실패",
    "{label} cancelled": "{label} 취소됨",
    "Cancelling {label}": "{label} 취소 중",
    # Dialogs
    "Yes": "예",
    "No": "아니요",
    "OK": "확인",
    "Password": "비밀번호",
    "Password for %1": "%1 비밀번호",
    "Reset to defaults": "기본값으로 재설정",
    "Reset settings fields to example defaults? This will not save .env yet.": (
        "설정 칸을 예시 기본값으로 바꿀까요? 아직 .env에 저장하지는 않습니다."
    ),
    # Settings page
    "Unsaved changes": "저장하지 않은 변경 사항",
    "Reload": "다시 불러오기",
    "Save": "저장",
    "Saved.": "저장했습니다.",
    "Not saved: {reason}": "저장하지 않았습니다: {reason}",
    "Example defaults filled in. Save to apply.": "예시 기본값을 채웠습니다. 저장해야 적용됩니다.",
    "Uses the values above, even before saving.": "저장하기 전에도 위에 입력한 값으로 테스트합니다.",
    "Testing...": "테스트 중...",
    "App": "앱",
    "Language": "언어",
    "Applies right away. Logs stay in English.": "바로 적용됩니다. 로그는 영어로 표시됩니다.",
    "Use system language": "시스템 언어 사용",
    "Status refresh": "상태 새로 고침",
    "How often Home checks the plug and RDP. Refresh still works when this is off.": (
        "홈 화면이 플러그와 RDP를 확인하는 주기입니다. 꺼도 새로 고침 버튼은 쓸 수 있습니다."
    ),
    "Every %1 s": "%1초마다",
    # Setting groups
    "Home Assistant": "Home Assistant",
    "Target PC": "대상 PC",
    "Power Safety": "전원 안전",
    # Setting labels and descriptions
    "Home Assistant URL": "Home Assistant 주소",
    "Base address, for example http://ha.example.local:8123.": "기본 주소입니다. 예: http://ha.example.local:8123",
    "Access token": "액세스 토큰",
    "Long-lived access token from your Home Assistant profile.": (
        "Home Assistant 프로필에서 만든 장기 액세스 토큰입니다."
    ),
    "Smart plug entity": "스마트 플러그 엔티티",
    "Switch entity that powers the target PC.": "대상 PC에 전원을 공급하는 스위치 엔티티입니다.",
    "Power sensor entity": "전력 센서 엔티티",
    "Sensor that reports the plug's power draw in watts.": "플러그의 소비 전력을 W 단위로 알려 주는 센서입니다.",
    "RDP host": "RDP 호스트",
    "Host name or address of the target PC for Remote Desktop.": (
        "원격 데스크톱으로 접속할 대상 PC의 호스트 이름 또는 주소입니다."
    ),
    "SSH target": "SSH 대상",
    "user@host used to shut down or reboot the target PC.": "대상 PC를 종료하거나 재부팅할 때 쓰는 user@host입니다.",
    "Target OS": "대상 OS",
    "Operating system on the target PC.": "대상 PC의 운영체제입니다.",
    "Running threshold (W)": "켜짐 판단 기준 (W)",
    "Power at or above this value means the PC is running.": "전력이 이 값 이상이면 PC가 켜져 있다고 판단합니다.",
    "RDP wait (s)": "RDP 대기 시간 (초)",
    "How long Remote On waits for RDP to answer.": "원격 켜기가 RDP 응답을 기다리는 시간입니다.",
    "Shutdown wait (s)": "종료 대기 시간 (초)",
    "How long Remote Off waits for power to drop. Plug power is not cut on timeout.": (
        "원격 끄기가 전력이 떨어지기를 기다리는 시간입니다. 시간이 지나면 플러그 전원을 끊지 않습니다."
    ),
    "Plug off time (s)": "플러그 꺼짐 시간 (초)",
    "How long the plug stays off during a power cycle.": "전원을 껐다 켤 때 플러그를 꺼 두는 시간입니다.",
    "Remote On low readings": "원격 켜기 저전력 확인 횟수",
    "Low readings in a row before Remote On power-cycles an on plug.": (
        "원격 켜기가 켜진 플러그를 껐다 켜기 전에 연속으로 확인할 저전력 횟수입니다."
    ),
    "Remote Off low readings": "원격 끄기 저전력 확인 횟수",
    "Low readings in a row before Remote Off cuts plug power.": (
        "원격 끄기가 플러그 전원을 끊기 전에 연속으로 확인할 저전력 횟수입니다."
    ),
}

TRANSLATIONS = {"en": {}, "ko": KO}


def resolve(choice: str) -> str:
    if choice in TRANSLATIONS:
        return choice
    return "ko" if QLocale.system().language() == QLocale.Language.Korean else "en"


def translate(language: str, text: str, **values: str) -> str:
    return TRANSLATIONS.get(language, {}).get(text, text).format(**values)

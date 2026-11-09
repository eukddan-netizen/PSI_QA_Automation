"""
화면보호기 설정 관련 Windows 레지스트리 제어 및 검증 핸들러
"""

import winreg
from typing import Dict, Any, Tuple


class ScreenSaverHandler:
    REG_PATH = r"Control Panel\Desktop"

    @classmethod
    def _open_key(cls, write: bool = False):
        access = winreg.KEY_READ | (winreg.KEY_WRITE if write else 0)
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, access)

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """
        현재 화면보호기 설정값을 읽어 반환합니다.
        - active: 활성화 여부 (bool)
        - timeout_seconds: 대기 시간 (초)
        - timeout_minutes: 대기 시간 (분)
        - is_secure: 다시 시작할 때 로그온 화면 표시 (bool)
        """
        with cls._open_key(write=False) as key:
            def read_val(name: str, default: str = "") -> str:
                try:
                    val, _ = winreg.QueryValueEx(key, name)
                    return str(val)
                except FileNotFoundError:
                    return default

            active = read_val("ScreenSaveActive", "0") == "1"
            timeout_str = read_val("ScreenSaveTimeOut", "0")
            timeout_sec = int(timeout_str) if timeout_str.isdigit() else 0
            is_secure = read_val("ScreenSaverIsSecure", "0") == "1"

            return {
                "active": active,
                "timeout_seconds": timeout_sec,
                "timeout_minutes": round(timeout_sec / 60, 2),
                "is_secure": is_secure,
            }

    @classmethod
    def is_secure(cls, max_timeout_minutes: int = 10) -> Tuple[bool, str]:
        """
        현재 설정이 보안점검 기준상 '안전'인지 판별합니다.
        기준:
        1. 화면보호기 활성화 (ScreenSaveActive == "1")
        2. 대기 시간 10분 이하 (ScreenSaveTimeOut <= 600초)
        3. 다시 시작할 때 로그온 화면 표시 체크 (ScreenSaverIsSecure == "1")
        """
        settings = cls.get_settings()

        if not settings["active"]:
            return False, "화면보호기가 비활성화 상태입니다."
        if settings["timeout_seconds"] > (max_timeout_minutes * 60) or settings["timeout_seconds"] <= 0:
            return False, f"대기 시간이 {settings['timeout_minutes']}분으로 {max_timeout_minutes}분 이하 기준을 초과했습니다."
        if not settings["is_secure"]:
            return False, "다시 시작할 때 로그온 화면 표시(화면 잠금)가 해제되어 있습니다."

        return True, "안전 (대기 10분 이하 및 로그온 화면 표시 활성화)"

    @classmethod
    def set_secure(cls, timeout_minutes: int = 10):
        """
        화면보호기를 '안전' 상태로 설정합니다.
        (활성화=True, 대기시간=10분(600초), 잠금=True)
        """
        timeout_sec = str(timeout_minutes * 60)
        with cls._open_key(write=True) as key:
            winreg.SetValueEx(key, "ScreenSaveActive", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(key, "ScreenSaveTimeOut", 0, winreg.REG_SZ, timeout_sec)
            winreg.SetValueEx(key, "ScreenSaverIsSecure", 0, winreg.REG_SZ, "1")

    @classmethod
    def set_vulnerable(cls, timeout_minutes: int = 15, lock_on_resume: bool = False):
        """
        화면보호기를 '취약' 상태로 임의 조작합니다. (테스트 주입용)
        예: 대기시간 15분 초과 또는 로그온 화면 표시 해제
        """
        timeout_sec = str(timeout_minutes * 60)
        is_secure_val = "1" if lock_on_resume else "0"
        with cls._open_key(write=True) as key:
            winreg.SetValueEx(key, "ScreenSaveActive", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(key, "ScreenSaveTimeOut", 0, winreg.REG_SZ, timeout_sec)
            winreg.SetValueEx(key, "ScreenSaverIsSecure", 0, winreg.REG_SZ, is_secure_val)

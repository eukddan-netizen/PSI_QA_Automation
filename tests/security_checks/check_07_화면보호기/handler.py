"""
7. 화면 보호기 설정 여부 점검 전용 OS 핸들러
- 대상 레지스트리: HKCU\\Control Panel\\Desktop
  * ScreenSaveActive ("1": 활성, "0": 비활성)
  * ScreenSaveTimeOut (초 단위 문자열, 600초 이하 안전 / 600초 초과 취약)
  * ScreenSaverIsSecure ("1": 다시 시작할 때 로그온 화면 표시 체크, "0": 해제)
"""

import ctypes
import winreg
from typing import Dict, Optional, Tuple
from common.os_utils import StateGuard, read_reg_value

REG_SUBKEY = r"Control Panel\Desktop"
SPI_SETSCREENSAVETIMEOUT = 0x000F
SPI_SETSCREENSAVEACTIVE = 0x0011
SPIF_SENDCHANGE = 0x0002


def _notify_win_ini_change(timeout_sec: int, active: int = 1) -> None:
    user32 = ctypes.windll.user32
    user32.SystemParametersInfoW(SPI_SETSCREENSAVEACTIVE, active, None, SPIF_SENDCHANGE)
    user32.SystemParametersInfoW(SPI_SETSCREENSAVETIMEOUT, timeout_sec, None, SPIF_SENDCHANGE)


def get_settings() -> Dict[str, Optional[str]]:
    """현재 화면보호기 레지스트리 설정 조회"""
    result: Dict[str, Optional[str]] = {}
    for name in ("ScreenSaveActive", "ScreenSaveTimeOut", "ScreenSaverIsSecure", "SCRNSAVE.EXE"):
        existed, val, _ = read_reg_value("HKCU", REG_SUBKEY, name)
        result[name] = str(val) if existed and val is not None else None
    return result


def set_vulnerable(
    guard: StateGuard, timeout_minutes: int = 15, lock_on_resume: bool = False
) -> None:
    """원래 레지스트리 값을 백업(StateGuard)한 뒤 지정된 화면보호기 상태로 변경합니다."""
    timeout_sec = timeout_minutes * 60
    secure_val = "1" if lock_on_resume else "0"

    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaveActive", "1", winreg.REG_SZ)
    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaveTimeOut", str(timeout_sec), winreg.REG_SZ)
    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaverIsSecure", secure_val, winreg.REG_SZ)

    existed, scr_val, _ = read_reg_value("HKCU", REG_SUBKEY, "SCRNSAVE.EXE")
    if not existed or not scr_val:
        guard.set_reg("HKCU", REG_SUBKEY, "SCRNSAVE.EXE", r"C:\Windows\system32\scrnsave.scr", winreg.REG_SZ)

    _notify_win_ini_change(timeout_sec, 1)


# --- 시나리오별 직관적인 단축 헬퍼 함수 ---

def set_timeout_vulnerable(guard: StateGuard, minutes: int = 15) -> None:
    """[시나리오 02] 대기 시간만 초과(기본 15분), 잠금 화면은 정상 체크('1') 주입"""
    set_vulnerable(guard, timeout_minutes=minutes, lock_on_resume=True)


def set_lock_vulnerable(guard: StateGuard) -> None:
    """[시나리오 03] 대기 시간은 10분 정상, 다시 시작할 때 로그온 화면 표시만 해제('0') 주입"""
    set_vulnerable(guard, timeout_minutes=10, lock_on_resume=False)


def set_both_vulnerable(guard: StateGuard) -> None:
    """[시나리오 04] 대기 시간 초과(15분) + 로그온 화면 표시 해제('0') 동시 취약 주입"""
    set_vulnerable(guard, timeout_minutes=15, lock_on_resume=False)


def set_secure(guard: StateGuard, timeout_minutes: int = 10) -> None:
    """원래 레지스트리 값을 백업한 뒤 화면보호기를 안전 상태(10분 이하, 로그온 화면 표시 체크)로 변경합니다."""
    timeout_sec = timeout_minutes * 60
    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaveActive", "1", winreg.REG_SZ)
    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaveTimeOut", str(timeout_sec), winreg.REG_SZ)
    guard.set_reg("HKCU", REG_SUBKEY, "ScreenSaverIsSecure", "1", winreg.REG_SZ)
    _notify_win_ini_change(timeout_sec, 1)


def is_secure() -> Tuple[bool, str]:
    """현재 화면보호기 설정이 보안 기준(활성화 + 대기시간 10분 이하 + 로그온 화면 표시 체크)을 충족하는지 판정"""
    s = get_settings()
    active = s.get("ScreenSaveActive") == "1"
    secure = s.get("ScreenSaverIsSecure") == "1"
    try:
        timeout = int(s.get("ScreenSaveTimeOut") or 9999)
    except ValueError:
        timeout = 9999

    if active and secure and timeout <= 600:
        return True, f"안전 (대기시간: {timeout // 60}분, 로그온 화면 표시: 설정됨)"
    return (
        False,
        f"취약 (활성: {active}, 대기시간: {timeout // 60}분, 로그온 화면 표시: {secure})",
    )

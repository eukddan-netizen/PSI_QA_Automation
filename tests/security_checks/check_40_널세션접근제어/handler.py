"""
40. 비인가된 사용자의 널(Null) 세션 접근 제어 설정 여부 점검 전용 OS 핸들러
- 대상 레지스트리: HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa
  * restrictanonymous (REG_DWORD): 0이면 취약(익명 열거 허용), 0 이외의 값(1 등)이면 안전(익명 열거 허용 안 함)
"""

import winreg
from typing import Optional, Tuple
from common.os_utils import StateGuard, read_reg_value

REG_SUBKEY = r"SYSTEM\CurrentControlSet\Control\Lsa"
VALUE_NAME = "restrictanonymous"


def get_restrict_anonymous() -> Optional[int]:
    """현재 restrictanonymous 레지스트리 값 조회"""
    existed, val, _ = read_reg_value("HKLM", REG_SUBKEY, VALUE_NAME)
    if not existed or val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def set_vulnerable(guard: StateGuard) -> None:
    """
    원래 레지스트리 값을 백업(StateGuard)한 뒤
    HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa 의 restrictanonymous 값을 0(취약)으로 변경합니다.
    """
    guard.set_reg("HKLM", REG_SUBKEY, VALUE_NAME, 0, winreg.REG_DWORD)


def set_secure(guard: StateGuard) -> None:
    """
    원래 레지스트리 값을 백업한 뒤
    HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa 의 restrictanonymous 값을 1(안전)로 변경합니다.
    """
    guard.set_reg("HKLM", REG_SUBKEY, VALUE_NAME, 1, winreg.REG_DWORD)


def is_secure() -> Tuple[bool, str]:
    """
    현재 restrictanonymous 값이 0 이외의 값(1 이상)으로 설정되어 있는지 검증합니다.
    """
    val = get_restrict_anonymous()
    if val is not None and val != 0:
        return True, f"안전 (restrictanonymous={val}, 익명 열거 허용 안 함)"
    return False, f"취약 (restrictanonymous={val}, 익명 열거 제한 비활성화)"


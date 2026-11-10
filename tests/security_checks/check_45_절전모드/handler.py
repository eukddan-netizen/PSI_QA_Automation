"""
45. 절전 모드 정책 설정 여부 점검 전용 OS 핸들러
- 제어 명령: powercfg /change standby-timeout-ac <분>
- 검증 레지스트리:
  HKLM\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes\\
  381b4222-f694-41f0-9685-ff5bb260df2e\\238c9fa8-0aad-41ed-83f4-97be242c8f20\\29f6c1db-86da-48c5-9fdb-f2b67b1f44da
  * ACSettingIndex (REG_DWORD, 초 단위): 0이면 취약('사용 안 함'), 1800(30분) 등 0 이외의 설정값이면 안전
"""

from typing import Optional, Tuple
from common.os_utils import StateGuard, read_reg_value, run_cmd

REG_SUBKEY = (
    r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes"
    r"\381b4222-f694-41f0-9685-ff5bb260df2e"
    r"\238c9fa8-0aad-41ed-83f4-97be242c8f20"
    r"\29f6c1db-86da-48c5-9fdb-f2b67b1f44da"
)
VALUE_NAME = "ACSettingIndex"


def get_ac_standby_seconds() -> Optional[int]:
    """현재 전원 연결 시 절전 모드 전환 시간(초, ACSettingIndex) 조회"""
    existed, val, _ = read_reg_value("HKLM", REG_SUBKEY, VALUE_NAME)
    if not existed or val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _set_standby_minutes(minutes: int) -> None:
    run_cmd(["powercfg", "/change", "standby-timeout-ac", str(minutes)], check=True)


def set_vulnerable(guard: StateGuard) -> None:
    """
    원래 ACSettingIndex(초) 값을 백업한 뒤,
    `powercfg /change standby-timeout-ac 0` 명령으로 절전 모드를 '사용 안 함(0초, 취약)'으로 변경합니다.
    """
    orig_sec = get_ac_standby_seconds()
    orig_min = (orig_sec // 60) if (orig_sec is not None and orig_sec > 0) else 30

    _set_standby_minutes(0)

    guard.add_restore(
        f"절전 모드(AC) 대기시간 원복 ({orig_min}분 / {orig_min * 60}초)",
        lambda: _set_standby_minutes(orig_min),
    )


def set_secure(guard: StateGuard, minutes: int = 30) -> None:
    """절전 모드(AC) 대기시간을 30분(1800초, 안전)으로 설정합니다."""
    orig_sec = get_ac_standby_seconds()
    orig_min = (orig_sec // 60) if (orig_sec is not None) else 30

    _set_standby_minutes(minutes)

    guard.add_restore(
        f"절전 모드(AC) 대기시간 원복 ({orig_min}분)",
        lambda: _set_standby_minutes(orig_min),
    )


def is_secure() -> Tuple[bool, str]:
    """
    현재 절전 모드 ACSettingIndex가 0보다 큰 값(조치 시 1800초=30분)으로 설정되어 있는지 검증합니다.
    """
    sec = get_ac_standby_seconds()
    if sec is not None and sec > 0:
        return True, f"안전 (ACSettingIndex={sec}초 / {sec // 60}분 후 절전 모드 전환)"
    return False, f"취약 (ACSettingIndex={sec}초, 절전 모드 전환 안 함)"


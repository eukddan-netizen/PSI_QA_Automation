"""
31. Guest 계정 사용 여부 점검 전용 OS 핸들러
- 제어 명령: net user Guest /active:yes (취약) / net user Guest /active:no (안전)
- 조회 명령: net user Guest 출력에서 '계정 활성(Account active)' 값 확인
"""

from typing import Tuple
from common.os_utils import StateGuard, is_local_user_active

TARGET_USER = "Guest"


def set_vulnerable(guard: StateGuard) -> None:
    """
    원래 Guest 계정 활성 상태를 백업(StateGuard)한 뒤
    `net user Guest /active:yes` 명령으로 Guest 계정을 활성화(취약)합니다.
    """
    guard.set_user_active(TARGET_USER, True)


def set_secure(guard: StateGuard) -> None:
    """
    원래 Guest 계정 활성 상태를 백업한 뒤
    `net user Guest /active:no` 명령으로 Guest 계정을 비활성화(안전)합니다.
    """
    guard.set_user_active(TARGET_USER, False)


def is_secure() -> Tuple[bool, str]:
    """
    현재 Guest 계정이 비활성화(active == False)되어 있는지 검증합니다.
    """
    active = is_local_user_active(TARGET_USER)
    if active is False:
        return True, "안전 (Guest 계정 활성 상태: 아니요/No)"
    if active is True:
        return False, "취약 (Guest 계정 활성 상태: 예/Yes)"
    return False, "점검불가 (Guest 계정 상태를 조회할 수 없음)"


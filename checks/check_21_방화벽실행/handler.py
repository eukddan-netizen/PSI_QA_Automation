"""
21. 방화벽 실행 여부 점검 전용 OS 핸들러 (뼈대)
- 구현 시 StateGuard를 사용하여 변경 전 원래 OS 설정값을 백업하고,
  테스트 실패/종료 시에도 원래 값으로 복구되도록 작성합니다.
"""

from typing import Tuple
from common.os_utils import StateGuard


def set_vulnerable(guard: StateGuard) -> None:
    """원래 설정값을 백업(guard)한 뒤 테스트할 취약 상태를 주입합니다."""
    raise NotImplementedError("21번 점검(방화벽실행) 취약 상태 주입 로직 구현 필요")


def set_secure(guard: StateGuard) -> None:
    """원래 설정값을 백업(guard)한 뒤 양호(안전) 상태를 주입합니다."""
    raise NotImplementedError("21번 점검(방화벽실행) 안전 상태 주입 로직 구현 필요")


def is_secure() -> Tuple[bool, str]:
    """현재 실제 OS 설정이 안전 상태인지 (안전여부 bool, 상세설명 str)을 반환합니다."""
    raise NotImplementedError("21번 점검(방화벽실행) OS 상태 검증 로직 구현 필요")

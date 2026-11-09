"""
pytest 공통 설정 및 fixture 정의
- state_guard: 각 점검 테스트가 변경한 레지스트리/계정/OS 설정을 테스트 종료 시(실패 포함) 원래 값으로 자동 복구
"""

import sys
from pathlib import Path
import pytest

ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.os_utils import StateGuard


@pytest.fixture(scope="function")
def state_guard():
    """
    점검 테스트 실행 전 OS 상태를 백업하고,
    테스트가 실패하거나 중단되어도 Teardown에서 반드시 원래 값으로 복구합니다.
    """
    guard = StateGuard()
    try:
        yield guard
    finally:
        errors = guard.restore_all()
        if errors:
            pytest.fail("OS 설정 원복 중 오류가 발생했습니다:\n" + "\n".join(errors))

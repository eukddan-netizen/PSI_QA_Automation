"""
[대분류: 보안점검 메인 탭] 공통 Fixture
- app_ctrl: 보안점검 프로그램(taKeeper.exe) 제어기
"""

import pytest
from core.app_controller import AppController


@pytest.fixture(scope="function")
def app_ctrl():
    """보안점검 프로그램 AppController Fixture"""
    ctrl = AppController()
    yield ctrl
    try:
        ctrl.close()
    except Exception:
        pass


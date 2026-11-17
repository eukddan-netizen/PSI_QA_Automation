"""
[app_checks] 공통 Fixture
- app_ctrl: 보안점검 프로그램(taKeeper.exe) 제어기
"""

import pytest

from core.app_controller import AppController, stop_delayed_rescan_watcher


@pytest.fixture(scope="session", autouse=True)
def delayed_tray_popup_cleanup():
    """세션 종료 시 지연된 트레이 재검사 팝업 감시 스레드를 정리합니다."""
    yield
    stop_delayed_rescan_watcher()


@pytest.fixture(scope="function")
def app_ctrl():
    """보안점검 프로그램 AppController Fixture"""
    ctrl = AppController()
    yield ctrl
    try:
        ctrl.close()
    except Exception:
        pass


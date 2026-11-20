"""
[app_checks] 공통 Fixture
- app_ctrl: 보안점검 프로그램(taKeeper.exe) 제어기
- test/module 종료 시 잔여 컨텍스트 메뉴·자동화 크롬·UI 애니메이션이 완전히 정리된 뒤
  다음 테스트가 시작되도록 직렬 안정화(settle) 배리어를 보장합니다.
"""

import ctypes
import time
import pytest
import win32con
import win32gui

from core.app_controller import AppController, stop_delayed_rescan_watcher
from core.desktop_utils import _get_debug_chrome_pids, _stop_debug_chrome


def _dismiss_stray_context_menu() -> None:
    """이전 테스트에서 열려 남은 Win32 컨텍스트 메뉴(#32768)가 있으면 ESC로 안전하게 닫습니다."""
    try:
        menu_hwnd = win32gui.FindWindow("#32768", None)
        if menu_hwnd and win32gui.IsWindowVisible(menu_hwnd):
            user32 = ctypes.windll.user32
            user32.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
            user32.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.2)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def delayed_tray_popup_cleanup():
    """세션 종료 시 지연된 트레이 재검사 팝업 감시 스레드를 정리합니다."""
    yield
    stop_delayed_rescan_watcher()


@pytest.fixture(scope="module", autouse=True)
def _ensure_module_clean_transition():
    """
    모듈 종료 시(모든 모듈 픽스처 Teardown 이후) 잔여 자동화 크롬(port 9222) 및
    컨텍스트 메뉴가 완전히 정리될 때까지 대기한 뒤 다음 테스트 모듈로 진입합니다.
    """
    yield
    _dismiss_stray_context_menu()
    try:
        if _get_debug_chrome_pids(9222):
            _stop_debug_chrome(9222, graceful=True)
    except Exception:
        pass
    time.sleep(0.8)


@pytest.fixture(scope="function", autouse=True)
def _ensure_test_settle():
    """개별 테스트 종료 후 잔여 컨텍스트 메뉴 정리 및 UI 포커스 안정화 대기"""
    yield
    _dismiss_stray_context_menu()
    time.sleep(0.35)


@pytest.fixture(scope="function")
def app_ctrl():
    """보안점검 프로그램 AppController Fixture"""
    ctrl = AppController()
    yield ctrl
    try:
        ctrl.close()
    except Exception:
        pass


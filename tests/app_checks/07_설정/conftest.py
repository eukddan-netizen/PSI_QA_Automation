"""
[대분류: 설정 탭] 공통 Fixture
- settings_session: 07_설정 모듈/패키지 전체에서 보안점검 프로그램(taKeeper.exe) 실행을 공유하여
  불필요한 프로그램 재실행 최소화 (최초 실행 시 다크 모드 초기 화면 RGB 스냅샷도 함께 보존)
"""

import pytest

from core.app_controller import AppController
from pages.client.settings_page import SettingsPage


@pytest.fixture(scope="package")
def settings_session():
    """설정 탭 테스트 전체가 공유하는 보안점검 프로그램 세션 Fixture"""
    ctrl = AppController()
    ctrl.launch(timeout=20)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    settings_page = SettingsPage(ctrl.hwnd)
    launch_rgb = settings_page.get_region_rgb_average("window_center")
    settings_page.wait_for_main_ready(timeout=15.0)
    initial_dark_snap = settings_page.get_theme_visual_snapshot()

    session = {
        "ctrl": ctrl,
        "settings_page": settings_page,
        "launch_rgb": launch_rgb,
        "initial_dark_snap": initial_dark_snap,
    }

    try:
        yield session
    finally:
        print("\n>>> [07_설정 Teardown] 보안점검 프로그램 종료")
        try:
            session["ctrl"].close()
        except Exception:
            pass

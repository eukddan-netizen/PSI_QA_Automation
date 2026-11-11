"""
[대분류: 트레이 아이콘] 공통 Fixture
- admin_page: 사용자 모니터에 크롬 새 창을 띄워 PSI 관리자 콘솔(/pcsafe, t1 부서)을 제어합니다.
- app_ctrl: 보안점검 프로그램(taKeeper.exe) 및 인사 UI(TA 공지) 제어기 (종료 시 인사 UI 우선 닫기 적용)
"""

import time
import pytest
from playwright.sync_api import sync_playwright

from core.app_controller import AppController
from core.desktop_utils import launch_visible_chrome
from pages.admin_patch_page import AdminPatchPage
from pages.admin_pcsafe_page import AdminPcsafePage


@pytest.fixture(scope="module")
def admin_page():
    """
    Playwright 기반 PSI 웹 관리자 콘솔 제어 Fixture
    - 사용자의 실제 모니터 세션에 크롬 새 창을 띄우고 Playwright CDP로 제어합니다.
    - /pcsafe 페이지 이동 후 't1' 부서 선택
    - 모듈 테스트 종료 후 KYC 사용자의 인사 UI 출력을 'OFF'로 안전 원복
    """
    proc = launch_visible_chrome(port=9222)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        admin = AdminPcsafePage(page)
        admin.login(username="admin", password="Qwe123!@#")
        time.sleep(1)
        admin.goto_pcsafe()
        time.sleep(1)
        admin.select_department("t1")
        time.sleep(1)
        yield admin

        # Teardown: 기본 상태(OFF)로 안전 원복 후 브라우저 닫기
        try:
            admin.set_hr_ui_status("KYC", "OFF")
            time.sleep(1)
        except Exception as e:
            print(f">>> Teardown 원복 중 예외: {e}")
        finally:
            try:
                browser.close()
            except Exception:
                pass
            proc.terminate()


@pytest.fixture(scope="module")
def patch_admin_page():
    """
    Playwright 기반 PSI 웹 관리자 콘솔 패치 관리(/patch) 제어 Fixture
    - 사용자의 실제 모니터 세션에 크롬 새 창을 띄우고 로그인 후 /patch로 이동합니다.
    """
    proc = launch_visible_chrome(port=9222)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        patch_admin = AdminPatchPage(page)
        patch_admin.login(username="admin", password="Qwe123!@#")
        time.sleep(1)
        patch_admin.goto_patch()
        time.sleep(1)
        yield patch_admin

        try:
            browser.close()
        except Exception:
            pass
        proc.terminate()


@pytest.fixture(scope="function")
def app_ctrl():
    """보안점검 프로그램 AppController Fixture (인사 UI 우선 닫기 포함)"""
    ctrl = AppController()
    yield ctrl
    try:
        ctrl.close()
    except Exception:
        pass


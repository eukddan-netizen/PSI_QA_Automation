"""
[대분류: 보안점검 메인 탭] 공통 Fixture
- app_ctrl: 보안점검 프로그램(taKeeper.exe) 제어기
- pcsafe_manage_page: PSI 관리자 콘솔 보안점검 항목 관리(/pcsafeManage) 제어 및 정책 원복 보장 Fixture
"""

import time
import pytest
from playwright.sync_api import sync_playwright

from core.app_controller import AppController
from core.desktop_utils import launch_visible_chrome
from pages.server.pcsafe_page import AdminPcsafePage
from pages.server.pcsafe_manage_page import AdminPcsafeManagePage
from pages.server.manage_config_page import AdminManageConfigPage


@pytest.fixture(scope="module")
def pcsafe_manage_page():
    """
    Playwright 기반 PSI 웹 관리자 콘솔 보안점검 항목 관리(/pcsafeManage) Fixture
    - 사용자 모니터 세션에 크롬 새 창을 띄우고 Playwright CDP로 제어합니다.
    - 't1' 정책의 초기 항목 점수(1, 2번) 및 안전 기준 점수를 백업한 뒤,
      모듈 테스트 종료 시(실패 포함) 원래 값으로 자동 원복합니다.
    """
    proc = launch_visible_chrome(port=9222)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        manage = AdminPcsafeManagePage(page)
        manage.login(username="admin", password="Qwe123!@#")
        time.sleep(1)
        manage.goto_pcsafe_manage()
        manage.select_policy("t1")
        orig_snapshot = manage.get_policy_snapshot(item_nos=(1, 2))
        print(f"\n>>> [pcsafe_manage_page] 초기 't1' 정책 스냅샷 백업: {orig_snapshot}")

        try:
            yield manage
        finally:
            try:
                manage.goto_pcsafe_manage()
                manage.select_policy("t1")
                manage.restore_policy_snapshot(orig_snapshot)
            except Exception as e:
                print(f">>> [Teardown] 't1' 정책 원복 중 예외: {e}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
                proc.terminate()


@pytest.fixture(scope="module")
def pcsafe_admin_page():
    """
    Playwright 기반 PSI 웹 관리자 콘솔 PC보안점검 관리(/pcsafe) Fixture
    - 현재 PC IP(ipconfig) 기반 사용자 행 검색 및 상세 정보 조회 제공
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
        admin.search_current_user_by_ip()
        time.sleep(1)

        try:
            yield admin
        finally:
            try:
                browser.close()
            except Exception:
                pass
            proc.terminate()


@pytest.fixture(scope="module")
def manage_config_page():
    """
    Playwright 기반 PSI 웹 관리자 콘솔 환경설정(/manageConfig) Fixture
    - 사용자 모니터 세션에 크롬 새 창을 띄우고 Playwright CDP로 제어합니다.
    - 보안점검 탭의 초기 '문의처' 문구를 백업한 뒤,
      모듈 테스트 종료 시(실패 포함) 원래 값으로 자동 원복을 보장합니다.
    """
    proc = launch_visible_chrome(port=9222)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        manage_cfg = AdminManageConfigPage(page)
        manage_cfg.login(username="admin", password="Qwe123!@#")
        time.sleep(1)
        manage_cfg.goto_manage_config()
        manage_cfg.select_tab("보안점검")
        orig_contact = manage_cfg.get_contact_text()
        print(f"\n>>> [manage_config_page] 초기 '문의처' 문구 백업: '{orig_contact}'")

        try:
            yield manage_cfg
        finally:
            try:
                manage_cfg.goto_manage_config()
                manage_cfg.select_tab("보안점검")
                current_val = manage_cfg.get_contact_text()
                if current_val != orig_contact:
                    print(f"\n>>> [manage_config_page Teardown] 문의처 원복 진행: '{current_val}' -> '{orig_contact}'")
                    manage_cfg.set_contact_text(orig_contact)
                    manage_cfg.save_config()
            except Exception as e:
                print(f">>> [Teardown] 문의처 원복 중 예외 발생: {e}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
                proc.terminate()


@pytest.fixture(scope="function")
def app_ctrl():
    """보안점검 프로그램 AppController Fixture"""
    ctrl = AppController()
    yield ctrl
    try:
        ctrl.close()
    except Exception:
        pass

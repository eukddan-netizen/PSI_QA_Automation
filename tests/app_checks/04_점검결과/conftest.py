"""
[대분류: 점검결과 탭] 공통 Fixture
- result_tab_session: 점검 실행 -> 점검결과 자동 이동 -> 메인 탭 복귀(보고서 서버 전송) -> 점검결과 탭 재진입 선행 보장
- server_result_data: 관리자 웹(/pcsafeManage, /pcsafe) 데이터 조회 후 자동화 크롬 창을 즉시 안전 종료
"""

import time
import pytest
from playwright.sync_api import sync_playwright

from core.app_controller import AppController
from core.desktop_utils import launch_visible_chrome
from pages.client.inspection_result_page import InspectionResultPage
from pages.client.main_page import MainPage
from pages.server.pcsafe_manage_page import AdminPcsafeManagePage
from pages.server.pcsafe_page import AdminPcsafePage


@pytest.fixture(scope="package")
def result_tab_session():
    """
    점검결과 탭 테스트 전제 조건 수행 Fixture:
    1. 보안점검 프로그램 실행 및 메인 화면 대기
    2. '▶ 점검 시작' 실행 -> '점검결과' 탭 자동 전환 대기
    3. '메인' 탭으로 복귀하여 서버로 점검 보고서 전송 및 최근점검일시 갱신 유도
    4. 다시 '점검결과' 탭으로 이동하여 테스트 시작 상태 준비
    """
    ctrl = AppController()
    ctrl.launch(timeout=20)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=20.0)

    print("\n>>> [04_inspection_result_tab 선행] 1단계: 점검 시작 및 점검결과 탭 자동 이동 대기...")
    main_page.click_start_inspection()
    nav = main_page.wait_for_inspection_and_result_tab(timeout=30.0)
    assert nav["reached_result_tab"], (
        f"점검 완료 후 '점검결과' 탭으로 자동 이동하지 못했습니다. (감지 탭: {nav['tabs_seen']})"
    )

    time.sleep(1.0)
    print(">>> [04_inspection_result_tab 선행] 2단계: '메인' 탭으로 복귀하여 보고서 서버 전송 트리거...")
    main_page.navigate_to_tab("메인")
    main_inspection_info = main_page.wait_for_main_ready(timeout=15.0)
    time.sleep(1.5)
    main_user_info = main_page.get_user_info()
    print(f">>> [04_inspection_result_tab 선행] 메인 탭 복귀 후 정보: score={main_inspection_info.get('score')}, user={main_user_info}")

    print(">>> [04_inspection_result_tab 선행] 3단계: '점검결과' 탭으로 재진입...")
    main_page.navigate_to_tab("점검결과")
    result_page = InspectionResultPage(ctrl.hwnd)
    result_page.wait_for_result_ready(timeout=15.0)

    try:
        yield {
            "ctrl": ctrl,
            "main_page": main_page,
            "result_page": result_page,
            "main_user_info": main_user_info,
            "main_inspection_info": main_inspection_info,
        }
    finally:
        print("\n>>> [04_inspection_result_tab Teardown] 보안점검 프로그램 종료")
        try:
            ctrl.close()
        except Exception:
            pass


@pytest.fixture(scope="package")
def server_result_data(result_tab_session):
    """
    클라이언트 사용자 부서 정보를 기준으로 관리자 웹(/pcsafeManage, /pcsafe)에서
    1) 좌측 부서트리 내 부서 적용 정책 파악 -> 정책 드롭다운 선택 -> 정책 관리 테이블/안전기준점수 수집
    2) /pcsafe 현재 PC IP 사용자 상세 정보 및 보고서 반영 데이터 수집
    3) 웹 조회 완료 즉시 자동화 전용 크롬 창(port=9222)만 종료 (사용자 개인 크롬 유지)
    """
    result_page: InspectionResultPage = result_tab_session["result_page"]
    user_info = result_page.get_user_info()
    dept_name = user_info.get("department", "").strip()
    assert dept_name, f"점검결과 탭에서 사용자 부서명을 읽을 수 없습니다: {user_info}"

    proc = launch_visible_chrome(port=9222)
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()

            try:
                manage = AdminPcsafeManagePage(page)
                manage.login(username="admin", password="Qwe123!@#")
                time.sleep(1.0)

                # 1. 보안점검 항목 관리(/pcsafeManage): 부서트리 정책 확인 -> 드롭다운 선택 -> 정책 테이블 수집
                manage.goto_pcsafe_manage()
                policy_name = manage.get_department_policy(dept_name)
                manage.select_policy(policy_name)
                safety_score = manage.get_safety_score()
                items = manage.get_all_policy_items()
                active_items = [it for it in items if it["use"] == "사용"]

                # 2. PC보안점검 관리(/pcsafe): 사용자 상세 정보 및 보고서 반영 결과 수집
                pcsafe = AdminPcsafePage(page)
                pcsafe.goto_pcsafe()
                pcsafe.search_current_user_by_ip()
                server_user = pcsafe.get_user_details()
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    finally:
        print(">>> [관리자 웹] 데이터 확인 완료 — 자동화 전용 크롬 창 종료")
        proc.terminate()

    return {
        "department": dept_name,
        "policy_name": policy_name,
        "safety_score": safety_score,
        "items": items,
        "active_items": active_items,
        "active_item_map": {it["no"]: it for it in active_items},
        "server_user": server_user,
    }

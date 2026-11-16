"""
[대분류: 점검이력 탭] 공통 Fixture
- history_test_session:
  1. 앱 실행 -> 설정 > 정보 탭 버전 수집 -> 점검 전 점검이력 건수 확인
  2. 점검 시작 -> 점검결과 탭 요약/전체 행/샘플 상세설명 수집 -> 메인 탭 복귀(보고서 서버 전송)
  3. 점검이력 탭 이동 -> 이력 목록(및 100건 초과 시 재실행 후 100건 유지) 확인
- server_history_data:
  - 관리자 웹(/pcsafeManage, /pcsafe)에서 사용자 부서 정책 안전기준점수 및 사용자 정보 수집 후 크롬 즉시 종료
"""

import time
from typing import Dict, List
import pytest
from playwright.sync_api import sync_playwright

from core.app_controller import AppController
from core.desktop_utils import launch_visible_chrome
from pages.client.history_page import HistoryPage
from pages.client.inspection_result_page import InspectionResultPage
from pages.client.main_page import MainPage
from pages.client.settings_page import SettingsPage
from pages.server.pcsafe_manage_page import AdminPcsafeManagePage
from pages.server.pcsafe_page import AdminPcsafePage


def _sample_result_descriptions(result_page: InspectionResultPage, result_rows: List[dict]) -> Dict[int, str]:
    """점검결과 탭에서 상태별(안전/취약/점검불가) 대표 항목들의 '상세보기' 진단결과 문구를 수집"""
    targets: List[int] = []
    for status in ("안전", "취약", "점검불가"):
        matched = [r["no"] for r in result_rows if r["status"] == status and r.get("has_detail_button")]
        targets.extend(matched[:2])

    descriptions: Dict[int, str] = {}
    for no in targets:
        desc = result_page.get_item_detail_description(check_num=no)
        if desc:
            descriptions[no] = desc
    return descriptions


@pytest.fixture(scope="package")
def history_test_session():
    """
    점검이력 탭 전체 테스트(목록, 상세 내역, 토글, 엑셀 내보내기)가 공유하는 실행 세션 Fixture.
    """
    ctrl = AppController()
    ctrl.launch(timeout=20)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=20.0)

    # 1. 설정 > 정보 탭에서 앱 버전 수집
    settings_page = SettingsPage(ctrl.hwnd)
    app_version = settings_page.get_app_version(timeout=10.0)
    print(f"\n>>> [05_history 선행] 설정 > 정보 탭 앱 버전: {app_version}")

    # 2. 점검 전 점검이력 목록 건수 확인 (최대 100건 기준 사전 상태 파악)
    main_page.navigate_to_tab("점검이력")
    history_page = HistoryPage(ctrl.hwnd)
    history_page.wait_for_history_list_ready(timeout=12.0)
    pre_records = history_page.get_all_history_records()
    pre_count = len(pre_records)
    print(f">>> [05_history 선행] 점검 실행 전 점검이력 건수: {pre_count}건")

    # 3. 메인 탭으로 이동 -> 점검 시작 -> 점검결과 탭 자동 이동 대기
    main_page.navigate_to_tab("메인")
    main_page.wait_for_main_ready(timeout=12.0)

    print(">>> [05_history 선행] '▶ 점검 시작' 실행 및 '점검결과' 탭 전환 대기...")
    main_page.click_start_inspection()
    nav = main_page.wait_for_inspection_and_result_tab(timeout=35.0)
    assert nav["reached_result_tab"], (
        f"점검 완료 후 '점검결과' 탭으로 자동 이동하지 못했습니다. (감지 탭: {nav['tabs_seen']})"
    )

    result_page = InspectionResultPage(ctrl.hwnd)
    result_page.wait_for_result_ready(timeout=15.0)
    result_stats = result_page.get_summary_stats()
    result_rows = result_page.get_all_result_rows()
    sampled_descriptions = _sample_result_descriptions(result_page, result_rows)
    print(
        f">>> [05_history 선행] 점검결과 탭 수집: 점수={result_stats.get('score_num')}점, "
        f"전체={len(result_rows)}건, 샘플 상세설명={len(sampled_descriptions)}건"
    )

    # 4. 메인 탭 복귀 -> 보고서 서버 전송 및 최근점검일시 갱신 유도
    main_page.navigate_to_tab("메인")
    main_inspection_info = main_page.wait_for_main_ready(timeout=15.0)
    time.sleep(1.5)
    main_user_info = main_page.get_user_info()
    print(f">>> [05_history 선행] 메인 탭 사용자 정보: {main_user_info}")

    # 5. 점검이력 탭 이동 및 이력 목록 확인
    history_page.navigate_to_tab("점검이력")
    post_header_immediate = history_page.wait_for_history_list_ready(timeout=12.0)
    post_records_immediate = history_page.get_all_history_records()
    post_count_immediate = len(post_records_immediate)
    print(
        f">>> [05_history 선행] 점검 직후 점검이력 건수: {post_count_immediate}건 "
        f"(헤더: {post_header_immediate})"
    )

    restarted_due_to_100_overflow = False
    post_header_final = post_header_immediate
    post_records_final = post_records_immediate

    # 100개인 상태에서 점검 진행 시 일시적으로 100개 초과 가능 -> 프로그램 재실행 시 최근 100개로 유지되는지 확인
    if post_count_immediate > 100:
        print(
            f">>> [05_history 선행] 이력 {post_count_immediate}건(100건 초과) 감지 -> "
            "보안점검 프로그램 재실행 후 최근 100개 유지 여부 검증 준비..."
        )
        restarted_due_to_100_overflow = True
        ctrl.close()
        time.sleep(1.0)
        ctrl = AppController()
        ctrl.launch(timeout=20)
        assert ctrl.hwnd, "재실행 후 내PC보안점검 메인 창 실행 실패"

        main_page = MainPage(ctrl.hwnd)
        main_page.wait_for_main_ready(timeout=20.0)
        result_page = InspectionResultPage(ctrl.hwnd)
        settings_page = SettingsPage(ctrl.hwnd)
        history_page = HistoryPage(ctrl.hwnd)
        history_page.navigate_to_tab("점검이력")
        post_header_final = history_page.wait_for_history_list_ready(timeout=12.0)
        post_records_final = history_page.get_all_history_records()
        print(f">>> [05_history 선행] 재실행 후 점검이력 건수: {len(post_records_final)}건")

    session_data = {
        "ctrl": ctrl,
        "main_page": main_page,
        "result_page": result_page,
        "history_page": history_page,
        "settings_page": settings_page,
        "app_version": app_version,
        "pre_count": pre_count,
        "pre_records": pre_records,
        "main_user_info": main_user_info,
        "main_inspection_info": main_inspection_info,
        "result_stats": result_stats,
        "result_rows": result_rows,
        "sampled_result_descriptions": sampled_descriptions,
        "post_header_immediate": post_header_immediate,
        "post_records_immediate": post_records_immediate,
        "post_count_immediate": post_count_immediate,
        "restarted_due_to_100_overflow": restarted_due_to_100_overflow,
        "post_header_final": post_header_final,
        "post_records_final": post_records_final,
    }

    try:
        yield session_data
    finally:
        print("\n>>> [05_history Teardown] 보안점검 프로그램 종료")
        try:
            session_data["ctrl"].close()
        except Exception:
            pass


@pytest.fixture(scope="package")
def server_history_data(history_test_session):
    """
    클라이언트 사용자 부서 기준 관리자 웹(/pcsafeManage, /pcsafe) 데이터 조회 후 크롬 즉시 종료.
    """
    main_user = history_test_session["main_user_info"]
    dept_name = (main_user.get("department") or "").strip()
    assert dept_name, f"메인 탭에서 사용자 부서명을 읽을 수 없습니다: {main_user}"

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

                manage.goto_pcsafe_manage()
                policy_name = manage.get_department_policy(dept_name)
                manage.select_policy(policy_name)
                safety_score = manage.get_safety_score()

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
        print(">>> [관리자 웹] 점검이력 비교용 데이터 조회 완료 — 자동화 크롬 종료")
        proc.terminate()

    return {
        "department": dept_name,
        "policy_name": policy_name,
        "safety_score": safety_score,
        "server_user": server_user,
    }


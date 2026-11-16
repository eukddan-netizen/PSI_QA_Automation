"""
[대분류: 점검 탭] 검증 테스트 (Excel 69릴리즈 Row 38~40 / TC 13_0001~14_0001)

1. test_inspection_tab_user_info_matches_main (TC 14_0001, 우선 실행)
   - 메인 탭의 사용자 정보(OS 정보, 부서명, 사용자명, 사용자 IP, 최근점검일시)와
     점검 탭의 사용자 정보 데이터가 완전히 일치하는지 검증
2. test_inspection_start_realtime_and_auto_navigation (TC 13_0001 ~ 13_0002)
   - 점검 탭 내 '▶ 점검 시작' 버튼 클릭 후 진행률/진행 시간 실시간 반영 및
     점검 완료(100%) 후 '점검결과' 탭 자동 전환 검증
"""

import pytest

from pages.client.inspection_page import InspectionPage
from pages.client.main_page import MainPage


@pytest.mark.app_check
@pytest.mark.app_inspection
def test_inspection_tab_user_info_matches_main(app_ctrl):
    """[TC 14_0001] 점검 탭 사용자 정보(OS/부서/사용자명/IP/최근점검일시)와 메인 탭 데이터 일치 검증"""
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(app_ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)
    main_user = main_page.get_user_info()
    print(f"\n>>> [메인 탭 사용자 정보] {main_user}")

    assert main_user.get("username"), f"메인 탭 사용자 정보를 읽을 수 없습니다: {main_user}"

    main_page.navigate_to_tab("점검")
    inspection_page = InspectionPage(app_ctrl.hwnd)
    inspection_page.wait_for_inspection_ready(timeout=10.0)
    insp_user = inspection_page.get_user_info()
    print(f">>> [점검 탭 사용자 정보] {insp_user}")

    fields = ("os", "department", "username", "ip", "last_inspection_time")
    errors = []
    for key in fields:
        m_val = main_user.get(key)
        i_val = insp_user.get(key)
        if not i_val:
            errors.append(f"점검 탭에서 '{key}' 값을 읽지 못했습니다. (메인 탭: '{m_val}')")
        elif m_val != i_val:
            errors.append(f"'{key}' 불일치! 메인 탭='{m_val}' != 점검 탭='{i_val}'")

    assert not errors, "\n".join(errors)
    print(">>> [TC 14_0001] 점검 탭 사용자 정보 <-> 메인 탭 사용자 정보 100% 일치 확인!")


@pytest.mark.app_check
@pytest.mark.app_inspection
def test_inspection_start_realtime_and_auto_navigation(app_ctrl):
    """[TC 13_0001 ~ 13_0002] 점검 탭 '▶ 점검 시작' 클릭 후 실시간 진행 반영 및 '점검결과' 탭 자동 이동 검증"""
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    inspection_page = InspectionPage(app_ctrl.hwnd)
    inspection_page.wait_for_main_ready(timeout=12.0)
    inspection_page.navigate_to_tab("점검")
    init_status = inspection_page.wait_for_inspection_ready(timeout=10.0)
    print(f"\n>>> [점검 탭 초기 상태] {init_status}")

    assert init_status.get("total_count") and init_status["total_count"] > 0, (
        f"점검 항목 전체 건수가 유효하지 않습니다: {init_status}"
    )

    inspection_page.click_start_inspection_on_tab()
    progress = inspection_page.monitor_inspection_progress(timeout=30.0)
    print(f">>> [점검 진행 모니터링 결과] {progress}")

    assert progress["reached_result_tab"], (
        f"점검 완료 후 '점검결과' 탭으로 자동 이동하지 못했습니다. (관측 진행률: {progress['progress_history']})"
    )
    assert progress["progress_history"] or progress["elapsed_times_seen"], (
        "점검 진행 중 프로그레스바 또는 진행 시간 UI 변화가 전혀 관측되지 않았습니다."
    )
    print(
        f">>> [TC 13_0001~13_0002] 점검 실시간 진행({progress['progress_history']}) 및 "
        f"'점검결과' 탭 자동 전환 검증 완료! (소요: {progress['elapsed']}초)"
    )

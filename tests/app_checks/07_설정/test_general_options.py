"""
설정 > 일반 옵션 및 완료 팝업 분기 테스트 (Row 59~60)
1. '점검 후 결과 화면으로 자동 이동' 옵션의 기본 체크 상태 검증
2. 옵션 체크 해제 후 메인 탭 또는 점검 탭에서 점검 진행 시:
   - 점검 완료 후 바로 결과 탭으로 이동하지 않고 '점검이 완료되었습니다. 결과 화면으로 이동합니다.' 팝업 노출 확인
   - 팝업 내 '결과 화면으로 이동' 버튼 클릭 시 '점검결과' 탭으로 이동 및 결과 표시 검증
   - 테스트 종료 시 옵션을 기본 상태(체크)로 원복
"""

import pytest

from pages.client.inspection_page import InspectionPage
from pages.client.inspection_result_page import InspectionResultPage
from pages.client.main_page import MainPage
from pages.client.settings_page import SettingsPage


@pytest.mark.app_check
@pytest.mark.app_settings
def test_auto_navigation_default_checked(settings_session):
    """[Row 59] '점검 후 결과 화면으로 자동 이동' 옵션의 기본값이 체크 상태인지 검증"""
    settings_page: SettingsPage = settings_session["settings_page"]

    is_checked = settings_page.get_auto_navigate_checked(timeout=10.0)
    print(f"\n>>> [설정 > 일반] '점검 후 결과 화면으로 자동 이동' 기본 체크 상태: {is_checked}")
    assert is_checked, "'점검 후 결과 화면으로 자동 이동' 옵션의 디폴트 상태가 체크(True)가 아닙니다."


@pytest.mark.app_check
@pytest.mark.app_settings
@pytest.mark.parametrize("start_tab", ["메인", "점검"])
def test_auto_navigation_disabled_popup_flow(settings_session, start_tab: str):
    """[Row 59~60] 자동 이동 해제 후 메인/점검 탭에서 점검 완료 시 팝업 노출 및 버튼 클릭 이동 검증"""
    ctrl = settings_session["ctrl"]
    settings_page: SettingsPage = settings_session["settings_page"]

    # 사전 확인: 기본값이 체크 상태인지 확인하고 해제
    initial_state = settings_page.get_auto_navigate_checked(timeout=10.0)
    print(f"\n>>> [설정 > 일반 ({start_tab} 탭 출발)] 초기 자동 이동 체크 상태: {initial_state}")
    assert initial_state, "'점검 후 결과 화면으로 자동 이동' 옵션이 체크된 상태여야 합니다."

    try:
        new_state = settings_page.set_auto_navigate_checked(False, timeout=8.0)
        assert not new_state, "'점검 후 결과 화면으로 자동 이동' 체크 해제 실패"
        print(">>> [설정 > 일반] '점검 후 결과 화면으로 자동 이동' 체크 해제 완료")

        if start_tab == "메인":
            main_page = MainPage(ctrl.hwnd)
            main_page.navigate_to_tab("메인", timeout=10.0)
            main_page.wait_for_main_ready(timeout=12.0)
            main_page.click_start_inspection()
        else:
            insp_page = InspectionPage(ctrl.hwnd)
            insp_page.navigate_to_tab("점검", timeout=10.0)
            insp_page.wait_for_inspection_ready(timeout=10.0)
            insp_page.click_start_inspection_on_tab()

        popup = settings_page.wait_for_result_move_popup(timeout=35.0)
        print(f">>> [완료 팝업 감지] {popup}")
        assert "점검이 완료되었습니다" in popup["message"], (
            f"완료 팝업 문구가 기대와 다릅니다: {popup['message']!r}"
        )
        assert SettingsPage.RESULT_POPUP_BUTTON in popup["buttons"], (
            f"팝업에 '{SettingsPage.RESULT_POPUP_BUTTON}' 버튼이 없습니다: {popup['buttons']}"
        )

        settings_page.click_result_move_popup_button(timeout=10.0)
        assert settings_page.get_active_tab_name() == "점검결과", (
            f"팝업 버튼 클릭 후 활성 탭이 '점검결과'가 아닙니다: {settings_page.get_active_tab_name()}"
        )

        result_page = InspectionResultPage(ctrl.hwnd)
        stats = result_page.wait_for_result_ready(timeout=12.0)
        print(f">>> [점검결과 탭 이동 확인] 요약={stats}")
        assert stats.get("score_num") is not None and stats.get("total_num", 0) > 0, (
            f"'점검결과' 탭 이동 후 결과 데이터가 정상 렌더링되지 않았습니다: {stats}"
        )
    finally:
        # 팝업이 남아 있으면 먼저 닫고 설정을 반드시 기본값(체크)으로 원복
        try:
            settings_page.dismiss_result_move_popup_if_present(timeout=1.5)
            restored = settings_page.set_auto_navigate_checked(True, timeout=8.0)
            print(f">>> [Teardown] '점검 후 결과 화면으로 자동 이동' 원복 상태: {restored}")
        except Exception as exc:
            print(f">>> [Teardown 경고] 자동 이동 옵션 원복 중 예외: {exc}")

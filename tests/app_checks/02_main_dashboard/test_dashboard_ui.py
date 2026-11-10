"""
메인 대시보드 상태 및 사용자 정보/경고 팝업 테스트 (Row 20~26, 33~34)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.skip(reason="구현 예정")
def test_dashboard_shield_status_by_history():
    """이력 유무 및 안전기준점수 이상/미만에 따른 방패 상태(대기/양호/취약) 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.skip(reason="구현 예정")
def test_below_threshold_close_warning_popup():
    """안전기준점수 미만 상태에서 우상단 X 클릭 시 PC 사용 제한 확인 팝업 출력 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.skip(reason="구현 예정")
def test_security_index_hover_tooltips():
    """PC보안지표 항목 hover 시 지표 점수 툴팁 표시 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.skip(reason="구현 예정")
def test_user_info_and_last_inspection_time():
    """사용자 정보 표시 및 최초 실행(0000-00-00)/점검 후 최근점검일시 갱신 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.skip(reason="구현 예정")
def test_past_history_click_navigation():
    """지난 검사내역 hover 점수 및 클릭 시 점검이력 상세 화면 이동 검증"""
    pass

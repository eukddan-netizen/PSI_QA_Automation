"""
트레이 우클릭 메뉴 동작 및 알림 팝업/로그 테스트 (Row 9~11, 16~19)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_tray_menu_main_launch():
    """트레이 > 내PC보안점검 클릭 시 메인 창 출력 또는 중복 실행 방지 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_tray_software_rescan():
    """트레이 > 프로그램 목록 재확인 클릭 시 성공 팝업 및 에이전트 로그 확인"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_tray_font_rescan():
    """트레이 > 폰트 목록 재확인 클릭 시 성공 팝업 및 에이전트 로그 확인"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_tray_agent_update():
    """트레이 > 에이전트 업데이트 실행 클릭 시 정상 동작 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_tray_info_popup():
    """트레이 > 정보 확인 클릭 시 제품명/서버/사용자IP 팝업 출력 확인"""
    pass

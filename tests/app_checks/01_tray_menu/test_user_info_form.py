"""
사용자 정보 입력 웹뷰 유효성 검증 테스트 (Row 12~15)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_user_info_required_fields_validation():
    """사번/이름 미입력 시 '사번 or 이름을 입력하세요' alert 팝업 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_user_info_invalid_data_validation():
    """미등록 인사 정보 입력 시 '일치하지 않습니다' alert 팝업 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.skip(reason="구현 예정")
def test_user_info_success_registration():
    """정상 인사 정보 입력 시 '정상 등록되었습니다' alert 팝업 검증"""
    pass

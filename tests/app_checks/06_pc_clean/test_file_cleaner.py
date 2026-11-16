"""
내 PC 정리 기능 및 실제 파일 삭제 검증 테스트 (Row 51~58)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_clean
@pytest.mark.skip(reason="구현 예정")
def test_clean_recycle_bin():
    """휴지통 비우기 실행 후 팝업 및 실제 휴지통 비워짐 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_clean
@pytest.mark.skip(reason="구현 예정")
def test_clean_temp_files():
    """더미 임시파일 생성 후 윈도우 임시파일 정리 실행 시 실제 삭제 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_clean
@pytest.mark.skip(reason="구현 예정")
def test_clean_browser_cache():
    """Chrome / Edge 브라우저 캐시 데이터 정리 실행 및 파일 감소 검증"""
    pass

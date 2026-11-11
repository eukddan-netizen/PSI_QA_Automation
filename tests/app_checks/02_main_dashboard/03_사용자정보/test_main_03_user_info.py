"""
[대분류: 보안점검 메인 탭 > 중분류 3: 사용자 정보] (Excel Row 25~26)

- Row 25: 최초 실행 시 최근점검일시 0000-00-00 00:00:00 출력
- Row 26: 점검 완료 후 결과 전송 시각으로 최근점검일시 자동 갱신
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_03
@pytest.mark.skip(reason="구현 예정")
def test_row25_initial_last_inspection_time():
    """[Row 25] 최초 실행 시 최근점검일시 '0000-00-00 00:00:00' 표기 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_03
@pytest.mark.skip(reason="구현 예정")
def test_row26_updated_last_inspection_time_after_scan():
    """[Row 26] 점검 완료 및 결과 전송 후 최근점검일시 자동 갱신 검증"""
    pass


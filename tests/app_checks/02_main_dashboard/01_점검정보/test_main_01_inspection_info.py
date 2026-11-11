"""
[대분류: 보안점검 메인 탭 > 중분류 1: 점검 정보] (Excel Row 20~23)

- Row 20: 최근 점검 이력 없음 -> 방패 아이콘 "대기", '취약점 검사 필요, 검사를 진행해 주십시오.' 문구
- Row 21: 최근 점검 이력 있음 (점수 >= 안전기준점수) -> 방패 아이콘 "양호"
- Row 22: 최근 점검 이력 있음 (점수 < 안전기준점수) -> 방패 아이콘 "취약", 창 닫기(X) 시 기준점수 미만 PC 사용 제한 팝업
- Row 23: '점검 시작' 버튼 클릭 -> 점검 진행 탭으로 이동 및 검사 개시
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
@pytest.mark.skip(reason="구현 예정")
def test_row20_shield_status_no_history():
    """[Row 20] 최근 점검 이력 없을 때 방패 대기 및 점검 필요 문구 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
@pytest.mark.skip(reason="구현 예정")
def test_row21_shield_status_good():
    """[Row 21] 최근 점검 점수 >= 기준점수일 때 방패 '양호' 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
@pytest.mark.skip(reason="구현 예정")
def test_row22_shield_status_vulnerable_and_close_warning():
    """[Row 22] 최근 점검 점수 < 기준점수일 때 방패 '취약' 및 우상단 X 클릭 시 사용 제한 팝업 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
@pytest.mark.skip(reason="구현 예정")
def test_row23_start_inspection_button():
    """[Row 23] '점검 시작' 버튼 클릭 시 점검 진행 탭으로 이동 및 검사 개시 검증"""
    pass


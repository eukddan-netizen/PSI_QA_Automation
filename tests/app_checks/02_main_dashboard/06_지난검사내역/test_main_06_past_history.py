"""
[대분류: 보안점검 메인 탭 > 중분류 6: 지난 검사내역] (Excel Row 33~34)

- Row 33: 검사 내역 항목에 hover 시 당시 점수 출력
- Row 34: 특정 검사 내역 클릭 시 '점검이력' 탭의 해당 상세 내역으로 즉시 이동
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_06
@pytest.mark.skip(reason="구현 예정")
def test_row33_past_history_hover_score():
    """[Row 33] 지난 검사내역 hover 시 당시 점수 출력 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_06
@pytest.mark.skip(reason="구현 예정")
def test_row34_past_history_click_navigation():
    """[Row 34] 특정 검사내역 클릭 시 '점검이력' 탭 해당 상세 이동 검증"""
    pass


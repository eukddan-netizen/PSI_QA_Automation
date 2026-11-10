"""
점검결과 테이블 헤더 클릭 정렬 테스트 (Row 69~71)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_result
@pytest.mark.skip(reason="구현 예정")
def test_sort_by_number_column():
    """1열 '번호' 헤더 클릭 시 오름차순/내림차순 정렬 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_result
@pytest.mark.skip(reason="구현 예정")
def test_sort_by_item_name_column():
    """2열 '점검 항목' 헤더 클릭 시 가나다순 정렬 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_result
@pytest.mark.skip(reason="구현 예정")
def test_sort_by_result_column():
    """3열 '결과' 헤더 클릭 시 상태별 정렬 검증"""
    pass

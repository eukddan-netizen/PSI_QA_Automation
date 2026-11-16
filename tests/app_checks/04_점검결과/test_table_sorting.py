"""
[대분류: 점검결과 탭 공통 UI] 결과 테이블 헤더 클릭 정렬 검증 (Row 69~71 / 요구사항 5번)
"""

from itertools import groupby
import pytest

from pages.client.inspection_result_page import InspectionResultPage


@pytest.mark.app_check
@pytest.mark.app_result
def test_sort_by_number_column(result_tab_session):
    """[Row 69] 1열 '번호' 헤더 2회 클릭 시 오름차순 -> 내림차순 정렬 검증"""
    result_page: InspectionResultPage = result_tab_session["result_page"]

    initial_rows = result_page.get_all_result_rows()
    expected_nos_set = sorted(r["no"] for r in initial_rows)
    assert len(expected_nos_set) > 0, "정렬할 결과 테이블 행이 없습니다."

    # 1회 클릭 -> 번호 오름차순
    result_page.click_table_header("번호")
    rows_asc = result_page.get_all_result_rows()
    nos_asc = [r["no"] for r in rows_asc]
    print(f"\n>>> ['번호' 1차 클릭] 상위 5개: {nos_asc[:5]}, 하위 3개: {nos_asc[-3:]}")
    assert nos_asc == expected_nos_set, f"'번호' 1회 클릭 후 오름차순 정렬 실패: {nos_asc[:10]}"

    # 2회 클릭 -> 번호 내림차순
    result_page.click_table_header("번호")
    rows_desc = result_page.get_all_result_rows()
    nos_desc = [r["no"] for r in rows_desc]
    print(f">>> ['번호' 2차 클릭] 상위 5개: {nos_desc[:5]}, 하위 3개: {nos_desc[-3:]}")
    assert nos_desc == list(reversed(expected_nos_set)), f"'번호' 2회 클릭 후 내림차순 정렬 실패: {nos_desc[:10]}"


@pytest.mark.app_check
@pytest.mark.app_result
def test_sort_by_item_name_column(result_tab_session):
    """[Row 70] 2열 '점검 항목' 헤더 2회 클릭 시 오름차순 -> 내림차순 정렬 검증"""
    result_page: InspectionResultPage = result_tab_session["result_page"]

    initial_rows = result_page.get_all_result_rows()
    expected_titles_asc = sorted(r["title"] for r in initial_rows)
    assert len(expected_titles_asc) > 0, "정렬할 결과 테이블 행이 없습니다."

    # 1회 클릭 -> 점검 항목명 오름차순
    result_page.click_table_header("점검 항목")
    rows_asc = result_page.get_all_result_rows()
    titles_asc = [r["title"] for r in rows_asc]
    print(f"\n>>> ['점검 항목' 1차 클릭] 상위 3개: {titles_asc[:3]}, 하위 3개: {titles_asc[-3:]}")
    assert titles_asc == expected_titles_asc, (
        f"'점검 항목' 1회 클릭 후 오름차순 정렬 실패: 실제={titles_asc[:5]} vs 기대={expected_titles_asc[:5]}"
    )

    # 2회 클릭 -> 점검 항목명 내림차순
    result_page.click_table_header("점검 항목")
    rows_desc = result_page.get_all_result_rows()
    titles_desc = [r["title"] for r in rows_desc]
    print(f">>> ['점검 항목' 2차 클릭] 상위 3개: {titles_desc[:3]}, 하위 3개: {titles_desc[-3:]}")
    assert titles_desc == list(reversed(expected_titles_asc)), (
        f"'점검 항목' 2회 클릭 후 내림차순 정렬 실패: 실제={titles_desc[:5]} vs 기대={list(reversed(expected_titles_asc))[:5]}"
    )


@pytest.mark.app_check
@pytest.mark.app_result
def test_sort_by_result_column(result_tab_session):
    """[Row 71] 3열 '결과' 헤더 2회 클릭 시 상태별 그룹 오름/내림차순 정렬 검증"""
    result_page: InspectionResultPage = result_tab_session["result_page"]

    # 1회 클릭 -> 상태별 정렬 (안전 먼저, 취약 나중)
    result_page.click_table_header("결과")
    rows_1 = result_page.get_all_result_rows()
    statuses_1 = [r["status"] for r in rows_1]
    groups_1 = [k for k, _ in groupby(statuses_1)]
    print(f"\n>>> ['결과' 1차 클릭] 상태 그룹 순서: {groups_1}")

    assert len(groups_1) == len(set(statuses_1)), (
        f"'결과' 1회 클릭 후 동일 상태끼리 연속 그룹화되지 않았습니다: {groups_1}"
    )
    if "안전" in groups_1 and "취약" in groups_1:
        assert groups_1.index("안전") < groups_1.index("취약"), (
            f"'결과' 1회 클릭 후 '안전'이 '취약'보다 먼저 정렬되어야 합니다: {groups_1}"
        )

    # 2회 클릭 -> 상태별 역순 정렬 (취약 먼저, 안전 나중)
    result_page.click_table_header("결과")
    rows_2 = result_page.get_all_result_rows()
    statuses_2 = [r["status"] for r in rows_2]
    groups_2 = [k for k, _ in groupby(statuses_2)]
    print(f">>> ['결과' 2차 클릭] 상태 그룹 순서: {groups_2}")

    assert len(groups_2) == len(set(statuses_2)), (
        f"'결과' 2회 클릭 후 동일 상태끼리 연속 그룹화되지 않았습니다: {groups_2}"
    )
    if "안전" in groups_2 and "취약" in groups_2:
        assert groups_2.index("취약") < groups_2.index("안전"), (
            f"'결과' 2회 클릭 후 '취약'이 '안전'보다 먼저 정렬되어야 합니다: {groups_2}"
        )
    if len(groups_1) > 1:
        assert groups_2 == list(reversed(groups_1)), (
            f"'결과' 2회 클릭 후 상태 그룹 순서가 역전되지 않았습니다: 1차={groups_1}, 2차={groups_2}"
        )

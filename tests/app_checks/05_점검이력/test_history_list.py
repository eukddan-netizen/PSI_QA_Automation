"""
점검이력 탭 목록 및 상세 내역 검증 테스트 (요구사항 1~7 / Row 38~44)
1. 최근점검일시: 메인 탭 최근점검일시 및 1번 행 일시 일치 검증
2. 안전기준점수: 관리자 웹(/pcsafeManage) 사용자 부서 적용 정책의 안전기준점수 일치 검증
3. 점검이력 최대 100건 제한(100건 상태에서 점검 시 일시 초과 후 재실행 시 최근 100건 유지 포함) 검증
4. 점검 진행 후 가장 최근 점검이력 클릭 -> 점검 상세 내역 이동 검증
5. 사용자 정보(점검일시/IP/사용자명/부서/OS/백신/버전) 일치 검증 (버전은 설정 > 정보 탭과 대조)
6. 점검 상세 내역의 요약 및 전체 항목 결과가 현재 점검결과 탭 데이터와 일치하는지 검증
7. 전체 열기 / 전체 닫기 토글 버튼 및 개별 행 아코디언 토글 동작 검증
"""

import pytest

from common.os_utils import get_antivirus_products, get_current_machine_ips
from pages.client.history_page import HistoryPage


def _normalize_ws(text: str) -> str:
    return " ".join((text or "").split())


@pytest.mark.app_check
@pytest.mark.app_history
def test_history_recent_time_and_safety_score(history_test_session, server_history_data):
    """
    [요구사항 1, 2]
    1) 점검이력 탭 상단 '최근점검일시'와 메인 탭 '최근점검일시', 이력 1번 행 '점검 일시' 일치 검증
    2) 점검이력 탭 우측 상단 '안전기준점수'와 관리자 웹(/pcsafeManage) 부서 정책 안전기준점수 일치 검증
    """
    main_user = history_test_session["main_user_info"]
    main_insp = history_test_session["main_inspection_info"]
    header = history_test_session["post_header_final"]
    records = history_test_session["post_records_final"]
    server_safety = server_history_data["safety_score"]
    server_user = server_history_data["server_user"]

    assert records, "점검이력 테이블에 파싱된 이력 행이 없습니다."

    main_time = main_user.get("last_inspection_time")
    history_time = header.get("last_inspection_time")
    row1_time = records[0].get("inspection_time")
    history_safety = header.get("safety_score")

    print(
        f"\n>>> [최근점검일시 검증] 메인='{main_time}', 점검이력헤더='{history_time}', "
        f"1번행='{row1_time}', 서버='{server_user.get('last_inspection_time')}'"
    )
    print(
        f">>> [안전기준점수 검증] 점검이력={history_safety}점, 메인={main_insp.get('safety_score')}점, "
        f"서버(/pcsafeManage 정책='{server_history_data['policy_name']}')={server_safety}점"
    )

    assert history_time, "점검이력 탭 상단에서 '최근점검일시'를 읽지 못했습니다."
    assert history_time == main_time, (
        f"점검이력 탭 최근점검일시('{history_time}')가 메인 탭 최근점검일시('{main_time}')와 다릅니다."
    )
    assert row1_time == history_time, (
        f"점검이력 1번 행 일시('{row1_time}')가 상단 최근점검일시('{history_time}')와 다릅니다."
    )
    if server_user.get("last_inspection_time"):
        assert history_time == server_user["last_inspection_time"], (
            f"점검이력 최근점검일시('{history_time}')가 서버 최종 점검일('{server_user['last_inspection_time']}')과 다릅니다."
        )

    assert history_safety == server_safety, (
        f"점검이력 우측 상단 안전기준점수({history_safety}점)가 서버 부서 적용 정책 "
        f"안전기준점수({server_safety}점)와 일치하지 않습니다."
    )
    if main_insp.get("safety_score") is not None:
        assert history_safety == main_insp["safety_score"], (
            f"점검이력 안전기준점수({history_safety}점)가 메인 탭 안전기준점수({main_insp['safety_score']}점)와 다릅니다."
        )


@pytest.mark.app_check
@pytest.mark.app_history
def test_history_list_max_100_limit(history_test_session):
    """
    [요구사항 3]
    점검이력 리스트 최대 100건 제한 검증:
    - 평상시(점검 전): 100건 이하
    - 100건 상태에서 점검 실행 직후 일시적으로 100건을 초과한 경우에도,
      보안점검 프로그램 재실행 시 최근 100건으로 유지되고 최신 이력이 1번에 위치해야 함
    """
    pre_count = history_test_session["pre_count"]
    immediate_count = history_test_session["post_count_immediate"]
    immediate_records = history_test_session["post_records_immediate"]
    restarted = history_test_session["restarted_due_to_100_overflow"]
    final_records = history_test_session["post_records_final"]
    final_count = len(final_records)

    print(
        f"\n>>> [이력 100건 제한 검증] 점검전={pre_count}건, 점검직후={immediate_count}건, "
        f"재실행여부={restarted}, 최종={final_count}건"
    )

    assert pre_count <= 100, f"초기 실행 시 점검이력이 100건을 초과했습니다: {pre_count}건"

    if immediate_count > 100:
        assert pre_count == 100, (
            f"점검 전 이력이 {pre_count}건(100건 미만)인데 점검 직후 {immediate_count}건으로 100건을 초과했습니다."
        )
        assert restarted, "100건 초과 후 보안점검 재실행 검증이 수행되지 않았습니다."
        assert final_count == 100, (
            f"100건 초과 후 보안점검 재실행 시 최근 100건으로 제한되어야 하나 {final_count}건이 표시되었습니다."
        )
        assert final_records[0]["inspection_time"] == immediate_records[0]["inspection_time"], (
            f"재실행 후 1번 최신 이력 일시('{final_records[0]['inspection_time']}')가 "
            f"방금 실행한 이력('{immediate_records[0]['inspection_time']}')과 다릅니다."
        )
    else:
        assert 1 <= final_count <= 100, f"점검이력 개수가 1~100 범위를 벗어났습니다: {final_count}건"

    # 번호 순번(1..N) 및 점검 일시 내림차순 정렬 검증
    nos = [r["no"] for r in final_records]
    assert nos == list(range(1, final_count + 1)), f"점검이력 번호 순번이 1~{final_count} 연속이 아닙니다: {nos[:10]}"

    times = [r["inspection_time"] for r in final_records]
    assert times == sorted(times, reverse=True), "점검이력 목록이 최신순(내림차순)으로 정렬되어 있지 않습니다."


@pytest.mark.app_check
@pytest.mark.app_history
def test_history_latest_detail_user_info(history_test_session, server_history_data):
    """
    [요구사항 4, 5]
    점검 진행 후 가장 최근 점검이력(1번 행) 클릭 -> 점검 상세 내역 이동 및
    사용자 정보(점검일시, 사용자 IP, 사용자명, 부서명, OS 정보, 바이러스백신, 버전) 검증
    """
    history_page: HistoryPage = history_test_session["history_page"]
    main_user = history_test_session["main_user_info"]
    server_user = server_history_data["server_user"]
    settings_version = history_test_session["app_version"]
    latest_row = history_test_session["post_records_final"][0]

    # 목록 상태 보장 후 1번 행 직접 클릭하여 상세 내역 진입
    if history_page.is_detail_view():
        history_page.click_back_to_list()
    elif history_page.get_active_tab_name() != "점검이력":
        history_page.navigate_to_tab("점검이력")
        history_page.wait_for_history_list_ready()

    history_page.click_history_row(row_index=0)
    assert history_page.is_detail_view(), "가장 최근 점검이력 클릭 후 '점검 상세 내역' 화면으로 이동하지 못했습니다."

    detail_user = history_page.get_detail_user_info()
    print(f"\n>>> [상세내역 사용자 정보] {detail_user}")
    print(f">>> [메인 탭 사용자 정보]   {main_user}")
    print(f">>> [설정>정보 탭 앱 버전]  {settings_version}")

    errors = []
    if detail_user.get("inspection_time") != main_user.get("last_inspection_time"):
        errors.append(
            f"점검일시 불일치: 상세='{detail_user.get('inspection_time')}' != 메인='{main_user.get('last_inspection_time')}'"
        )
    if detail_user.get("inspection_time") != latest_row.get("inspection_time"):
        errors.append(
            f"점검일시 불일치: 상세='{detail_user.get('inspection_time')}' != 1번행='{latest_row.get('inspection_time')}'"
        )

    local_ips = get_current_machine_ips()
    for field in ("ip", "username", "department", "os"):
        d_val = detail_user.get(field)
        m_val = main_user.get(field)
        if not d_val:
            errors.append(f"상세내역 사용자 정보 '{field}' 값이 비어 있습니다.")
        elif d_val != m_val:
            errors.append(f"'{field}' 불일치: 상세='{d_val}' != 메인='{m_val}'")

    if detail_user.get("ip") != server_user.get("ip"):
        errors.append(f"IP 서버 불일치: 상세='{detail_user.get('ip')}' != 서버='{server_user.get('ip')}'")
    if detail_user.get("ip") not in local_ips:
        errors.append(f"상세 IP('{detail_user.get('ip')}')가 로컬 IP 목록({local_ips})에 없습니다.")
    if detail_user.get("username") != server_user.get("username"):
        errors.append(f"사용자명 서버 불일치: 상세='{detail_user.get('username')}' != 서버='{server_user.get('username')}'")
    if detail_user.get("department") != server_user.get("department"):
        errors.append(f"부서명 서버 불일치: 상세='{detail_user.get('department')}' != 서버='{server_user.get('department')}'")

    if server_user.get("os") and server_user["os"] not in detail_user.get("os", ""):
        errors.append(f"OS 정보 서버 불일치: 서버 '{server_user['os']}' 미포함 (상세: '{detail_user.get('os')}')")
    if server_user.get("sp") and server_user["sp"] not in detail_user.get("os", ""):
        errors.append(f"OS SP 서버 불일치: 서버 '{server_user['sp']}' 미포함 (상세: '{detail_user.get('os')}')")

    # 바이러스백신 검증
    av = detail_user.get("antivirus", "")
    if not av:
        errors.append("상세내역 '바이러스백신' 값이 비어 있습니다.")
    else:
        os_avs = get_antivirus_products()
        print(f">>> [OS SecurityCenter2 백신 목록] {os_avs}")
        if os_avs and not any(av.lower() in installed.lower() or installed.lower() in av.lower() for installed in os_avs):
            errors.append(f"바이러스백신 불일치: 상세='{av}', OS 등록 백신={os_avs}")

    # 버전 검증 (설정 > 정보 탭의 앱 버전과 일치)
    if detail_user.get("version") != settings_version:
        errors.append(
            f"버전 불일치: 상세='{detail_user.get('version')}' != 설정>정보='{settings_version}'"
        )

    assert not errors, "\n".join(errors)


@pytest.mark.app_check
@pytest.mark.app_history
def test_history_detail_results_match_inspection_result_tab(history_test_session):
    """
    [요구사항 6]
    점검 상세 내역의 요약 수치 및 각 항목별 결과/항목명/상세설명이
    현재 점검결과 탭의 데이터와 100% 일치하는지 검증
    """
    history_page: HistoryPage = history_test_session["history_page"]
    result_stats = history_test_session["result_stats"]
    result_rows = history_test_session["result_rows"]
    sampled_descs = history_test_session["sampled_result_descriptions"]
    latest_row = history_test_session["post_records_final"][0]

    history_page.ensure_latest_detail_view()

    # 1. 요약 테이블 비교
    summary = history_page.get_detail_summary()
    print(f"\n>>> [상세내역 요약] {summary}")
    print(f">>> [점검결과 요약] {result_stats}")

    assert summary.get("score") == result_stats.get("score_num"), (
        f"상세내역 점수({summary.get('score')}점) != 점검결과 탭 점수({result_stats.get('score_num')}점)"
    )
    assert summary.get("safe_count") == result_stats.get("safe_num"), (
        f"상세내역 안전({summary.get('safe_count')}건) != 점검결과 탭({result_stats.get('safe_num')}건)"
    )
    assert summary.get("vulnerable_count") == result_stats.get("vulnerable_num"), (
        f"상세내역 취약({summary.get('vulnerable_count')}건) != 점검결과 탭({result_stats.get('vulnerable_num')}건)"
    )
    assert summary.get("unable_count") == result_stats.get("cannot_check_num"), (
        f"상세내역 점검불가({summary.get('unable_count')}건) != 점검결과 탭({result_stats.get('cannot_check_num')}건)"
    )
    assert summary.get("uninspected_count") == 0, (
        f"점검 완료 이력의 미점검 건수가 0이 아닙니다: {summary.get('uninspected_count')}건"
    )
    assert (
        summary["safe_count"] + summary["vulnerable_count"] + summary["unable_count"] + summary["uninspected_count"]
        == result_stats.get("total_num")
    ), "상세내역 요약 건수 합계가 점검결과 전체 건수와 다릅니다."

    # 이력 목록 1번 행 수치와도 일치 확인
    assert summary["score"] == latest_row["score"]
    assert summary["safe_count"] == latest_row["safe_count"]
    assert summary["vulnerable_count"] == latest_row["vulnerable_count"]
    assert summary["unable_count"] == latest_row["unable_count"]
    assert summary["uninspected_count"] == latest_row["uninspected_count"]

    # 2. 전체 열기 후 모든 항목의 번호/항목명/상태/상세설명 비교
    _, toggle_label = history_page.get_toggle_all_button_state()
    if toggle_label == "전체 열기":
        history_page.click_toggle_all(expected_next_label="전체 닫기")

    detail_items = history_page.get_detail_items()
    detail_map = {item["no"]: item for item in detail_items if item["no"] is not None}
    result_map = {row["no"]: row for row in result_rows}

    assert len(detail_items) == len(result_rows), (
        f"상세내역 항목 개수({len(detail_items)}개) != 점검결과 탭 항목 개수({len(result_rows)}개)"
    )

    errors = []
    for no, r_row in result_map.items():
        d_item = detail_map.get(no)
        if d_item is None:
            errors.append(f"[{no}번] 점검 상세 내역에서 항목을 찾을 수 없습니다.")
            continue
        if d_item["title"] != r_row["title"]:
            errors.append(f"[{no}번] 항목명 불일치: 상세='{d_item['title']}' != 결과='{r_row['title']}'")
        if d_item["status"] != r_row["status"]:
            errors.append(f"[{no}번 {r_row['title']}] 결과 불일치: 상세='{d_item['status']}' != 결과='{r_row['status']}'")
        if not d_item["description"]:
            errors.append(f"[{no}번 {r_row['title']}] 상세 설명이 비어 있습니다.")

    # 점검결과 '상세보기' 모달 진단결과와 상세내역 아코디언 설명 대조
    # (점검상세내역에는 백신 세부 상태 등 추가 하위 줄이 포함될 수 있으므로 포함 여부로 검증)
    for no, res_desc in sampled_descs.items():
        d_item = detail_map.get(no)
        if not d_item or not d_item.get("description"):
            errors.append(f"[{no}번] 상세 설명 비교 대상이 없습니다.")
            continue
        norm_res = _normalize_ws(res_desc)
        norm_hist = _normalize_ws(d_item["description"])
        if norm_res not in norm_hist:
            errors.append(f"[{no}번] 진단결과 설명 불일치:\n  점검결과='{norm_res}'\n  상세내역='{norm_hist}'")

    assert not errors, "\n".join(errors)
    print(f">>> [상세내역 정합성] 전체 {len(detail_items)}개 항목 상태/항목명 및 대표 {len(sampled_descs)}건 상세설명 100% 일치!")


@pytest.mark.app_check
@pytest.mark.app_history
def test_history_detail_toggle_all_and_individual(history_test_session):
    """
    [요구사항 7]
    '전체 열기' / '전체 닫기' 토글 버튼 및 개별 행 아코디언 토글 기능 동작 검증
    """
    history_page: HistoryPage = history_test_session["history_page"]
    history_page.ensure_latest_detail_view()

    # 시작 상태 정규화: 모두 닫힌 상태('전체 열기' 버튼 상태)로 맞춤
    _, cur_label = history_page.get_toggle_all_button_state()
    if cur_label == "전체 닫기":
        history_page.click_toggle_all(expected_next_label="전체 열기")

    closed_items = history_page.get_detail_items()
    assert closed_items, "상세 내역 아코디언 항목이 없습니다."
    assert all((not it["is_open"]) and it["arrow"] == "▼" and it["description"] is None for it in closed_items), (
        "초기 닫힘 상태에서 열려 있는 항목이 있습니다."
    )

    # 1. '전체 열기' 클릭 -> '전체 닫기' 전환 및 모든 항목 열림 확인
    next_label = history_page.click_toggle_all(expected_next_label="전체 닫기")
    assert next_label == "전체 닫기", f"'전체 열기' 클릭 후 버튼 라벨 불일치: '{next_label}'"

    opened_items = history_page.get_detail_items()
    assert len(opened_items) == len(closed_items)
    not_opened = [it["no"] for it in opened_items if not (it["is_open"] and it["arrow"] == "▲" and it["description"])]
    assert not not_opened, f"'전체 열기' 클릭 후 열리지 않은 항목이 있습니다: {not_opened}"
    print(f"\n>>> [토글 검증] '전체 열기' 클릭 -> {len(opened_items)}개 전 항목 펼침(▲) 및 상세설명 노출 확인")

    # 2. '전체 닫기' 클릭 -> '전체 열기' 복귀 및 모든 항목 닫힘 확인
    next_label2 = history_page.click_toggle_all(expected_next_label="전체 열기")
    assert next_label2 == "전체 열기", f"'전체 닫기' 클릭 후 버튼 라벨 불일치: '{next_label2}'"

    reclosed_items = history_page.get_detail_items()
    still_open = [it["no"] for it in reclosed_items if it["is_open"] or it["arrow"] != "▼" or it["description"] is not None]
    assert not still_open, f"'전체 닫기' 클릭 후 닫히지 않은 항목이 있습니다: {still_open}"
    print(f">>> [토글 검증] '전체 닫기' 클릭 -> {len(reclosed_items)}개 전 항목 접힘(▼) 확인")

    # 3. 개별 행 아코디언 토글 동작 확인 (1번 항목만 열기 -> 다시 닫기)
    first_no = reclosed_items[0]["no"]
    assert first_no is not None
    history_page.click_item_accordion(first_no)
    after_single_open = history_page.get_detail_items()
    assert after_single_open[0]["is_open"] and after_single_open[0]["arrow"] == "▲" and after_single_open[0]["description"], (
        f"{first_no}번 개별 아코디언 클릭 후 항목이 열리지 않았습니다."
    )
    others_opened = [it["no"] for it in after_single_open[1:] if it["is_open"]]
    assert not others_opened, f"개별 아코디언 클릭 시 다른 항목까지 열렸습니다: {others_opened}"

    history_page.click_item_accordion(first_no)
    after_single_close = history_page.get_detail_items()
    assert (not after_single_close[0]["is_open"]) and after_single_close[0]["arrow"] == "▼" and after_single_close[0]["description"] is None, (
        f"{first_no}번 개별 아코디언 재클릭 후 항목이 닫히지 않았습니다."
    )
    print(f">>> [토글 검증] {first_no}번 개별 행 아코디언 열기/닫기 동작 확인 완료!")

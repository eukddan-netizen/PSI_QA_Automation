"""
[대분류: 점검결과 탭] 상단 방패/점수, 사용자 정보, 서버 정책 정합성 및 요약 카운트 검증
- Row 66~68 및 점검결과 탭 공통 요구사항 1~4번
"""

import re
import pytest

from common.os_utils import get_current_machine_ips
from pages.client.inspection_result_page import InspectionResultPage


def _normalize_item_title(name: str) -> str:
    """항목명 비교를 위해 [선택]/[권고] 접두어 제거 및 SW/소프트웨어, HW/하드웨어 표기를 정규화합니다."""
    text = re.sub(r"\[(선택|권고)\]", "", name or "")
    text = text.lower()
    text = text.replace("소프트웨어", "sw").replace("하드웨어", "hw")
    text = re.sub(r"\s+", " ", text).strip()
    return text


@pytest.mark.app_check
@pytest.mark.app_result
def test_010_점검결과_방패_점수_정합성(result_tab_session, server_result_data):
    """
    [APP-04-01-010] 점검결과 탭 방패 아이콘·종합 점수 및 서버 안전기준점수 정합성 검증
    """
    result_page: InspectionResultPage = result_tab_session["result_page"]
    main_inspection_info = result_tab_session["main_inspection_info"]

    stats = result_page.get_summary_stats()
    rows = result_page.get_all_result_rows()
    shield = result_page.get_shield_visual_state()

    score_num = stats.get("score_num")
    assert score_num is not None, f"점검결과 탭에서 종합 점수를 읽을 수 없습니다: {stats}"

    safety_score = server_result_data["safety_score"]
    item_map = server_result_data["active_item_map"]

    # 서버 정책 배점 기준 예상 점수 산출 (안전 판정 항목 배점 합산)
    expected_score = sum(item_map[r["no"]]["score"] for r in rows if r["status"] == "안전" and r["no"] in item_map)
    expected_shield = "양호" if score_num >= safety_score else "위험"

    print(
        f"\n>>> [방패/점수 검증] 점검결과={score_num}점, 메인={main_inspection_info.get('score')}점, "
        f"정책계산={expected_score}점, 안전기준점수={safety_score}점, "
        f"기대방패='{expected_shield}', 실제방패='{shield}'"
    )

    assert score_num == main_inspection_info.get("score"), (
        f"점검결과 탭 점수({score_num}점)와 메인 탭 점수({main_inspection_info.get('score')}점)가 다릅니다."
    )
    assert score_num == expected_score, (
        f"점검결과 탭 점수({score_num}점)가 서버 정책 배점 합산({expected_score}점)과 일치하지 않습니다."
    )
    assert shield["state"] == expected_shield, (
        f"안전기준점수({safety_score}점) 대비 종합 점수({score_num}점)의 기대 방패 상태는 '{expected_shield}'이나 "
        f"실제 화면 방패 상태는 '{shield['state']}'입니다. ({shield})"
    )


@pytest.mark.app_check
@pytest.mark.app_result
def test_020_점검결과_사용자정보_서버정합성(result_tab_session, server_result_data):
    """
    [APP-04-01-020] 점검결과 탭 사용자 정보와 메인 탭 및 관리자 웹 보고서 일치 검증
    메인 탭 및 관리자 웹(/pcsafe) 보고서 반영 데이터 일치 검증
    """
    result_page: InspectionResultPage = result_tab_session["result_page"]
    main_user = result_tab_session["main_user_info"]
    result_user = result_page.get_user_info()
    result_stats = result_page.get_summary_stats()

    print(f"\n>>> [점검결과 탭 사용자 정보] {result_user}")
    print(f">>> [메인 탭 사용자 정보]     {main_user}")

    errors = []
    for field in ("os", "department", "username", "ip", "last_inspection_time"):
        r_val = result_user.get(field)
        m_val = main_user.get(field)
        if not r_val:
            errors.append(f"점검결과 탭에서 '{field}' 값을 읽지 못했습니다.")
        elif r_val != m_val:
            errors.append(f"메인 탭과 '{field}' 불일치: 점검결과='{r_val}' != 메인='{m_val}'")

    server_user = server_result_data["server_user"]
    local_ips = get_current_machine_ips()
    print(f">>> [관리자 웹(/pcsafe) 사용자 정보] {server_user}")

    if result_user.get("department") != server_user.get("department"):
        errors.append(f"서버와 부서명 불일치: 앱='{result_user.get('department')}' != 서버='{server_user.get('department')}'")
    if result_user.get("username") != server_user.get("username"):
        errors.append(f"서버와 사용자명 불일치: 앱='{result_user.get('username')}' != 서버='{server_user.get('username')}'")
    if result_user.get("ip") != server_user.get("ip"):
        errors.append(f"서버와 IP 불일치: 앱='{result_user.get('ip')}' != 서버='{server_user.get('ip')}'")
    if result_user.get("ip") not in local_ips:
        errors.append(f"앱 사용자 IP('{result_user.get('ip')}')가 로컬 IP 목록({local_ips})에 없습니다.")

    server_os = server_user.get("os", "")
    server_sp = server_user.get("sp", "")
    app_os = result_user.get("os", "")
    if server_os and server_os not in app_os:
        errors.append(f"OS 정보 불일치: 서버 '{server_os}' 미포함 (앱: '{app_os}')")
    if server_sp and server_sp not in app_os:
        errors.append(f"OS SP 불일치: 서버 '{server_sp}' 미포함 (앱: '{app_os}')")

    if result_user.get("last_inspection_time") != server_user.get("last_inspection_time"):
        errors.append(
            f"최근점검일시 서버 보고서 동기화 불일치: 앱='{result_user.get('last_inspection_time')}' "
            f"!= 서버='{server_user.get('last_inspection_time')}'"
        )
    if result_stats.get("score_text") and server_user.get("score") != result_stats.get("score_text"):
        errors.append(
            f"점검 점수 서버 보고서 동기화 불일치: 앱='{result_stats.get('score_text')}' "
            f"!= 서버='{server_user.get('score')}'"
        )

    assert not errors, "\n".join(errors)


@pytest.mark.app_check
@pytest.mark.app_result
def test_030_서버정책_항목정합성_및_조치버튼(result_tab_session, server_result_data):
    """
    [APP-04-01-030] 관리자 웹 부서 적용 정책과 점검결과 항목·배점·조치 버튼 노출 검증
    - 사용자 부서 -> 좌측 부서트리 적용 정책 확인 -> 정책 선택 -> 우측 테이블 정책 추출
    - 활성 점검 항목 개수/번호/항목명 일치
    - 점수 배점 합산 일치
    - 취약 시 버튼 표시 설정('조치' vs '도움말')과 테이블 내 '조치' 버튼 노출 여부 1:1 전수 일치
    """
    result_page: InspectionResultPage = result_tab_session["result_page"]
    stats = result_page.get_summary_stats()
    rows = result_page.get_all_result_rows()

    dept = server_result_data["department"]
    policy_name = server_result_data["policy_name"]
    active_items = server_result_data["active_items"]
    active_map = server_result_data["active_item_map"]

    print(f"\n>>> [정책 정합성 검증] 부서='{dept}', 적용 정책='{policy_name}', 활성 항목={len(active_items)}개")

    assert len(rows) == len(active_items), (
        f"점검결과 항목 수({len(rows)}개)와 서버 활성 정책 항목 수({len(active_items)}개)가 다릅니다."
    )

    # 점수 배점 합산 검증
    earned_score = sum(active_map[r["no"]]["score"] for r in rows if r["status"] == "안전" and r["no"] in active_map)
    assert stats.get("score_num") == earned_score, (
        f"배점 기반 계산 점수({earned_score}점)와 화면 점수({stats.get('score_num')}점) 불일치"
    )

    errors = []
    for row in rows:
        no = row["no"]
        if no not in active_map:
            errors.append(f"[{no}번] 서버 활성 정책에 존재하지 않는 항목입니다: {row}")
            continue

        pol = active_map[no]
        if _normalize_item_title(row["title"]) not in _normalize_item_title(pol["name"]):
            errors.append(f"[{no}번] 항목명 불일치: 앱='{row['title']}', 서버='{pol['name']}'")

        if not row["has_detail_button"]:
            errors.append(f"[{no}번 {row['title']}] '상세보기' 버튼이 누락되었습니다.")

        # 취약 시 버튼 표시('조치' vs '도움말') 일치 검증
        if row["status"] == "취약":
            if pol["vuln_button"] == "조치" and not row["has_action_button"]:
                errors.append(
                    f"[{no}번 {row['title']}] 서버 정책은 취약 시 '조치'이나 결과 테이블에 '조치' 버튼이 없습니다."
                )
            elif pol["vuln_button"] == "도움말" and row["has_action_button"]:
                errors.append(
                    f"[{no}번 {row['title']}] 서버 정책은 취약 시 '도움말'이나 결과 테이블에 '조치' 버튼이 노출되었습니다."
                )
        else:
            if row["has_action_button"]:
                errors.append(
                    f"[{no}번 {row['title']}] 상태가 '{row['status']}'인데 '조치' 버튼이 노출되었습니다."
                )

    assert not errors, "\n".join(errors)
    print(f">>> [정책 정합성 검증 완료] {len(rows)}개 전 항목의 번호/항목명/배점/취약시버튼('조치'/'도움말') 100% 일치!")


@pytest.mark.app_check
@pytest.mark.app_result
def test_040_상단요약건수_결과테이블_일치(result_tab_session):
    """
    [APP-04-01-040] 점검결과 상단 요약 건수(전체·안전·취약·불가)와 테이블 행 개수 일치 검증
    """
    result_page: InspectionResultPage = result_tab_session["result_page"]
    stats = result_page.get_summary_stats()
    rows = result_page.get_all_result_rows()

    actual_total = len(rows)
    actual_safe = sum(1 for r in rows if r["status"] == "안전")
    actual_vuln = sum(1 for r in rows if r["status"] == "취약")
    actual_cannot = sum(1 for r in rows if r["status"] == "점검불가")
    unique_nos = {r["no"] for r in rows}

    print(
        f"\n>>> [카운트 검증] 상단요약=({stats.get('total_num')}/{stats.get('safe_num')}/"
        f"{stats.get('vulnerable_num')}/{stats.get('cannot_check_num')}) vs "
        f"테이블실측=({actual_total}/{actual_safe}/{actual_vuln}/{actual_cannot})"
    )

    assert actual_total > 0, "점검결과 테이블에 파싱된 항목이 없습니다."
    assert len(unique_nos) == actual_total, f"테이블에 중복된 항목 번호가 있습니다: 총 {actual_total}행 중 고유 {len(unique_nos)}개"
    assert actual_safe + actual_vuln + actual_cannot == actual_total, (
        f"미분류 상태 항목이 존재합니다: 전체={actual_total}, 안전={actual_safe}, 취약={actual_vuln}, 점검불가={actual_cannot}"
    )

    assert stats.get("total_num") == actual_total, f"전체 건수 불일치: 요약={stats.get('total_num')} != 테이블={actual_total}"
    assert stats.get("safe_num") == actual_safe, f"안전 건수 불일치: 요약={stats.get('safe_num')} != 테이블={actual_safe}"
    assert stats.get("vulnerable_num") == actual_vuln, f"취약 건수 불일치: 요약={stats.get('vulnerable_num')} != 테이블={actual_vuln}"
    assert stats.get("cannot_check_num") == actual_cannot, f"점검불가 건수 불일치: 요약={stats.get('cannot_check_num')} != 테이블={actual_cannot}"

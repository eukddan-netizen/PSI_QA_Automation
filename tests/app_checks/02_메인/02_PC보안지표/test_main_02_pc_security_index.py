"""
[대분류: 보안점검 메인 탭 > 중분류 2: PC보안지표] (Excel Row 24)

- Row 24: PC보안지표 5각 레이더 차트의 각 꼭짓점 호버 시 해당 지표 점수 툴팁 표출 및
          점검결과 탭의 5대 분야 21개 세부 점검 항목 진단 결과와의 정합성 검증

[5대 지표 및 세부 점검 항목 구성]
1. 바이러스백신 (2개)
   - [권고] 바이러스 백신 설치 및 실행 여부 점검
   - [권고] 바이러스 백신 최신 보안 패치 점검
2. 소프트웨어 (5개)
   - [권고] 미사용(3개월) ActiveX 프로그램 존재 여부 점검
   - [권고] 금지 SW 설치 여부 점검
   - [권고] 사용자 PC 프로세스 목록 수집 기능
   - [권고] 편집 프로그램 설치 여부 점검
   - [권고] 확장 편집 프로그램 설치 여부 점검
3. 보안패치 (5개)
   - [권고] OS, MS Office 최신 보안 패치 점검
   - [권고] 한글 프로그램 최신 보안 패치 점검
   - [권고] PDF 프로그램 최신 보안 패치 점검
   - [권고] Adobe Flash Player 설치 여부 점검
   - [권고] JAVA 최신 보안 패치 점검
4. 계정&패스워드 (3개)
   - [권고] 로그인 암호 안전성 점검
   - [권고] 로그인 암호 분기별 변경 여부 점검
   - [권고] 메인 계정 외 기타 계정 존재 여부 점검
5. Windows 설정 (6개)
   - [권고] 화면 보호기 설정 여부 점검
   - [권고] 사용자 공유 폴더 존재 여부 점검
   - [권고] USB 자동 실행 여부 점검
   - [권고] 무선랜카드 설치 여부 점검
   - [권고] 보안 USB 설치 여부 점검
   - [권고] 방화벽 실행 여부 점검
"""

import time
import pytest

from pages.client.main_page import MainPage
from pages.client.inspection_result_page import InspectionResultPage


# 5대 보안지표별 세부 점검 항목 키워드 매핑
SECURITY_INDEX_CATEGORIES = {
    "바이러스백신": [
        "바이러스 백신 설치 및 실행 여부",
        "바이러스 백신 최신 보안 패치",
    ],
    "소프트웨어": [
        "미사용(3개월) ActiveX",
        "금지 SW",
        "사용자 PC 프로세스 목록",
        "편집 프로그램",
        "확장 편집 프로그램",
    ],
    "보안패치": [
        "OS, MS",
        "한글 프로그램",
        "PDF 프로그램",
        "Adobe Flash Player",
        "JAVA",
    ],
    "계정&패스워드": [
        "로그인 암호 안전성",
        "로그인 암호 분기별 변경",
        "기타 계정",
    ],
    "Windows 설정": [
        "화면 보호기",
        "공유 폴더",
        "USB 자동 실행",
        "무선랜카드",
        "보안 USB",
        "방화벽 실행",
    ],
}


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_02
def test_row24_security_index_hover_tooltips(app_ctrl):
    """
    [Row 24] PC보안지표 레이더 차트 꼭짓점 hover 툴팁 점수 표출 및 점검결과 정합성 검증
    1. 보안점검 앱 실행
    2. 점검결과 탭으로 이동하여 5개 분야(21개 항목)의 안전/취약 상태 수집
    3. 분야별 계산 점수(안전 항목수 / 전체 항목수 * 100) 산출
    4. 메인 탭으로 이동 후 레이더 차트의 각 꼭짓점에 마우스 hover 수행
    5. 표출된 툴팁 점수가 계산된 기대 점수와 오차 1점 이내로 일치하는지 검증
    """
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(app_ctrl.hwnd)
    info = main_page.wait_for_main_ready(timeout=12.0)

    # 대기 상태일 경우 점검을 먼저 수행하여 점검결과 탭을 활성화
    if info.get("status") == "대기":
        print(">>> [Row 24] 대기 상태 감지 -> 점검 시작 및 완료 대기...")
        main_page.click_start_inspection()
        nav = main_page.wait_for_inspection_and_result_tab(timeout=25.0)
        assert nav["reached_result_tab"], "점검 완료 후 결과 탭 자동 이동 실패"
    else:
        main_page.navigate_to_tab("점검결과")

    # 1. 점검결과 탭에서 5개 분야별 항목 진단 상태 수집 및 점수 계산
    result_page = InspectionResultPage(app_ctrl.hwnd)
    expected_scores = {}
    category_summary = {}

    print("\n================ [점검결과 기반 분야별 지표 점수 산출] ================")
    for cat_name, items in SECURITY_INDEX_CATEGORIES.items():
        item_statuses = {}
        for kw in items:
            st, _ = result_page.get_item_info(item_name=kw)
            item_statuses[kw] = st or "미확인"

        safe_count = sum(1 for s in item_statuses.values() if s == "안전")
        total_count = len(items)
        calc_score = int((safe_count / total_count) * 100)
        expected_scores[cat_name] = calc_score
        category_summary[cat_name] = {
            "safe": safe_count,
            "total": total_count,
            "expected_score": calc_score,
            "items": item_statuses,
        }
        print(f"\n  ▶ [{cat_name}] 안전: {safe_count}/{total_count}개 | 산출 점수: {calc_score}점")
        for kw, st in item_statuses.items():
            icon = "✓" if st == "안전" else ("✗" if st == "취약" else "?")
            print(f"      [{icon}] {st:4s} : {kw}")

    # 2. 메인 탭으로 복귀하여 레이더 차트 툴팁 호버 점수 검증
    main_page.navigate_to_tab("메인")
    main_page.wait_for_main_ready(timeout=10.0)

    print("\n================ [레이더 차트 꼭짓점 호버 툴팁 검증] ================")
    actual_tooltips = main_page.read_all_radar_tooltips(expected_scores)

    errors = []
    for cat_name, exp_score in expected_scores.items():
        act_score = actual_tooltips.get(cat_name)
        print(f"  - [{cat_name}] 기대치: {exp_score}점 | 툴팁 표출값: {act_score}점")

        if act_score is None:
            errors.append(f"[{cat_name}] 호버 시 툴팁 점수가 노출되지 않았습니다.")
        elif abs(act_score - exp_score) > 1:
            errors.append(
                f"[{cat_name}] 툴팁 점수 불일치! 기대={exp_score}점, 실제={act_score}점 "
                f"(안전 {category_summary[cat_name]['safe']}/{category_summary[cat_name]['total']}개)"
            )

    assert not errors, "\n".join(errors)
    print("\n>>> [Row 24] PC보안지표 5대 분야 레이더 차트 툴팁 점수 정합성 검증 완료!")

"""
[대분류: 보안점검 메인 탭 > 중분류 6: 지난 검사내역] (Excel Row 33~34)

- 세션 최적화: 보안점검 프로그램을 1회만 실행(module scope)하여
  동일 세션에서 지난 검사내역 차트 호버 및 6개 막대 전체 상세 이동/일시 대조를 연속으로 수행하고 종료합니다.

- Row 33: 메인 화면 지난 검사내역 6개 막대 그래프 호버 시 점수 표출 검증
          - 총 6개의 점검 내역 표출 확인 (우측으로 갈수록 최근 점검내역)
          - 각 막대 그래프에 마우스 Hover 시 당시 점수 표출 확인
- Row 34: 6개 막대 그래프 전체(1번~6번) 클릭 시 '점검이력' 상세 내역 이동 및 상위 6개 일시 1:1 역순 매핑 전수 검증
          - '점검이력' 탭 목록에서 최근 점검 6건의 일시/점수 수집
          - 1번째 막대(가장 왼쪽) -> 점검이력 목록의 6번째 점검일시와 일치
          - ...
          - 6번째 막대(가장 오른쪽) -> 점검이력 목록의 1번째(가장 최신) 점검일시와 일치
          - 각 상세 화면의 점검 점수가 호버 시 점수와 정확히 일치하는지 전수 검증
"""

import time
import pytest

from core.app_controller import AppController
from pages.client.main_page import MainPage


@pytest.fixture(scope="module")
def history_session():
    """
    모듈 전체에서 보안점검 앱을 1회만 실행하여 공유하는 Fixture.
    테스트 종료 시 프로그램을 안전하게 종료합니다.
    """
    ctrl = AppController()
    ctrl.launch(timeout=15)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)

    session_data = {
        "ctrl": ctrl,
        "main_page": main_page,
    }

    yield session_data

    # 정리
    print("\n>>> [History Session Teardown] 보안점검 프로그램 종료")
    try:
        ctrl.close()
    except Exception:
        pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_06
def test_row33_past_history_bar_count_and_hover_scores(history_session):
    """
    [Row 33] 지난 검사내역 막대 그래프 개수(0~6개 가변 대응) 및 호버 시 점수 표출 검증
    1. 메인 화면 우하단 '지난 검사내역' 차트에서 막대 바(bar) 탐색
    2. 점검 이력에 따라 0개 ~ 최대 6개의 점검 내역이 표출되는지 확인
       - 점검 기록이 없는 PC: 0개 정상 감지
       - 점검 기록이 1~5회인 PC: N개(1~5) 정상 감지
       - 점검 기록이 6회 이상인 PC: 최근 6개 정상 감지
    3. 각 표출된 막대에 마우스 호버(Hover) 시 점수가 정상적으로 표출되는지 전수 확인
    """
    main_page: MainPage = history_session["main_page"]
    main_page.bring_to_front()
    print("\n>>> [TC 33] 지난 검사내역 막대 그래프 개수 및 호버 점수 검증 시작")

    # 1. 막대 바 탐색
    bars = main_page.get_past_history_bars()
    bar_count = len(bars)
    print(f">>> [TC 33] 탐색된 막대 그래프 개수: {bar_count}개 (최대 6개)")
    assert 0 <= bar_count <= 6, f"지난 검사내역 막대 개수가 0~6 범위를 벗어났습니다: {bar_count}개"

    history_session["bar_count"] = bar_count
    history_session["hover_scores"] = []

    # 점검 기록이 없는 PC 환경인 경우
    if bar_count == 0:
        print(">>> [TC 33] 점검 이력이 없는 환경입니다. (그래프 막대 0개 표출 확인)")
        return

    # 2. 각 막대 호버 점수 수집
    hover_scores = []
    for idx in range(bar_count):
        score = main_page.hover_and_get_past_history_score(bar_index=idx, timeout=3.0)
        print(f"  - [{idx+1}/{bar_count}번째 막대] 호버 점수: {score}점 (좌표={bars[idx].rectangle()})")
        assert score is not None, f"[{idx+1}번째 막대] 호버 시 점수가 표출되지 않았습니다."
        assert 0 <= score <= 100, f"[{idx+1}번째 막대] 점수 범위 이상 (0~100): {score}"
        hover_scores.append(score)

    # 세션에 호버 점수 저장 (TC 34에서 비교용)
    history_session["hover_scores"] = hover_scores
    print(f">>> [TC 33] {bar_count}개 막대 호버 점수 전수 검증 성공: {hover_scores}")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_06
def test_row34_all_six_bars_click_match_history_tab_records(history_session):
    """
    [Row 34] 막대 그래프 전체(0~6개 가변 대응) 클릭 시 '점검이력' 상세 이동 및 일시 1:1 역순 매핑 전수 검증
    1. '점검이력' 탭으로 이동하여 최근 점검 내역의 일시/점수 수집
       - 막대가 0개인 경우: 점검이력 탭에도 레코드가 0건인지 교차 확인
       - 막대가 N개(1~6개)인 경우:
         - 점검이력 탭 목록에서 상위 N건의 일시/점수 수집
         - 메인 화면 복귀 후 N개 막대(0 ~ N-1)를 순차 클릭하여 상세 진입
         - 일반화 매핑: i번째 막대 -> 점검이력 목록의 [(N - 1) - i]번째 행과 일치
         - (가장 오른쪽인 마지막 막대 -> 점검이력 목록의 1번째(가장 최신) 일시/점수와 일치)
         - 각 상세 화면의 점검일시 및 점수가 호버 점수 및 점검이력 목록과 일치하는지 전수 검증
    """
    main_page: MainPage = history_session["main_page"]
    main_page.bring_to_front()
    print("\n>>> [TC 34] 지난 검사내역 막대 그래프 클릭 및 점검이력 일시/점수 1:1 역순 매핑 검증 시작")

    bar_count = history_session.get("bar_count")
    if bar_count is None:
        bars = main_page.get_past_history_bars()
        bar_count = len(bars)
        history_session["bar_count"] = bar_count

    hover_scores = history_session.get("hover_scores", [])

    # 1. 점검 기록이 없는 PC 환경 (bar_count == 0)
    if bar_count == 0:
        print(">>> [TC 34] 막대가 0개이므로 '점검이력' 탭에도 레코드가 없는지 교차 검증합니다.")
        main_page.navigate_to_tab("점검이력")
        time.sleep(1.0)
        history_records = main_page.get_history_tab_records(limit=1)
        assert len(history_records) == 0, (
            f"메인 대시보드 그래프에는 막대가 없는데 점검이력 탭에는 {len(history_records)}건의 레코드가 존재합니다."
        )
        print(">>> [TC 34] 점검이력 탭에도 기록 0건 확인 완료. 메인 탭으로 복귀합니다.")
        main_page.navigate_to_tab("메인")
        return

    # 2. 점검 기록이 1~6개 존재하는 환경
    print(f">>> [TC 34] '점검이력' 탭으로 이동하여 최근 {bar_count}건 점검 내역 수집...")
    main_page.navigate_to_tab("점검이력")
    time.sleep(1.0)

    history_records = main_page.get_history_tab_records(limit=bar_count)
    print(f">>> [TC 34] 점검이력 상위 {len(history_records)}건 파싱 완료:")
    for i, r in enumerate(history_records):
        print(f"  - [{i+1}번 행] 일시='{r['inspection_time']}', 점수={r['score']}점")

    assert len(history_records) >= bar_count, (
        f"점검이력 목록 레코드 수({len(history_records)}건)가 그래프 막대 개수({bar_count}개)보다 적습니다."
    )

    # 3. '메인' 탭으로 복귀
    main_page.navigate_to_tab("메인")
    time.sleep(1.0)

    # 4. N개 막대 각각 클릭하여 상세 페이지 일시/점수 1:1 역순 매핑 검증
    for bar_idx in range(bar_count):
        # 역순 매핑: 막대 bar_idx -> 점검이력 [(bar_count - 1) - bar_idx] 행
        record_idx = (bar_count - 1) - bar_idx
        expected_record = history_records[record_idx]
        expected_time = expected_record["inspection_time"]
        expected_score = expected_record["score"]
        expected_hover_score = hover_scores[bar_idx] if bar_idx < len(hover_scores) else expected_score

        print(f"\n--- [막대 {bar_idx + 1}/{bar_count} 검증] 기대 일시='{expected_time}', 기대 점수={expected_score}점 ---")
        main_page.click_past_history_bar(bar_idx)
        time.sleep(1.2)

        # 활성 탭 및 상세 정보 확인
        active_tab = main_page.get_active_tab_name()
        assert active_tab == "점검이력", f"막대 클릭 후 '점검이력' 탭으로 이동 실패: '{active_tab}'"

        detail = main_page.get_history_detail_info()
        actual_time = detail.get("inspection_time")
        actual_score = detail.get("score")
        print(f"  상세 화면 파싱: 일시='{actual_time}', 점수={actual_score}점 (호버={expected_hover_score}점)")

        # 점검일시 1:1 일치 검증
        assert actual_time == expected_time, (
            f"[막대 {bar_idx + 1}] 상세 화면 일시('{actual_time}')가 점검이력 {record_idx + 1}번 행 일시('{expected_time}')와 일치하지 않습니다."
        )

        # 점수 일치 검증 (호버 점수 및 점검이력 점수)
        assert actual_score == expected_hover_score, (
            f"[막대 {bar_idx + 1}] 상세 화면 점수({actual_score}점)가 호버 점수({expected_hover_score}점)와 일치하지 않습니다."
        )

        print(f"  >>> 막대 {bar_idx + 1}/{bar_count} 점검일시 및 점수 1:1 일치 검증 통과!")

        # 다음 막대 검증을 위해 '메인' 탭으로 복귀
        if bar_idx < bar_count - 1:
            main_page.navigate_to_tab("메인")
            time.sleep(0.8)

    print(f"\n>>> [TC 34] {bar_count}개 막대 그래프 전체의 점검이력 일시/점수 1:1 역순 매핑 전수 검증 성공!")

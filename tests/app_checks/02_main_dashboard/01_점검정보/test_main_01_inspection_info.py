"""
[대분류: 보안점검 메인 탭 > 중분류 1: 점검 정보] (Excel Row 20~23)

- Row 20: 정책 수정/미점검 대기 상태 -> 회색 방패('대기'), '취약점 검사 필요' / '검사를 진행해 주십시오' 및 서버 안전기준점수 연동 검증
- Row 21: 안전 기준 점수(10점) 하향 후 점검 완료 -> 점수 >= 안전기준점수, 파란 방패('양호'), 안전기준점수 10점 및 즉시 닫기 검증
- Row 22: 안전 기준 점수(100점) 상향 후 점검 완료 -> 점수 < 안전기준점수, 빨간 방패('위험'), 안전기준점수 100점 및 닫기(X) 사용 제한 경고 팝업 검증
- Row 23: '점검 시작' 버튼 클릭 -> '점검' 탭 진행 후 '점검결과' 탭 자동 이동 검증
"""

import time
import pytest

from pages.inspection_result_page import InspectionResultPage
from pages.main_page import MainPage


POLICY_NAME = "t1"
ITEM_1_NO = 1
ITEM_1_NAME = "[권고] 바이러스 백신 설치 및 실행 여부 점검"
ITEM_2_NO = 2
ITEM_2_NAME = "[권고] 바이러스 백신 최신 보안 패치 점검"


def _run_scan_and_return_to_main(app_ctrl, expected_safety_score: int) -> MainPage:
    """트레이로 앱 실행 후 정책 반영 안전기준점수를 1차 확인하고, 점검 완료 뒤 메인 탭으로 복귀"""
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 핸들을 획득하지 못했습니다."

    main_page = MainPage(app_ctrl.hwnd)
    pre_info = main_page.wait_for_main_ready(timeout=12.0)
    print(f">>> [점검 전 메인 정보] {pre_info}")
    assert pre_info["safety_score"] == expected_safety_score, (
        f"메인 화면 안전기준점수가 서버 정책({expected_safety_score}점)과 다릅니다: {pre_info['safety_score']}"
    )

    main_page.click_start_inspection()
    nav = main_page.wait_for_inspection_and_result_tab(timeout=25.0)
    assert nav["reached_result_tab"], (
        f"점검 시작 후 '점검결과' 탭으로 이동하지 못했습니다. (감지된 탭: {nav['tabs_seen']})"
    )

    main_page.navigate_to_tab("메인")
    main_page.wait_for_main_ready(timeout=10.0)
    return main_page


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
def test_row20_shield_status_no_history(pcsafe_manage_page, app_ctrl):
    """[Row 20] 정책 변경(1번=2점, 2번=0점) 후 방패 '대기', 점검 필요 문구 및 서버 안전기준점수 연동 검증"""
    pcsafe_manage_page.goto_pcsafe_manage()
    pcsafe_manage_page.select_policy(POLICY_NAME)

    orig_1 = pcsafe_manage_page.get_item_score(ITEM_1_NO, ITEM_1_NAME)
    orig_2 = pcsafe_manage_page.get_item_score(ITEM_2_NO, ITEM_2_NAME)
    server_safety_score = pcsafe_manage_page.get_safety_score()

    # 이미 (2, 0) 상태였다면 다른 값으로 한 번 적용해 정책 변경 이벤트가 반드시 발생하도록 보장
    if (orig_1, orig_2) == (2, 0):
        pcsafe_manage_page.set_item_score(ITEM_1_NO, 1, ITEM_1_NAME)
        pcsafe_manage_page.set_item_score(ITEM_2_NO, 1, ITEM_2_NAME)
        pcsafe_manage_page.save_and_apply_policy()

    try:
        pcsafe_manage_page.set_item_score(ITEM_1_NO, 2, ITEM_1_NAME)
        pcsafe_manage_page.set_item_score(ITEM_2_NO, 0, ITEM_2_NAME)
        pcsafe_manage_page.save_and_apply_policy()

        app_ctrl.launch(timeout=15)
        assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

        main_page = MainPage(app_ctrl.hwnd)
        info = main_page.wait_for_main_ready(timeout=12.0)
        shield = main_page.get_shield_visual_state()
        print(f">>> [Row 20 대기 상태] info={info}")
        print(f">>> [Row 20 방패 색상] shield={shield}")

        assert info["status"] == "대기", f"기대 상태는 '대기'이나 실제는 '{info['status']}'입니다. ({info['joined_text']})"
        assert info["need_scan_text"], f"'취약점 검사 필요 / 검사를 진행해 주십시오' 문구가 노출되지 않았습니다: {info['joined_text']}"
        assert info["safety_score"] == server_safety_score, (
            f"화면 안전기준점수({info['safety_score']}점)가 서버 설정({server_safety_score}점)과 일치하지 않습니다."
        )
        assert shield["state"] == "대기", f"대기 상태의 회색 방패가 아닙니다: {shield}"
    finally:
        app_ctrl.close()
        if (orig_1, orig_2) != (2, 0):
            pcsafe_manage_page.goto_pcsafe_manage()
            pcsafe_manage_page.select_policy(POLICY_NAME)
            pcsafe_manage_page.set_item_score(ITEM_1_NO, orig_1, ITEM_1_NAME)
            pcsafe_manage_page.set_item_score(ITEM_2_NO, orig_2, ITEM_2_NAME)
            pcsafe_manage_page.save_and_apply_policy()


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
def test_row21_shield_status_good(pcsafe_manage_page, app_ctrl):
    """[Row 21] 안전 기준 점수 10점 설정 및 점검 후 점수 >= 안전기준점수, 방패 '양호' 및 무팝업 종료 검증"""
    target_safety = 10
    pcsafe_manage_page.goto_pcsafe_manage()
    pcsafe_manage_page.select_policy(POLICY_NAME)
    pcsafe_manage_page.set_safety_score(target_safety)
    pcsafe_manage_page.save_and_apply_policy()

    main_page = _run_scan_and_return_to_main(app_ctrl, expected_safety_score=target_safety)

    info = main_page.get_inspection_info()
    shield = main_page.get_shield_visual_state()
    print(f">>> [Row 21 안전 상태] info={info}")
    print(f">>> [Row 21 방패 색상] shield={shield}")

    assert not info["need_scan_text"], f"점검 완료 후에도 대기 문구가 남아 있습니다: {info['joined_text']}"
    assert info["safety_score"] == target_safety, (
        f"화면 안전기준점수({info['safety_score']}점)가 서버 설정({target_safety}점)과 다릅니다."
    )
    assert info["score"] is not None and info["score"] >= target_safety, (
        f"점검점수({info['score']}점)가 안전기준점수({target_safety}점) 이상이어야 합니다."
    )
    assert info["total_count"] is not None and info["vulnerable_count"] is not None, (
        f"점검 항목 수/취약 건수 파싱 실패: {info['joined_text']}"
    )
    assert info["status"] == "안전", f"기대 상태는 '안전'이나 실제는 '{info['status']}'입니다."
    assert shield["state"] == "양호", f"안전 상태의 파란색('양호') 방패가 아닙니다: {shield}"

    # 안전 기준 점수 충족 시 우상단 X 클릭하면 경고 팝업 없이 즉시 종료되어야 함
    main_page.click_close_button()
    popup = main_page.wait_for_close_warning_popup(timeout=2.0)
    assert popup is None, f"안전 상태에서는 종료 경고 팝업이 뜨지 않아야 합니다: {popup}"

    for _ in range(10):
        if not main_page.is_window_visible():
            break
        time.sleep(0.3)
    assert not main_page.is_window_visible(), "안전 상태에서 X 클릭 후 창이 즉시 닫히지 않았습니다."


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
def test_row22_shield_status_vulnerable_and_close_warning(pcsafe_manage_page, app_ctrl):
    """[Row 22] 안전 기준 점수 100점 설정 및 점검 후 점수 < 안전기준점수, 방패 '위험' 및 X 닫기 경고 팝업 검증"""
    target_safety = 100
    pcsafe_manage_page.goto_pcsafe_manage()
    pcsafe_manage_page.select_policy(POLICY_NAME)
    pcsafe_manage_page.set_safety_score(target_safety)
    pcsafe_manage_page.save_and_apply_policy()

    main_page = _run_scan_and_return_to_main(app_ctrl, expected_safety_score=target_safety)

    info = main_page.get_inspection_info()
    shield = main_page.get_shield_visual_state()
    print(f">>> [Row 22 취약 상태] info={info}")
    print(f">>> [Row 22 방패 색상] shield={shield}")

    assert not info["need_scan_text"], f"점검 완료 후에도 대기 문구가 남아 있습니다: {info['joined_text']}"
    assert info["safety_score"] == target_safety, (
        f"화면 안전기준점수({info['safety_score']}점)가 서버 설정({target_safety}점)과 다릅니다."
    )
    assert info["score"] is not None and info["score"] < target_safety, (
        f"취약 상태 검증을 위해 점검점수({info['score']}점)가 {target_safety}점 미만이어야 합니다."
    )
    assert info["total_count"] is not None and info["vulnerable_count"] is not None, (
        f"점검 항목 수/취약 건수 파싱 실패: {info['joined_text']}"
    )
    assert info["status"] == "취약", f"기대 상태는 '취약'이나 실제는 '{info['status']}'입니다."
    assert shield["state"] == "위험", f"취약 상태의 빨간색('위험') 방패가 아닙니다: {shield}"

    # 안전 기준 점수 미만 시 X 클릭 -> 사용 제한 경고 팝업 노출 및 취소/종료 동작 검증
    main_page.click_close_button()
    popup = main_page.wait_for_close_warning_popup(timeout=4.0)
    assert popup is not None, "안전 기준 점수 미만 상태에서 X 클릭 시 경고 팝업이 노출되어야 합니다."
    assert "안전 기준 점수 미만" in popup["message"], f"경고 문구 불일치: {popup['message']}"
    assert "종료하시겠습니까" in popup["message"], f"종료 확인 문구 불일치: {popup['message']}"
    assert "취소" in popup["buttons"] and "종료" in popup["buttons"], (
        f"팝업 버튼('취소', '종료') 누락: {popup['buttons']}"
    )

    assert main_page.click_popup_button("취소"), "경고 팝업 '취소' 버튼 클릭 실패"
    assert main_page.is_window_visible(), "'취소' 클릭 후 창이 닫히지 않고 유지되어야 합니다."

    main_page.click_close_button()
    popup2 = main_page.wait_for_close_warning_popup(timeout=4.0)
    assert popup2 is not None, "재닫기 시도 시 경고 팝업이 다시 노출되어야 합니다."
    assert main_page.click_popup_button("종료"), "경고 팝업 '종료' 버튼 클릭 실패"

    for _ in range(10):
        if not main_page.is_window_visible():
            break
        time.sleep(0.3)
    assert not main_page.is_window_visible(), "경고 팝업에서 '종료' 클릭 후 창이 닫히지 않았습니다."


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_01
def test_row23_start_inspection_button(app_ctrl):
    """[Row 23] '점검 시작' 버튼 클릭 시 점검 진행 탭 경유 후 '점검결과' 탭으로 이동 검증"""
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(app_ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)
    assert main_page.get_active_tab_name() == "메인", (
        f"초기 활성 탭이 '메인'이 아닙니다: {main_page.get_active_tab_name()}"
    )

    main_page.click_start_inspection()
    nav = main_page.wait_for_inspection_and_result_tab(timeout=25.0)
    print(f">>> [Row 23 탭 전환 결과] {nav}")

    assert nav["reached_result_tab"], (
        f"점검 시작 후 '점검결과' 탭으로 자동 이동하지 않았습니다. (감지된 탭: {nav['tabs_seen']})"
    )

    result_page = InspectionResultPage(app_ctrl.hwnd)
    stats = {}
    for _ in range(10):
        stats = result_page.get_summary_stats()
        if "score_num" in stats and "total_num" in stats:
            break
        time.sleep(0.5)
    print(f">>> [Row 23 점검결과 요약] {stats}")
    assert "score_num" in stats and "total_num" in stats, (
        f"'점검결과' 탭 전환 후 결과 요약이 정상 표시되지 않았습니다: {stats}"
    )

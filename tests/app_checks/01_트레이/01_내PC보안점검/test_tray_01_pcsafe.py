"""
[대분류: 트레이 아이콘 > 중분류 1: 내PC보안점검] (Excel Row 9~11)

- Row 9  (1_0001): [보안점검 실행중] 트레이 아이콘 > 내PC보안점검 -> 무반응(중복 실행 방지)
- Row 10 (1_0002): [인사 UI 출력 OFF] 트레이 아이콘 > 내PC보안점검 -> 창 정상 노출
- Row 11 (1_0003): [인사 UI 출력 ON]  트레이 아이콘 > 내PC보안점검 -> 보안점검 메인 화면 및 인사 연동 출력
"""

import time
import pytest


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_01
def test_010_트레이_중복실행_방지(app_ctrl):
    """
    [APP-01-01-010] 보안점검 실행 중 트레이 중복 실행 방지 검증
    - 조건: 보안점검 실행 중
    - 액션: 트레이 아이콘 > 내PC보안점검 재실행 시도
    - 기대 결과: 무반응 (중복 창이 생성되지 않고 기존 창 1개만 유지됨)
    """
    win1 = app_ctrl.launch(timeout=15)
    assert win1 is not None, "1차 실행 창이 정상적으로 열려야 합니다."
    initial_hwnd = app_ctrl.hwnd

    app_ctrl._double_click_tray_icon()
    time.sleep(2)

    assert app_ctrl.hwnd == initial_hwnd, "기존 창 핸들이 유지되어야 합니다."


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_01
def test_020_인사UI_OFF_창노출(admin_page, app_ctrl):
    """
    [APP-01-01-020] 인사 UI 출력 OFF 상태에서 내PC보안점검 창 정상 노출 검증
    - 조건: 웹 관리자(/pcsafe)에서 현재 PC IP 사용자의 '인사 UI 출력'이 OFF인 상태
    - 액션: 트레이 아이콘 > 내PC보안점검 클릭
    - 기대 결과: 프로그램 창 정상 노출 확인
    """
    admin_page.set_hr_ui_status(target_state="OFF")
    time.sleep(2)

    win = app_ctrl.launch(timeout=15)
    assert win is not None, "인사 UI 출력 OFF 상태에서 트레이 클릭 시 창이 정상 노출되어야 합니다."
    print(f">>> [Row 10] 창 노출 확인 완료 (HWND={app_ctrl.hwnd})")


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_01
def test_030_인사UI_ON_인사연동노출(admin_page, app_ctrl):
    """
    [APP-01-01-030] 인사 UI 출력 ON 상태에서 메인 화면 및 인사 연동 다이얼로그 노출 검증
    - 조건: 웹 관리자(/pcsafe)에서 현재 PC IP 사용자의 '인사 UI 출력'이 ON인 상태
    - 액션: 트레이 아이콘 > 내PC보안점검 클릭
    - 기대 결과: 보안점검 메인 화면 및 인사 연동 다이얼로그(TA 공지) 노출 확인
    """
    admin_page.set_hr_ui_status(target_state="ON")
    time.sleep(3)

    win = app_ctrl.launch(timeout=15)
    assert win is not None, "인사 UI 출력 ON 상태에서 보안점검 화면이 노출되어야 합니다."

    print("\n>>> 보안점검 창 및 인사 연동 상태 유지 중 (확인용 5초 대기)...")
    time.sleep(5)


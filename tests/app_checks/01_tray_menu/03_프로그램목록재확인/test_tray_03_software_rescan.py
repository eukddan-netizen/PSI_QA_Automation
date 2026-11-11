"""
[대분류: 트레이 아이콘 > 중분류 3: 프로그램 목록 재확인] (Excel Row 16)

- Row 16 (3_0001): 트레이 아이콘 > 프로그램 목록 재확인 -> "소프트웨어 목록 재검사를 성공적으로 수행하였습니다." 팝업 확인
"""

import pytest
from common.os_utils import require_admin


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_03
def test_row16_software_rescan(app_ctrl):
    """
    [Row 16: 3_0001]
    - 조건: 정상 동작
    - 액션: 트레이 아이콘 > 프로그램 목록 재확인 클릭
    - 기대 결과: "소프트웨어 목록 재검사를 성공적으로 수행하였습니다." 팝업 출력 확인
    """
    require_admin(
        "보안 에이전트(taAssistant) 트레이 우클릭 메뉴 제어(Windows UIPI 제약 우회)를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    app_ctrl.click_tray_menu_item("프로그램 목록 재확인")
    dialog = app_ctrl.wait_for_tray_dialog(timeout=15.0)
    assert dialog is not None, "프로그램 목록 재확인 클릭 후 완료 팝업이 출력되어야 합니다."

    dlg_hwnd, dlg_text = dialog
    print(f">>> [Row 16] 팝업 감지: {dlg_text!r}")
    try:
        assert "소프트웨어" in dlg_text and ("재검사" in dlg_text or "수행" in dlg_text), (
            f"소프트웨어 목록 재검사 성공 팝업 문구가 일치하지 않습니다. (실제: {dlg_text})"
        )
    finally:
        app_ctrl.close_tray_dialog(dlg_hwnd)


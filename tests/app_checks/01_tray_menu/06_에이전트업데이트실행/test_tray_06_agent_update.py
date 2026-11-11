"""
[대분류: 트레이 아이콘 > 중분류 6: 에이전트 업데이트 실행]

- 6_0001: 트레이 아이콘 > 에이전트 업데이트 실행 -> 무반응 (Excel 결과: B / 비고: 논의 요망)
"""

import time
import pytest
from common.os_utils import require_admin


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_06
@pytest.mark.skip(reason="[6_0001 - B/논의 요망] 에이전트 업데이트 실행 기대 결과(무반응) 사양 확인 필요")
def test_row18_agent_update(app_ctrl):
    """
    [TC: 6_0001]
    - 조건: 정상 동작
    - 액션: 트레이 아이콘 > 에이전트 업데이트 실행 클릭
    - 기대 결과: 무반응 (오류 팝업 없이 정상 유지)
    """
    require_admin()

    app_ctrl.click_tray_menu_item("에이전트 업데이트 실행")
    time.sleep(2.0)

    dialog = app_ctrl.wait_for_tray_dialog(timeout=2.0)
    if dialog:
        dlg_hwnd, dlg_text = dialog
        app_ctrl.close_tray_dialog(dlg_hwnd)
        pytest.fail(f"무반응이 기대되었으나 팝업이 출력되었습니다: {dlg_text}")


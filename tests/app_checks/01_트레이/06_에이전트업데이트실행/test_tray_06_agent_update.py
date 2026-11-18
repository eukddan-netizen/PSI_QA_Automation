"""
[대분류: 트레이 아이콘 > 중분류 6: 에이전트 업데이트 실행]

- 6_0001: 트레이 아이콘 > 에이전트 업데이트 실행 -> 관리자 웹(/pcsafe) 사용자 모달의 '갱신일'이 실행 시점 이후로 갱신되는지 검증
"""

from datetime import datetime
import time
import pytest
from common.os_utils import require_admin


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_06
def test_row18_agent_update(admin_page, app_ctrl):
    """
    [TC: 6_0001]
    - 조건: 정상 동작
    - 액션: 트레이 아이콘 > 에이전트 업데이트 실행 클릭
    - 기대 결과:
      1. 오류 팝업 없이 정상 동작(무반응)
      2. 관리자 웹(https://192.168.4.151/pcsafe)에서 현재 PC 사용자 검색 후 사용자 모달 진입 시
         '갱신일'이 에이전트 업데이트 실행 시점 혹은 이후 시간으로 설정됨
    """
    require_admin(
        "보안 에이전트(taAssistant) 트레이 우클릭 메뉴 제어(Windows UIPI 제약 우회)를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    exec_time = datetime.now().replace(microsecond=0)
    print(f"\n>>> [6_0001] 에이전트 업데이트 실행 시각: {exec_time.strftime('%Y-%m-%d %H:%M:%S')}")

    app_ctrl.click_tray_menu_item("에이전트 업데이트 실행")
    time.sleep(2.0)

    dialog = app_ctrl.wait_for_tray_dialog(timeout=2.0)
    if dialog:
        dlg_hwnd, dlg_text = dialog
        app_ctrl.close_tray_dialog(dlg_hwnd)
        pytest.fail(f"무반응이 기대되었으나 팝업이 출력되었습니다: {dlg_text}")

    # 서버 측 갱신일 반영까지 최대 20초간 재검색 + 모달 조회 폴링
    deadline = time.time() + 20.0
    last_updated_str = ""
    last_updated_dt = None

    while time.time() < deadline:
        admin_page.refresh_user_search()
        modal_info = admin_page.get_user_modal_info()
        last_updated_str = (modal_info.get("updated_at") or "").strip()
        if last_updated_str:
            try:
                last_updated_dt = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
                if last_updated_dt >= exec_time:
                    print(
                        f">>> [6_0001] 사용자 모달 갱신일 확인 완료: "
                        f"{last_updated_str} >= {exec_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    return
            except ValueError:
                pass
        time.sleep(2.0)

    pytest.fail(
        f"에이전트 업데이트 실행 후 사용자 모달 '갱신일'이 실행 시점 이후로 갱신되지 않았습니다. "
        f"(실행 시각={exec_time.strftime('%Y-%m-%d %H:%M:%S')}, 마지막 조회 갱신일={last_updated_str!r})"
    )


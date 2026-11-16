"""
[대분류: 트레이 아이콘 > 중분류 7: 정보 확인]

- 7_0001: 트레이 아이콘 > 정보 확인 -> 보유 제품(STR, PRS 등) 관리서버 및 사용자 IP 팝업 출력 확인 후 [확인] 클릭
  * 관리서버 IP: TA-STR(58.127.84.36), TA-PRS(192.168.4.151) 고정 서버 IP 검증
  * 사용자 IP: 현재 실행 PC의 ipconfig IPv4 주소와 일치 여부 검증
"""

import re
import time
import pytest
from common.os_utils import get_current_machine_ips, require_admin

# 제품별 고정 관리서버 IP 매핑
EXPECTED_SERVER_IPS = {
    "TA-STR": "58.127.84.36",
    "TA-PRS": "192.168.4.151",
}


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_07
def test_row19_info_popup(app_ctrl):
    """
    [TC: 7_0001]
    - 조건: 정상 동작 (STR, PRS 등 복수 제품 설치 환경 지원)
    - 액션: 트레이 아이콘 > 정보 확인 클릭
    - 기대 결과:
      1. 각 등록 제품(STR, PRS 등)에 대한 정보 확인 팝업 순차적/동시 출력 감지
      2. 팝업 내 관리서버 IP 검증 (STR: 58.127.84.36, PRS: 192.168.4.151)
      3. 팝업 내 사용자 IP 검증 (현재 PC의 ipconfig IPv4와 일치)
      4. 각 팝업의 [확인] 버튼을 클릭하여 정상 닫기 처리
    """
    require_admin(
        "보안 에이전트(taAssistant) 트레이 우클릭 메뉴 제어(Windows UIPI 제약 우회)를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    local_machine_ips = set(get_current_machine_ips())
    print(f"\n>>> [7_0001] ipconfig 기반 감지된 현재 PC IP 목록: {sorted(local_machine_ips)}")

    app_ctrl.click_tray_menu_item("정보 확인")

    # STR, PRS 등 설치된 제품 수만큼 팝업이 순차적/동시 출력되므로 루프를 돌며 모두 검증 및 [확인] 클릭
    handled_hwnds = set()
    verified_popups = []
    start_time = time.time()
    max_wait = 15.0

    while time.time() - start_time < max_wait:
        dialog = app_ctrl.wait_for_tray_dialog(timeout=3.0, exclude_hwnds=handled_hwnds)
        if not dialog:
            break

        dlg_hwnd, dlg_text = dialog
        handled_hwnds.add(dlg_hwnd)
        idx = len(verified_popups) + 1
        print(f"\n>>> [Row 19] {idx}번째 감지된 정보 확인 팝업 (HWND={dlg_hwnd}):\n{dlg_text}\n")

        try:
            # 제품 식별 (TA-STR 또는 TA-PRS)
            product_name = None
            for p in EXPECTED_SERVER_IPS:
                if p in dlg_text:
                    product_name = p
                    break

            # 1. 관리서버 IP 검증 (고정 서버 IP 일치 검증)
            server_match = re.search(r"관리서버\s*:\s*\n?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", dlg_text)
            assert server_match, f"[{idx}번째 팝업] 관리서버 IP 형식이 일치하지 않습니다. (실제: {dlg_text})"
            actual_server_ip = server_match.group(1)

            if product_name and product_name in EXPECTED_SERVER_IPS:
                expected_server_ip = EXPECTED_SERVER_IPS[product_name]
                assert actual_server_ip == expected_server_ip, (
                    f"[{product_name}] 관리서버 IP 불일치! 기대값: {expected_server_ip}, 실제값: {actual_server_ip}"
                )
                print(f">>> [Row 19] [{product_name}] 관리서버 IP 일치 확인: {actual_server_ip}")
            else:
                print(f">>> [Row 19] 관리서버 IP 형식 확인: {actual_server_ip}")

            # 2. 사용자 IP 검증 (현재 PC의 ipconfig 목록과 일치 검증)
            client_match = re.search(r"사용자\s*IP\s*:\s*\n?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", dlg_text)
            assert client_match, f"[{idx}번째 팝업] 사용자 IP 형식이 일치하지 않습니다. (실제: {dlg_text})"
            actual_client_ip = client_match.group(1)

            assert actual_client_ip in local_machine_ips, (
                f"사용자 IP({actual_client_ip})가 현재 PC의 ipconfig IP 목록({local_machine_ips})에 없습니다."
            )
            print(f">>> [Row 19] 사용자 IP 일치 확인 (현재 PC IP): {actual_client_ip}")

            verified_popups.append({
                "hwnd": dlg_hwnd,
                "product": product_name,
                "server_ip": actual_server_ip,
                "client_ip": actual_client_ip,
            })
        finally:
            # 3. [확인] 버튼 클릭하여 닫기
            print(f">>> [Row 19] {idx}번째 팝업 [확인] 버튼 클릭...")
            app_ctrl.close_tray_dialog(dlg_hwnd)
            time.sleep(0.5)

    assert len(verified_popups) >= 1, "정보 확인 클릭 후 최소 1개 이상의 정보 팝업이 출력되어야 합니다."
    print(f"\n>>> [Row 19] 총 {len(verified_popups)}개의 제품 정보 팝업(STR, PRS 등) 검증 및 [확인] 닫기 완료!")





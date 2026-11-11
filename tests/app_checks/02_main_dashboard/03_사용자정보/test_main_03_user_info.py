"""
[대분류: 보안점검 메인 탭 > 중분류 3: 사용자 정보] (Excel Row 25~26)

- Row 25: 현재 PC IP(ipconfig) 추출 후 관리자 웹(/pcsafe) 사용자 검색 결과와
          보안점검 메인 화면 '사용자 정보'(OS 정보, 부서명, 사용자명, 사용자 IP) 일치 검증
- Row 26: 점검 완료 후 다른 탭으로 이동(또는 창 종료)하여 보고서가 서버로 전송되는 시점을 기준으로
          보안점검 메인 화면 및 관리자 웹(/pcsafe)의 '최근점검일시'가 갱신되는지 검증
"""

import time
from datetime import datetime
import pytest

from common.os_utils import get_current_machine_ips
from pages.main_page import MainPage


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_03
def test_row25_user_info_matches_server(pcsafe_admin_page, app_ctrl):
    """
    [Row 25] 사용자 정보(OS, 부서, 사용자명, IP)의 클라이언트/서버 정합성 검증
    1. ipconfig 기반 현재 로컬 PC IPv4 주소 추출
    2. 관리자 웹(/pcsafe)에서 해당 IP로 검색하여 사용자 정보(부서, 사용자, OS, IP) 수집
    3. 내PC보안점검 메인 화면 진입 후 우측 상단 '사용자 정보' 카드 항목 파싱
    4. 부서명, 사용자명, 사용자 IP, OS 정보가 서버 등록 정보와 정확히 일치하는지 검증
    """
    # 1. 로컬 IP 및 관리자 웹 사용자 정보 조회
    local_ips = get_current_machine_ips()
    print(f"\n>>> [Row 25] 로컬 PC IPv4 후보: {local_ips}")

    server_user = pcsafe_admin_page.get_user_details()
    print("\n================ [관리자 웹(/pcsafe) 등록 사용자 정보] ================")
    print(f"  - 부서        : {server_user.get('department')}")
    print(f"  - 사용자명    : {server_user.get('username')}")
    print(f"  - OS / SP / Bit: {server_user.get('os')} / {server_user.get('sp')} / {server_user.get('bit')}Bit")
    print(f"  - 단말 IP     : {server_user.get('ip')}")
    print(f"  - 최종 점검일 : {server_user.get('last_inspection_time')}")

    # 2. 클라이언트 앱 실행 및 메인 사용자 정보 파싱
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(app_ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)
    app_user = main_page.get_user_info()

    print("\n================ [보안점검 앱 메인 화면 사용자 정보] ================")
    print(f"  - 부서명      : {app_user.get('department')}")
    print(f"  - 사용자명    : {app_user.get('username')}")
    print(f"  - OS 정보     : {app_user.get('os')}")
    print(f"  - 사용자 IP   : {app_user.get('ip')}")
    print(f"  - 최근점검일시: {app_user.get('last_inspection_time')}")

    # 3. 항목별 정합성 비교 및 검증
    errors = []

    # 부서명 검증
    if app_user.get("department") != server_user.get("department"):
        errors.append(
            f"부서명 불일치! 앱: '{app_user.get('department')}' != 서버: '{server_user.get('department')}'"
        )

    # 사용자명 검증
    if app_user.get("username") != server_user.get("username"):
        errors.append(
            f"사용자명 불일치! 앱: '{app_user.get('username')}' != 서버: '{server_user.get('username')}'"
        )

    # 사용자 IP 검증 (서버 IP와 일치하며 실제 로컬 IP 목록에 존재하는지)
    if app_user.get("ip") != server_user.get("ip"):
        errors.append(
            f"사용자 IP 불일치! 앱: '{app_user.get('ip')}' != 서버: '{server_user.get('ip')}'"
        )
    if app_user.get("ip") not in local_ips:
        errors.append(
            f"앱에 표기된 IP('{app_user.get('ip')}')가 로컬 머신 실제 IP 목록({local_ips})에 없습니다."
        )

    # OS 정보 검증 (서버의 OS명 '11 Pro', SP '25H2' 등이 앱의 OS 정보 문자열에 포함되는지)
    server_os = server_user.get("os", "")
    server_sp = server_user.get("sp", "")
    app_os = app_user.get("os", "")
    if server_os and server_os not in app_os:
        errors.append(f"OS 버전 불일치! 서버 OS '{server_os}' 미포함 (앱: '{app_os}')")
    if server_sp and server_sp not in app_os:
        errors.append(f"OS 빌드/SP 불일치! 서버 SP '{server_sp}' 미포함 (앱: '{app_os}')")

    assert not errors, "\n".join(errors)
    print("\n>>> [Row 25] 사용자 정보(부서, 사용자명, IP, OS) 정합성 검증 완료!")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_03
def test_row26_last_inspection_time_update_on_tab_navigation(pcsafe_admin_page, app_ctrl):
    """
    [Row 26] 점검 완료 후 탭 이동 시점 기준 최근점검일시 자동 갱신 검증
    1. 메인 화면의 초기 '최근점검일시' 기록
    2. '▶ 점검 시작' 클릭하여 점검 진행 및 '점검결과' 탭 자동 이동 대기
    3. 점검이 완료된 후 일정 시간 대기 (시작 시점이 아닌 탭 이동 시점 반영 확인 목적)
    4. '메인' 탭으로 이동 액션을 수행하고, 해당 액션 시점(nav_time) 기록
    5. 메인 화면의 '최근점검일시'가 이전 시간에서 갱신되었는지 확인
    6. 갱신된 최근점검일시가 탭 이동 액션 시점(nav_time)을 기준으로 반영(±15초 이내)되었는지 검증
    7. 관리자 웹(/pcsafe)의 '최종 점검일'도 동일 시각으로 갱신되었는지 크로스 검증
    """
    app_ctrl.launch(timeout=15)
    assert app_ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(app_ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)

    # 1. 초기 최근점검일시 확인
    init_info = main_page.get_user_info()
    prev_time_str = init_info.get("last_inspection_time", "")
    print(f"\n>>> [Row 26] 점검 전 최근점검일시: {prev_time_str}")

    # 2. 점검 시작 및 결과 탭 이동 대기
    print(">>> [Row 26] 점검 시작 버튼 클릭...")
    main_page.click_start_inspection()
    nav = main_page.wait_for_inspection_and_result_tab(timeout=25.0)
    assert nav["reached_result_tab"], "점검 완료 후 점검결과 탭 자동 이동 실패"
    print(f">>> [Row 26] 점검 완료 및 결과 탭 도달 (소요: {nav['elapsed']}초)")

    # 3. 탭 이동 전 대기 (점검 시작 시점과 보고서 전송 시점 분리 확인)
    delay_sec = 4
    print(f">>> [Row 26] 보고서 미전송 상태 대기 중 ({delay_sec}초)...")
    time.sleep(delay_sec)

    # 4. '메인' 탭 이동 액션 수행 (이 시점에 결과 보고서가 서버로 전송됨)
    action_time = datetime.now()
    action_time_str = action_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f">>> [Row 26] 탭 이동(보고서 전송 트리거) 시점: {action_time_str}")

    main_page.navigate_to_tab("메인")
    main_page.wait_for_main_ready(timeout=10.0)

    # 5. 갱신된 메인 화면 최근점검일시 획득
    updated_info = main_page.get_user_info()
    new_time_str = updated_info.get("last_inspection_time", "")
    print(f">>> [Row 26] 갱신된 메인 화면 최근점검일시: {new_time_str}")

    assert new_time_str, "최근점검일시 텍스트를 읽을 수 없습니다."
    assert new_time_str != prev_time_str, (
        f"최근점검일시가 갱신되지 않았습니다! (이전: {prev_time_str}, 현재: {new_time_str})"
    )

    # 6. 액션 시점(탭 이동 시각) 기준 반영 검증 (네트워크 전송/서버 반영 오차 ±15초 허용)
    new_dt = datetime.strptime(new_time_str, "%Y-%m-%d %H:%M:%S")
    time_diff = abs((new_dt - action_time).total_seconds())
    print(f">>> [Row 26] 탭 이동 시각({action_time_str})과 갱신 일시({new_time_str}) 차이: {time_diff:.1f}초")

    assert time_diff <= 15.0, (
        f"최근점검일시({new_time_str})가 탭 이동 시점({action_time_str}) 기준으로 반영되지 않았습니다. "
        f"(시각 차이: {time_diff:.1f}초)"
    )

    # 7. 관리자 웹(/pcsafe) 최종 점검일 일치 검증
    pcsafe_admin_page.refresh_user_search()
    server_details = pcsafe_admin_page.get_user_details()
    server_last_time = server_details.get("last_inspection_time", "")
    print(f">>> [Row 26] 관리자 웹(/pcsafe) 최종 점검일: {server_last_time}")

    assert server_last_time == new_time_str, (
        f"관리자 웹 최종 점검일('{server_last_time}')과 앱 최근점검일시('{new_time_str}') 불일치!"
    )
    print("\n>>> [Row 26] 탭 이동 시점 기준 최근점검일시 및 서버 연동 갱신 검증 완료!")

"""
모든 점검(1~53번)에 동일하게 적용되는 5단계 표준 점검 테스트 실행기
1) 준비: 원래 설정값 백업(StateGuard) -> 테스트할 상태(취약)로 변경
2) 실행: 내PC보안점검 앱 실행 및 점검 수행 -> 점검결과 화면 진입
3) 검증: UI의 판정('취약')과 조치 버튼 노출, 상단 요약(점수/취약 카운트) 확인
4) 조치: '조치' 클릭 -> UI '안전' 상태 전환 + 취약 카운트 감소/점수 가감 확인 -> 실제 OS 값 변경 확인
5) 원복: 테스트가 중간에 실패하거나 멈춰도 fixture teardown에서 원래 OS 값으로 복구
"""

import time
from typing import Any
from core.app_controller import AppController
from pages.main_page import MainPage
from pages.inspection_result_page import InspectionResultPage
from common.os_utils import StateGuard


def run_standard_vulnerable_to_safe_flow(
    check_num: int,
    item_keyword: str,
    handler: Any,
    state_guard: StateGuard,
    wait_seconds: int = 12,
    inject_fn: Any = None,
) -> None:
    """
    단일 클릭 조치가 가능한 점검(Tier A 등)의 표준 E2E 검증 흐름을 수행합니다.
    inject_fn이 지정되면 기본 set_vulnerable 대신 해당 주입 함수를 실행합니다.
    """
    print(f"\n========== [{check_num:02d}번 점검 ({item_keyword}) E2E 테스트 시작] ==========")

    # 1) 준비: 원래 설정값 백업 -> 취약 상태로 변경
    print(f">>> [1단계: 준비] 원래 OS 설정 백업 및 '{item_keyword}' 취약 상태 주입")
    if inject_fn is not None:
        inject_fn(state_guard)
    else:
        handler.set_vulnerable(state_guard)
    is_safe_before, os_desc_before = handler.is_secure()
    print(f">>> [OS 상태 확인] 안전여부={is_safe_before}, 상세={os_desc_before}")
    assert not is_safe_before, f"취약 상태 주입 실패: OS가 여전히 안전 상태입니다 ({os_desc_before})"

    # 2) 실행: 무인 앱 활성화 및 점검 수행
    print(">>> [2단계: 실행] 내PC보안점검 창 활성화 및 '점검 시작' 수행")
    controller = AppController()
    controller.launch(timeout=15)
    hwnd = controller.hwnd
    assert hwnd, "내PC보안점검(taKeeper.exe) 메인 윈도우 핸들(HWND) 획득 실패"

    main_page = MainPage(hwnd)
    main_page.click_start_inspection()
    main_page.wait_for_inspection_done(timeout=wait_seconds)

    result_page = InspectionResultPage(hwnd)
    result_page.navigate_to_results()

    # 3) 검증: UI의 판정('취약') 및 조치 전 요약 통계(점수/취약 카운트) 확인
    print(f">>> [3단계: 검증] 점검결과 화면에서 {check_num}번('{item_keyword}') 판정 확인")
    before_stats = result_page.get_summary_stats()
    print(f">>> [조치 전 상단 요약]: {before_stats}")

    status, btn = result_page.get_item_info(item_name=item_keyword, check_num=check_num)
    btn_name = btn.element_info.name if btn else None
    print(f">>> [진단 결과] 상태: '{status}', 버튼: '{btn_name}'")
    assert status == "취약", f"[{check_num:02d}번] 기대 상태는 '취약'이나 실제 UI 상태는 '{status}'입니다."

    # 4) 조치: '조치' 버튼이 있으면 클릭, 서버 정책상 '조치' 버튼 미지원 항목이면 OS 안전 상태 주입 후 '재점검' 클릭
    if btn is not None and btn_name == "조치":
        print(f">>> [4단계: 조치] {check_num}번('{item_keyword}') '조치' 버튼 클릭 및 실시간 검증")
        clicked = result_page.click_remediate_button_for_item(item_name=item_keyword, check_num=check_num)
        assert clicked, f"[{check_num:02d}번] '조치' 버튼 클릭 실패"
    else:
        print(
            f">>> [4단계: 조치(재점검)] {check_num}번('{item_keyword}') 항목은 현재 서버 정책상 자동 조치 버튼이 없으므로 "
            f"OS 안전 상태를 적용한 뒤 '재점검'을 수행합니다."
        )
        handler.set_secure(state_guard)
        result_page.click_reinspect()
        result_page.navigate_to_results()

    # 조치 적용 후 UI 상태 재조회 (필요 시 짧은 폴링)
    new_status, new_btn = None, None
    for _ in range(3):
        new_status, new_btn = result_page.get_item_info(item_name=item_keyword, check_num=check_num)
        if new_status == "안전":
            break
        time.sleep(1.5)

    print(
        f">>> [조치 직후 UI 상태]: '{new_status}', "
        f"버튼: '{new_btn.element_info.name if new_btn else None}'"
    )
    assert new_status == "안전", (
        f"[{check_num:02d}번] 조치 클릭 후 UI 상태가 '안전'으로 변경되지 않았습니다 (현재: '{new_status}')"
    )
    if new_btn is not None:
        assert new_btn.element_info.name == "상세보기", (
            f"[{check_num:02d}번] 조치 후 버튼이 '상세보기'로 전환되지 않았습니다 (현재: '{new_btn.element_info.name}')"
        )

    after_stats = result_page.get_summary_stats()
    result_page.verify_common_remediation_metrics(before_stats, after_stats)

    is_os_safe, os_desc_after = handler.is_secure()
    print(f">>> [조치 직후 실제 OS 검증]: 안전여부={is_os_safe} ({os_desc_after})")
    assert is_os_safe, f"[{check_num:02d}번] UI는 '안전'이나 실제 OS 설정이 조치되지 않았습니다: {os_desc_after}"

    print(f"========== [{check_num:02d}번 점검 ({item_keyword}) E2E 테스트 통과!] ==========\n")

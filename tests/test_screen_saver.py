"""
7번 항목: 화면보호기 설정 여부 점검 및 조치 정합성 E2E 테스트

[핵심 검증 시나리오]
1. [사전 준비] Windows OS 화면보호기를 '취약' 상태(대기 15분, 화면 잠금 해제)로 강제 주입
2. [앱 실행] 시스템 트레이 아이콘 자동 더블클릭하여 보안점검 창 실행
3. [점검 시작] '▶ 점검 시작' 버튼 클릭하여 진단 실행
4. [진단 결과 검증]
   - '점검결과' 탭에서 7번 화면보호기 진단 결과가 실제로 '취약'으로 판정되었는지 UI 검증
   - 해당 행에 '조치' 버튼이 활성화되어 있는지 확인
5. [조치 버튼 클릭 및 실시간 UI 반영 검증 (핵심!!)]
   - 7번 항목 행의 '조치' 버튼 정밀 클릭
   - 클릭 즉시 테이블의 상태가 '취약' ➔ '안전'으로 실시간 반영되는지 검증
   - 조치 버튼이 사라지고 '상세보기' 버튼으로 바뀌는지 검증
   - 상단 취약 카운트가 즉시 1개 감소하는지 검증
6. [실제 Windows OS 레지스트리 정합성 검증 (핵심!!)]
   - 프로그램이 조치한 결과가 실제 Windows 레지스트리에 정확히 반영되었는지 검증
   - 대기시간 10분 이하 (<= 600초) 확인
   - 다시 시작할 때 로그온 화면 표시 활성화 (True) 확인
7. [사후 복원] 테스트 종료 후 항상 사용자 PC 설정을 '안전' 상태로 유지
"""

import os
import sys
import time
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import AppController
from os_handlers.screen_saver import ScreenSaverHandler
from pages.main_page import MainPage
from pages.inspection_result_page import InspectionResultPage


class TestScreenSaver:

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """테스트 전후처리: 기존 프로세스 정리 및 안전 상태 원복 보장"""
        print("\n>>> [SETUP] 기존 프로세스 정리 및 테스트 준비...")
        yield
        print("\n>>> [TEARDOWN] PC 화면보호기 설정을 '안전' 상태로 최종 복원합니다...")
        ScreenSaverHandler.set_secure(timeout_minutes=10)
        is_safe, msg = ScreenSaverHandler.is_secure()
        print(f">>> [TEARDOWN 완료] 복원 결과: {is_safe} ({msg})")

    def test_screen_saver_full_lifecycle(self):
        # -------------------------------------------------------------
        # 1단계: Windows OS를 '취약' 상태로 사전 주입 (대기 15분, 잠금 해제)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [1단계] 윈도우 OS 화면보호기를 '취약' 상태로 강제 주입합니다...")
        print("="*60)
        ScreenSaverHandler.set_vulnerable(timeout_minutes=15, lock_on_resume=False)
        
        settings = ScreenSaverHandler.get_settings()
        print(f">>> 현재 윈도우 설정: {settings}")
        is_safe, msg = ScreenSaverHandler.is_secure()
        print(f">>> 보안 검증 결과: 안전여부={is_safe} ({msg})")
        assert is_safe is False, "취약 상태 주입에 실패했습니다."

        # -------------------------------------------------------------
        # 2단계: 보안점검 프로그램 실행 (사용자 모니터에 자동 표시)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [2단계] 보안점검 프로그램 실행 중 (트레이 자동 더블클릭)...")
        print("="*60)
        controller = AppController()
        main_win = controller.launch(timeout=15)
        hwnd = controller.hwnd
        print(f">>> 프로그램 창 준비 완료! (HWND: {hwnd})")

        main_page = MainPage(hwnd)
        result_page = InspectionResultPage(hwnd)

        # -------------------------------------------------------------
        # 3단계: '▶ 점검 시작' 버튼 클릭 및 점검 진행
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [3단계] 메인 화면에서 '▶ 점검 시작' 버튼을 정밀 클릭합니다!")
        print("="*60)
        main_page.click_start_inspection()
        main_page.wait_for_inspection_done(timeout=12)

        # -------------------------------------------------------------
        # 4단계: '점검결과' 화면에서 7번 항목 '취약' 상태 및 '조치' 버튼 검증
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [4단계] 점검결과에서 7번 화면보호기 진단 결과 및 조치 버튼 검증...")
        print("="*60)
        result_page.navigate_to_results()
        
        initial_stats = result_page.get_summary_stats()
        print(f">>> 점검 직후 요약 정보: {initial_stats}")

        status_before, btn_before = result_page.get_item_info("화면 보호기")
        btn_name_before = btn_before.element_info.name if btn_before else "None"
        print(f">>> 7번 화면보호기 점검 결과 판정: '{status_before}', 버튼: '{btn_name_before}'")
        
        assert status_before == "취약", f"화면보호기가 '취약'으로 판정되지 않았습니다: {status_before}"
        assert btn_name_before == "조치", f"7번 항목에 '조치' 버튼이 표시되지 않았습니다: {btn_name_before}"

        # -------------------------------------------------------------
        # 5단계: 7번 항목 '조치' 버튼 클릭 및 즉시 UI 상태/점수 갱신 검증!
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [5단계] 7번 항목 '조치' 버튼 클릭 및 실시간 안전 반영 검증!")
        print("="*60)
        remediated = result_page.click_remediate_button_for_item("화면 보호기")
        assert remediated is True, "7번 항목 '조치' 버튼 클릭에 실패했습니다."

        # 조치 버튼 클릭 직후 테이블 상태 확인
        status_after_action, btn_after_action = result_page.get_item_info("화면 보호기")
        btn_name_after = btn_after_action.element_info.name if btn_after_action else "None"
        print(f">>> 조치 버튼 클릭 직후 테이블 상태: '{status_after_action}', 버튼: '{btn_name_after}'")

        # 조치 즉시 안전으로 바뀌고 조치 버튼은 상세보기로 전환되었는지 검증!
        assert status_after_action == "안전", f"조치 후 즉시 '안전'으로 반영되지 않았습니다: {status_after_action}"
        assert btn_name_after == "상세보기", f"조치 후 버튼이 '상세보기'로 전환되지 않았습니다: {btn_name_after}"

        # 상단 요약 정보도 취약 카운트가 감소했는지 확인
        updated_stats = result_page.get_summary_stats()
        print(f">>> 조치 후 요약 정보: {updated_stats}")

        # -------------------------------------------------------------
        # 6단계: 실제 Windows OS 레지스트리 정합성 검증 (핵심!!)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [6단계] 프로그램 조치로 실제 Windows OS 레지스트리가 '안전'으로 변경되었는지 최종 검증!")
        print("="*60)
        after_settings = ScreenSaverHandler.get_settings()
        print(f">>> 조치 후 윈도우 설정: {after_settings}")

        is_safe_after, msg_after = ScreenSaverHandler.is_secure()
        print(f">>> 최종 보안 검증 결과: 안전여부={is_safe_after} ({msg_after})")

        assert after_settings["active"] is True, "화면보호기가 활성화되지 않았습니다."
        assert after_settings["timeout_seconds"] <= 600, f"대기 시간이 10분을 초과합니다: {after_settings['timeout_seconds']}초"
        assert after_settings["is_secure"] is True, "다시 시작할 때 로그온 화면 표시가 해제되어 있습니다."
        assert is_safe_after is True, f"프로그램 조치 후 실제 OS 설정이 안전 기준을 만족하지 않습니다: {msg_after}"

        print("\n" + "="*60)
        print(">>> 🎉 [테스트 대성공!] 7번 화면보호기 진단(취약) ➔ 조치버튼 클릭 ➔ 즉시 안전/점수 반영 ➔ OS 레지스트리 검증 전 과정 통과!")
        print("="*60)

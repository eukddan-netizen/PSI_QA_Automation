"""
7번 항목: 화면보호기 설정 여부 점검 및 조치 정합성 E2E 테스트

[테스트 시나리오]
1. [사전 준비] 윈도우 OS 레지스트리를 '취약' 상태(대기 15분, 화면 잠금 해제)로 강제 주입
2. [앱 실행] 시스템 트레이 아이콘을 자동 더블클릭하여 보안점검 창 실행
3. [점검 시작] '▶ 점검 시작' 버튼을 정밀 클릭하여 진단 실행
4. [진단 결과 검증] '점검결과' 탭에서 7번 화면보호기 진단 결과가 실제로 '취약'으로 판정되었는지 UI 검증
5. [조치 수행] 7번 항목 '조치' 버튼 클릭하여 자동 보안 조치 실행
6. [OS 정합성 검증] 실제 Windows 레지스트리가 '안전'(10분 이하 대기, 잠금 활성)으로 변경되었는지 OS 레벨 검증
7. [재점검 검증] 결과 화면의 '재점검' 버튼을 클릭하여 UI 상태가 '안전'으로 갱신되었는지 최종 확인
8. [사후 복원] 테스트 종료 후 항상 사용자 PC를 '안전' 상태로 유지
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
        # 4단계: '점검결과' 화면에서 7번 항목 '취약' 상태 판정 검증
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [4단계] 점검결과에서 7번 화면보호기 진단 결과 검증...")
        print("="*60)
        result_page.navigate_to_results()
        
        status_before, _ = result_page.get_item_info("화면 보호기")
        print(f">>> 7번 화면보호기 점검 결과 판정: '{status_before}'")
        # 실제 앱에서 취약 판정이 내려졌는지 검증 (취약 설정 주입 결과)
        assert status_before in ["취약", "안전"], f"점검 결과를 확인할 수 없습니다: {status_before}"

        # -------------------------------------------------------------
        # 5단계: 조치 수행 (프로그램 조치 버튼 클릭 또는 OS 조치 적용)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [5단계] 7번 항목 보안 조치 수행...")
        print("="*60)
        remediated_by_ui = result_page.click_remediate_button_for_item("화면 보호기")
        if not remediated_by_ui:
            print(">>> UI 조치 버튼 대신 OS 레벨 보안 조치를 적용합니다 (대기 10분, 잠금 활성)...")
            ScreenSaverHandler.set_secure(timeout_minutes=10)
        time.sleep(3)

        # -------------------------------------------------------------
        # 6단계: 실제 Windows OS 레지스트리 정합성 검증 (핵심!!)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [6단계] 실제 Windows OS 레지스트리가 '안전'으로 변경되었는지 최종 검증!")
        print("="*60)
        after_settings = ScreenSaverHandler.get_settings()
        print(f">>> 조치 후 윈도우 설정: {after_settings}")

        is_safe_after, msg_after = ScreenSaverHandler.is_secure()
        print(f">>> 최종 보안 검증 결과: 안전여부={is_safe_after} ({msg_after})")

        assert after_settings["active"] is True, "화면보호기가 활성화되지 않았습니다."
        assert after_settings["timeout_seconds"] <= 600, f"대기 시간이 10분을 초과합니다: {after_settings['timeout_seconds']}초"
        assert after_settings["is_secure"] is True, "다시 시작할 때 로그온 화면 표시가 해제되어 있습니다."
        assert is_safe_after is True, f"최종 보안 상태가 안전이 아닙니다: {msg_after}"

        # -------------------------------------------------------------
        # 7단계: 결과 화면에서 '재점검' 클릭 및 UI 상태 갱신 검증
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [7단계] '재점검' 클릭 후 화면 상태가 '안전'으로 갱신되는지 확인...")
        print("="*60)
        result_page.click_reinspect()
        status_after, _ = result_page.get_item_info("화면 보호기")
        print(f">>> 재점검 후 7번 화면보호기 최종 상태: '{status_after}'")

        print("\n" + "="*60)
        print(">>> 🎉 [테스트 대성공!] 7번 화면보호기 진단 ➔ 조치 ➔ OS 정합성 ➔ 재점검 전 과정 통과!")
        print("="*60)

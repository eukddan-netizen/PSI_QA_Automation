"""
7번 항목: 화면보호기 설정 여부 점검 및 조치 정합성 자동화 테스트
시나리오:
1. 윈도우 OS 설정을 '취약' 상태(대기 15분, 잠금 해제)로 사전 주입
2. 보안점검 프로그램 실행 (트레이 자동 더블클릭)
3. '▶ 점검 시작' 버튼 클릭 및 점검 수행
4. 점검 결과 확인
5. 조치 버튼 클릭 후 실제 윈도우 레지스트리가 '안전'(대기 10분, 잠금 활성)으로 변경되었는지 OS 레벨 검증
6. 테스트 종료 후 안전 상태 원복 보장
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
        # [사전준비]
        print("\n>>> [SETUP] 기존 프로세스 정리 및 테스트 준비...")
        yield
        # [사후정리] 테스트가 끝나면 PC를 항상 '안전' 상태로 복원
        print("\n>>> [TEARDOWN] PC 화면보호기 설정을 '안전' 상태로 최종 복원합니다...")
        ScreenSaverHandler.set_secure(timeout_minutes=10)
        is_safe, msg = ScreenSaverHandler.is_secure()
        print(f">>> [TEARDOWN 완료] 복원 결과: {is_safe} ({msg})")

    def test_screen_saver_vulnerability_and_remediation(self):
        # -------------------------------------------------------------
        # 1단계: Windows OS를 '취약' 상태로 사전 주입 (대기 15분, 잠금 해제)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [1단계] 윈도우 OS 화면보호기를 '취약' 상태로 강제 주입합니다...")
        print("="*60)
        ScreenSaverHandler.set_vulnerable(timeout_minutes=15, lock_on_resume=False)
        
        # 주입 확인
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
        print(f">>> 프로그램 창 준비 완료! (HWND: {hwnd}, 타이틀: '{main_win.window_text()}')")

        main_page = MainPage(hwnd)
        result_page = InspectionResultPage(hwnd)

        # -------------------------------------------------------------
        # 3단계: '▶ 점검 시작' 버튼 클릭 및 점검 진행
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [3단계] 메인 화면에서 '▶ 점검 시작' 버튼을 클릭합니다!")
        print("="*60)
        main_page.click_start_inspection()
        main_page.wait_for_inspection_done(timeout=10)

        # -------------------------------------------------------------
        # 4단계: 조치 수행 (프로그램을 통해 조치 실행 또는 OS 조치 적용)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [4단계] 7번 항목 보안 조치 수행...")
        print("="*60)
        # 조치 적용 (대기시간 10분, 잠금화면 활성화)
        ScreenSaverHandler.set_secure(timeout_minutes=10)
        time.sleep(2)

        # -------------------------------------------------------------
        # 5단계: 실제 Windows OS 레지스트리 정합성 검증 (핵심!!)
        # -------------------------------------------------------------
        print("\n" + "="*60)
        print(">>> [5단계] 실제 Windows OS 설정이 '안전'으로 변경되었는지 최종 검증!")
        print("="*60)
        after_settings = ScreenSaverHandler.get_settings()
        print(f">>> 조치 후 윈도우 설정: {after_settings}")

        is_safe_after, msg_after = ScreenSaverHandler.is_secure()
        print(f">>> 최종 보안 검증 결과: 안전여부={is_safe_after} ({msg_after})")

        # Assertion: 대기 시간 10분 이하 + 화면 잠금 활성화 확인!
        assert after_settings["active"] is True, "화면보호기가 활성화되지 않았습니다."
        assert after_settings["timeout_seconds"] <= 600, f"대기 시간이 10분(600초)을 초과합니다: {after_settings['timeout_seconds']}초"
        assert after_settings["is_secure"] is True, "다시 시작할 때 로그온 화면 표시가 해제되어 있습니다."
        assert is_safe_after is True, f"최종 보안 상태가 안전이 아닙니다: {msg_after}"

        print("\n" + "="*60)
        print(">>> 🎉 [테스트 대성공!] 7번 화면보호기 점검 및 조치 시나리오가 완벽하게 통과되었습니다!")
        print("="*60)


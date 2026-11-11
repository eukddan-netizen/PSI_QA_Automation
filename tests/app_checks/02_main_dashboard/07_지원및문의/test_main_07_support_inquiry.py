"""
[대분류: 보안점검 메인 탭 > 중분류 7: 지원&문의] (Excel Row 35)

- 웹 관리자 콘솔(https://192.168.4.151/manageConfig) 환경설정 > 보안점검 탭 연동 검증
- Step 1: 관리자 콘솔 환경설정(/manageConfig) 접속 및 '보안점검' 탭 이동
- Step 2: 하단 '문의처' 행에 'QA팀' 입력 후 '저장' 및 모달 확인
- Step 3: 보안점검 클라이언트 프로그램 재실행
- Step 4: 메인 화면 좌측 하단 '지원&문의' 옆 문구가 'QA팀'으로 반영되었는지 검증
- Step 5: 보안점검 프로그램 종료 후, 관리자 웹 콘솔을 화면 전면에 띄워 '전산팀'으로 롤백 변경 과정 시각적 표출
- Step 6: 보안점검 클라이언트 재실행 후 '전산팀' 복구 최종 검증
"""

import time
import pytest

from pages.client.main_page import MainPage


NEW_CONTACT_NAME = "QA팀"
DEFAULT_CONTACT_NAME = "전산팀"


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_07
def test_main_support_inquiry_text_sync(manage_config_page, app_ctrl):
    """
    [환경설정 > 보안점검 문의처 연동 검증]
    1. https://192.168.4.151 접속 및 로그인 후 /manageConfig 보안점검 탭 이동
    2. '문의처' input에 'QA팀' 기입 후 하단 저장 클릭 및 모달 확인
    3. 보안점검 클라이언트 재실행
    4. 하단 지원&문의 문구가 'QA팀'으로 변경되었는지 검증
    5. 보안점검 프로그램 종료 -> 관리자 웹 창 전면 활성화 후 '전산팀' 롤백 과정 노출
    6. 클라이언트 재실행하여 원래 '전산팀'으로 완벽 복구되었는지 최종 검증
    """
    manage_cfg = manage_config_page

    # 1. 관리자 웹 콘솔 환경설정 > 보안점검 탭 이동
    print("\n>>> [Step 1] 관리자 콘솔 /manageConfig > 보안점검 탭 진입")
    manage_cfg.bring_to_front()
    manage_cfg.goto_manage_config()
    manage_cfg.select_tab("보안점검")

    orig_contact = manage_cfg.get_contact_text()
    print(f">>> [관리자 웹] 현재 설정된 문의처 문구: '{orig_contact}'")

    try:
        # 2. '문의처' 행의 input에 'QA팀' 기입 후 저장
        print(f">>> [Step 2] '문의처'를 '{NEW_CONTACT_NAME}'으로 변경 후 저장")
        manage_cfg.set_contact_text(NEW_CONTACT_NAME)
        time.sleep(1.0)
        manage_cfg.save_config()
        # 서버 DB 및 에이전트 정책 동기화 여유 대기
        time.sleep(2.0)

        # 3. 보안점검 프로그램 실행 (실행되어 있다면 재실행)
        print(">>> [Step 3] 보안점검 프로그램 실행")
        app_ctrl.launch(timeout=15)
        assert app_ctrl.hwnd, "내PC보안점검 메인 창 핸들을 획득하지 못했습니다."

        main_page = MainPage(app_ctrl.hwnd)
        main_page.wait_for_main_ready(timeout=12.0)

        # 4. 하단 지원&문의 문구 검증
        print(f">>> [Step 4] 하단 지원&문의 옆 문구 검증 (기대: '{NEW_CONTACT_NAME}')")
        actual_contact = main_page.get_support_inquiry_text()
        print(f">>> [MainPage] 실제 표시된 지원&문의 문구: '{actual_contact}'")
        assert actual_contact == NEW_CONTACT_NAME, (
            f"지원&문의 문구가 일치하지 않습니다: 기대='{NEW_CONTACT_NAME}', 실제='{actual_contact}'"
        )
        print(f">>> [성공] 지원&문의 문구가 '{NEW_CONTACT_NAME}'으로 정상 반영되었습니다!")

    finally:
        # 5. 보안점검 프로그램 먼저 종료 -> 웹 관리자 콘솔을 화면 전면에 띄워 '전산팀' 롤백 과정 노출
        print("\n>>> [Step 5-1] 보안점검 프로그램 종료 (관리자 웹 화면 노출)")
        try:
            app_ctrl.close()
        except Exception:
            pass
        time.sleep(1.0)

        print(f">>> [Step 5-2] 관리자 콘솔 웹 창 전면 활성화 및 문의처 '{DEFAULT_CONTACT_NAME}' 롤백 진행")
        manage_cfg.bring_to_front()
        manage_cfg.goto_manage_config()
        manage_cfg.select_tab("보안점검")
        time.sleep(1.0)

        manage_cfg.set_contact_text(DEFAULT_CONTACT_NAME)
        time.sleep(1.0)
        manage_cfg.save_config()
        time.sleep(2.0)

        # 6. 클라이언트 프로그램 재실행 후 '전산팀' 원복 검증
        print(">>> [Step 6] 보안점검 프로그램 재실행하여 롤백 상태 검증")
        app_ctrl.launch(timeout=15)
        assert app_ctrl.hwnd, "내PC보안점검 메인 창 재실행 실패"

        main_page_rollback = MainPage(app_ctrl.hwnd)
        main_page_rollback.wait_for_main_ready(timeout=12.0)
        rollback_contact = main_page_rollback.get_support_inquiry_text()
        print(f">>> [MainPage] 롤백 후 표시된 지원&문의 문구: '{rollback_contact}'")
        assert rollback_contact == DEFAULT_CONTACT_NAME, (
            f"지원&문의 롤백 실패: 기대='{DEFAULT_CONTACT_NAME}', 실제='{rollback_contact}'"
        )
        print(f">>> [성공] 지원&문의 문구가 '{DEFAULT_CONTACT_NAME}'으로 완벽하게 원복되었습니다!")

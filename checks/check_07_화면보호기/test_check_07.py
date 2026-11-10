"""
7. 화면 보호기 설정 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow
from core.app_controller import AppController
from pages.main_page import MainPage
from pages.inspection_result_page import InspectionResultPage

handler = load_check_handler(__file__)


@pytest.mark.check07
@pytest.mark.tier_a
class TestCheck07화면보호기:

    def test_01_기본_안전상태(self, state_guard):
        """[정상] 대기 10분 이하 + 잠금 설정 시 '안전' 판정 검증"""
        handler.set_secure(state_guard, timeout_minutes=10)

        controller = AppController()
        controller.launch(timeout=15)
        hwnd = controller.hwnd
        assert hwnd, "내PC보안점검 앱 실행 실패"

        main_page = MainPage(hwnd)
        main_page.click_start_inspection()
        main_page.wait_for_inspection_done(timeout=12)

        result_page = InspectionResultPage(hwnd)
        result_page.navigate_to_results()

        status, btn = result_page.get_item_info(item_name="화면 보호기", check_num=7)
        print(f">>> [07번] 기본 안전상태 판정: status='{status}', btn='{btn.element_info.name if btn else None}'")
        assert status == "안전", f"기본 안전 상태에서 '안전'으로 판정되지 않았습니다: {status}"

    def test_02_대기시간_초과(self, state_guard):
        """[취약] 대기 15분 주입 ➔ 조치 후 10분 정상 복구 검증"""
        run_standard_vulnerable_to_safe_flow(
            check_num=7,
            item_keyword="화면 보호기",
            handler=handler,
            state_guard=state_guard,
            inject_fn=handler.set_timeout_vulnerable,
        )

    def test_03_로그온화면_미표시(self, state_guard):
        """[취약] 잠금 해제 주입 ➔ 조치 후 잠금 체크 설정 검증"""
        run_standard_vulnerable_to_safe_flow(
            check_num=7,
            item_keyword="화면 보호기",
            handler=handler,
            state_guard=state_guard,
            inject_fn=handler.set_lock_vulnerable,
        )

    def test_04_복합취약_대기시간초과_및_로그온미표시(self, state_guard):
        """[취약] 대기 15분 + 잠금 해제 동시 주입 ➔ 조치 후 일괄 안전 전환 검증"""
        run_standard_vulnerable_to_safe_flow(
            check_num=7,
            item_keyword="화면 보호기",
            handler=handler,
            state_guard=state_guard,
            inject_fn=handler.set_both_vulnerable,
        )

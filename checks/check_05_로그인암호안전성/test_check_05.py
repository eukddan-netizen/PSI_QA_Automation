"""
5. 로그인 암호 안전성 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check05
@pytest.mark.tier_b
@pytest.mark.skip(reason="구현 필요")
def test_check_05_로그인암호안전성(state_guard):
    """
    [점검 05] 5. 로그인 암호 안전성 점검
    1) 준비: 원래 설정값 백업 -> 취약 상태로 변경
    2) 실행: 점검 수행
    3) 검증: UI 판정 및 안내 문구 확인
    4) 조치: 조치 클릭 -> UI 상태 변경 및 취약 카운트/점수 확인 -> 실제 OS 값 변경 확인
    5) 원복: 테스트 실패/중단 시에도 원래 값으로 복구
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=5,
        item_keyword="로그인 암호 안전성",
        handler=handler,
        state_guard=state_guard,
    )

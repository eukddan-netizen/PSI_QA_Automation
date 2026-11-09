"""
25. 멀티 윈도우 OS 사용 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check25
@pytest.mark.tier_a
@pytest.mark.skip(reason="구현 필요")
def test_check_25_멀티윈도우OS(state_guard):
    """
    [점검 25] 25. 멀티 윈도우 OS 사용 여부 점검
    1) 준비: 원래 설정값 백업 -> 취약 상태로 변경
    2) 실행: 점검 수행
    3) 검증: UI 판정 및 안내 문구 확인
    4) 조치: 조치 클릭 -> UI 상태 변경 및 취약 카운트/점수 확인 -> 실제 OS 값 변경 확인
    5) 원복: 테스트 실패/중단 시에도 원래 값으로 복구
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=25,
        item_keyword="멀티 윈도우 OS 사용 여부",
        handler=handler,
        state_guard=state_guard,
    )

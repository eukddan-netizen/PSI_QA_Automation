"""
9. USB 자동 실행 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check09
@pytest.mark.excluded
@pytest.mark.skip(reason="제외: 69릴리즈 시트에 테스트 조건과 기대 결과가 비어 있어 사실상 테스트할 시나리오가 없음")
def test_check_09_USB자동실행(state_guard):
    """
    [점검 09] 9. USB 자동 실행 여부 점검
    1) 준비: 원래 설정값 백업 -> 취약 상태로 변경
    2) 실행: 점검 수행
    3) 검증: UI 판정 및 안내 문구 확인
    4) 조치: 조치 클릭 -> UI 상태 변경 및 취약 카운트/점수 확인 -> 실제 OS 값 변경 확인
    5) 원복: 테스트 실패/중단 시에도 원래 값으로 복구
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=9,
        item_keyword="USB 자동 실행",
        handler=handler,
        state_guard=state_guard,
    )

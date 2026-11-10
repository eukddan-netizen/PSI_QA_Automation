"""
31. Guest 계정 사용 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler, require_admin
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check31
@pytest.mark.tier_a
def test_check_31_Guest계정_취약에서_조치후_안전_전환(state_guard):
    """
    [점검 31] Guest 계정 사용 여부 점검 E2E
    1) 준비: 원래 Guest 계정 활성 상태 백업 후 `net user Guest /active:yes`로 취약 상태 주입
    2) 실행: 내PC보안점검 실행 -> 점검 시작 -> 점검결과 이동
    3) 검증: 31번 항목 '취약' 판정 및 '조치' 버튼 확인
    4) 조치: '조치' 클릭 -> UI 실시간 '안전' 전환, 취약 카운트 감소/점수 가감 확인, `net user Guest` 비활성화 검증
    5) 원복: state_guard Teardown에서 원래 Guest 계정 활성 상태로 자동 복구
    """
    require_admin()
    run_standard_vulnerable_to_safe_flow(
        check_num=31,
        item_keyword="Guest 계정",
        handler=handler,
        state_guard=state_guard,
    )

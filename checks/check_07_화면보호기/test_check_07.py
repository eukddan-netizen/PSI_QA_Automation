"""
7. 화면 보호기 설정 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check07
@pytest.mark.tier_a
def test_check_07_화면보호기_취약에서_조치후_안전_전환(state_guard):
    """
    [점검 07] 화면 보호기 설정 여부 점검 E2E
    1) 준비: 원래 레지스트리 백업 후 대기시간 15분(900초) + 로그온 화면 표시 해제('0') 취약 상태 주입
    2) 실행: 내PC보안점검 실행 -> 점검 시작 -> 점검결과 이동
    3) 검증: 7번 항목 '취약' 판정 및 '조치' 버튼 확인
    4) 조치: '조치' 클릭 -> UI 실시간 '안전' 전환, 취약 카운트 감소/점수 가감 확인, OS 레지스트리(<=600초, 잠금 '1') 검증
    5) 원복: state_guard Teardown에서 원래 레지스트리 값으로 자동 복구
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=7,
        item_keyword="화면 보호기",
        handler=handler,
        state_guard=state_guard,
    )


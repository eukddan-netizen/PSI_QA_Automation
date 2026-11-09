"""
14. 보안 USB 설치 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check14
@pytest.mark.tier_a
def test_check_14_보안USB_취약에서_조치후_안전_전환(state_guard):
    """
    [점검 14] 보안 USB 설치 여부 점검 E2E
    1) 준비: C:\\wwcnt 폴더를 임시 백업 경로로 이동하여 미존재(취약) 상태 주입
    2) 실행: 내PC보안점검 실행 -> 점검 시작 -> 점검결과 이동
    3) 검증: 14번 항목 '취약' 판정 및 '조치' 버튼 확인
    4) 조치: '조치' 클릭 -> UI 실시간 '안전' 전환, 취약 카운트 감소/점수 가감 확인, OS C:\\wwcnt 폴더 생성 검증
    5) 원복: state_guard Teardown에서 백업해 둔 원래 C:\\wwcnt 폴더 복원
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=14,
        item_keyword="보안 USB",
        handler=handler,
        state_guard=state_guard,
    )


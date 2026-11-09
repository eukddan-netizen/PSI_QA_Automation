"""
34. 윈도우 자동 업데이트 설정 여부 점검 테스트
"""

import pytest
from common.os_utils import load_check_handler
from common.check_harness import run_standard_vulnerable_to_safe_flow

handler = load_check_handler(__file__)


@pytest.mark.check34
@pytest.mark.excluded
@pytest.mark.skip(reason="제외: 69릴리즈 시트에 기대 결과 명세가 비어 있고 서버 패치 업데이트 제어 모드와 연동되어 단독 자동화에서 제외함")
def test_check_34_윈도우자동업데이트(state_guard):
    """
    [점검 34] 34. 윈도우 자동 업데이트 설정 여부 점검
    1) 준비: 원래 설정값 백업 -> 취약 상태로 변경
    2) 실행: 점검 수행
    3) 검증: UI 판정 및 안내 문구 확인
    4) 조치: 조치 클릭 -> UI 상태 변경 및 취약 카운트/점수 확인 -> 실제 OS 값 변경 확인
    5) 원복: 테스트 실패/중단 시에도 원래 값으로 복구
    """
    run_standard_vulnerable_to_safe_flow(
        check_num=34,
        item_keyword="윈도우 자동 업데이트 설정 여부",
        handler=handler,
        state_guard=state_guard,
    )

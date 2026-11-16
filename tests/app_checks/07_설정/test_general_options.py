"""
설정 > 일반 옵션 및 완료 팝업 분기 테스트 (Row 59~60)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_settings
@pytest.mark.skip(reason="구현 예정")
def test_auto_navigation_disabled_popup_flow():
    """자동 이동 해제 시 '결과 화면으로 이동' 팝업 출력 및 버튼 클릭 이동 검증"""
    pass

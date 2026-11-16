"""
점검 내역 엑셀 내보내기 및 파일 정합성 검증 테스트 (Row 45~47)
"""

import pytest


@pytest.mark.app_check
@pytest.mark.app_history
@pytest.mark.skip(reason="구현 예정")
def test_excel_export_dialog_and_popup():
    """엑셀 아이콘 클릭 -> 파일 저장 다이얼로그 -> 완료 팝업 출력 검증"""
    pass


@pytest.mark.app_check
@pytest.mark.app_history
@pytest.mark.skip(reason="구현 예정")
def test_excel_export_file_content_validation():
    """실제 저장된 엑셀 파일 파싱 후 점검 결과 데이터 정합성 검증"""
    pass

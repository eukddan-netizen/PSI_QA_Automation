"""
[대분류: 트레이 아이콘 > 중분류 2: 사용자 정보 입력] (Excel Row 12~15)

[정상 등록 계정 정보]
- 사번: 0014
- 이름: KYC

- Row 12 (2_0001): [웹뷰 진입] 트레이 > 사용자 정보 입력 웹뷰 정상 출력 검증
- Row 13 (2_0002): [필수 값 미입력] 사번/이름/둘 다 미입력 시 alert 팝업 검증
- Row 14 (2_0003): [잘못된 값 입력] 미등록 인사 정보 입력 후 저장 시 '등록된 인사 정보와 일치하지 않습니다' alert 팝업 검증
- Row 15 (2_0004): [정상 등록] 정상 인사 정보(0014 / KYC) 입력 후 저장 시 '정상 등록되었습니다' alert 팝업 검증
"""

import time
import pytest
from common.os_utils import require_admin

from core.app_controller import AppController
from pages.user_info_form_page import UserInfoFormPage


VALID_EMP_NO = "0014"
VALID_NAME = "KYC"
INVALID_EMP_NO = "9999"
INVALID_NAME = "홍길동"


@pytest.fixture(scope="module")
def user_form():
    """
    모듈 내 사용자 정보 입력 테스트(Row 12~15)를 위해:
    1. 트레이 아이콘 우클릭 > '사용자 정보 입력'을 직접 클릭하여 웹뷰 창을 열고
    2. UserInfoFormPage 객체를 제공합니다.
    3. 모듈 완료 시 열린 사용자 정보 창을 안전하게 닫습니다.
    """
    require_admin(
        "보안 에이전트(taAssistant) 트레이 우클릭 메뉴 제어를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    ctrl = AppController()
    ctrl.close_hr_ui()
    time.sleep(0.5)

    ctrl.click_tray_menu_item("사용자 정보 입력")
    time.sleep(1.5)

    form = UserInfoFormPage()
    assert form.is_visible(), "트레이 아이콘 > '사용자 정보 입력' 클릭 시 화면에 입력 창이 노출되어야 합니다."
    yield form

    try:
        ctrl.close_hr_ui()
    except Exception:
        pass


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_02
def test_row12_user_info_form_entry(user_form):
    """
    [Row 12: 2_0001]
    - 조건: 웹뷰 진입 (인사 UI 출력 정책 적용 상태)
    - 액션: 트레이 아이콘 > 사용자 정보 입력
    - 기대 결과: 사용자 입력 웹뷰 화면 정상 출력 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 웹뷰 창이 화면에 정상 출력되어야 합니다."


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_02
def test_row13_user_info_required_fields_validation(user_form):
    """
    [Row 13: 2_0002]
    - 조건: 필수 값 미입력
    - 액션: 1. 둘 다 미입력 / 2. 이름 미입력 / 3. 사번 미입력 후 저장
    - 기대 결과: '사번 or 이름을 입력하세요.' alert 팝업 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 창이 열려 있어야 합니다."

    user_form.fill_form(emp_no="", name="")
    user_form.click_save()
    alert1 = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert1 and any(k in alert1 for k in ["사번", "번호", "이름", "입력"]), (
        f"미입력 alert 팝업이 노출되어야 합니다. (실제: {alert1})"
    )

    user_form.fill_form(emp_no=VALID_EMP_NO, name="")
    user_form.click_save()
    alert2 = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert2 and any(k in alert2 for k in ["이름", "입력"]), (
        f"이름 미입력 alert 팝업이 노출되어야 합니다. (실제: {alert2})"
    )

    user_form.fill_form(emp_no="", name=VALID_NAME)
    user_form.click_save()
    alert3 = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert3 and any(k in alert3 for k in ["사번", "번호", "입력"]), (
        f"사번 미입력 alert 팝업이 노출되어야 합니다. (실제: {alert3})"
    )


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_02
def test_row14_user_info_invalid_data_validation(user_form):
    """
    [Row 14: 2_0003]
    - 조건: 잘못된 값 입력
    - 액션: 미등록 인사 정보(9999 / 홍길동) 입력 후 저장
    - 기대 결과: '등록된 인사 정보와 일치하지 않습니다' alert 팝업 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 창이 열려 있어야 합니다."

    user_form.fill_form(emp_no=INVALID_EMP_NO, name=INVALID_NAME)
    user_form.click_save()
    alert = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert and ("일치하지 않습니다" in alert or "미등록" in alert or "확인" in alert), (
        f"일치하지 않음 alert 팝업이 노출되어야 합니다. (실제: {alert})"
    )


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_02
def test_row15_user_info_success_registration(user_form):
    """
    [Row 15: 2_0004]
    - 조건: 정상 등록
    - 액션: 등록되어 있는 정상 인사 정보(0014 / KYC) 입력 후 저장
    - 기대 결과: '정상 등록되었습니다' alert 팝업 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 창이 열려 있어야 합니다."

    user_form.fill_form(emp_no=VALID_EMP_NO, name=VALID_NAME)
    user_form.click_save()
    alert = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert and ("정상 등록" in alert or "성공" in alert or "등록되었습니다" in alert), (
        f"정상 등록 alert 팝업이 노출되어야 합니다. (실제: {alert})"
    )


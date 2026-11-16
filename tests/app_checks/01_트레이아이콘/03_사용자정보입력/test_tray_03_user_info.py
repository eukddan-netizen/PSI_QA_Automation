"""
[대분류: 트레이 아이콘 > 중분류 3: 사용자 정보 입력]

[정상 등록 계정 정보]
- 관리자 웹(/pcsafe)에서 현재 PC IP 검색 후 사용자 정보 모달에서 사번/사용자명을 동적으로 조회

- 3_0001: [웹뷰 진입] 트레이 > 사용자 정보 입력 웹뷰 정상 출력 검증
- 3_0002: [필수 값 미입력] 사번/이름/둘 다 미입력 시 alert 팝업 검증
- 3_0003: [잘못된 값 입력] 미등록 인사 정보 입력 후 저장 시 '등록된 인사 정보와 일치하지 않습니다' alert 팝업 검증
- 3_0004: [정상 등록] 조회된 정상 인사 정보(사번 / 사용자명) 입력 후 저장 시 '정상 등록되었습니다' alert 팝업 검증
"""

import time
import pytest
from common.os_utils import require_admin

from core.app_controller import AppController
from pages.client.tray.user_info_form_page import UserInfoFormPage


INVALID_EMP_NO = "9999"
INVALID_NAME = "홍길동"


@pytest.fixture(scope="module")
def valid_user_info(admin_page):
    """
    관리자 웹(/pcsafe)에 접속해 현재 PC IP 사용자의 '사용자 정보' 모달에서
    사번(emp_no)과 사용자명(username)을 동적으로 조회합니다.
    """
    info = admin_page.get_user_modal_info()
    emp_no = info.get("emp_no", "").strip()
    username = info.get("username", "").strip()
    assert emp_no and username, (
        f"관리자 웹(/pcsafe) 사용자 정보 모달에서 사번/사용자명을 조회할 수 없습니다: {info}"
    )
    return {"emp_no": emp_no, "username": username}


@pytest.fixture(scope="module")
def user_form():
    """
    모듈 내 사용자 정보 입력 테스트(3_0001~3_0004)를 위해:
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
@pytest.mark.tray_03
def test_row12_user_info_form_entry(user_form):
    """
    [TC: 3_0001]
    - 조건: 웹뷰 진입 (인사 UI 출력 정책 적용 상태)
    - 액션: 트레이 아이콘 > 사용자 정보 입력
    - 기대 결과: 사용자 입력 웹뷰 화면 정상 출력 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 웹뷰 창이 화면에 정상 출력되어야 합니다."


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_03
def test_row13_user_info_required_fields_validation(user_form, valid_user_info):
    """
    [TC: 3_0002]
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

    user_form.fill_form(emp_no=valid_user_info["emp_no"], name="")
    user_form.click_save()
    alert2 = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert2 and any(k in alert2 for k in ["이름", "입력"]), (
        f"이름 미입력 alert 팝업이 노출되어야 합니다. (실제: {alert2})"
    )

    user_form.fill_form(emp_no="", name=valid_user_info["username"])
    user_form.click_save()
    alert3 = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert3 and any(k in alert3 for k in ["사번", "번호", "입력"]), (
        f"사번 미입력 alert 팝업이 노출되어야 합니다. (실제: {alert3})"
    )


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_03
def test_row14_user_info_invalid_data_validation(user_form):
    """
    [TC: 3_0003]
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
@pytest.mark.tray_03
def test_row15_user_info_success_registration(user_form, valid_user_info):
    """
    [TC: 3_0004]
    - 조건: 정상 등록
    - 액션: 관리자 웹에서 조회된 정상 인사 정보(사번 / 사용자명) 입력 후 저장
    - 기대 결과: '정상 등록되었습니다' alert 팝업 확인
    """
    assert user_form.is_visible(), "사용자 정보 입력 창이 열려 있어야 합니다."

    user_form.fill_form(emp_no=valid_user_info["emp_no"], name=valid_user_info["username"])
    user_form.click_save()
    alert = user_form.get_alert_text_and_accept(timeout=5.0)
    assert alert and ("정상 등록" in alert or "성공" in alert or "등록되었습니다" in alert), (
        f"정상 등록 alert 팝업이 노출되어야 합니다. (실제: {alert})"
    )


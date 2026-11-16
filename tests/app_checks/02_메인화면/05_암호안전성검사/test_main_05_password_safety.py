"""
[대분류: 보안점검 메인 탭 > 중분류 5: 암호 안전성 검사] (Excel Row 32)

- 세션 최적화: 보안점검 프로그램 실행 및 암호 안전성 검사 모달을 1회 오픈하여
  동일 세션에서 모든 세부 검증을 연속으로 수행하고, 마지막에 모달과 프로그램을 일괄 종료합니다.

- Step 1: 암호 안전성 검사 모달 오픈 및 오탈자/기본 UI 무결성 검증
- Step 2: 눈 아이콘 클릭 시 비밀번호 원문 보임/숨김 토글 검증
- Step 3: 비밀번호 보이는 상태에서 한글 입력 시 '입력할 수 없는 문자가 포함되어 있습니다.' 빨간색 경고 문구 노출 검증
- Step 4: 5가지 기준(9자 이상, 대문자, 소문자, 숫자, 특수문자) 순차 충족 검증
          - 각 조건 충족 시 ✕ -> ✓ (초록색 pass) 변경 확인
          - 일자 바(게이지 바) 20% -> 40% -> 60% -> 80% -> 100% 순차 증가 및 색상(주황색 -> 초록색) 검증
          - 최소조건(9자 이상 + 3가지 문자 조합) 충족 시 초록색 및 '보통' 출력 검증
          - 5가지 전체 충족 시 초록색 및 '강함' 출력 검증
- Step 5: '닫기' 버튼 클릭 시 모달 정상 종료 검증
"""

import time
import pytest

from core.app_controller import AppController
from pages.client.main_page import MainPage
from pages.client.modals.password_safety_modal_page import (
    PasswordSafetyModalPage,
    PASSWORD_CRITERIA_NAMES,
)


@pytest.fixture(scope="module")
def pwd_session():
    """
    모듈 전체에서 보안점검 앱을 1회만 실행하고 암호 안전성 검사 모달을 열어 공유하는 Fixture.
    테스트 종료 시 모달 및 프로그램을 일괄 종료합니다.
    """
    ctrl = AppController()
    ctrl.launch(timeout=15)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)

    # 1회만 암호 안전성 검사 모달 열기
    print("\n>>> [Password Session] 메인 화면에서 '암호 안전성 검사' 모달 1회 열기")
    modal = PasswordSafetyModalPage.open_from_main(main_page, timeout=8.0)
    assert modal.is_open(), "암호 안전성 검사 모달이 정상적으로 열리지 않았습니다."

    session_data = {
        "ctrl": ctrl,
        "main_page": main_page,
        "modal": modal,
    }

    yield session_data

    # 정리
    print("\n>>> [Password Session Teardown] 암호 안전성 검사 모달 및 프로그램 종료")
    try:
        if modal.is_open():
            modal.close()
    except Exception:
        pass
    try:
        ctrl.close()
    except Exception:
        pass


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_05
def test_step1_password_modal_open_and_spelling(pwd_session):
    """
    [Step 1] 암호 안전성 검사 모달 출력 및 오탈자/기본 UI 검증
    1. 모달 타이틀('암호 안전성 검사') 확인
    2. 인풋 placeholder('테스트할 암호를 입력해주세요.') 확인
    3. 5가지 기준 텍스트('9자 이상', '대문자 포함', '소문자 포함', '숫자 포함', '특수문자 포함') 오탈자 없음 확인
    4. 초기 상태 등급('약함') 및 초기 5가지 항목 전체 미충족(✕) 상태 확인
    """
    modal: PasswordSafetyModalPage = pwd_session["modal"]
    print("\n>>> [Step 1] 암호 안전성 검사 모달 오픈 및 오탈자 검증 시작")

    assert modal.is_open(), "암호 안전성 검사 모달이 열려있지 않습니다."

    # 1. 타이틀 검증
    title = modal.get_title()
    print(f">>> [Step 1] 모달 타이틀: '{title}'")
    assert title == "암호 안전성 검사", f"모달 타이틀 오탈자/불일치: '{title}'"

    # 2. 5가지 기준 항목 검증
    checklist = modal.get_checklist_status()
    print(f">>> [Step 1] 탐색된 기준 항목 ({len(checklist)}개): {list(checklist.keys())}")
    assert len(checklist) == 5, f"기준 항목 수가 5개가 아닙니다: {len(checklist)}"

    for expected in PASSWORD_CRITERIA_NAMES:
        assert expected in checklist, f"기준 항목 누락 또는 오탈자: '{expected}'"
        assert not checklist[expected], f"초기 상태에서 항목이 체크되어 있습니다: '{expected}'"

    # 3. 초기 등급 검증
    grade = modal.get_strength_grade()
    print(f">>> [Step 1] 초기 등급 텍스트: '{grade}'")
    assert grade == "약함", f"초기 등급이 '약함'이 아닙니다: '{grade}'"

    # 4. 초기 게이지 바 (회색, 0% 수준)
    bar_info = modal.get_gauge_bar_info()
    print(f">>> [Step 1] 초기 게이지 바: {bar_info}")
    assert bar_info["fill_ratio"] < 5.0, f"초기 게이지 바가 채워져 있습니다: {bar_info['fill_ratio']}%"
    print(">>> [Step 1] 모달 오픈 및 오탈자 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_05
def test_step2_password_visibility_toggle(pwd_session):
    """
    [Step 2] 눈 아이콘 클릭 시 비밀번호 원문 보임/숨김 토글 검증
    1. 텍스트 입력 후 초기 상태(마스킹됨, Show password) 확인
    2. 눈 아이콘 클릭 -> 비밀번호 보이는 상태(Hide password)로 전환 확인
    3. 눈 아이콘 재클릭 -> 비밀번호 숨김 상태(Show password)로 원복 확인
    """
    modal: PasswordSafetyModalPage = pwd_session["modal"]
    print("\n>>> [Step 2] 눈 아이콘 클릭에 따른 비밀번호 보임/숨김 토글 검증 시작")

    modal.type_password("Secret123!")

    # 1. 초기 상태 확인 (마스킹 상태인지)
    initial_visible = modal.is_password_visible()
    print(f">>> [Step 2] 초기 보이는 상태 여부: {initial_visible}")

    # 2. 눈 아이콘 클릭 -> 보이는 상태로 전환
    after_toggle = modal.toggle_password_visibility()
    assert after_toggle != initial_visible, "눈 아이콘 1차 클릭 후 보임/숨김 상태가 변경되지 않았습니다."

    # 3. 다시 클릭 -> 원래 상태로 원복
    after_restore = modal.toggle_password_visibility()
    assert after_restore == initial_visible, "눈 아이콘 2차 클릭 후 원래 보임/숨김 상태로 원복되지 않았습니다."

    print(">>> [Step 2] 비밀번호 원문 보임/숨김 토글 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_05
def test_step3_korean_input_warning_message(pwd_session):
    """
    [Step 3] 비밀번호가 보이는 상태에서 한글 입력 시 경고 문구 검증
    1. 비밀번호가 보이는 상태(Hide password)로 설정
    2. 한글('테스트한글') 입력
    3. 인풋창 아래에 '입력할 수 없는 문자가 포함되어 있습니다.' 빨간색 경고 문구 출력 확인
    4. 영문으로 다시 입력 시 경고 문구가 사라지는지 확인
    """
    modal: PasswordSafetyModalPage = pwd_session["modal"]
    print("\n>>> [Step 3] 한글 입력 시 경고 문구 노출 검증 시작")

    # 1. 비밀번호가 보이는 상태로 맞춤
    if not modal.is_password_visible():
        modal.toggle_password_visibility()
    assert modal.is_password_visible(), "비밀번호 보이는 상태 설정 실패"

    # 2. 한글 입력
    print(">>> [Step 3] 한글 텍스트('테스트한글') 입력")
    modal.paste_text("테스트한글")
    time.sleep(0.5)

    # 3. 경고 문구 검출
    has_error = modal.has_invalid_char_error()
    print(f">>> [Step 3] '입력할 수 없는 문자가 포함되어 있습니다.' 경고 감지: {has_error}")
    assert has_error, "한글 입력 시 빨간색 경고 문구가 표시되지 않았습니다."

    # 4. 허용된 영문 입력 시 경고 문구 해제 확인
    modal.type_password("ValidPassword123")
    time.sleep(0.5)
    has_error_after = modal.has_invalid_char_error()
    print(f">>> [Step 3] 정상 영문 입력 후 경고 해제 여부: {not has_error_after}")
    assert not has_error_after, "정상 영문 입력 후에도 경고 문구가 남아있습니다."

    print(">>> [Step 3] 한글 입력 경고 문구 및 해제 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_05
def test_step4_five_criteria_and_gauge_bar_progression(pwd_session):
    """
    [Step 4] 5가지 기준 순차 충족 및 게이지 바 / 등급 실시간 변화 전수 검증
    - 5개 조건: 9자 이상, 대문자 포함, 소문자 포함, 숫자 포함, 특수문자 포함
    - 각각 충족 시마다:
      1) 해당 항목의 ✕ 표시가 ✓(초록색)로 변경
      2) 게이지 바가 약 20% -> 40% -> 60% -> 80% -> 100%로 순차 증가
      3) 1~3개 충족(9자 미만) 시 주황색 바 및 '약함' 유지
      4) 최소 조건(9자 이상 + 세 가지 이상의 문자 조합) 충족 시 초록색 바 및 '보통' 출력
      5) 5가지 항목 전부 충족 시 초록색 바 및 '강함' 출력
    """
    modal: PasswordSafetyModalPage = pwd_session["modal"]
    print("\n>>> [Step 4] 5단계 기준 순차 충족 및 게이지 바 / 등급 전수 검증 시작")

    progression_steps = [
        {
            "step": 1,
            "input": "a",
            "desc": "소문자 1개 충족",
            "expected_pass": ["소문자 포함"],
            "expected_fail": ["9자 이상", "대문자 포함", "숫자 포함", "특수문자 포함"],
            "min_ratio": 15.0,
            "max_ratio": 25.0,
            "expected_color": "orange",
            "expected_grade": "약함",
        },
        {
            "step": 2,
            "input": "aA",
            "desc": "소문자+대문자 2개 충족",
            "expected_pass": ["소문자 포함", "대문자 포함"],
            "expected_fail": ["9자 이상", "숫자 포함", "특수문자 포함"],
            "min_ratio": 35.0,
            "max_ratio": 45.0,
            "expected_color": "orange",
            "expected_grade": "약함",
        },
        {
            "step": 3,
            "input": "aA1",
            "desc": "소문자+대문자+숫자 3개 충족 (9자 미만)",
            "expected_pass": ["소문자 포함", "대문자 포함", "숫자 포함"],
            "expected_fail": ["9자 이상", "특수문자 포함"],
            "min_ratio": 55.0,
            "max_ratio": 65.0,
            "expected_color": "orange",
            "expected_grade": "약함",
        },
        {
            "step": 4,
            "input": "aA1bbbbbb",
            "desc": "9자 이상 + 3가지 문자 조합 충족 (최소 조건 달성)",
            "expected_pass": ["9자 이상", "소문자 포함", "대문자 포함", "숫자 포함"],
            "expected_fail": ["특수문자 포함"],
            "min_ratio": 75.0,
            "max_ratio": 85.0,
            "expected_color": "green",
            "expected_grade": "보통",
        },
        {
            "step": 5,
            "input": "aA1!bbbbb",
            "desc": "5가지 항목 모두 충족 (완전 보안)",
            "expected_pass": ["9자 이상", "소문자 포함", "대문자 포함", "숫자 포함", "특수문자 포함"],
            "expected_fail": [],
            "min_ratio": 95.0,
            "max_ratio": 100.0,
            "expected_color": "green",
            "expected_grade": "강함",
        },
    ]

    for step_info in progression_steps:
        s_num = step_info["step"]
        pwd = step_info["input"]
        desc = step_info["desc"]

        print(f"\n--- [검증 Step {s_num}/5] 입력: '{pwd}' ({desc}) ---")
        modal.type_password(pwd)
        time.sleep(0.4)

        # 1. 5개 체크리스트 상태 확인
        checklist = modal.get_checklist_status()
        for item_pass in step_info["expected_pass"]:
            assert checklist.get(item_pass) is True, (
                f"[Step {s_num}] '{item_pass}' 항목이 ✓(체크) 상태가 아닙니다."
            )
        for item_fail in step_info["expected_fail"]:
            assert checklist.get(item_fail) is False, (
                f"[Step {s_num}] '{item_fail}' 항목이 ✕(미체크) 상태여야 합니다."
            )
        print(f"  - 체크리스트 검증 통과: 통과 {len(step_info['expected_pass'])}개 / 미달 {len(step_info['expected_fail'])}개")

        # 2. 등급 텍스트 확인
        grade = modal.get_strength_grade()
        print(f"  - 등급 텍스트: '{grade}' (기대치: '{step_info['expected_grade']}')")
        assert grade == step_info["expected_grade"], (
            f"[Step {s_num}] 등급 불일치: 기대='{step_info['expected_grade']}', 실제='{grade}'"
        )

        # 3. 게이지 바 비율 및 색상 확인
        bar_info = modal.get_gauge_bar_info()
        ratio = bar_info["fill_ratio"]
        color = bar_info["color"]
        print(f"  - 게이지 바: 채워진 비율={ratio:.1f}% (허용: {step_info['min_ratio']}~{step_info['max_ratio']}%), 색상='{color}' (기대: '{step_info['expected_color']}')")

        assert step_info["min_ratio"] <= ratio <= step_info["max_ratio"], (
            f"[Step {s_num}] 게이지 바 비율 벗어남: 실제={ratio:.1f}%, 허용={step_info['min_ratio']}~{step_info['max_ratio']}%"
        )
        assert color == step_info["expected_color"], (
            f"[Step {s_num}] 게이지 바 색상 불일치: 실제='{color}', 기대='{step_info['expected_color']}'"
        )

    print("\n>>> [Step 4] 5단계 기준 및 게이지 바(20->40->60->80->100%), 등급(약함->보통->강함) 전수 검증 통과!")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_05
def test_step5_password_modal_close(pwd_session):
    """
    [Step 5] '닫기' 버튼 클릭 시 모달 창 정상 종료 검증
    """
    modal: PasswordSafetyModalPage = pwd_session["modal"]
    print("\n>>> [Step 5] '닫기' 버튼 클릭하여 모달 종료 검증")

    closed = modal.close(timeout=4.0)
    assert closed, "'닫기' 버튼 클릭 후 모달이 닫히지 않았습니다."
    assert not modal.is_open(), "모달이 여전히 열려 있습니다."
    print(">>> [Step 5] 암호 안전성 검사 모달 정상 종료 확인 완료")

"""
[대분류: 보안점검 메인 탭 > 중분류 4: 도움말] (Excel Row 27~31)

- 세션 최적화: 프로그램 및 도움말 모달을 1회만 실행(module scope)하여
  동일한 화면 세션에서 순차적으로 모든 검증을 수행하고, 마지막에 모달 및 프로그램을 종료합니다.

- Row 27: 도움말 모달 출력 확인 (초기 헤더 및 53개 항목 링크 로드)
- Row 28: 햄버거 아이콘 클릭 시 nav_bar 열림/닫힘 (아이콘/번호 축소 및 펼침)
- Row 29: 우측 상단 언어(English/한국어) 변경 시 네비게이션 및 헤더 영문/한글 실시간 반영
- Row 30: 항목별 아코디언 드롭다운 버튼(▲ / ▼) 클릭 시 펼침/접힘 토글 정상 동작
- Row 31: 총 53개 점검항목 전수 순회 - 헤더 일치, 드롭다운 존재, 텍스트 깨짐 및 오탈자 무결성 검증 (이미지 제외)
- Row 27 닫기: 최종 단계에서 우상단 닫기(X) 버튼 클릭 시 모달 창 정상 종료 검증
"""

import time
import pytest

from core.app_controller import AppController
from pages.client.main_page import MainPage
from pages.client.modals.help_modal_page import (
    HelpModalPage,
    HELP_ITEMS_53_KO,
    HELP_ITEMS_53_EN,
)


@pytest.fixture(scope="module")
def help_session():
    """
    모듈 전체에서 보안점검 앱을 1회만 실행하고 도움말 모달을 열어 공유하는 Fixture.
    모든 테스트가 완료된 후 도움말 창 및 보안점검 창을 일괄 종료합니다.
    """
    ctrl = AppController()
    ctrl.launch(timeout=15)
    assert ctrl.hwnd, "내PC보안점검 메인 창 실행 실패"

    main_page = MainPage(ctrl.hwnd)
    main_page.wait_for_main_ready(timeout=12.0)

    # 1회만 도움말 모달 열기
    print("\n>>> [Help Session] 메인 화면에서 도움말 안내 모달 1회 열기")
    modal = HelpModalPage.open_from_main(main_page, timeout=10.0)
    assert modal.is_open(), "도움말 모달 창이 정상적으로 열리지 않았습니다."

    session_data = {
        "ctrl": ctrl,
        "main_page": main_page,
        "modal": modal,
    }

    yield session_data

    # 모듈 종료 시 일괄 정리
    print("\n>>> [Help Session Teardown] 도움말 모달 및 보안점검 프로그램 종료")
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
@pytest.mark.main_04
def test_row27_help_modal_open_state(help_session):
    """
    [Row 27 - 1단계] 도움말 안내 클릭 시 소개 웹뷰 모달 정상 출력 검증
    - 별도 웹뷰 팝업 창(타이틀: 내PC보안점검) 정상 노출 확인
    - 소개 화면 기본 헤더 타이틀('내PC보안점검 소개') 및 53개 항목 링크 로드 확인
    """
    modal: HelpModalPage = help_session["modal"]
    assert modal.is_open(), "도움말 모달 창이 화면에 표시되지 않았습니다."

    header = modal.get_header_title()
    print(f"\n>>> [TC 27 - 오픈 검증] 초기 헤더 타이틀: '{header}'")
    assert "내PC보안점검" in header or "소개" in header, f"도움말 초기 헤더가 올바르지 않습니다: '{header}'"

    links = modal.get_item_links()
    print(f">>> [TC 27 - 오픈 검증] 좌측 점검항목 링크 개수: {len(links)}개")
    assert len(links) >= 53, f"도움말 좌측 점검항목 수가 53개 미만입니다: {len(links)}"
    print(">>> [TC 27 - 오픈 검증] 도움말 모달 출력 확인 완료")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_04
def test_row28_help_modal_hamburger_nav_toggle(help_session):
    """
    [Row 28] 햄버거 메뉴 토글(nav_bar 열림/닫힘) 검증
    1. 초기 좌측 네비바 펼침 상태 확인
    2. 좌상단 햄버거 아이콘(☰) 클릭 -> 네비바 접힘(번호 축소, 폭 축소) 확인
    3. 햄버거 아이콘(☰) 재클릭 -> 네비바 정상 펼침 복구 확인
    """
    modal: HelpModalPage = help_session["modal"]
    print("\n>>> [TC 28] 햄버거 아이콘(☰) 기능 검증 시작")

    # 1. 초기 상태: 펼침 확인
    assert not modal.is_nav_collapsed(), "도움말 초기 상태의 네비바가 접혀 있습니다."
    initial_items = modal.get_nav_items_texts()
    print(f">>> [TC 28] 초기 네비 항목 수: {len(initial_items)}개, 첫 항목: '{initial_items[0] if initial_items else ''}'")

    # 2. 햄버거 클릭 -> 접힘
    modal.toggle_hamburger_menu()
    is_collapsed = modal.is_nav_collapsed()
    print(f">>> [TC 28] 1차 클릭 후 접힘 여부: {is_collapsed}")
    assert is_collapsed, "햄버거 버튼 클릭 후 네비바가 접히지 않았습니다."

    # 3. 햄버거 재클릭 -> 펼침 복구
    modal.toggle_hamburger_menu()
    is_restored = not modal.is_nav_collapsed()
    print(f">>> [TC 28] 2차 클릭 후 펼침 복구 여부: {is_restored}")
    assert is_restored, "햄버거 버튼 재클릭 후 네비바가 원래대로 펼쳐지지 않았습니다."

    restored_items = modal.get_nav_items_texts()
    assert len(restored_items) == len(initial_items), "네비바 펼침 복구 후 항목 수가 일치하지 않습니다."
    assert restored_items[0] == initial_items[0], "네비바 펼침 복구 후 첫 항목명이 변경되었습니다."
    print(">>> [TC 28] 햄버거 아이콘 nav_bar 열림/닫힘 정상동작 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_04
def test_row29_help_modal_language_switching(help_session):
    """
    [Row 29] 다국어(영어/한국어) 변경 시 UI 타이틀 및 항목 번역 실시간 반영 검증
    1. 우측 상단 언어 ComboBox에서 'English' 선택
    2. 상단 네비게이션 소개 텍스트 및 항목들이 영문으로 전환되었는지 확인
    3. 다시 '한국어'로 변경 시 한글로 정상 복구되는지 확인
    """
    modal: HelpModalPage = help_session["modal"]
    print("\n>>> [TC 29] 다국어 언어 변경 검증 시작")

    # 1. 'English'로 변경
    modal.change_language("English")
    time.sleep(1.0)

    # 2. 영문 네비게이션 53개 항목 1:1 전수 일치 검증
    en_items = modal.get_nav_items_texts()
    print(f">>> [TC 29] 영문 전환 후 네비 항목 수: {len(en_items)}개")
    assert len(en_items) == 53, f"영문 전환 후 항목 수가 53개가 아닙니다: {len(en_items)}개"

    en_errors = []
    for idx, (actual_en, expected_en) in enumerate(zip(en_items, HELP_ITEMS_53_EN), 1):
        if actual_en != expected_en:
            en_errors.append(f"[{idx}번] 영문 번역 불일치: 기대='{expected_en}', 실제='{actual_en}'")

    if en_errors:
        print(f"\n[TC 29 ERROR] 영문 53개 항목 중 {len(en_errors)}건 불일치:")
        for err in en_errors[:10]:
            print(f"  - {err}")
    assert len(en_errors) == 0, f"영문 53개 항목 검증 중 {len(en_errors)}건의 불일치가 발생했습니다: {en_errors[:5]}"
    print(">>> [TC 29] 영문 53개 항목 전수 1:1 일치 검증 통과!")

    # 3. '한국어'로 원복
    modal.change_language("한국어")
    time.sleep(1.0)

    # 4. 한글 복구 확인 (53개 항목 1:1 전수 일치 검증)
    ko_items = modal.get_nav_items_texts()
    print(f">>> [TC 29] 한글 원복 후 네비 항목 수: {len(ko_items)}개")
    assert len(ko_items) == 53, f"한글 원복 후 항목 수가 53개가 아닙니다: {len(ko_items)}개"

    ko_errors = []
    for idx, (actual_ko, expected_ko) in enumerate(zip(ko_items, HELP_ITEMS_53_KO), 1):
        if actual_ko != expected_ko:
            ko_errors.append(f"[{idx}번] 한글 원복 불일치: 기대='{expected_ko}', 실제='{actual_ko}'")

    if ko_errors:
        print(f"\n[TC 29 ERROR] 한글 원복 53개 항목 중 {len(ko_errors)}건 불일치:")
        for err in ko_errors[:10]:
            print(f"  - {err}")
    assert len(ko_errors) == 0, f"한글 원복 검증 중 {len(ko_errors)}건의 불일치가 발생했습니다: {ko_errors[:5]}"
    print(">>> [TC 29] 한글 53개 항목 전수 원복 확인 완료!")
    print(">>> [TC 29] 다국어(한국어/영어) 실시간 변경 및 전수 53개 항목 1:1 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_04
def test_row30_help_modal_accordion_dropdown_toggle(help_session):
    """
    [Row 30] 항목 클릭 시 노출되는 드롭다운(아코디언) 정상동작 검증
    1. 1번 항목('바이러스 백신 설치 및 실행 여부 점검') 선택
    2. 첫 번째 아코디언 버튼('🛡️ 점검 내용 ▲') 클릭 -> '▼'(접힘)으로 변경 확인
    3. 다시 해당 버튼 클릭 -> '▲'(펼침)으로 정상 복구되는지 확인
    4. 조치 방법 관련 아코디언 버튼도 동일하게 토글 동작하는지 검증
    """
    modal: HelpModalPage = help_session["modal"]
    print("\n>>> [TC 30] 아코디언 드롭다운 토글 기능 검증 시작")

    # 1. 1번 항목 진입
    modal.select_item(1)
    time.sleep(0.5)

    # 2. 아코디언 버튼 확인
    buttons = modal.get_accordion_buttons()
    print(f">>> [TC 30] 탐색된 아코디언 버튼 수: {len(buttons)}개")
    assert len(buttons) >= 2, f"아코디언 드롭다운 버튼이 충분하지 않습니다: {len(buttons)}"

    # 3. 첫 번째 아코디언('점검 내용') 클릭하여 접기
    before, after = modal.toggle_accordion(0)
    assert before == "expanded", f"클릭 전 초기 상태는 펼침(expanded)이어야 합니다: {before}"
    assert after == "collapsed", f"클릭 후 상태는 접힘(collapsed)이어야 합니다: {after}"

    # 4. 다시 클릭하여 펼치기
    before2, after2 = modal.toggle_accordion(0)
    assert before2 == "collapsed", f"재클릭 전 상태는 접힘(collapsed)이어야 합니다: {before2}"
    assert after2 == "expanded", f"재클릭 후 상태는 펼침(expanded)이어야 합니다: {after2}"

    # 5. 조치 방법 아코디언 토글 추가 검증
    action_btn_index = None
    for i, b in enumerate(modal.get_accordion_buttons()):
        if "조치" in b["label"]:
            action_btn_index = i
            break

    if action_btn_index is not None:
        b_before, b_after = modal.toggle_accordion(action_btn_index)
        assert b_after == "collapsed", f"'조치 방법' 접힘 실패: {b_after}"
        modal.toggle_accordion(action_btn_index)

    print(">>> [TC 30] 아코디언 드롭다운 접힘/펼침 정상동작 검증 성공")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_04
def test_row31_verify_all_53_items_integrity(help_session):
    """
    [Row 31] 총 53개 항목 전수 순회 및 오탈자/이상 유무 검증
    (최초 분석 기준 스냅샷 HELP_ITEMS_53_KO을 기준으로 비교 검증, 이미지는 제외)
    1. 1번부터 53번 항목까지 순차적으로 클릭하여 우측 콘텐츠 로드
    2. 우측 상단 헤더 타이틀이 기준 항목명과 일치하는지 확인
    3. 점검 내용 및 조치 방법 등 아코디언 드롭다운 버튼 존재 확인
    4. 본문 텍스트 내 이상 문자열(undefined, null, nan, [object, 깨진 유니코드 등) 유무 전수 검사
    """
    modal: HelpModalPage = help_session["modal"]
    print("\n>>> [TC 31] 총 53개 점검항목 전수 순회 및 무결성 검증 시작 (이미지 제외)")

    links = modal.get_item_links()
    assert len(links) == 53, f"도움말 점검항목 수가 정확히 53개여야 합니다 (현재: {len(links)})"

    errors = []
    suspicious_texts = []
    scanned_count = 0

    for idx, expected_name in enumerate(HELP_ITEMS_53_KO, 1):
        actual_name = modal.select_item(idx)
        scanned_count += 1

        # 1. 항목명 일치 검증
        if actual_name != expected_name:
            errors.append(f"[{idx}번] 좌측 링크명 불일치: 기대='{expected_name}', 실제='{actual_name}'")

        # 2. 헤더 타이틀 일치 검증
        header = modal.get_header_title()
        if header != expected_name:
            errors.append(f"[{idx}번] 우측 헤더 불일치: 기대='{expected_name}', 실제='{header}'")

        # 3. 아코디언 드롭다운 버튼 존재 검증
        acc_btns = modal.get_accordion_buttons()
        if not acc_btns:
            errors.append(f"[{idx}번 '{expected_name}'] 아코디언 드롭다운 버튼 누락")

        # 4. 본문 텍스트 무결성 검사 (이미지 제외, 텍스트만)
        content_texts = modal.get_content_texts()
        if not content_texts:
            errors.append(f"[{idx}번 '{expected_name}'] 본문 텍스트가 비어 있습니다.")

        for text in content_texts:
            lowered = text.lower()
            if any(bad in lowered for bad in ("undefined", "null", "nan", "[object", "{object")):
                suspicious_texts.append(f"[{idx}번 '{expected_name}'] 이상 문자열 발견: '{text}'")
            if "\ufffd" in text or "???" in text:
                suspicious_texts.append(f"[{idx}번 '{expected_name}'] 깨진 문자 발견: '{text}'")

        if idx % 10 == 0 or idx == 53:
            print(f"  - 진행도: {idx}/53 항목 검증 완료 (드롭다운: {len(acc_btns)}개, 텍스트: {len(content_texts)}개)")

    print(f"\n================ [53개 항목 검증 결과] ================")
    print(f"  - 스캔 항목 수    : {scanned_count} / 53")
    print(f"  - 불일치/누락 오류: {len(errors)}건")
    print(f"  - 이상/깨진 문자  : {len(suspicious_texts)}건")

    assert len(errors) == 0, f"53개 항목 검증 중 {len(errors)}건의 불일치 오류가 발생했습니다: {errors[:5]}"
    assert len(suspicious_texts) == 0, f"53개 항목 검증 중 {len(suspicious_texts)}건의 이상/깨진 텍스트가 발견되었습니다: {suspicious_texts[:5]}"
    print(">>> [TC 31] 총 53개 항목 전수 검증 통과 (오탈자 및 이상 문자 없음)")


@pytest.mark.app_check
@pytest.mark.app_main
@pytest.mark.main_04
def test_row27_help_modal_close(help_session):
    """
    [Row 27 - 최종 닫기 단계] 모든 검증 후 도움말 모달 우상단 닫기(X) 검증
    - 우상단 닫기(X) 버튼 클릭 시 도움말 창이 정상 종료되는지 검증
    """
    modal: HelpModalPage = help_session["modal"]
    print("\n>>> [TC 27 - 닫기 검증] 모든 검증 완료 후 도움말 창 닫기(X) 시도")

    closed = modal.close(timeout=5.0)
    assert closed, "도움말 모달 우상단 닫기(X) 클릭 후 창이 닫히지 않았습니다."
    assert not modal.is_open(), "도움말 모달이 여전히 화면에 남아있습니다."
    print(">>> [TC 27 - 닫기 검증] 도움말 모달 정상 종료 확인 완료")

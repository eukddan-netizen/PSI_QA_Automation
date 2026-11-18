"""
설정 > 외형 테마 및 버전 정보 테스트 (Row 61~65)
1. test_default_theme_is_dark:
   - 최초 실행/로딩 화면 배경이 다크 모드인지 검증
   - 설정 > 외형 기본 선택이 '다크 모드'이고 '시스템 테마'가 OS 설정과 일치('현재 시스템: 다크/라이트')하는지 검증
2. test_version_info_display:
   - 설정 > 정보 탭의 '앱 버전'과 관리자 웹(/manageAgent) '최근 등록 정보' 내 taKeeper.exe 버전 일치 검증
3. test_theme_mode_toggle_and_integrity:
   - '라이트 모드' 전환 및 재실행 후 영속성(초기 화면 포함) 검증
   - 라이트 모드 상태에서 전체 6개 탭(메인/점검/점검결과/점검이력/PC정리/설정) 및
     핵심 UI(방패, 차트, 모달, 실시간 점검, 결과 상세, 이력 상세, PC정리 시스템정보/체크박스) 무결성 검증
   - 종료 시 반드시 '다크 모드'로 원복
"""

import winreg
import pytest
from playwright.sync_api import sync_playwright

from core.desktop_utils import launch_visible_chrome
from pages.client.clean_page import CleanPage
from pages.client.history_page import HistoryPage
from pages.client.inspection_page import InspectionPage
from pages.client.inspection_result_page import InspectionResultPage
from pages.client.main_page import MainPage
from pages.client.modals.password_safety_modal_page import PasswordSafetyModalPage
from pages.client.settings_page import SettingsPage
from pages.server.manage_agent_page import AdminManageAgentPage


def _get_windows_apps_theme() -> str:
    """Windows 개인 설정 앱 테마(AppsUseLightTheme) 조회 -> '다크' 또는 '라이트'"""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "라이트" if int(val) == 1 else "다크"
    except Exception:
        return "다크"


def _assert_light_theme(settings_page: SettingsPage, label: str) -> None:
    snap = settings_page.get_theme_visual_snapshot()
    print(f">>> [라이트 모드 시각 확인 - {label}] {snap}")
    assert snap["is_light"], (
        f"[{label}] 화면 배경이 라이트 모드 밝기 기준(>190)을 충족하지 않습니다: {snap}"
    )


@pytest.mark.app_check
@pytest.mark.app_settings
def test_010_최초실행_기본테마_다크모드(settings_session):
    """
    [APP-07-02-010] 최초 실행 화면 및 설정 > 외형 기본값 다크 모드 검증
    """
    settings_page: SettingsPage = settings_session["settings_page"]
    launch_rgb = settings_session["launch_rgb"]
    dark_snap = settings_session["initial_dark_snap"]

    print(f"\n>>> [초기 실행/로딩 화면 중앙 RGB] {launch_rgb}")
    assert all(c < 90 for c in launch_rgb), (
        f"최초 실행/로딩 화면이 다크 모드가 아닙니다: RGB={launch_rgb}"
    )

    print(f">>> [메인 화면 다크 모드 RGB 스냅샷] {dark_snap}")
    assert dark_snap["is_dark"], f"메인 화면 배경이 다크 모드가 아닙니다: {dark_snap}"

    theme_state = settings_page.get_theme_options_state(timeout=10.0)
    print(f">>> [설정 > 외형 기본 상태] {theme_state}")
    assert theme_state["active_theme"] == "다크 모드", (
        f"기본 선택 테마가 '다크 모드'가 아닙니다: {theme_state['active_theme']}"
    )
    assert theme_state["options"]["다크 모드"]["has_active_badge"], (
        f"'다크 모드' 옵션에 '활성' 배지가 없습니다: {theme_state['options']['다크 모드']}"
    )

    expected_os_theme = _get_windows_apps_theme()
    sys_label = theme_state.get("system_theme_label") or ""
    assert expected_os_theme in sys_label, (
        f"'시스템 테마' 표기('{sys_label}')가 현재 Windows 시스템 테마('{expected_os_theme}')와 다릅니다."
    )


@pytest.mark.app_check
@pytest.mark.app_settings
def test_020_설정_정보탭_앱버전_서버일치(settings_session):
    """
    [APP-07-02-020] 설정 > 정보 탭 앱 버전과 관리자 웹 등록 에이전트 버전 일치 검증
    """
    settings_page: SettingsPage = settings_session["settings_page"]
    client_version = settings_page.get_app_version(timeout=10.0)
    print(f"\n>>> [설정 > 정보] 클라이언트 앱 버전: '{client_version}'")
    assert client_version, "클라이언트 '설정 > 정보' 탭에서 앱 버전을 읽지 못했습니다."

    proc = launch_visible_chrome(port=9222)
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()

            try:
                agent_page = AdminManageAgentPage(page)
                agent_page.login(username="admin", password="Qwe123!@#")
                agent_page.goto_manage_agent()
                reg_text = agent_page.get_recent_registration_text()
                modules = agent_page.get_registered_module_versions()
                server_takeeper_version = agent_page.get_module_version("taKeeper.exe")
                print(f">>> [관리자 웹 /manageAgent] 최근 등록 정보: {reg_text}")
                print(f">>> [관리자 웹 /manageAgent] 파싱된 모듈 버전: {modules}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    finally:
        proc.terminate()

    assert client_version == server_takeeper_version, (
        f"클라이언트 앱 버전('{client_version}')이 서버(/manageAgent) '최근 등록 정보'의 "
        f"taKeeper.exe 버전('{server_takeeper_version}')과 일치하지 않습니다."
    )
    print(f">>> [버전 일치 검증 성공] 클라이언트 == 서버(taKeeper.exe) == '{client_version}'")


@pytest.mark.app_check
@pytest.mark.app_settings
def test_030_라이트모드_전환_영속성_UI무결성(settings_session):
    """
    [APP-07-02-030] 라이트 모드 전환·재실행 영속성 및 전체 탭 UI 무결성 검증
    """
    ctrl = settings_session["ctrl"]
    settings_page: SettingsPage = settings_session["settings_page"]

    initial_state = settings_page.get_theme_options_state(timeout=10.0)
    print(f"\n>>> [초기 테마 상태] {initial_state['active_theme']}")

    try:
        # 1. 라이트 모드 선택 및 즉시 배경 전환 확인
        settings_page.select_theme("라이트 모드", timeout=8.0)
        light_state = settings_page.get_theme_options_state(timeout=8.0)
        assert light_state["active_theme"] == "라이트 모드"
        assert light_state["options"]["라이트 모드"]["has_active_badge"]
        _assert_light_theme(settings_page, "설정 > 외형 (전환 직후)")

        # 2. 앱 재실행 후 라이트 모드 영속성 확인 (영속성 검증을 위한 유일한 의도적 재실행)
        ctrl.close()
        ctrl.launch(timeout=20)
        assert ctrl.hwnd, "라이트 모드 재실행 후 메인 창 실행 실패"

        settings_page = SettingsPage(ctrl.hwnd)
        settings_session["settings_page"] = settings_page
        main_page = MainPage(ctrl.hwnd)
        main_info = main_page.wait_for_main_ready(timeout=15.0)
        _assert_light_theme(settings_page, "메인 (재실행 직후)")
        restarted_theme = settings_page.get_theme_options_state(timeout=8.0)
        assert restarted_theme["active_theme"] == "라이트 모드", (
            f"재실행 후 '라이트 모드' 설정이 유지되지 않았습니다: {restarted_theme['active_theme']}"
        )

        # 3. [메인 탭] 대시보드 정보, 방패, 차트, 암호안전성 모달 검증
        main_page.navigate_to_tab("메인", timeout=10.0)
        main_info = main_page.wait_for_main_ready(timeout=15.0)
        _assert_light_theme(settings_page, "메인")

        user_info = main_page.get_user_info()
        support_txt = main_page.get_support_inquiry_text()
        shield_main = main_page.get_shield_visual_state()
        radar_elem = main_page.get_radar_chart_element()
        history_bars = main_page.get_past_history_bars()
        print(
            f">>> [라이트 모드 메인 검증] info={main_info['status']}({main_info.get('score')}점), "
            f"shield={shield_main['state']}, user={user_info.get('username')}, "
            f"support='{support_txt}', bars={len(history_bars)}, radar={radar_elem.rectangle()}"
        )
        assert user_info.get("username") and user_info.get("ip")
        assert support_txt
        assert shield_main["state"] in ("양호", "위험", "대기"), f"방패 상태 이상: {shield_main}"

        # 암호 안전성 검사 모달: 오픈, 타이틀, 5대 기준/등급/게이지 바 렌더링 및 닫기 확인
        pwd_modal = PasswordSafetyModalPage.open_from_main(main_page, timeout=8.0)
        try:
            assert pwd_modal.get_title() == "암호 안전성 검사"
            checklist = pwd_modal.get_checklist_status()
            assert len(checklist) == 5, f"기준 항목 수 이상: {checklist}"
            assert pwd_modal.get_strength_grade() == "약함"
            bar = pwd_modal.get_gauge_bar_info()
            assert bar["color"] == "gray", f"라이트 모드 암호 초기 게이지 바 색상 이상: {bar}"
        finally:
            if pwd_modal.is_open():
                pwd_modal.close()

        # 4. [점검 탭] UI 렌더링 및 실시간 점검 -> 점검결과 자동 이동 검증
        insp_page = InspectionPage(ctrl.hwnd)
        insp_page.navigate_to_tab("점검", timeout=10.0)
        insp_status = insp_page.wait_for_inspection_ready(timeout=10.0)
        _assert_light_theme(settings_page, "점검")
        assert insp_status.get("total_count", 0) > 0

        insp_page.click_start_inspection_on_tab()
        progress = insp_page.monitor_inspection_progress(timeout=35.0)
        assert progress["reached_result_tab"], f"라이트 모드에서 점검 완료 후 결과 탭 이동 실패: {progress}"

        # 5. [점검결과 탭] 방패/요약/결과 테이블/상세보기 모달 검증
        result_page = InspectionResultPage(ctrl.hwnd)
        stats = result_page.wait_for_result_ready(timeout=12.0)
        _assert_light_theme(settings_page, "점검결과")
        shield_res = result_page.get_shield_visual_state()
        rows = result_page.get_all_result_rows()
        print(f">>> [라이트 모드 점검결과] stats={stats}, shield={shield_res['state']}, rows={len(rows)}")
        assert shield_res["state"] in ("양호", "위험"), f"점검결과 방패 상태 이상: {shield_res}"
        assert len(rows) == stats["total_num"]
        detail_desc = result_page.get_item_detail_description(check_num=rows[0]["no"], timeout=5.0)
        assert detail_desc, "라이트 모드 점검결과 '상세보기' 진단결과 모달 텍스트를 읽지 못했습니다."

        # 6. [점검이력 탭] 목록 및 상세 내역 뷰 검증
        history_page = HistoryPage(ctrl.hwnd)
        history_page.navigate_to_tab("점검이력", timeout=10.0)
        history_header = history_page.wait_for_history_list_ready(timeout=12.0)
        _assert_light_theme(settings_page, "점검이력(목록)")
        records = history_page.get_all_history_records()
        assert records and history_header.get("last_inspection_time")

        history_page.click_history_row(row_index=0, timeout=12.0)
        assert history_page.is_detail_view()
        _assert_light_theme(settings_page, "점검이력(상세)")
        detail_summary = history_page.get_detail_summary()
        assert detail_summary.get("score") is not None
        history_page.click_back_to_list(timeout=10.0)

        # 7. [PC정리 탭] 시스템 정보 카드 및 체크박스 UI 동작 검증 (실제 삭제 미수행)
        clean_page = CleanPage(ctrl.hwnd)
        clean_page.navigate_to_tab("PC정리", timeout=10.0)
        clean_page.wait_for_clean_ready(timeout=10.0)
        _assert_light_theme(settings_page, "PC정리")
        os_text = clean_page.get_os_version_text()
        avs = clean_page.get_antivirus_items()
        fws = clean_page.get_firewall_items()
        assert os_text and avs and fws
        clean_page.set_checkbox("Windows", True)
        assert clean_page.get_checkbox_state("휴지통 비우기") == 1
        clean_page.set_checkbox("Windows", False)
        assert clean_page.get_checkbox_state("휴지통 비우기") == 0

        # 8. [설정 탭] 일반 / 외형 / 정보 하위 탭 라이트 모드 렌더링 확인
        for sub in ("일반", "외형", "정보"):
            settings_page.open_sub_tab(sub, timeout=8.0)
            _assert_light_theme(settings_page, f"설정 > {sub}")
        assert settings_page.get_theme_options_state()["active_theme"] == "라이트 모드"
    finally:
        # 반드시 기본 테마('다크 모드')로 원복
        try:
            settings_page = SettingsPage(ctrl.hwnd)
            settings_page.dismiss_result_move_popup_if_present(timeout=1.0)
            try:
                _, win_f = settings_page._connect_window()
                for b in win_f.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() in ("확인", "닫기"):
                        b.invoke()
                        break
            except Exception:
                pass
            settings_page.select_theme("다크 모드", timeout=10.0)
            restored_snap = settings_page.get_theme_visual_snapshot()
            print(f">>> [Teardown] 다크 모드 원복 완료: {restored_snap}")
        except Exception as exc:
            print(f">>> [Teardown 경고] 다크 모드 원복 중 예외: {exc}")

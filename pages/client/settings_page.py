"""
보안점검 프로그램 '설정' 탭 페이지 Object
- 좌측 설정 하위 탭('일반', '외형', '정보') 전환
- '일반' 탭: '점검 후 결과 화면으로 자동 이동' 체크박스 제어 및 점검 완료 후 '결과 화면으로 이동' 팝업 제어
- '외형' 탭: '라이트 모드' / '다크 모드' / '시스템 테마' 상태 조회/전환 및 테마 배경 색상(RGB) 판별
- '정보' 탭: '앱 버전' 문자열 조회
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import win32gui
from PIL import ImageGrab

from pages.client.main_page import MainPage


class SettingsPage(MainPage):
    """'설정' 탭 전용 Page Object (MainPage 공통 기능 상속)"""

    AUTO_NAV_CHECKBOX_NAME = "점검 후 결과 화면으로 자동 이동"
    RESULT_POPUP_MESSAGE = "점검이 완료되었습니다. 결과 화면으로 이동합니다."
    RESULT_POPUP_BUTTON = "결과 화면으로 이동"
    THEME_OPTIONS = ("라이트 모드", "다크 모드", "시스템 테마")

    def _safe_descendants(self, win, control_type: Optional[str] = None, retries: int = 3) -> List[Any]:
        """크롬 웹뷰 UIA 일시적 control_type=None KeyError 방어 조회"""
        for _ in range(retries):
            try:
                if control_type:
                    return win.descendants(control_type=control_type)
                return win.descendants()
            except (KeyError, Exception):
                time.sleep(0.2)
        return []

    def wait_for_settings_ready(self, timeout: float = 10.0) -> None:
        """'설정' 탭 DOM(하위 메뉴 '일반', '외형', '정보') 렌더링 완료 대기"""
        deadline = time.time() + timeout
        while True:
            try:
                if self.get_active_tab_name() == "설정":
                    _, win = self._connect_window()
                    items = {(d.element_info.name or "").strip() for d in win.descendants(control_type="ListItem")}
                    if "일반" in items and "외형" in items and "정보" in items:
                        time.sleep(0.3)
                        return
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError("'설정' 탭 DOM 로딩 대기 시간 초과")
            time.sleep(0.3)

    def select_sub_tab(self, tab_name: str, timeout: float = 6.0) -> None:
        """'설정' 탭 좌측 하위 탭('일반', '외형', '정보') 클릭 및 활성화 대기"""
        self.wait_for_settings_ready(timeout=timeout)
        target_h, win = self._connect_window()

        target_item = None
        for item in win.descendants(control_type="ListItem"):
            if (item.element_info.name or "").strip() == tab_name:
                target_item = item
                break

        if target_item is None:
            raise RuntimeError(f"'설정' 탭에서 '{tab_name}' 하위 메뉴를 찾을 수 없습니다.")

        try:
            target_item.invoke()
        except Exception:
            self._click_element(target_item, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win_chk = self._connect_window()
            for item in win_chk.descendants(control_type="ListItem"):
                if (item.element_info.name or "").strip() == tab_name:
                    if "active" in (item.element_info.class_name or ""):
                        time.sleep(0.3)
                        return
            time.sleep(0.25)

        raise TimeoutError(f"'설정 > {tab_name}' 하위 탭 활성화 대기 시간 초과")

    def open_sub_tab(self, tab_name: str, timeout: float = 8.0) -> None:
        """'설정' 탭으로 이동한 뒤 지정 하위 탭('일반', '외형', '정보') 활성화"""
        if self.get_active_tab_name() != "설정":
            self.navigate_to_tab("설정", timeout=timeout)
        self.select_sub_tab(tab_name, timeout=timeout)

    # ------------------------------------------------------------------
    # 일반 옵션 ('점검 후 결과 화면으로 자동 이동') 및 완료 팝업 제어
    # ------------------------------------------------------------------
    def _find_auto_navigate_checkbox(self):
        """'설정 > 일반' 화면에서 '점검 후 결과 화면으로 자동 이동' CheckBox 요소 반환"""
        target_h, win = self._connect_window()
        for cb in win.descendants(control_type="CheckBox"):
            name = (cb.element_info.name or "").strip()
            if name == self.AUTO_NAV_CHECKBOX_NAME or "자동 이동" in name:
                return target_h, cb
        raise RuntimeError(f"'설정 > 일반'에서 '{self.AUTO_NAV_CHECKBOX_NAME}' 체크박스를 찾을 수 없습니다.")

    def get_auto_navigate_checked(self, timeout: float = 8.0) -> bool:
        """'점검 후 결과 화면으로 자동 이동' 체크박스 현재 체크 여부 반환"""
        self.open_sub_tab("일반", timeout=timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                _, cb = self._find_auto_navigate_checkbox()
                return int(cb.get_toggle_state()) == 1
            except Exception:
                time.sleep(0.25)
        raise TimeoutError(f"'{self.AUTO_NAV_CHECKBOX_NAME}' 체크박스 상태 조회 실패")

    def set_auto_navigate_checked(self, checked: bool, timeout: float = 8.0) -> bool:
        """'점검 후 결과 화면으로 자동 이동' 체크박스를 지정 상태(True/False)로 변경"""
        current = self.get_auto_navigate_checked(timeout=timeout)
        if current == checked:
            return current

        target_h, cb = self._find_auto_navigate_checkbox()
        try:
            cb.toggle()
        except Exception:
            self._click_element(cb, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            _, cb_chk = self._find_auto_navigate_checkbox()
            state = int(cb_chk.get_toggle_state()) == 1
            if state == checked:
                return state

        raise TimeoutError(f"'{self.AUTO_NAV_CHECKBOX_NAME}' 체크박스 상태 변경({checked}) 시간 초과")

    def wait_for_result_move_popup(self, timeout: float = 35.0) -> Dict[str, Any]:
        """
        자동 이동 해제 상태에서 점검 완료 시 노출되는
        '점검이 완료되었습니다. 결과 화면으로 이동합니다.' 팝업과 '결과 화면으로 이동' 버튼 대기.
        """
        start = time.time()
        tabs_seen: List[str] = []
        while time.time() - start < timeout:
            active: Optional[str] = None
            try:
                _, win = self._connect_window()
                texts = [
                    (d.element_info.name or "").strip()
                    for d in self._safe_descendants(win, control_type="Text")
                    if d.element_info.name
                ]
                buttons = [
                    (b.element_info.name or "").strip()
                    for b in self._safe_descendants(win, control_type="Button")
                    if b.element_info.name
                ]

                if any("점검이 완료되었습니다" in t or "결과 화면으로 이동합니다" in t for t in texts) and (
                    self.RESULT_POPUP_BUTTON in buttons
                ):
                    relevant = [t for t in texts if "점검이 완료되었습니다" in t or "결과 화면으로 이동" in t]
                    return {
                        "message": "\n".join(relevant),
                        "buttons": buttons,
                        "tabs_seen": tabs_seen,
                        "elapsed": round(time.time() - start, 2),
                    }

                active = self.get_active_tab_name()
            except (KeyError, Exception):
                pass

            if active and (not tabs_seen or tabs_seen[-1] != active):
                tabs_seen.append(active)
            if active == "점검결과":
                raise AssertionError(
                    f"자동 이동 옵션을 해제했으나 팝업 없이 '점검결과' 탭으로 자동 전환되었습니다. (tabs_seen={tabs_seen})"
                )

            time.sleep(0.25)

        raise TimeoutError(
            f"점검 완료 후 '{self.RESULT_POPUP_BUTTON}' 팝업이 {timeout}초 내에 나타나지 않았습니다. "
            f"(관측 탭: {tabs_seen})"
        )

    def click_result_move_popup_button(self, timeout: float = 10.0) -> None:
        """완료 팝업의 '결과 화면으로 이동' 버튼 클릭 및 '점검결과' 탭 전환 대기"""
        deadline = time.time() + timeout
        clicked = False
        while time.time() < deadline:
            try:
                target_h, win = self._connect_window()
                for b in self._safe_descendants(win, control_type="Button"):
                    if (b.element_info.name or "").strip() == self.RESULT_POPUP_BUTTON:
                        try:
                            b.invoke()
                        except Exception:
                            self._click_element(b, target_h)
                        clicked = True
                        break
                if clicked:
                    break
            except (KeyError, Exception):
                pass
            time.sleep(0.25)

        if not clicked:
            raise RuntimeError(f"완료 팝업에서 '{self.RESULT_POPUP_BUTTON}' 버튼을 찾을 수 없습니다.")

        nav_deadline = time.time() + timeout
        while time.time() < nav_deadline:
            try:
                if self.get_active_tab_name() == "점검결과":
                    time.sleep(0.5)
                    return
            except (KeyError, Exception):
                pass
            time.sleep(0.25)

        raise TimeoutError(
            f"'{self.RESULT_POPUP_BUTTON}' 클릭 후 '점검결과' 탭으로 이동하지 못했습니다. "
            f"(현재: {self.get_active_tab_name()})"
        )

    def dismiss_result_move_popup_if_present(self, timeout: float = 2.0) -> bool:
        """티어다운 안전 정리용: '결과 화면으로 이동' 팝업이 열려 있으면 클릭하여 닫기"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                target_h, win = self._connect_window()
                for b in win.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() == self.RESULT_POPUP_BUTTON:
                        self._click_element(b, target_h)
                        time.sleep(0.5)
                        return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    # ------------------------------------------------------------------
    # 외형 옵션 (테마 전환 및 화면 테마 색상 측정)
    # ------------------------------------------------------------------
    def get_theme_options_state(self, timeout: float = 8.0) -> Dict[str, Any]:
        """
        '설정 > 외형'의 테마 라디오 버튼('라이트 모드', '다크 모드', '시스템 테마') 선택 상태,
        '활성' 배지, '현재 시스템: ...' 문구를 파싱하여 반환합니다.
        """
        self.open_sub_tab("외형", timeout=timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win = self._connect_window()
            radios: Dict[str, Dict[str, Any]] = {}
            active_theme: Optional[str] = None
            system_theme_label: Optional[str] = None

            for rb in win.descendants(control_type="RadioButton"):
                full_name = (rb.element_info.name or "").strip()
                selected = bool(rb.is_selected())
                for opt in self.THEME_OPTIONS:
                    if full_name.startswith(opt):
                        radios[opt] = {
                            "selected": selected,
                            "full_name": full_name,
                            "has_active_badge": "활성" in full_name,
                        }
                        if selected:
                            active_theme = opt
                        if opt == "시스템 테마":
                            system_theme_label = full_name

            for t in win.descendants(control_type="Text"):
                txt = (t.element_info.name or "").strip()
                if txt.startswith("현재 시스템:"):
                    system_theme_label = txt
                    break

            if len(radios) == len(self.THEME_OPTIONS) and active_theme is not None:
                return {
                    "active_theme": active_theme,
                    "options": radios,
                    "system_theme_label": system_theme_label,
                }
            time.sleep(0.25)

        raise TimeoutError("'설정 > 외형' 테마 옵션 상태를 읽지 못했습니다.")

    def select_theme(self, theme_name: str, timeout: float = 8.0) -> None:
        """지정된 테마('라이트 모드', '다크 모드', '시스템 테마') 선택 및 활성화 대기"""
        if theme_name not in self.THEME_OPTIONS:
            raise ValueError(f"지원하지 않는 테마 이름입니다: {theme_name!r} (가능: {self.THEME_OPTIONS})")

        self.open_sub_tab("외형", timeout=timeout)
        target_h, win = self._connect_window()
        target_rb = None
        for rb in win.descendants(control_type="RadioButton"):
            if (rb.element_info.name or "").strip().startswith(theme_name):
                target_rb = rb
                break

        if target_rb is None:
            raise RuntimeError(f"'설정 > 외형'에서 '{theme_name}' 라디오 버튼을 찾을 수 없습니다.")

        if not target_rb.is_selected():
            try:
                target_rb.select()
            except Exception:
                self._click_element(target_rb, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self.get_theme_options_state(timeout=timeout)
            if state["active_theme"] == theme_name:
                time.sleep(0.4)
                return
            time.sleep(0.25)

        raise TimeoutError(f"'{theme_name}' 테마 활성화 대기 시간 초과")

    def get_region_rgb_average(self, region: str = "header_empty") -> Tuple[int, int, int]:
        """
        창 내 지정된 배경 영역의 평균 RGB 색상을 측정하여 반환합니다.
        - 'window_center': 창 중앙(로딩/초기 실행 화면 다크/라이트 판별용)
        - 'header_empty': 상단 타이틀('내PC보안점검') 우측의 빈 헤더 영역
        - 'sidebar_empty': 좌측 사이드바('설정' 메뉴 아래 ~ '지원&문의' 위) 빈 영역
        - 'main_right_margin': 본문(.main) 우측 상단 여백 영역
        """
        self.bring_to_front()
        if region == "window_center":
            r = win32gui.GetWindowRect(self.hwnd)
            cx = (r[0] + r[2]) // 2
            cy = (r[1] + r[3]) // 2
            bbox = (cx - 100, cy - 100, cx + 100, cy + 100)
        else:
            _, win = self._connect_window()
            wr = win.rectangle()
            if region == "header_empty":
                bbox = (wr.left + 450, wr.top + 12, wr.right - 200, wr.top + 65)
            elif region == "sidebar_empty":
                bbox = (wr.left + 20, wr.top + 520, wr.left + 120, wr.bottom - 100)
            elif region == "main_right_margin":
                main_rect = wr
                for grp in win.descendants(control_type="Group"):
                    if (grp.element_info.class_name or "") == "main":
                        main_rect = grp.rectangle()
                        break
                bbox = (main_rect.right - 25, main_rect.top + 20, main_rect.right - 5, main_rect.top + 120)
            else:
                raise ValueError(f"지원하지 않는 배경 측정 영역입니다: {region!r}")

        crop = ImageGrab.grab(bbox=bbox).convert("RGB")
        pixels = list(crop.get_flattened_data())
        count = len(pixels)
        return (
            sum(p[0] for p in pixels) // count,
            sum(p[1] for p in pixels) // count,
            sum(p[2] for p in pixels) // count,
        )

    def get_theme_visual_snapshot(self) -> Dict[str, Any]:
        """현재 화면의 헤더/사이드바/본문 여백 배경 RGB를 측정하여 다크/라이트 테마 적용 상태 반환"""
        header_rgb = self.get_region_rgb_average("header_empty")
        sidebar_rgb = self.get_region_rgb_average("sidebar_empty")
        margin_rgb = self.get_region_rgb_average("main_right_margin")

        avg_luma = (
            sum(header_rgb) / 3.0 + sum(sidebar_rgb) / 3.0 + sum(margin_rgb) / 3.0
        ) / 3.0

        return {
            "header_rgb": header_rgb,
            "sidebar_rgb": sidebar_rgb,
            "main_margin_rgb": margin_rgb,
            "avg_luminance": round(avg_luma, 1),
            "is_dark": all(c < 80 for c in header_rgb + sidebar_rgb + margin_rgb),
            "is_light": all(c > 190 for c in header_rgb + sidebar_rgb + margin_rgb),
        }

    # ------------------------------------------------------------------
    # 정보 탭 ('앱 버전')
    # ------------------------------------------------------------------
    def get_app_version(self, timeout: float = 8.0) -> str:
        """'설정 > 정보' 탭으로 이동하여 '앱 버전' 값을 반환 (예: '5.1.70.3')"""
        self.open_sub_tab("정보", timeout=timeout)

        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win = self._connect_window()
            texts = [
                (t.element_info.name or "").strip()
                for t in win.descendants(control_type="Text")
                if t.element_info.name
            ]
            for idx, txt in enumerate(texts):
                if txt == "앱 버전" and idx + 1 < len(texts):
                    version = texts[idx + 1]
                    if version:
                        return version
            time.sleep(0.25)

        raise RuntimeError("'설정 > 정보' 탭에서 '앱 버전' 값을 찾을 수 없습니다.")

"""
보안점검 메인 화면 > 도움말 모달(HelpModalPage) Page Object
- 메인 화면 우측 '도움말 안내' 카드 클릭으로 팝업 호출 및 닫기
- 좌측 햄버거 메뉴(☰) 토글(접힘/펼침) 제어 및 상태 검증
- 53개 보안점검 항목 리스트 순회 및 상세 콘텐츠(점검 내용, 조치 방법 등) 검증
- 아코디언 드롭다운 버튼(▲ / ▼) 토글 동작 검증
- 우측 상단 다국어(한국어 / English) 언어 전환 및 실시간 반영 검증
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Union
import win32gui
import win32con
from pywinauto import Application
import pywinauto.keyboard as keyboard


# 53개 도움말 점검항목 기준 목록 (한국어)
HELP_ITEMS_53_KO = [
    "바이러스 백신 설치 및 실행 여부 점검",
    "바이러스 백신 최신 보안 패치 점검",
    "OS, MS Office 최신 보안 패치 점검",
    "한글 프로그램 최신 보안 패치 점검",
    "로그인 암호 안전성 점검",
    "로그인 암호 분기별 변경 여부 점검",
    "화면 보호기 설정 여부 점검",
    "사용자 공유 폴더 존재 여부 점검",
    "USB 자동 실행 여부 점검",
    "미사용(3개월) ActiveX 컨트롤 존재 여부 점검",
    "PDF 프로그램 최신 보안 패치 점검",
    "편집 프로그램 설치 여부 점검",
    "무선랜카드 설치 여부 점검",
    "보안 USB 설치 여부 점검",
    "금지 SW 설치 여부 점검",
    "사용자 PC 프로세스 목록 수집 기능",
    "메인 계정 외 기타 계정 존재 여부 점검",
    "확장 편집 프로그램 설치 여부 점검",
    "Adobe Flash Player 설치 여부 점검",
    "JAVA 최신 보안 패치 점검",
    "방화벽 실행 여부 점검",
    "복구 콘솔에서 자동 로그온 금지 설정 여부 점검",
    "원격 데스크톱 금지 설정 여부 점검",
    "파일 시스템 NTFS 사용 여부 점검",
    "멀티 윈도우 OS 사용 여부 점검",
    "Google Chrome 최신 업데이트 점검",
    "유해 SW 설치 여부 점검",
    "유해 ActiveX 설치 여부 점검",
    "유해 프로세스 실행 여부 점검",
    "미사용 계정 존재 여부 점검",
    "Guest 계정 사용 여부 점검",
    "Administrator 계정 사용 여부 점검",
    "암호 사용 기간 제한 설정 여부 점검",
    "윈도우 자동 업데이트 설정 여부 점검",
    "보안센터 실행 여부 점검",
    "NTP 시간서버와 자동 동기화 설정 여부 점검",
    "최근 암호 기억 기능 사용 여부 점검",
    "암호 사용 최대/최소 기간 설정 여부 점검",
    "원격 데스크톱 포트 설정 점검",
    "비인가 사용자 접근 제어 설정 여부 점검",
    "신뢰 사이트 등록 여부 점검",
    "사용자 계정 컨트롤(UAC) 설정 여부 점검",
    "Host 파일 사용 여부 점검",
    "인가된 DNS 서버 사용 점검",
    "절전 모드 정책 설정 여부 점검",
    "하드디스크 절전 정책 설정 여부 점검",
    "모니터 절전 정책 설정 여부 점검",
    "윈도우 자동 로그온 금지 설정 여부 점검",
    "윈도우 패치 지원 종료 여부 점검",
    "비인가 무선 AP 사용 여부 점검",
    "비인가 서비스 실행 여부 점검",
    "비인가 메신저 사용 여부 점검",
    "방화벽 정책 설정 여부 점검",
]

# 53개 도움말 점검항목 기준 목록 (English)
HELP_ITEMS_53_EN = [
    "Check antivirus installation and execution",
    "Check antivirus latest security patch",
    "Check latest security patches for OS and MS Office",
    "Check latest security patch for Hancom Office HWP",
    "Check login password security",
    "Windows Login Password Age(>3Months",
    "Check screen saver settings",
    "Check for existence of user shared folders",
    "Check if USB auto-run is enabled",
    "Check for unused (3 months) ActiveX controls",
    "Check latest security patch for PDF program",
    "Check if an editing program is installed",
    "Check if a wireless LAN card is installed",
    "Check if a secure USB program is installed",
    "Check if prohibited software is installed",
    "Collect user PC process list",
    "Check for existence of accounts other than the main account",
    "Check if an extended editing program is installed",
    "Check whether Adobe Flash Player is installed",
    "Check latest security patch for JAVA",
    "Check if the firewall is running",
    "Check if auto logon is disabled in recovery console",
    "Check if Remote Desktop is disabled",
    "Check if NTFS file system is used",
    "Check if multi-Windows OS is used",
    "Check latest update for Google Chrome",
    "Check if harmful software is installed",
    "Check if harmful ActiveX controls are installed",
    "Check if harmful processes are running",
    "Check for existence of unused accounts",
    "Check if the Guest account is enabled",
    "Check if the Administrator account is enabled",
    "Check if password expiration policy is enforced",
    "Check if Windows automatic updates are enabled",
    "Check if the Security Center is running",
    "Check if automatic synchronization with NTP time server is enabled",
    "Check if password history retention is enabled",
    "Check if maximum/minimum password age policy is set",
    "Check remote desktop port settings",
    "Check if unauthorized user access is restricted",
    "Check if trusted sites are registered",
    "Check if User Account Control (UAC) is enabled",
    "Check if the Hosts file is used",
    "Check if authorized DNS servers are used",
    "Check if power-saving mode policy is set",
    "Check if hard disk power-saving policy is set",
    "Check if monitor power-saving policy is set",
    "Check if Windows automatic logon is disabled",
    "Check if Windows patch support has ended",
    "Check if unauthorized wireless AP is in use",
    "Check if unauthorized services are running",
    "Check if unauthorized messengers are in use",
    "Check if firewall policy is configured",
]


class HelpModalPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    @classmethod
    def find_help_window(cls, exclude_hwnd: Optional[int] = None) -> Optional[int]:
        """열려있는 도움말 창 HWND 탐색 (taKeeper_ 팝업 창)"""
        found_h = None
        def enum_cb(h, _):
            nonlocal found_h
            if win32gui.IsWindowVisible(h):
                title = win32gui.GetWindowText(h)
                w_cls = win32gui.GetClassName(h)
                if exclude_hwnd and h == exclude_hwnd:
                    return
                # 도움말 창은 taKeeper_{...} 클래스이며 메인 창 GUID({02D334FF-...})와 다름
                if "내PC보안점검" in title and w_cls.startswith("taKeeper_") and not w_cls.startswith("taKeeper_{02D334FF"):
                    found_h = h
        win32gui.EnumWindows(enum_cb, None)
        return found_h

    @classmethod
    def open_from_main(cls, main_page, timeout: float = 10.0) -> "HelpModalPage":
        """
        메인 화면의 '도움말 안내' 카드를 클릭하여 도움말 창을 열고 HelpModalPage 인스턴스를 반환합니다.
        """
        existing_help = cls.find_help_window(exclude_hwnd=main_page.hwnd)
        if existing_help:
            return cls(existing_help)

        main_page.bring_to_front()
        target_h, win = main_page._connect_window()

        clicked = False
        for d in win.descendants():
            name = (d.element_info.name or "").strip()
            if name == "도움말 안내":
                print(f">>> [HelpModalPage] 메인 화면 '도움말 안내' 카드 클릭: {d.rectangle()}")
                main_page._click_element(d, target_h)
                clicked = True
                break

        if not clicked:
            raise RuntimeError("메인 화면에서 '도움말 안내' 카드를 찾을 수 없습니다.")

        start = time.time()
        while time.time() - start < timeout:
            help_h = cls.find_help_window(exclude_hwnd=main_page.hwnd)
            if help_h:
                time.sleep(1.0)  # 웹뷰 렌더링 안정화 대기
                return cls(help_h)
            time.sleep(0.3)

        raise TimeoutError("도움말 모달 창이 제한 시간 내에 열리지 않았습니다.")

    def _get_chrome_widget_hwnd(self) -> Optional[int]:
        """도움말 창 내부 최상위 Chrome_WidgetWin_1 핸들 탐색"""
        widget_h = None

        def cb_child(ch, _):
            nonlocal widget_h
            if widget_h is None and "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                widget_h = ch

        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return widget_h

    def _get_target_hwnd(self) -> int:
        """도움말 창 내부 Chrome_WidgetWin_1 또는 Chrome_RenderWidgetHostHWND 핸들 탐색"""
        target_h = None

        def cb_child(ch, _):
            nonlocal target_h
            cls_name = win32gui.GetClassName(ch)
            if "Chrome_WidgetWin_1" in cls_name or "Chrome_Render" in cls_name:
                target_h = ch

        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return target_h or self.hwnd

    def _connect_window(self, handle: Optional[int] = None):
        """pywinauto UIA 윈도우 객체 및 대상 HWND 반환"""
        target_h = handle or self._get_target_hwnd()
        app = Application(backend="uia").connect(handle=target_h)
        return target_h, app.window(handle=target_h)

    def _click_element(self, elem, target_h: Optional[int] = None) -> None:
        """
        물리 마우스 이동(SetCursorPos) 없이 PostMessage로 요소를 클릭합니다.
        PostMessage가 실패할 경우에만 click_input()으로 폴백합니다.
        """
        click_hwnd = target_h or self._get_target_hwnd()
        try:
            rect = elem.rectangle()
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            local_x, local_y = win32gui.ScreenToClient(click_hwnd, (cx, cy))
            l_param = ((local_y & 0xFFFF) << 16) | (local_x & 0xFFFF)
            win32gui.PostMessage(click_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
            time.sleep(0.08)
            win32gui.PostMessage(click_hwnd, win32con.WM_LBUTTONUP, 0, l_param)
        except Exception:
            elem.click_input()

    def is_open(self) -> bool:
        """도움말 창이 현재 열려 있고 화면에 표시 중인지 확인"""
        return bool(self.hwnd and win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd))

    def bring_to_front(self) -> None:
        """도움말 창을 포커스 활성화"""
        from core.desktop_utils import bring_window_to_front, switch_to_user_desktop
        switch_to_user_desktop()
        if bring_window_to_front(self.hwnd):
            time.sleep(0.3)

    def _find_close_button(self) -> Tuple[Optional[int], Optional[Any]]:
        """
        도움말 창 우측 상단의 닫기(X) 버튼을 Chrome_WidgetWin_1 / 대상 웹뷰 / 최상위 창 순으로 탐색합니다.
        """
        search_handles: List[int] = []
        for h in (self._get_chrome_widget_hwnd(), self._get_target_hwnd(), self.hwnd):
            if h and h not in search_handles and win32gui.IsWindow(h):
                search_handles.append(h)

        for handle in search_handles:
            try:
                _, win = self._connect_window(handle=handle)
                win_rect = win.rectangle()
                top_bar_bottom = win_rect.top + 80

                candidate_btns = []
                for b in win.descendants(control_type="Button"):
                    r = b.rectangle()
                    if r.width() <= 0 or r.height() <= 0:
                        continue
                    if r.top < top_bar_bottom and r.right > win_rect.right - 150:
                        candidate_btns.append(b)

                if candidate_btns:
                    close_btn = max(candidate_btns, key=lambda btn: btn.rectangle().right)
                    return handle, close_btn
            except Exception:
                continue

        return None, None

    def close(self, timeout: float = 5.0) -> bool:
        """우측 상단 닫기(X) 버튼을 클릭하여 도움말 창 닫기"""
        if not self.is_open():
            return True

        self.bring_to_front()
        click_hwnd, close_btn = self._find_close_button()

        if close_btn is not None:
            print(f">>> [HelpModalPage] 도움말 창 닫기(X) 버튼 클릭: {close_btn.rectangle()}")
            try:
                close_btn.invoke()
            except Exception:
                self._click_element(close_btn, click_hwnd)
        else:
            # Fallback: WM_CLOSE / SC_CLOSE
            target_h = self._get_chrome_widget_hwnd() or self._get_target_hwnd()
            sent = False
            for h in (self.hwnd, target_h):
                if not h or not win32gui.IsWindow(h):
                    continue
                try:
                    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
                    sent = True
                    break
                except Exception:
                    continue
            if not sent:
                win32gui.PostMessage(self.hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)

        start = time.time()
        while time.time() - start < timeout:
            if not self.is_open():
                print(">>> [HelpModalPage] 도움말 창이 정상적으로 닫혔습니다.")
                return True
            time.sleep(0.25)
        return False

    def toggle_hamburger_menu(self, timeout: float = 5.0) -> None:
        """좌측 상단 햄버거 메뉴(☰) 버튼 클릭 후 네비게이션 접힘/펼침 상태 전환 대기"""
        before_collapsed = self.is_nav_collapsed()
        target_h, win = self._connect_window()
        menu_btn = None
        for b in win.descendants(control_type="Button"):
            name = (b.element_info.name or "").strip()
            cls_name = b.element_info.class_name or ""
            if name == "☰" or "menu-btn" in cls_name:
                menu_btn = b
                break

        if not menu_btn:
            raise RuntimeError("좌측 상단 햄버거 메뉴(☰) 버튼을 찾을 수 없습니다.")

        print(f">>> [HelpModalPage] 햄버거 메뉴(☰) 버튼 클릭")
        try:
            menu_btn.invoke()
        except Exception:
            self._click_element(menu_btn, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_nav_collapsed() != before_collapsed:
                time.sleep(0.25)
                return
            time.sleep(0.15)
        raise TimeoutError("햄버거 메뉴(☰) 클릭 후 네비바 상태가 변경되지 않았습니다.")

    def is_nav_collapsed(self) -> bool:
        """
        좌측 네비게이션 목록이 접힌(축소) 상태인지 확인.
        - 축소 상태일 경우 ListItem의 텍스트가 번호("1", "2")로 축소되고 너비가 좁아짐 (< 100px)
        - 펼쳐진 상태일 경우 긴 한글 항목명 및 넓은 너비 (> 200px) 유지
        """
        _, win = self._connect_window()
        list_items = win.descendants(control_type="ListItem")
        if not list_items:
            return False

        first_item = list_items[0]
        name = (first_item.element_info.name or "").strip()
        width = first_item.rectangle().width()
        # 축소 상태: name == "1" 이거나 width < 120
        return name == "1" or width < 120

    def get_item_links(self) -> List[Any]:
        """좌측 네비게이션 목록의 53개 항목 하이퍼링크 객체 목록 반환"""
        _, win = self._connect_window()
        links = []
        for d in win.descendants(control_type="Hyperlink"):
            cls_name = d.element_info.class_name or ""
            if "lg-link" in cls_name:
                links.append(d)
        return links

    def get_nav_items_texts(self) -> List[str]:
        """좌측 네비게이션 목록에 표시된 항목 텍스트 목록 반환"""
        _, win = self._connect_window()
        return [
            (d.element_info.name or "").strip()
            for d in win.descendants(control_type="Hyperlink")
            if "lg-link" in (d.element_info.class_name or "")
        ]

    def select_item(self, target: Union[int, str], timeout: float = 5.0) -> str:
        """
        지정 번호(1~53) 또는 항목명으로 도움말 항목 선택 후 우측 본문/헤더 반영 대기
        """
        links = self.get_item_links()
        if not links:
            raise RuntimeError("도움말 항목 리스트를 찾을 수 없습니다.")

        target_link = None
        if isinstance(target, int):
            if 1 <= target <= len(links):
                target_link = links[target - 1]
            else:
                raise IndexError(f"항목 번호는 1~{len(links)} 사이여야 합니다: {target}")
        else:
            for l in links:
                if target in (l.element_info.name or ""):
                    target_link = l
                    break

        if not target_link:
            raise ValueError(f"지정한 도움말 항목을 찾을 수 없습니다: {target}")

        item_name = (target_link.element_info.name or "").strip()
        print(f">>> [HelpModalPage] 항목 선택: '{item_name}'")
        try:
            target_link.invoke()
        except Exception:
            self._click_element(target_link)

        deadline = time.time() + timeout
        while time.time() < deadline:
            header = self.get_header_title()
            if header == item_name or item_name in header:
                if self.get_content_texts():
                    return item_name
            time.sleep(0.15)
        return item_name

    def get_header_title(self) -> str:
        """우측 상단 현재 선택된 항목의 헤더 타이틀 반환"""
        _, win = self._connect_window()
        for d in win.descendants(control_type="Text"):
            r = d.rectangle()
            # 우측 본문 상단 헤더 영역 (left >= 600, top < 260)
            if r.left >= 600 and r.top < 260:
                name = (d.element_info.name or "").strip()
                if name:
                    return name
        return ""

    def get_accordion_buttons(self) -> List[Dict[str, Any]]:
        """
        우측 본문에 존재하는 아코디언 드롭다운 버튼 목록 및 상태 정보 반환
        - name: 버튼 전체 텍스트 (예: '🛡️ 점검 내용 ▲')
        - label: 화살표 제외 라벨 (예: '🛡️ 점검 내용')
        - state: 'expanded'(▲) 또는 'collapsed'(▼)
        - element: UIA 요소 객체
        """
        _, win = self._connect_window()
        buttons = []
        for b in win.descendants(control_type="Button"):
            r = b.rectangle()
            if r.left < 600:
                continue
            name = (b.element_info.name or "").strip()
            if "▲" in name or "▼" in name:
                state = "expanded" if "▲" in name else "collapsed"
                label = name.replace("▲", "").replace("▼", "").strip()
                buttons.append({
                    "name": name,
                    "label": label,
                    "state": state,
                    "element": b
                })
        return buttons

    def toggle_accordion(self, button_label_or_index: Union[int, str], timeout: float = 5.0) -> Tuple[str, str]:
        """
        지정된 아코디언 버튼을 클릭하여 접힘/펼침 토글 후 상태 전환 완료까지 대기.
        (클릭 전 상태, 클릭 후 상태) 반환
        """
        btns = self.get_accordion_buttons()
        if not btns:
            raise RuntimeError("현재 화면에 아코디언 버튼이 없습니다.")

        target_btn_info = None
        if isinstance(button_label_or_index, int):
            if 0 <= button_label_or_index < len(btns):
                target_btn_info = btns[button_label_or_index]
        else:
            for b in btns:
                if button_label_or_index in b["label"] or button_label_or_index in b["name"]:
                    target_btn_info = b
                    break

        if not target_btn_info:
            raise ValueError(f"아코디언 버튼을 찾을 수 없습니다: {button_label_or_index}")

        before_state = target_btn_info["state"]
        btn_elem = target_btn_info["element"]
        print(f">>> [HelpModalPage] 아코디언 '{target_btn_info['name']}' 클릭 (현재: {before_state})")
        try:
            btn_elem.invoke()
        except Exception:
            self._click_element(btn_elem)

        deadline = time.time() + timeout
        after_state = before_state
        while time.time() < deadline:
            refreshed_btns = self.get_accordion_buttons()
            for b in refreshed_btns:
                if target_btn_info["label"] == b["label"]:
                    after_state = b["state"]
                    break
            if after_state != before_state:
                print(f">>> [HelpModalPage] 아코디언 토글 결과: {before_state} -> {after_state}")
                return before_state, after_state
            time.sleep(0.15)

        print(f">>> [HelpModalPage] 아코디언 토글 결과: {before_state} -> {after_state}")
        return before_state, after_state

    def get_content_texts(self) -> List[str]:
        """우측 본문 영역의 모든 텍스트 목록 수집 (이미지는 제외)"""
        _, win = self._connect_window()
        texts = []
        for d in win.descendants(control_type="Text"):
            r = d.rectangle()
            if r.left < 600:
                continue
            name = (d.element_info.name or "").strip()
            if name and name not in ("▲", "▼"):
                texts.append(name)
        return texts

    def _is_language_applied(self, is_en: bool) -> bool:
        """좌측 53개 도움말 항목이 목표 언어(영문/한글)로 반영되었는지 확인"""
        cur_items = self.get_nav_items_texts()
        if len(cur_items) == 53:
            first = cur_items[0]
            return first.isascii() if is_en else (not first.isascii())
        return False

    def _wait_language_applied(self, is_en: bool, wait_sec: float) -> bool:
        """지정 시간 동안 목표 언어 반영 여부를 폴링 대기"""
        deadline = time.time() + wait_sec
        while time.time() < deadline:
            if self._is_language_applied(is_en):
                return True
            time.sleep(0.2)
        return False

    def _post_key(self, target_h: int, vk_code: int) -> None:
        """SendInput 없이 대상 창 핸들에 PostMessage로 단일 키 입력을 전송합니다."""
        win32gui.PostMessage(target_h, win32con.WM_KEYDOWN, vk_code, 0)
        time.sleep(0.05)
        win32gui.PostMessage(target_h, win32con.WM_KEYUP, vk_code, 0)

    def change_language(self, target_lang: str, timeout: float = 6.0) -> None:
        """
        우측 상단 언어 선택 드롭다운(ComboBox)에서 언어 변경 ('English' 또는 '한국어') 및 목록 반영 대기
        """
        self.bring_to_front()
        target_h, win = self._connect_window()
        combo = None
        for d in win.descendants(control_type="ComboBox"):
            combo = d
            break

        if not combo:
            raise RuntimeError("우측 상단 언어 선택 드롭다운을 찾을 수 없습니다.")

        is_en = target_lang.lower() in ("english", "en", "영어")
        vk_arrow = win32con.VK_DOWN if is_en else win32con.VK_UP
        arrow_key = "{DOWN}" if is_en else "{UP}"
        print(f">>> [HelpModalPage] 언어 변경 시작 -> '{target_lang}'")

        # 이미 원하는 언어가 적용되어 있으면 즉시 반환
        if self._is_language_applied(is_en):
            print(f">>> [HelpModalPage] 이미 '{target_lang}' 상태입니다.")
            return

        # 1차: 물리 마우스/키보드(SetCursorPos/SendInput) 없이 PostMessage 클릭 + PostMessage 키 전송
        try:
            try:
                combo.set_focus()
            except Exception:
                pass
            self._click_element(combo, target_h)
            time.sleep(0.25)
            self._post_key(target_h, vk_arrow)
            time.sleep(0.15)
            self._post_key(target_h, win32con.VK_RETURN)
            if self._wait_language_applied(is_en, min(3.0, timeout)):
                print(f">>> [HelpModalPage] 언어 변경 완료 -> '{target_lang}'")
                return
        except Exception as e:
            print(f">>> [HelpModalPage] PostMessage 언어 변경 시도 예외({e}) -> 폴백 진행")

        # 2차: 실제 마우스 클릭 + keyboard.send_keys 폴백
        try:
            combo.click_input()
            time.sleep(0.25)
            keyboard.send_keys(arrow_key)
            time.sleep(0.15)
            keyboard.send_keys("{ENTER}")
            if self._wait_language_applied(is_en, timeout):
                print(f">>> [HelpModalPage] 언어 변경 완료(click_input 폴백) -> '{target_lang}'")
                return
        except Exception as e:
            print(f">>> [HelpModalPage] click_input 폴백 예외({e})")

        raise TimeoutError(f"언어 변경('{target_lang}') 반영 대기 시간 초과")


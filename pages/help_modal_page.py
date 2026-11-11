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

    def _connect_window(self):
        """pywinauto UIA 윈도우 객체 및 내부 크롬 HWND 반환"""
        target_h = self._get_target_hwnd()
        app = Application(backend="uia").connect(handle=target_h)
        return target_h, app.window(handle=target_h)

    def is_open(self) -> bool:
        """도움말 창이 현재 열려 있고 화면에 표시 중인지 확인"""
        return bool(self.hwnd and win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd))

    def bring_to_front(self) -> None:
        """도움말 창을 포커스 활성화"""
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

    def close(self, timeout: float = 5.0) -> bool:
        """우측 상단 닫기(X) 버튼을 클릭하여 도움말 창 닫기"""
        if not self.is_open():
            return True

        self.bring_to_front()
        target_h, win = self._connect_window()
        win_rect = win.rectangle()
        top_bar_bottom = win_rect.top + 70

        candidate_btns = []
        for b in win.descendants(control_type="Button"):
            r = b.rectangle()
            if r.top < top_bar_bottom and r.right > win_rect.right - 120:
                candidate_btns.append(b)

        if candidate_btns:
            close_btn = max(candidate_btns, key=lambda btn: btn.rectangle().right)
            print(f">>> [HelpModalPage] 도움말 창 닫기(X) 버튼 클릭: {close_btn.rectangle()}")
            try:
                close_btn.invoke()
            except Exception:
                close_btn.click_input()
        else:
            # Fallback: WM_CLOSE
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

        start = time.time()
        while time.time() - start < timeout:
            if not self.is_open():
                print(">>> [HelpModalPage] 도움말 창이 정상적으로 닫혔습니다.")
                return True
            time.sleep(0.25)
        return False

    def toggle_hamburger_menu(self) -> None:
        """좌측 상단 햄버거 메뉴(☰) 버튼 클릭 (접힘/펼침 토글)"""
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
            # Fallback: pywinauto click_input
            menu_btn.click_input()
        time.sleep(0.8)

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

    def select_item(self, target: Union[int, str]) -> str:
        """
        지정 번호(1~53) 또는 항목명으로 도움말 항목 선택
        """
        _, win = self._connect_window()
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
            target_link.click_input()
        time.sleep(0.4)
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

    def toggle_accordion(self, button_label_or_index: Union[int, str]) -> Tuple[str, str]:
        """
        지정된 아코디언 버튼을 클릭하여 접힘/펼침 토글.
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
            btn_elem.click_input()
        time.sleep(0.5)

        # 클릭 후 상태 재확인
        refreshed_btns = self.get_accordion_buttons()
        after_state = "unknown"
        for b in refreshed_btns:
            if target_btn_info["label"] == b["label"]:
                after_state = b["state"]
                break

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

    def change_language(self, target_lang: str) -> None:
        """
        우측 상단 언어 선택 드롭다운(ComboBox)에서 언어 변경 ('English' 또는 '한국어')
        """
        _, win = self._connect_window()
        combo = None
        for d in win.descendants(control_type="ComboBox"):
            combo = d
            break

        if not combo:
            raise RuntimeError("우측 상단 언어 선택 드롭다운을 찾을 수 없습니다.")

        print(f">>> [HelpModalPage] 언어 변경 시작 -> '{target_lang}'")
        combo.click_input()
        time.sleep(0.3)

        if target_lang.lower() in ("english", "en", "영어"):
            # 드롭다운 아래 화살표로 'English' 선택
            keyboard.send_keys("{DOWN}")
            time.sleep(0.2)
            keyboard.send_keys("{ENTER}")
        else:
            # 드롭다운 위 화살표로 '한국어' 선택
            keyboard.send_keys("{UP}")
            time.sleep(0.2)
            keyboard.send_keys("{ENTER}")
        time.sleep(1.0)
        print(f">>> [HelpModalPage] 언어 변경 완료 -> '{target_lang}'")


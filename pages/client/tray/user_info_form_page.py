"""
사용자 정보 입력 웹뷰 (taPopper.exe / TopAegis.Popper.Window) 제어 Page Object
- 사번(userNum) 및 이름(userId) 입력 필드 제어
- 저장 버튼 클릭 및 Alert 팝업 감지/확인
- 인사 UI 창 닫기
"""

import time
from typing import Optional, Tuple
import ctypes
import win32gui
import win32con
from pywinauto import Application, WindowSpecification


class UserInfoFormPage:
    WINDOW_TITLE_KEYWORDS = ["TA 공지", "사용자", "인사", "내PC보안점검"]

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd or self.find_window()
        self.app: Optional[Application] = None
        self.win: Optional[WindowSpecification] = None
        self.child_hwnd: Optional[int] = None
        if self.hwnd:
            self._connect()

    @classmethod
    def find_window(cls, timeout: float = 10.0) -> Optional[int]:
        """사용자 정보 입력(TA 공지) 창 핸들 탐색"""
        start = time.time()
        while time.time() - start < timeout:
            target_h = None
            def cb(h, _):
                nonlocal target_h
                if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h):
                    cls_name = win32gui.GetClassName(h)
                    title = win32gui.GetWindowText(h)
                    if cls_name == "TopAegis.Popper.Window" or "TA 공지" in title:
                        target_h = h
            win32gui.EnumWindows(cb, None)
            if target_h:
                return target_h
            time.sleep(0.5)
        return None

    def _connect(self):
        """UI Automation 바인딩"""
        target_h = None
        def cb_child(ch, _):
            nonlocal target_h
            if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        self.child_hwnd = target_h or self.hwnd

        self.app = Application(backend="uia").connect(handle=self.child_hwnd)
        self.win = self.app.window(handle=self.child_hwnd)

    def is_visible(self) -> bool:
        """창이 정상 노출되었는지 확인"""
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.hwnd = self.find_window(timeout=2.0)
            if self.hwnd:
                self._connect()
        return self.hwnd is not None and win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)

    def fill_form(self, emp_no: Optional[str] = None, name: Optional[str] = None) -> None:
        """사번과 이름 입력 (UIA SetValue + 클립보드/포커스 보장)"""
        if not self.win:
            self._connect()

        edits = self.win.descendants(control_type="Edit")
        if len(edits) >= 2:
            self._set_edit_value(edits[0], emp_no or "")
            time.sleep(0.3)
            self._set_edit_value(edits[1], name or "")
            time.sleep(0.3)
        else:
            raise RuntimeError("사번/이름 입력 필드를 찾을 수 없습니다.")

    def _set_edit_value(self, edit_elem, text: str):
        """Webview Edit 컨트롤에 클릭 포커스 후 UIA SetValue 및 키 입력 보장"""
        # 1. 대상 컨트롤 중앙 클릭하여 포커스 이동
        rect = edit_elem.rectangle()
        user32 = ctypes.windll.user32
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        user32.SetCursorPos(cx, cy)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
        time.sleep(0.1)

        # 2. UIA ValuePattern SetValue
        try:
            edit_elem.iface_value.SetValue(text)
        except Exception:
            pass

        # 3. DOM input 이벤트 트리거를 위해 Backspace 및 한 글자 타이핑 보정
        if text:
            # 전체 선택 후 교체
            user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('A'), 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
            user32.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)

            # 클립보드로 붙여넣어 완벽하게 DOM input 이벤트 유도
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            user32.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
        else:
            # 빈 값일 경우 전체 선택 후 백스페이스
            user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('A'), 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
            user32.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            user32.keybd_event(win32con.VK_BACK, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(win32con.VK_BACK, 0, win32con.KEYEVENTF_KEYUP, 0)

    def click_save(self) -> None:
        """저장 버튼 클릭"""
        if not self.win:
            self._connect()

        save_btn = None
        for b in self.win.descendants(control_type="Button"):
            if b.element_info.name == "저장":
                save_btn = b
                break

        if save_btn:
            save_btn.invoke()
        else:
            raise RuntimeError("'저장' 버튼을 찾을 수 없습니다.")

    def get_alert_text_and_accept(self, timeout: float = 5.0) -> Optional[str]:
        """
        저장 후 웹뷰 내부에 뜨는 Alert 모달 팝업의 텍스트를 읽고 '확인' 버튼을 클릭합니다.
        """
        start = time.time()
        while time.time() - start < timeout:
            if not self.child_hwnd or not win32gui.IsWindow(self.child_hwnd):
                break
            try:
                app = Application(backend="uia").connect(handle=self.child_hwnd)
                win = app.window(handle=self.child_hwnd)
                texts = [t.element_info.name for t in win.descendants(control_type="Text") if t.element_info.name]
                # '알림' 및 메시지 추출
                alert_msg = None
                for t in texts:
                    if t != "알림" and any(k in t for k in ["입력하세요", "일치하지", "등록되었습니다", "미등록"]):
                        alert_msg = t
                        break

                if alert_msg:
                    # 확인 버튼 클릭
                    for b in win.descendants(control_type="Button"):
                        if b.element_info.name == "확인":
                            b.invoke()
                            break
                    time.sleep(0.5)
                    return alert_msg
            except Exception:
                pass
            time.sleep(0.3)
        return None

    def close(self) -> bool:
        """인사 UI 창 닫기 (MSAA TitleBar 닫기)"""
        from core.app_controller import AppController
        return AppController.close_hr_ui()


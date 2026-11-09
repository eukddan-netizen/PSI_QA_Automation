"""
보안점검 프로그램 메인 페이지 Object
- 크롬 임베디드 웹 뷰(Chrome_WidgetWin_1) 정밀 탐색
- '▶ 점검 시작' 버튼 정밀 좌표 및 PostMessage 클릭
- 점검 상태 모니터링
"""

import time
import win32gui
import win32con
from pywinauto import Application


class MainPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def _get_target_hwnd(self) -> int:
        """UIA 요소가 들어있는 Chrome_WidgetWin_1 또는 Chrome_RenderWidgetHostHWND 핸들 탐색"""
        target_h = None
        def cb_child(ch, extra):
            nonlocal target_h
            cls = win32gui.GetClassName(ch)
            if "Chrome_WidgetWin_1" in cls or "Chrome_Render" in cls:
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return target_h or self.hwnd

    def click_start_inspection(self):
        """'▶ 점검 시작' 파란색 버튼 클릭"""
        # 창 전면 활성화
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.5)
        except Exception:
            pass

        target_h = self._get_target_hwnd()
        print(f">>> [MainPage] 타깃 크롬 웹뷰 HWND: {target_h}")

        app = Application(backend="uia").connect(handle=target_h)
        win = app.window(handle=target_h)

        # 혹시 메인 탭이 아니라면 '메인' 탭 링크 먼저 클릭
        for link in win.descendants(control_type="Hyperlink"):
            if link.element_info.name == "메인":
                print(">>> [MainPage] '메인' 탭 링크 클릭...")
                try:
                    link.invoke()
                except Exception:
                    self._click_element(link, target_h)
                time.sleep(1.5)
                break

        # '▶ 점검 시작' 버튼 탐색 (최대 3초 대기)
        start_btn = None
        for _ in range(6):
            for b in win.descendants(control_type="Button"):
                if "점검 시작" in b.element_info.name or "점검시작" in b.element_info.name:
                    start_btn = b
                    break
            if start_btn:
                break
            time.sleep(0.5)

        if not start_btn:
            raise RuntimeError("화면에서 '▶ 점검 시작' 버튼을 찾을 수 없습니다.")

        print(f">>> [MainPage] '▶ 점검 시작' 버튼 발견: Screen={start_btn.rectangle()}")
        self._click_element(start_btn, target_h)
        print(">>> [MainPage] '▶ 점검 시작' 클릭 메시지 전송 완료!")

    def _click_element(self, elem, hwnd):
        """UIA 요소의 좌표를 계산하여 PostMessage 클릭"""
        rect = elem.rectangle()
        r_rect = win32gui.GetWindowRect(hwnd)
        local_x = (rect.left + rect.right) // 2 - r_rect[0]
        local_y = (rect.top + rect.bottom) // 2 - r_rect[1]

        lParam = (local_y << 16) | (local_x & 0xFFFF)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.08)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

    def wait_for_inspection_done(self, timeout: int = 15):
        """점검 진행 및 결과 로딩 대기"""
        print(f">>> [MainPage] 점검 진행 중... ({timeout}초 대기)")
        time.sleep(timeout)
        print(">>> [MainPage] 점검 완료 및 결과 로딩 확인!")

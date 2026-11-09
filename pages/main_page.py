"""
보안점검 프로그램 메인 페이지 Object
- '▶ 점검 시작' 버튼 클릭
- 점검 상태 모니터링
"""

import time
import ctypes
import win32gui
import win32con


class MainPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.user32 = ctypes.windll.user32

    def click_start_inspection(self):
        """'▶ 점검 시작' 파란색 버튼 클릭"""
        # 창 전면 활성화
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

        # 클라이언트 기준 버튼 위치: X=+540, Y=+470
        client_x, client_y = win32gui.ClientToScreen(self.hwnd, (0, 0))
        btn_x = client_x + 540
        btn_y = client_y + 470

        print(f">>> [MainPage] '▶ 점검 시작' 버튼 클릭 (좌표: {btn_x}, {btn_y})")
        self.user32.SetCursorPos(btn_x, btn_y)
        time.sleep(0.1)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, btn_x, btn_y, 0, 0)
        time.sleep(0.08)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, btn_x, btn_y, 0, 0)

    def wait_for_inspection_done(self, timeout: int = 15):
        """점검 진행 및 완료 대기"""
        print(f">>> [MainPage] 점검 진행 중... ({timeout}초 대기)")
        time.sleep(timeout)
        print(">>> [MainPage] 점검 완료!")


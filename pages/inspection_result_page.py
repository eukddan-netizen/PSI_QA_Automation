"""
보안점검 프로그램 점검결과 페이지 Object
- '점검결과' 탭 이동
- 7번 항목(화면보호기) 상태 및 조치 버튼 제어
- '재점검' 버튼 제어
"""

import time
import ctypes
import win32gui
import win32con
from os_handlers.screen_saver import ScreenSaverHandler


class InspectionResultPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.user32 = ctypes.windll.user32

    def navigate_to_results(self):
        """사이드바의 '점검결과' 메뉴 클릭 (상대 좌표: X=+55, Y=+240)"""
        try:
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.2)
        except Exception:
            pass

        client_x, client_y = win32gui.ClientToScreen(self.hwnd, (0, 0))
        target_x = client_x + 55
        target_y = client_y + 240

        print(f">>> [ResultPage] '점검결과' 메뉴 클릭 (좌표: {target_x}, {target_y})")
        self.user32.SetCursorPos(target_x, target_y)
        time.sleep(0.1)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
        time.sleep(0.08)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
        time.sleep(2.0)

    def verify_os_status(self) -> tuple[bool, str]:
        """실제 Windows OS 레지스트리의 화면보호기 안전/취약 상태 검증"""
        return ScreenSaverHandler.is_secure()

    def click_remediate_button(self):
        """
        7번 항목 조치 (또는 하단의 '전체 조치' 버튼 클릭)
        결과 화면 하단의 조치 버튼을 클릭하여 보안 조치를 수행합니다.
        """
        client_x, client_y = win32gui.ClientToScreen(self.hwnd, (0, 0))
        # 결과 화면 하단의 '조치' / '전체 조치' 버튼 위치 (화면 하단 중앙 부근)
        # 1200x840 기준: X = client_x + 550, Y = client_y + 790
        action_x = client_x + 550
        action_y = client_y + 790

        print(f">>> [ResultPage] 조치 버튼 클릭 시도 (좌표: {action_x}, {action_y})")
        self.user32.SetCursorPos(action_x, action_y)
        time.sleep(0.1)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, action_x, action_y, 0, 0)
        time.sleep(0.08)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, action_x, action_y, 0, 0)
        time.sleep(3.0)  # 조치 적용 대기

    def click_reinspect(self):
        """결과 화면 하단의 '재점검' 버튼 클릭 (1200x840 기준: X = client_x + 650, Y = client_y + 790)"""
        client_x, client_y = win32gui.ClientToScreen(self.hwnd, (0, 0))
        reinspect_x = client_x + 650
        reinspect_y = client_y + 790

        print(f">>> [ResultPage] '재점검' 버튼 클릭 (좌표: {reinspect_x}, {reinspect_y})")
        self.user32.SetCursorPos(reinspect_x, reinspect_y)
        time.sleep(0.1)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, reinspect_x, reinspect_y, 0, 0)
        time.sleep(0.08)
        self.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, reinspect_x, reinspect_y, 0, 0)
        time.sleep(5.0)  # 재점검 대기


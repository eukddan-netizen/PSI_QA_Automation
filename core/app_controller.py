"""
보안점검 프로그램(taKeeper.exe) 제어 컨트롤러
- 시스템 트레이 자동 더블클릭을 통한 실제 모니터 창 실행
- 백그라운드 프로세스 정리 및 창 핸들 획득
- UI Automation 기반 창 제어
"""

import os
import sys
import time
import ctypes
import subprocess
from typing import Optional

# 1. win32gui 임포트 전에 무조건 DPI 인식 및 사용자 데스크톱 전환을 먼저 수행해야 합니다.
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32con
import win32gui
from pywinauto import Application, WindowSpecification


class AppController:
    WINDOW_TITLE = "내PC보안점검"
    EXE_NAME = "taKeeper.exe"

    def __init__(self):
        self.app: Optional[Application] = None
        self.main_window: Optional[WindowSpecification] = None
        self.hwnd: Optional[int] = None

    @classmethod
    def kill_existing(cls):
        """혹시 백그라운드에 남아있는 기존 프로세스 정리"""
        os.system(f"taskkill /f /im {cls.EXE_NAME} >nul 2>&1")
        time.sleep(1)

    def launch(self, timeout: int = 15) -> WindowSpecification:
        """
        시스템 트레이 아이콘을 자동으로 더블클릭하여
        사용자 실제 모니터에 보안점검 창을 띄우고 창 객체를 반환합니다.
        """
        # 1. 기존 프로세스 정리
        self.kill_existing()

        # 2. 트레이 더블클릭 실행
        self._double_click_tray_icon()

        # 3. 창 뜰 때까지 대기 및 핸들 획득
        self.hwnd = self._wait_for_window(timeout=timeout)
        if not self.hwnd:
            print(">>> 1차 시도에서 창 미감지, 트레이 더블클릭 1회 재시도...")
            self._double_click_tray_icon()
            self.hwnd = self._wait_for_window(timeout=timeout)

        if not self.hwnd:
            raise TimeoutError(f"보안점검 창('{self.WINDOW_TITLE}')이 화면에 뜨지 않았습니다.")

        # 4. 전면 활성화
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass

        # 5. pywinauto 바인딩
        self.app = Application(backend="uia").connect(handle=self.hwnd)
        self.main_window = self.app.window(handle=self.hwnd)
        return self.main_window

    def _double_click_tray_icon(self):
        """작업표시줄 숨겨진 아이콘 영역에서 보안점검 아이콘 더블클릭"""
        user32 = ctypes.windll.user32

        def mouse_click(x, y):
            user32.SetCursorPos(x, y)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

        # 1단계: 숨겨진 아이콘 표시(^) 버튼 클릭 (1515, 1170)
        mouse_click(1515, 1170)
        time.sleep(0.8)

        # 2단계: TA-STR / TA-PRS 아이콘 더블클릭 (1465, 993)
        user32.SetCursorPos(1465, 993)
        time.sleep(0.1)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 1465, 993, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 1465, 993, 0, 0)
        time.sleep(0.1)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 1465, 993, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 1465, 993, 0, 0)

    def _wait_for_window(self, timeout: int = 15) -> Optional[int]:
        """사용자 모니터에 표시된 창 핸들 탐색"""
        start = time.time()
        while time.time() - start < timeout:
            target_hwnd = None
            def cb(hwnd, extra):
                nonlocal target_hwnd
                if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if self.WINDOW_TITLE in title:
                        target_hwnd = hwnd

            win32gui.EnumWindows(cb, None)
            if target_hwnd:
                return target_hwnd
            time.sleep(0.5)
        return None

    def close(self):
        """창 닫기 및 프로세스 종료"""
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        self.kill_existing()

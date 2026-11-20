"""
보안점검 프로그램(taKeeper.exe) 제어 컨트롤러
- 시스템 트레이 자동 더블클릭을 통한 실제 모니터 창 실행
- 백그라운드 프로세스 정리 및 창 핸들 획득
- UI Automation 기반 창 제어
"""

from contextlib import contextmanager
import os
import sys
import time
import threading
import ctypes
from ctypes import wintypes
import subprocess
from typing import List, Optional, Tuple

# 1. win32gui 임포트 전에 무조건 DPI 인식 및 사용자 데스크톱 전환을 먼저 수행해야 합니다.
try:
    _u32 = ctypes.windll.user32
    _u32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
    _u32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    if not _u32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4)):
        _u32.SetProcessDPIAware()
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from core.desktop_utils import bring_window_to_front, switch_to_user_desktop
switch_to_user_desktop()

import win32con
import win32gui
from pywinauto import Application, WindowSpecification


class AppController:
    WINDOW_TITLE = "내PC보안점검"
    EXE_NAME = "taKeeper.exe"

    # 트레이 우클릭 메뉴(#32768, 전체 높이 약 210px) 내 각 항목의 세로 상대 비율
    TRAY_MENU_RATIOS = {
        "내PC보안점검": 15 / 210,
        "패치 현황": 53 / 210,
        "사용자 정보 입력": 80 / 210,
        "프로그램 목록 재확인": 105 / 210,
        "폰트 목록 재확인": 130 / 210,
        "에이전트 업데이트 실행": 155 / 210,
        "정보 확인": 195 / 210,
    }

    def __init__(self):
        self.app: Optional[Application] = None
        self.main_window: Optional[WindowSpecification] = None
        self.hwnd: Optional[int] = None

    @classmethod
    def kill_existing(cls, timeout: float = 5.0):
        """혹시 백그라운드에 남아있는 기존 프로세스 정리 후 완전 종료 대기"""
        subprocess.run(
            ["taskkill", "/f", "/im", cls.EXE_NAME],
            capture_output=True,
            timeout=5,
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            res = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {cls.EXE_NAME}", "/NH"],
                capture_output=True,
                text=True,
                encoding="cp949",
                errors="replace",
                timeout=3,
            )
            if cls.EXE_NAME.lower() not in (res.stdout or "").lower():
                return
            time.sleep(0.2)

    def bring_to_front(self) -> bool:
        """보안점검 메인 창을 최상단으로 활성화"""
        return bring_window_to_front(self.hwnd) if self.hwnd else False

    def launch(self, timeout: int = 30) -> WindowSpecification:
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
        self.bring_to_front()

        # 5. pywinauto 바인딩
        self.app = Application(backend="uia").connect(handle=self.hwnd)
        self.main_window = self.app.window(handle=self.hwnd)
        return self.main_window

    @staticmethod
    @contextmanager
    def _per_monitor_dpi():
        """스레드 DPI 인식을 Per-Monitor Aware v2(-4)로 임시 전환합니다."""
        user32 = ctypes.windll.user32
        prev_ctx = None
        try:
            user32.SetThreadDpiAwarenessContext.argtypes = [wintypes.HANDLE]
            user32.SetThreadDpiAwarenessContext.restype = wintypes.HANDLE
            prev_ctx = user32.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
        except Exception:
            prev_ctx = None
        try:
            yield user32
        finally:
            if prev_ctx:
                try:
                    user32.SetThreadDpiAwarenessContext(prev_ctx)
                except Exception:
                    pass

    def _open_tray_overflow(self) -> None:
        """작업표시줄 숨겨진 아이콘 영역(오버플로)이 닫혀 있으면 엽니다."""
        ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
        if ov and win32gui.IsWindowVisible(ov):
            return

        opened = False
        try:
            tray = win32gui.FindWindow("Shell_TrayWnd", None)
            if tray:
                tray_app = Application(backend="uia").connect(handle=tray)
                tray_win = tray_app.window(handle=tray)
                chevron_btn = None
                for b in tray_win.descendants(control_type="Button"):
                    b_name = (b.element_info.name or "").strip()
                    b_aid = (b.element_info.automation_id or "").strip()
                    if (
                        "숨겨진 아이콘 표시" in b_name
                        or "Show hidden icons" in b_name
                        or "SystemTrayChevron" in b_aid
                    ):
                        chevron_btn = b
                        break
                if chevron_btn is not None:
                    try:
                        chevron_btn.invoke()
                        opened = True
                    except Exception:
                        rect = chevron_btn.rectangle()
                        if rect.width() > 0 and rect.height() > 0:
                            cx = (rect.left + rect.right) // 2
                            cy = (rect.top + rect.bottom) // 2
                            user32 = ctypes.windll.user32
                            user32.SetCursorPos(cx, cy)
                            time.sleep(0.05)
                            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            time.sleep(0.05)
                            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            opened = True
                    if opened:
                        time.sleep(0.7)
        except Exception:
            pass

        if not opened:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            fx = int(screen_w * 0.79) if screen_w else 1515
            fy = screen_h - 30 if screen_h else 1170
            print(f">>> [트레이] '숨겨진 아이콘 표시' UIA 버튼 미발견 — 폴백 좌표 클릭: ({fx}, {fy})")
            user32.SetCursorPos(fx, fy)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.8)

    def _close_tray_overflow(self) -> None:
        """열려 있는 숨겨진 아이콘 오버플로 창을 UIA 버튼 이벤트로 닫습니다."""
        ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
        if not (ov and win32gui.IsWindowVisible(ov)):
            return

        try:
            tray = win32gui.FindWindow("Shell_TrayWnd", None)
            if tray:
                tray_app = Application(backend="uia").connect(handle=tray)
                tray_win = tray_app.window(handle=tray)
                for b in tray_win.descendants(control_type="Button"):
                    b_name = (b.element_info.name or "").strip()
                    if "숨겨진 아이콘" in b_name or "Show hidden icons" in b_name:
                        b.invoke()
                        time.sleep(0.4)
                        return
        except Exception:
            pass

        ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
        if ov and win32gui.IsWindowVisible(ov):
            try:
                win32gui.PostMessage(ov, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)
                win32gui.PostMessage(ov, win32con.WM_KEYUP, win32con.VK_ESCAPE, 0)
                time.sleep(0.3)
            except Exception:
                pass

    @staticmethod
    def _find_ta_icon_center_in_hwnd(hwnd: int, is_overflow: bool = False) -> Optional[Tuple[int, int]]:
        """지정된 윈도우 핸들 내에서 TA-STR / TA-PRS 트레이 아이콘의 중앙 좌표를 탐색합니다."""
        if not hwnd or not win32gui.IsWindowVisible(hwnd):
            return None
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0) or 1920
        screen_h = user32.GetSystemMetrics(1) or 1200

        def _scan() -> Optional[Tuple[int, int, str, object]]:
            app = Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)
            candidates = []
            for b in win.descendants(control_type="Button"):
                name = (b.element_info.name or "").strip()
                aid = (b.element_info.automation_id or "").strip()
                if "TA-STR" not in name and "TA-PRS" not in name:
                    continue
                # Shell_TrayWnd 내 실행 중인 앱 작업표시줄 버튼(Chrome/브라우저 등) 오탐 방지
                if not is_overflow:
                    if aid.startswith("Appid:") or "Chrome" in name or "Edge" in name:
                        continue
                rect = b.rectangle()
                if rect.width() <= 0 or rect.height() <= 0:
                    continue
                if rect.right <= 0 or rect.bottom <= 0 or rect.left >= screen_w or rect.top >= screen_h:
                    continue
                if not is_overflow and rect.left < screen_w // 2:
                    continue
                candidates.append((rect.width(), name, rect))

            if not candidates:
                return None

            # 가장 좁은(구체적인) 버튼 선택
            candidates.sort(key=lambda item: item[0])
            width, name, rect = candidates[0]

            # Windows 11 작업표시줄 UIA에서 트레이 버튼의 right가 화면 끝(예: 1920)까지
            # 늘어나 보고되는 경우, 실제 아이콘은 rect.left 기준 첫 아이콘 폭(~36px) 내에 위치
            if width > 80:
                cx = rect.left + min(rect.height() // 2, 20)
            else:
                cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            if not (0 <= cx < screen_w and 0 <= cy < screen_h):
                return None
            return cx, cy, name, rect

        try:
            first = _scan()
            if first is None:
                return None
            if is_overflow:
                # 오버플로 창 애니메이션으로 좌표가 흔들리는 현상 방지를 위해 안정화 대기
                time.sleep(0.15)
                second = _scan()
                if second is not None:
                    first = second
            cx, cy, name, rect = first
            print(f">>> [트레이 탐색] '{name}' 위치=({cx}, {cy}), rect={rect}, overflow={is_overflow}")
            return cx, cy
        except Exception:
            pass
        return None

    def _locate_ta_tray_icon(self, timeout: float = 20.0) -> Tuple[int, int, bool]:
        """
        TA-STR / TA-PRS 트레이 아이콘 좌표를 탐색합니다.
        1) 작업표시줄(Shell_TrayWnd)에 직접 고정·노출된 경우 오버플로를 열지 않고 좌표 반환
        2) 없으면 숨겨진 아이콘 영역(오버플로)을 열어 탐색
        3) 에이전트 업데이트 직후 등 일시적으로 트레이 아이콘이 재등록되는 중이라면
           timeout 동안 작업표시줄과 오버플로 영역을 반복 재탐색합니다.
        반환값: (x, y, opened_overflow)
        """
        deadline = time.time() + max(3.0, timeout)
        next_overflow_check_at = 0.0
        logged_waiting = False

        while True:
            tray_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            pos = self._find_ta_icon_center_in_hwnd(tray_hwnd, is_overflow=False)
            if pos is not None:
                return pos[0], pos[1], False

            now = time.time()
            if now >= next_overflow_check_at:
                self._open_tray_overflow()
                ov_deadline = min(deadline, time.time() + 1.8)
                while time.time() < ov_deadline:
                    ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
                    if ov and win32gui.IsWindowVisible(ov):
                        pos = self._find_ta_icon_center_in_hwnd(ov, is_overflow=True)
                        if pos is not None:
                            return pos[0], pos[1], True
                    time.sleep(0.2)

                # 오버플로에서도 미발견 시 팝업을 닫고 다음 주기까지 작업표시줄 재등장을 감시
                self._close_tray_overflow()
                next_overflow_check_at = time.time() + 4.0

            if time.time() >= deadline:
                break

            if not logged_waiting:
                print(
                    ">>> [트레이 탐색] TA-STR/TA-PRS 트레이 아이콘 미감지 "
                    "(에이전트 재시작·재등록 대기 후 재탐색 중...)"
                )
                logged_waiting = True
            time.sleep(0.5)

        raise RuntimeError(
            "작업표시줄 및 숨겨진 아이콘 영역에서 'TA-STR' 또는 'TA-PRS' 트레이 아이콘을 찾지 못했습니다."
        )

    def _double_click_tray_icon(self):
        """작업표시줄 또는 숨겨진 아이콘 영역에서 보안점검 아이콘 더블클릭"""
        with self._per_monitor_dpi() as user32:
            cx, cy, opened_overflow = self._locate_ta_tray_icon()

            user32.SetCursorPos(cx, cy)
            time.sleep(0.1)
            for _ in range(2):
                user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.08)
            time.sleep(0.6)

            if opened_overflow:
                self._close_tray_overflow()

    @staticmethod
    def _find_menu_item_center(menu_hwnd: int, item_name: str, fallback_ratio: float) -> Tuple[int, int]:
        """#32768 컨텍스트 메뉴에서 대상 항목의 중앙 좌표를 계산합니다 (HMENU 텍스트 탐색 우선)."""
        rect = win32gui.GetWindowRect(menu_hwnd)
        cx = (rect[0] + rect[2]) // 2
        try:
            hmenu = ctypes.windll.user32.SendMessageW(menu_hwnd, 0x01E1, 0, 0)  # MN_GETHMENU
            if hmenu:
                count = win32gui.GetMenuItemCount(hmenu)
                for idx in range(count):
                    try:
                        text = win32gui.GetMenuString(hmenu, idx, win32con.MF_BYPOSITION) or ""
                    except Exception:
                        text = ""
                    clean = text.replace("&", "").strip()
                    if item_name in clean:
                        item_rect = wintypes.RECT()
                        if ctypes.windll.user32.GetMenuItemRect(0, hmenu, idx, ctypes.byref(item_rect)):
                            if item_rect.right > item_rect.left and item_rect.bottom > item_rect.top:
                                return (
                                    (item_rect.left + item_rect.right) // 2,
                                    (item_rect.top + item_rect.bottom) // 2,
                                )
        except Exception:
            pass
        cy = rect[1] + int((rect[3] - rect[1]) * fallback_ratio)
        return cx, cy

    def click_tray_menu_item(self, item_name: str, timeout: float = 10.0) -> None:
        """
        트레이 아이콘을 우클릭하여 컨텍스트 메뉴(#32768)를 열고 지정된 항목을 클릭합니다.
        주의: taAssistant.exe가 관리자 권한(Elevated)으로 동작하는 환경에서는
        UIPI 제약으로 인해 테스트 실행 콘솔도 관리자 권한(Run as Administrator)이 필요합니다.
        """
        if item_name not in self.TRAY_MENU_RATIOS:
            raise ValueError(f"지원하지 않는 트레이 메뉴 항목입니다: {item_name}")

        with self._per_monitor_dpi() as user32:
            # 이전 테스트의 잔여 컨텍스트 메뉴(#32768)가 열려 있으면 먼저 정리
            stale_menu = win32gui.FindWindow("#32768", None)
            if stale_menu and win32gui.IsWindowVisible(stale_menu):
                user32.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
                user32.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.25)

            menu_hwnd = 0
            opened_overflow = False
            max_attempts = 3
            per_attempt_timeout = max(2.5, timeout / max_attempts)

            for attempt in range(1, max_attempts + 1):
                ix, iy, opened_overflow = self._locate_ta_tray_icon()

                user32.SetCursorPos(ix, iy)
                time.sleep(0.15)
                user32.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(0.06)
                user32.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

                start = time.time()
                while time.time() - start < per_attempt_timeout:
                    h = win32gui.FindWindow("#32768", None)
                    if h and win32gui.IsWindowVisible(h):
                        mrect = win32gui.GetWindowRect(h)
                        if mrect[2] > mrect[0] and mrect[3] > mrect[1]:
                            menu_hwnd = h
                            break
                    time.sleep(0.15)

                if menu_hwnd:
                    break

                if attempt < max_attempts:
                    print(
                        f">>> [AppController] 트레이 컨텍스트 메뉴(#32768) 미감지 "
                        f"({attempt}/{max_attempts}차) -> 포커스 안정화 후 재시도..."
                    )
                    if opened_overflow:
                        self._close_tray_overflow()
                        opened_overflow = False
                    user32.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
                    user32.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.5)

            if not menu_hwnd:
                if opened_overflow:
                    self._close_tray_overflow()
                raise TimeoutError("트레이 우클릭 컨텍스트 메뉴(#32768)가 열리지 않았습니다.")

            time.sleep(0.1)
            cx, cy = self._find_menu_item_center(
                menu_hwnd, item_name, self.TRAY_MENU_RATIOS[item_name]
            )

            user32.SetCursorPos(cx, cy)
            time.sleep(0.15)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.6)

            still_open = win32gui.FindWindow("#32768", None)
            if still_open and win32gui.IsWindowVisible(still_open):
                user32.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
                user32.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
                if opened_overflow:
                    self._close_tray_overflow()
                raise PermissionError(
                    f"트레이 메뉴 '{item_name}' 클릭 후 메뉴가 닫히지 않았습니다. "
                    "관리자 권한 콘솔에서 실행 중인지 확인하십시오."
                )

            if opened_overflow:
                self._close_tray_overflow()

    @staticmethod
    def _find_tray_dialogs(exclude_hwnds: Optional[set] = None) -> List[Tuple[int, str]]:
        """현재 화면에 표시된 트레이 알림/정보 팝업(#32770)들의 (HWND, 본문 텍스트) 목록을 반환합니다."""
        if exclude_hwnds is None:
            exclude_hwnds = set()

        found_hwnds = []
        def cb(h, _):
            if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h):
                if h not in exclude_hwnds and win32gui.GetClassName(h) == "#32770":
                    rect = win32gui.GetWindowRect(h)
                    w = rect[2] - rect[0]
                    h_len = rect[3] - rect[1]
                    # TopAegis 팝업 크기 필터 (가로 150~600, 세로 80~450)
                    if 150 < w < 600 and 80 < h_len < 450:
                        found_hwnds.append(h)
        win32gui.EnumWindows(cb, None)

        dialogs: List[Tuple[int, str]] = []
        for dlg_hwnd in found_hwnds:
            texts = []
            def child_cb(ch, _):
                txt = win32gui.GetWindowText(ch).strip()
                if txt:
                    texts.append(txt)
            win32gui.EnumChildWindows(dlg_hwnd, child_cb, None)
            if texts:
                dialogs.append((dlg_hwnd, "\n".join(texts)))
        return dialogs

    def wait_for_tray_dialog(self, timeout: float = 20.0, exclude_hwnds: Optional[set] = None) -> Optional[Tuple[int, str]]:
        """
        트레이 메뉴 클릭 후 출력되는 Win32 알림/정보 팝업(#32770)의 (HWND, 본문 텍스트)를 반환합니다.
        보안 에이전트 팝업은 윈도우 타이틀이 빈 문자열이고 내부 자식(Static) 컨트롤에 텍스트가 나뉘어 있으므로,
        모든 자식 컨트롤의 텍스트를 수집하여 결합합니다.
        """
        start = time.time()
        while time.time() - start < timeout:
            for dlg_hwnd, full_text in self._find_tray_dialogs(exclude_hwnds=exclude_hwnds):
                combined = full_text.replace("\n", " ")
                if any(k in combined for k in ("TA-", "서버", "IP", "소프트웨어", "폰트", "재검사", "업데이트", "성공")) or full_text:
                    return dlg_hwnd, full_text

            time.sleep(0.3)
        return None

    @staticmethod
    def close_tray_dialog(dlg_hwnd: int) -> bool:
        """
        트레이 알림/정보 팝업(#32770)의 [확인] 버튼(하단 Static/Button)을 클릭하여 안전하게 창을 닫습니다.
        """
        if not dlg_hwnd or not win32gui.IsWindow(dlg_hwnd):
            return True

        # 1. 자식 컨트롤 중 하단에 위치한 확인 버튼(Static 또는 Button) 탐색 및 클릭
        btn_candidates = []
        def child_cb(ch, _):
            rect = win32gui.GetWindowRect(ch)
            txt = win32gui.GetWindowText(ch).strip()
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if 30 <= w <= 130 and 15 <= h <= 50:
                btn_candidates.append((ch, rect, txt))
        win32gui.EnumChildWindows(dlg_hwnd, child_cb, None)

        if btn_candidates:
            # 가장 하단에 위치한 버튼 컨트롤 클릭
            target_btn = max(btn_candidates, key=lambda item: item[1][1])[0]
            try:
                win32gui.PostMessage(target_btn, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
                time.sleep(0.05)
                win32gui.PostMessage(target_btn, win32con.WM_LBUTTONUP, 0, 0)
            except Exception:
                pass

            btn_deadline = time.time() + 1.0
            while time.time() < btn_deadline:
                if not win32gui.IsWindow(dlg_hwnd) or not win32gui.IsWindowVisible(dlg_hwnd):
                    return True
                time.sleep(0.1)

        # 2. 아직 안 닫혔다면 IDOK(1) 및 WM_CLOSE 전송
        for msg, wparam in ((win32con.WM_COMMAND, 1), (win32con.WM_CLOSE, 0)):
            if not win32gui.IsWindow(dlg_hwnd) or not win32gui.IsWindowVisible(dlg_hwnd):
                return True
            try:
                win32gui.PostMessage(dlg_hwnd, msg, wparam, 0)
            except Exception:
                pass
            close_deadline = time.time() + 0.8
            while time.time() < close_deadline:
                if not win32gui.IsWindow(dlg_hwnd) or not win32gui.IsWindowVisible(dlg_hwnd):
                    return True
                time.sleep(0.1)

        return not (win32gui.IsWindow(dlg_hwnd) and win32gui.IsWindowVisible(dlg_hwnd))

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

    @classmethod
    def close_hr_ui(cls) -> bool:
        """
        인사 UI 창('TA 공지', TopAegis.Popper.Window)이 열려 있는 경우
        MSAA TitleBar 닫기 액션을 통해 안전하게 먼저 닫습니다.
        """
        import ctypes
        import win32gui
        try:
            import comtypes.client
            comtypes.client.GetModule("oleacc.dll")
            from comtypes.gen.Accessibility import IAccessible
        except Exception:
            IAccessible = None

        popper_hwnd = None
        def cb(h, _):
            nonlocal popper_hwnd
            if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h):
                if win32gui.GetClassName(h) == "TopAegis.Popper.Window" or "TA 공지" in win32gui.GetWindowText(h):
                    popper_hwnd = h
        win32gui.EnumWindows(cb, None)

        if not popper_hwnd:
            return True

        print(f">>> [AppController] 열려 있는 인사 UI(TA 공지, HWND={popper_hwnd}) 감지 -> 먼저 닫기 진행...")
        closed = False
        if IAccessible:
            pacc = ctypes.POINTER(IAccessible)()
            res = ctypes.windll.oleacc.AccessibleObjectFromWindow(
                popper_hwnd, 0xFFFFFFFE, ctypes.byref(IAccessible._iid_), ctypes.byref(pacc)
            )
            if res == 0 and pacc:
                try:
                    pacc.accDoDefaultAction(5)
                    time.sleep(0.5)
                    closed = not win32gui.IsWindow(popper_hwnd)
                except Exception as e:
                    print(f">>> [AppController] 인사 UI MSAA 닫기 예외: {e}")

        if not closed and win32gui.IsWindow(popper_hwnd):
            try:
                rect = win32gui.GetWindowRect(popper_hwnd)
                x = rect[2] - 25
                y = rect[1] + 20
                user32 = ctypes.windll.user32
                user32.SetCursorPos(x, y)
                time.sleep(0.05)
                user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                time.sleep(0.5)
            except Exception:
                pass

        time.sleep(0.5)
        is_closed = not (win32gui.IsWindow(popper_hwnd) and win32gui.IsWindowVisible(popper_hwnd))
        if is_closed:
            print(">>> [AppController] 인사 UI 닫기 완료!")
        return is_closed

    @classmethod
    def _wait_process_exited(cls, timeout: float = 4.0) -> bool:
        """taKeeper.exe 프로세스가 OS 프로세스 목록에서 완전히 사라질 때까지 대기합니다."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                res = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {cls.EXE_NAME}", "/NH"],
                    capture_output=True,
                    text=True,
                    encoding="cp949",
                    errors="replace",
                    timeout=3,
                )
                if cls.EXE_NAME.lower() not in (res.stdout or "").lower():
                    return True
            except Exception:
                return True
            time.sleep(0.2)
        return False

    def close(self, timeout: float = 5.0) -> bool:
        """
        보안점검 창 종료 전,
        1. 화면에 떠있는 인사 UI('TA 공지')가 있다면 인사 UI를 먼저 닫고
        2. 보안점검 창의 우상단 닫기(X) 버튼을 클릭하여 안전하게 닫고
        3. taKeeper.exe 프로세스가 완전히 종료될 때까지 대기(미종료 시 강제 정리)합니다.
        """
        # 1. 인사 UI 먼저 닫기
        self.close_hr_ui()

        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self._wait_process_exited(timeout=1.5)
            return True

        # 1. 대상 크롬 임베디드 웹뷰 핸들 탐색
        target_h = None
        def cb(ch, _):
            nonlocal target_h
            if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb, None)
        target_h = target_h or self.hwnd

        window_closed = False
        try:
            app = Application(backend="uia").connect(handle=target_h)
            win = app.window(handle=target_h)

            def _click_elem(elem):
                r_rect = win32gui.GetWindowRect(target_h)
                rect = elem.rectangle()
                local_x = (rect.left + rect.right) // 2 - r_rect[0]
                local_y = (rect.top + rect.bottom) // 2 - r_rect[1]
                lParam = (local_y << 16) | (local_x & 0xFFFF)
                win32gui.PostMessage(target_h, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                time.sleep(0.08)
                win32gui.PostMessage(target_h, win32con.WM_LBUTTONUP, 0, lParam)

            # 2. 우상단 닫기(X) 버튼 탐색 및 클릭 (상단바 영역에서 가장 우측에 위치한 버튼)
            start_time = time.time()
            close_btn = None
            while time.time() - start_time < timeout:
                win_rect = win.rectangle()
                top_bar_bottom = win_rect.top + 70

                candidate_btns = []
                for b in win.descendants(control_type="Button"):
                    r = b.rectangle()
                    if r.top < top_bar_bottom and r.right > win_rect.right - 150:
                        candidate_btns.append(b)

                if candidate_btns:
                    close_btn = max(candidate_btns, key=lambda btn: btn.rectangle().right)
                    break
                time.sleep(0.4)

            if close_btn:
                print(f">>> [AppController] 우상단 닫기 버튼(X) 클릭: {close_btn.rectangle()}")
                _click_elem(close_btn)

            # 3. 우상단 X 클릭 후 창 종료 또는 '종료' 확인 팝업 노출/종료 대기
            close_deadline = time.time() + max(timeout, 4.0)
            clicked_exit = False
            while time.time() < close_deadline:
                if not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)):
                    if not clicked_exit:
                        print(">>> [AppController] 안전 기준 점수 충족 상태: 팝업 없이 즉시 종료 완료!")
                    else:
                        print(">>> [AppController] 보안점검 창 정상 종료 확인 완료!")
                    window_closed = True
                    break

                if not clicked_exit:
                    exit_btn = None
                    try:
                        for b in win.descendants(control_type="Button"):
                            try:
                                if b.element_info.name == "종료":
                                    exit_btn = b
                                    break
                            except Exception:
                                continue
                    except Exception:
                        # 창 종료 중 웹뷰 DOM 해제로 인한 일시적 UIA KeyError(None) 등은 무시하고 다음 루프에서 창 종료 여부 재확인
                        time.sleep(0.15)
                        continue
                    if exit_btn:
                        print(f">>> [AppController] 안전 기준 점수 미만 팝업 감지 -> '종료' 버튼 클릭: {exit_btn.rectangle()}")
                        _click_elem(exit_btn)
                        clicked_exit = True
                        time.sleep(0.2)
                        continue
                time.sleep(0.25)
        except Exception as e:
            print(f">>> [AppController] 닫기 버튼 상호작용 중 예외 발생: {e}")

        # 4. 창 종료 여부 최종 확인 대기
        if not window_closed:
            final_deadline = time.time() + 2.0
            while time.time() < final_deadline:
                if not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)):
                    print(">>> [AppController] 보안점검 창 정상 종료 확인 완료!")
                    window_closed = True
                    break
                time.sleep(0.2)

        # 5. taKeeper.exe 프로세스 완전 종료 보장 (다음 테스트 실행 시 잔여 프로세스 간섭 방지)
        if not self._wait_process_exited(timeout=3.5):
            print(">>> [AppController] taKeeper.exe 잔여 프로세스 감지 -> 완전 종료 강제 정리...")
            self.kill_existing(timeout=5.0)
            window_closed = True

        self.hwnd = None
        return window_closed


# ---------------------------------------------------------------------------
# 지연된 트레이 재검사 완료 팝업 자동 정리 워처
# (프로그램 목록 재확인 / 폰트 목록 재확인 1분 타임아웃 PASS 이후 7~8분 뒤 뜨는 팝업 대응)
# ---------------------------------------------------------------------------
_delayed_watcher_lock = threading.Lock()
_delayed_watcher_keywords: set = set()
_delayed_watcher_stop = threading.Event()
_delayed_watcher_thread: Optional[threading.Thread] = None
_delayed_watcher_deadline: float = 0.0


def _delayed_rescan_watcher_loop() -> None:
    """백그라운드에서 지연된 재검사 완료 팝업(#32770)을 감시해 자동으로 닫습니다."""
    while not _delayed_watcher_stop.wait(1.0):
        with _delayed_watcher_lock:
            keywords = set(_delayed_watcher_keywords)
            deadline = _delayed_watcher_deadline

        if not keywords or time.time() >= deadline:
            break

        try:
            dialogs = AppController._find_tray_dialogs()
        except Exception:
            continue

        for dlg_hwnd, dlg_text in dialogs:
            if "재검사" not in dlg_text:
                continue
            matched = [kw for kw in keywords if kw in dlg_text]
            if not matched:
                continue

            print(f">>> [지연 팝업 자동 정리] {', '.join(matched)} 재검사 완료 팝업 감지(HWND={dlg_hwnd}) -> [확인] 닫기 처리")
            AppController.close_tray_dialog(dlg_hwnd)
            with _delayed_watcher_lock:
                for kw in matched:
                    _delayed_watcher_keywords.discard(kw)


def register_delayed_rescan_watcher(keyword: str, ttl_seconds: float = 900.0) -> None:
    """
    지정된 키워드(예: '소프트웨어', '폰트')를 포함한 지연 재검사 완료 팝업이
    이후 테스트 진행 중 출력되면 자동으로 닫도록 백그라운드 감시 스레드를 등록합니다.
    """
    global _delayed_watcher_thread, _delayed_watcher_deadline

    with _delayed_watcher_lock:
        _delayed_watcher_keywords.add(keyword)
        _delayed_watcher_deadline = max(_delayed_watcher_deadline, time.time() + ttl_seconds)

        if _delayed_watcher_thread is None or not _delayed_watcher_thread.is_alive():
            _delayed_watcher_stop.clear()
            _delayed_watcher_thread = threading.Thread(
                target=_delayed_rescan_watcher_loop,
                name="delayed-tray-popup-watcher",
                daemon=True,
            )
            _delayed_watcher_thread.start()


def stop_delayed_rescan_watcher() -> None:
    """지연 재검사 팝업 백그라운드 감시 스레드를 중지합니다."""
    with _delayed_watcher_lock:
        _delayed_watcher_keywords.clear()
        _delayed_watcher_stop.set()

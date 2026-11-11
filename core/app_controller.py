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
from typing import Optional, Tuple

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
                for b in tray_win.descendants(control_type="Button"):
                    if (b.element_info.name or "") == "숨겨진 아이콘 표시":
                        b.invoke()
                        opened = True
                        time.sleep(0.7)
                        break
        except Exception:
            pass

        if not opened:
            user32 = ctypes.windll.user32
            user32.SetCursorPos(1515, 1170)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 1515, 1170, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 1515, 1170, 0, 0)
            time.sleep(0.8)

    def _close_tray_overflow(self) -> None:
        """열려 있는 숨겨진 아이콘 오버플로 창을 UIA 버튼 이벤트로 닫습니다."""
        try:
            tray = win32gui.FindWindow("Shell_TrayWnd", None)
            if tray:
                tray_app = Application(backend="uia").connect(handle=tray)
                tray_win = tray_app.window(handle=tray)
                for b in tray_win.descendants(control_type="Button"):
                    if "숨겨진 아이콘 표시 숨기기" in (b.element_info.name or ""):
                        b.invoke()
                        time.sleep(0.4)
                        return
        except Exception:
            pass

        ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
        if ov and win32gui.IsWindowVisible(ov):
            user32 = ctypes.windll.user32
            user32.SetCursorPos(1515, 1170)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 1515, 1170, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 1515, 1170, 0, 0)
            time.sleep(0.3)

    def _get_ta_tray_icon_center(self) -> Tuple[int, int]:
        """오버플로 창 내 TA-STR / TA-PRS 트레이 아이콘의 화면 중앙 좌표를 탐색합니다."""
        try:
            ov = win32gui.FindWindow("TopLevelWindowForOverflowXamlIsland", None)
            if ov and win32gui.IsWindowVisible(ov):
                ov_app = Application(backend="uia").connect(handle=ov)
                ov_win = ov_app.window(handle=ov)
                for b in ov_win.descendants(control_type="Button"):
                    name = b.element_info.name or ""
                    if "TA-STR" in name or "TA-PRS" in name:
                        rect = b.rectangle()
                        return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
        except Exception:
            pass
        return (1463, 993)

    def _double_click_tray_icon(self):
        """작업표시줄 숨겨진 아이콘 영역에서 보안점검 아이콘 더블클릭 후 오버플로 닫기"""
        user32 = ctypes.windll.user32
        self._open_tray_overflow()
        cx, cy = self._get_ta_tray_icon_center()

        user32.SetCursorPos(cx, cy)
        time.sleep(0.1)
        for _ in range(2):
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
            time.sleep(0.08)
        time.sleep(0.6)

        self._close_tray_overflow()

    def click_tray_menu_item(self, item_name: str, timeout: float = 5.0) -> None:
        """
        트레이 아이콘을 우클릭하여 컨텍스트 메뉴(#32768)를 열고 지정된 항목을 클릭합니다.
        주의: taAssistant.exe가 관리자 권한(Elevated)으로 동작하는 환경에서는
        UIPI 제약으로 인해 테스트 실행 콘솔도 관리자 권한(Run as Administrator)이 필요합니다.
        """
        if item_name not in self.TRAY_MENU_RATIOS:
            raise ValueError(f"지원하지 않는 트레이 메뉴 항목입니다: {item_name}")

        user32 = ctypes.windll.user32
        self._open_tray_overflow()
        ix, iy = self._get_ta_tray_icon_center()

        user32.SetCursorPos(ix, iy)
        time.sleep(0.1)
        user32.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

        menu_hwnd = 0
        start = time.time()
        while time.time() - start < timeout:
            h = win32gui.FindWindow("#32768", None)
            if h and win32gui.IsWindowVisible(h):
                menu_hwnd = h
                break
            time.sleep(0.2)

        if not menu_hwnd:
            self._close_tray_overflow()
            raise TimeoutError("트레이 우클릭 컨텍스트 메뉴(#32768)가 열리지 않았습니다.")

        rect = win32gui.GetWindowRect(menu_hwnd)
        cx = (rect[0] + rect[2]) // 2
        cy = rect[1] + int((rect[3] - rect[1]) * self.TRAY_MENU_RATIOS[item_name])

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
            self._close_tray_overflow()
            raise PermissionError(
                f"트레이 메뉴 '{item_name}' 클릭 후 메뉴가 닫히지 않았습니다. "
                "관리자 권한 콘솔에서 실행 중인지 확인하십시오."
            )

        self._close_tray_overflow()

    def wait_for_tray_dialog(self, timeout: float = 10.0, exclude_hwnds: Optional[set] = None) -> Optional[Tuple[int, str]]:
        """
        트레이 메뉴 클릭 후 출력되는 Win32 알림/정보 팝업(#32770)의 (HWND, 본문 텍스트)를 반환합니다.
        보안 에이전트 팝업은 윈도우 타이틀이 빈 문자열이고 내부 자식(Static) 컨트롤에 텍스트가 나뉘어 있으므로,
        모든 자식 컨트롤의 텍스트를 수집하여 결합합니다.
        """
        if exclude_hwnds is None:
            exclude_hwnds = set()

        start = time.time()
        while time.time() - start < timeout:
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

            for dlg_hwnd in found_hwnds:
                texts = []
                def child_cb(ch, _):
                    txt = win32gui.GetWindowText(ch).strip()
                    if txt:
                        texts.append(txt)
                win32gui.EnumChildWindows(dlg_hwnd, child_cb, None)

                combined = " ".join(texts)
                if any(k in combined for k in ("TA-", "서버", "IP", "소프트웨어", "폰트", "재검사", "업데이트", "성공")) or texts:
                    full_text = "\n".join(texts)
                    return dlg_hwnd, full_text

            time.sleep(0.3)
        return None

    def close_tray_dialog(self, dlg_hwnd: int) -> bool:
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
                time.sleep(0.4)
            except Exception:
                pass

        # 2. 아직 안 닫혔다면 IDOK(1) 및 WM_CLOSE 전송
        if win32gui.IsWindow(dlg_hwnd):
            try:
                win32gui.PostMessage(dlg_hwnd, win32con.WM_COMMAND, 1, 0)
                time.sleep(0.3)
            except Exception:
                pass

        if win32gui.IsWindow(dlg_hwnd):
            try:
                win32gui.PostMessage(dlg_hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.3)
            except Exception:
                pass

        return not win32gui.IsWindow(dlg_hwnd)

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

    def close(self, timeout: float = 5.0) -> bool:
        """
        보안점검 창 종료 전,
        1. 화면에 떠있는 인사 UI('TA 공지')가 있다면 인사 UI를 먼저 닫고
        2. 보안점검 창의 우상단 닫기(X) 버튼을 클릭하여 안전하게 닫습니다.
        """
        # 1. 인사 UI 먼저 닫기
        self.close_hr_ui()

        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return True

        # 1. 대상 크롬 임베디드 웹뷰 핸들 탐색
        target_h = None
        def cb(ch, _):
            nonlocal target_h
            if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb, None)
        target_h = target_h or self.hwnd

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
                time.sleep(0.5)

            # 3. 우상단 X 클릭 후 창 상태 확인
            # - 안전 기준 점수 이상: 팝업 없이 창이 바로 닫힘
            # - 안전 기준 점수 미만: "종료하시겠습니까?" 팝업 노출 -> '종료' 버튼 클릭 필요
            if not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)):
                print(">>> [AppController] 안전 기준 점수 충족 상태: 팝업 없이 즉시 종료 완료!")
                return True

            # 창이 아직 열려 있다면 확인 팝업 감지 시 '종료' 버튼 클릭
            for _ in range(5):
                if not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)):
                    break
                exit_btn = None
                for b in win.descendants(control_type="Button"):
                    if b.element_info.name == "종료":
                        exit_btn = b
                        break
                if exit_btn:
                    print(f">>> [AppController] 안전 기준 점수 미만 팝업 감지 -> '종료' 버튼 클릭: {exit_btn.rectangle()}")
                    _click_elem(exit_btn)
                    time.sleep(0.5)
                    break
                time.sleep(0.3)
        except Exception as e:
            print(f">>> [AppController] 닫기 버튼 상호작용 중 예외 발생: {e}")

        # 4. 창 종료 여부 확인 대기
        for _ in range(10):
            if not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)):
                print(">>> [AppController] 보안점검 창 정상 종료 확인 완료!")
                return True
            time.sleep(0.3)

        return not (win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd))

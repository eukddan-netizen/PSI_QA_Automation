"""
트레이 아이콘 > '패치 현황' 웹뷰 (taPopper.exe / TopAegis.Popper.Window) 제어 Page Object
- '권고패치 현황' 테이블(종류, 전체, 설치, 패치율, 총계) 추출
- '설치 패치 목록' 테이블(종류, 이름, 발표일) 추출
- 하단 '확인' 버튼 클릭 및 창 닫기
"""

import ctypes
import re
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32gui
from pywinauto import Application, WindowSpecification


class TrayPatchStatusPage:
    """트레이 우클릭 > '패치 현황' 팝업('TA 공지') UI Automation 래퍼"""

    def __init__(self, hwnd: Optional[int] = None, timeout: float = 10.0):
        self.hwnd = hwnd or self.find_window(timeout=timeout)
        self.app: Optional[Application] = None
        self.win: Optional[WindowSpecification] = None
        self.child_hwnd: Optional[int] = None
        if self.hwnd:
            self._connect()

    @classmethod
    def find_window(cls, timeout: float = 10.0) -> Optional[int]:
        """패치 현황(TA 공지) 창 핸들 탐색"""
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
            time.sleep(0.4)
        return None

    def _connect(self) -> None:
        """Embedded Chromium(Chrome_WidgetWin_1) UIA 바인딩"""
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
        """창이 화면에 정상 노출되었는지 확인"""
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.hwnd = self.find_window(timeout=2.0)
            if self.hwnd:
                self._connect()
        return self.hwnd is not None and win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)

    @staticmethod
    def _parse_int(text: str) -> int:
        m = re.search(r"(\d+)", text or "")
        if not m:
            raise ValueError(f"숫자를 추출할 수 없습니다: {text!r}")
        return int(m.group(1))

    @staticmethod
    def _extract_table_rows(table_elem) -> List[List[str]]:
        rows: List[List[str]] = []
        for row in table_elem.children(control_type="DataItem"):
            cells = [(c.element_info.name or "").strip() for c in row.children(control_type="DataItem")]
            if cells:
                rows.append(cells)
        return rows

    def read_patch_status(self, timeout: float = 10.0) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
        """
        팝업 내 두 테이블의 렌더링 완료를 대기한 뒤 데이터를 추출합니다.
        반환값:
          - summary_by_type: {종류: {"total": int, "installed": int, "rate_text": str, "rate_value": int}}
          - installed_patches: [{"type": str, "name": str, "release_date": str}, ...]
        """
        if not self.win:
            self._connect()

        start = time.time()
        tables = []
        while time.time() - start < timeout:
            try:
                tables = self.win.descendants(control_type="Table")
                if len(tables) >= 2:
                    t0_rows = self._extract_table_rows(tables[0])
                    if any(r and r[0] == "총계" for r in t0_rows):
                        break
            except Exception:
                pass
            time.sleep(0.4)
        else:
            raise TimeoutError("'패치 현황' 팝업 테이블이 제한 시간 내에 렌더링되지 않았습니다.")

        summary_rows = self._extract_table_rows(tables[0])
        if not summary_rows or summary_rows[0][:4] != ["종류", "전체", "설치", "패치율"]:
            raise AssertionError(f"권고패치 현황 테이블 헤더가 예상과 다릅니다: {summary_rows[:1]}")

        summary_by_type: Dict[str, Dict[str, Any]] = {}
        for cells in summary_rows[1:]:
            if len(cells) < 4:
                continue
            category = cells[0]
            summary_by_type[category] = {
                "total": self._parse_int(cells[1]),
                "installed": self._parse_int(cells[2]),
                "rate_text": cells[3],
                "rate_value": self._parse_int(cells[3]),
            }

        list_rows = self._extract_table_rows(tables[1])
        if not list_rows or list_rows[0][:3] != ["종류", "이름", "발표일"]:
            raise AssertionError(f"설치 패치 목록 테이블 헤더가 예상과 다릅니다: {list_rows[:1]}")

        installed_patches: List[Dict[str, str]] = []
        for cells in list_rows[1:]:
            if len(cells) < 3:
                continue
            installed_patches.append(
                {
                    "type": cells[0],
                    "name": cells[1],
                    "release_date": cells[2],
                }
            )

        return summary_by_type, installed_patches

    def close(self) -> bool:
        """하단 [확인] 버튼을 클릭하여 창 닫기 (실패 시 MSAA 닫기 폴백)"""
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return True

        try:
            if self.win:
                for b in self.win.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() == "확인":
                        b.invoke()
                        time.sleep(0.6)
                        break
        except Exception:
            pass

        if win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd):
            from core.app_controller import AppController
            return AppController.close_hr_ui()
        return True


"""
보안점검 프로그램 점검결과 페이지 Object
- 크롬 임베디드 렌더러 기반 UIA 정밀 제어
- 특정 점검 항목(예: 7번 화면보호기) 상태('안전' / '취약') 조회
- 특정 항목의 '조치' 버튼 클릭 및 실시간 안전 반영 검증
- 상단 취약 개수 및 점수 조회
- 하단 '재점검' 버튼 제어
"""

import time
import win32gui
import win32con
from typing import Optional, Tuple, Dict
from pywinauto import Application
from os_handlers.screen_saver import ScreenSaverHandler


class InspectionResultPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def _get_target_window(self):
        """UIA 요소들이 존재하는 Chrome_WidgetWin_1 윈도우 핸들 탐색"""
        target_h = None
        def cb_child(ch, extra):
            nonlocal target_h
            cls = win32gui.GetClassName(ch)
            if "Chrome_WidgetWin_1" in cls:
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return target_h or self.hwnd

    def _get_app_window(self):
        h = self._get_target_window()
        app = Application(backend="uia").connect(handle=h)
        return app.window(handle=h)

    def navigate_to_results(self):
        """사이드바의 '점검결과' 메뉴 클릭"""
        win = self._get_app_window()
        for link in win.descendants(control_type="Hyperlink"):
            if link.element_info.name == "점검결과":
                print(">>> [ResultPage] '점검결과' 메뉴 클릭")
                try:
                    link.invoke()
                except Exception:
                    self._click_element(link)
                time.sleep(2.0)
                break

    def get_summary_stats(self) -> Dict[str, str]:
        """상단의 점검 결과 요약 정보(점수, 취약 항목 수 등) 조회"""
        win = self._get_app_window()
        stats = {}
        for d in win.descendants(control_type="Text"):
            name = d.element_info.name
            if name:
                if "취약:" in name:
                    stats["vulnerable_count"] = name
                elif "점검불가:" in name:
                    stats["cannot_check_count"] = name
        return stats

    def get_item_info(self, item_name: str = "화면 보호기") -> Tuple[Optional[str], Optional[object]]:
        """
        점검 결과 테이블에서 특정 항목의 (진단상태 문자열, 조치/상세보기 버튼) 반환
        - 상태: "안전", "취약", "점검불가"
        - 버튼: "조치" 버튼이 있으면 최우선 반환, 없으면 "상세보기" 반환
        """
        win = self._get_app_window()
        desc = win.descendants()

        target_idx = -1
        for i, d in enumerate(desc):
            if item_name in d.element_info.name:
                target_idx = i
                break

        if target_idx == -1:
            return None, None

        status = None
        action_btn = None
        detail_btn = None

        # 해당 항목 인덱스 주변에서 상태 및 버튼 정밀 탐색
        for j in range(target_idx, min(len(desc), target_idx + 10)):
            elem_name = desc[j].element_info.name
            ctrl_type = desc[j].element_info.control_type

            if elem_name in ["안전", "취약", "점검불가"]:
                status = elem_name

            if ctrl_type == "Button":
                if elem_name == "조치":
                    action_btn = desc[j]
                elif elem_name == "상세보기":
                    detail_btn = desc[j]

        # '조치' 버튼이 있으면 조치 버튼을, 없으면 상세보기 버튼 반환
        chosen_btn = action_btn or detail_btn
        return status, chosen_btn

    def _click_element(self, elem):
        """UIA 요소의 좌표를 계산하여 PostMessage 클릭"""
        rect = elem.rectangle()
        target_h = self._get_target_window()
        r_rect = win32gui.GetWindowRect(target_h)
        local_x = (rect.left + rect.right) // 2 - r_rect[0]
        local_y = (rect.top + rect.bottom) // 2 - r_rect[1]

        lParam = (local_y << 16) | (local_x & 0xFFFF)
        win32gui.PostMessage(target_h, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.08)
        win32gui.PostMessage(target_h, win32con.WM_LBUTTONUP, 0, lParam)

    def click_remediate_button_for_item(self, item_name: str = "화면 보호기") -> bool:
        """특정 항목의 '조치' 버튼 클릭"""
        status, btn = self.get_item_info(item_name)
        print(f">>> [ResultPage] '{item_name}' 현재 진단 상태: {status}")
        if btn and btn.element_info.name == "조치":
            print(f">>> [ResultPage] '{item_name}' '조치' 버튼 발견! 클릭 실행: {btn.rectangle()}")
            self._click_element(btn)
            time.sleep(2.5)  # 조치 적용 및 UI 실시간 반영 대기
            return True
        else:
            print(f">>> [ResultPage] '{item_name}' 조치 버튼이 없습니다. (현재 버튼: '{btn.element_info.name if btn else 'None'}')")
            return False

    def click_reinspect(self):
        """결과 화면 하단의 '재점검' 버튼 클릭"""
        win = self._get_app_window()
        for btn in win.descendants(control_type="Button"):
            if "재점검" in btn.element_info.name:
                print(">>> [ResultPage] '재점검' 버튼 클릭!")
                self._click_element(btn)
                time.sleep(10.0)  # 재점검 수행 대기
                break

    def verify_os_status(self) -> tuple[bool, str]:
        """실제 Windows OS 레지스트리의 화면보호기 안전/취약 상태 검증"""
        return ScreenSaverHandler.is_secure()

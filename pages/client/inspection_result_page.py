"""
보안점검 프로그램 점검결과 페이지 Object
- 크롬 임베디드 렌더러 기반 UIA 정밀 제어
- 특정 점검 항목(점검 번호 또는 항목 이름 키워드) 상태('안전' / '취약' / '점검불가') 조회
- 특정 항목의 '조치' 버튼 클릭 및 실시간 안전 반영 검증
- 상단 취약 개수, 안전 개수 및 점수 조회 및 조치 전후 가감 검증
- 하단 '재점검' 버튼 제어
"""

import re
import time
import win32gui
import win32con
from typing import Any, Dict, Optional, Tuple
from pywinauto import Application


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

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        상단의 점검 결과 요약 정보(점수, 전체/안전/취약/점검불가 항목 수)를 조회합니다.
        기존 문자열 키('vulnerable_count' 등)와 정수형 키('score_num', 'vulnerable_num' 등)를 함께 반환합니다.
        """
        win = self._get_app_window()
        stats: Dict[str, Any] = {}
        texts = [d.element_info.name.strip() for d in win.descendants(control_type="Text") if d.element_info.name]

        for idx, name in enumerate(texts):
            if name == "점검결과" and idx + 1 < len(texts):
                next_val = texts[idx + 1]
                if next_val.isdigit():
                    stats["score_num"] = int(next_val)
                    stats["score_text"] = f"{next_val}점"
            elif name.startswith("전체:"):
                stats["total_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["total_num"] = int(m.group(1))
            elif name.startswith("안전:"):
                stats["safe_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["safe_num"] = int(m.group(1))
            elif name.startswith("취약:"):
                stats["vulnerable_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["vulnerable_num"] = int(m.group(1))
            elif name.startswith("점검불가:"):
                stats["cannot_check_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["cannot_check_num"] = int(m.group(1))

        return stats

    def _find_item_Anchor_index(self, desc, item_name: str = "", check_num: Optional[int] = None) -> int:
        """
        결과 테이블에서 점검 번호(DataItem name == str(check_num)) 또는
        항목 이름 부분 문자열로 해당 행의 시작 인덱스를 탐색합니다.
        점검 개편으로 이름이나 번호 중 하나가 바뀌어도 유연하게 찾을 수 있습니다.
        """
        if check_num is not None:
            num_str = str(check_num)
            for i, d in enumerate(desc):
                if d.element_info.control_type == "DataItem" and d.element_info.name.strip() == num_str:
                    # 번호 셀 뒤쪽(i+1 ~ i+3)에 점검 제목 셀이 위치함
                    return i

        if item_name:
            for i, d in enumerate(desc):
                name = d.element_info.name or ""
                if item_name in name:
                    return i

        return -1

    def get_item_info(
        self, item_name: str = "화면 보호기", check_num: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[object]]:
        """
        점검 결과 테이블에서 특정 항목의 (진단상태 문자열, 조치/상세보기 버튼) 반환
        - 상태: "안전", "취약", "점검불가"
        - 버튼: "조치" 버튼이 있으면 최우선 반환, 없으면 "상세보기" 반환
        """
        win = self._get_app_window()
        desc = win.descendants()

        target_idx = self._find_item_Anchor_index(desc, item_name=item_name, check_num=check_num)
        if target_idx == -1:
            return None, None

        status = None
        action_btn = None
        detail_btn = None

        # 해당 항목 인덱스 주변(번호 셀부터 최대 12개 요소)에서 상태 및 버튼 정밀 탐색
        for j in range(target_idx, min(len(desc), target_idx + 12)):
            elem_name = (desc[j].element_info.name or "").strip()
            ctrl_type = desc[j].element_info.control_type

            # 다음 행의 점검 번호(숫자 DataItem)를 만나면 탐색 종료
            if j > target_idx + 2 and ctrl_type == "DataItem" and elem_name.isdigit():
                break

            if elem_name in ["안전", "취약", "점검불가"] and status is None:
                status = elem_name

            if ctrl_type == "Button":
                if elem_name == "조치" and action_btn is None:
                    action_btn = desc[j]
                elif elem_name == "상세보기" and detail_btn is None:
                    detail_btn = desc[j]

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

    def click_remediate_button_for_item(
        self, item_name: str = "화면 보호기", check_num: Optional[int] = None
    ) -> bool:
        """특정 항목의 '조치' 버튼 클릭"""
        status, btn = self.get_item_info(item_name=item_name, check_num=check_num)
        label = f"{check_num}번({item_name})" if check_num else item_name
        print(f">>> [ResultPage] '{label}' 현재 진단 상태: {status}")
        if btn and btn.element_info.name == "조치":
            print(f">>> [ResultPage] '{label}' '조치' 버튼 발견! 클릭 실행: {btn.rectangle()}")
            self._click_element(btn)
            time.sleep(2.5)  # 조치 적용 및 UI 실시간 반영 대기
            return True
        else:
            print(
                f">>> [ResultPage] '{label}' 조치 버튼이 없습니다. "
                f"(현재 버튼: '{btn.element_info.name if btn else 'None'}')"
            )
            return False

    def click_reinspect(self):
        """결과 화면 하단의 '재점검' 버튼 클릭"""
        win = self._get_app_window()
        for btn in win.descendants(control_type="Button"):
            if "재점검" in (btn.element_info.name or ""):
                print(">>> [ResultPage] '재점검' 버튼 클릭!")
                self._click_element(btn)
                time.sleep(10.0)  # 재점검 수행 대기
                break

    @staticmethod
    def verify_common_remediation_metrics(before_stats: Dict[str, Any], after_stats: Dict[str, Any]) -> None:
        """
        53개 점검 공통 검증 시나리오:
        1) 조치 후 상단 '취약' 카운트가 조치 전보다 감소했는지 검증
        2) 조치 후 상단 '안전' 카운트가 증가하고, 점수가 서버 배점 설정에 따라 가감(상승 또는 유지)되었는지 확인
        """
        print(f">>> [공통 요약 검증] 조치 전: {before_stats} -> 조치 후: {after_stats}")

        if "vulnerable_num" in before_stats and "vulnerable_num" in after_stats:
            assert after_stats["vulnerable_num"] < before_stats["vulnerable_num"], (
                f"조치 후 취약 건수가 감소하지 않았습니다: "
                f"조치 전 {before_stats['vulnerable_num']}건 -> 조치 후 {after_stats['vulnerable_num']}건"
            )

        if "safe_num" in before_stats and "safe_num" in after_stats:
            assert after_stats["safe_num"] > before_stats["safe_num"], (
                f"조치 후 안전 건수가 증가하지 않았습니다: "
                f"조치 전 {before_stats['safe_num']}건 -> 조치 후 {after_stats['safe_num']}건"
            )

        if "score_num" in before_stats and "score_num" in after_stats:
            delta = after_stats["score_num"] - before_stats["score_num"]
            print(f">>> [점수 가감 확인] 조치 전 {before_stats['score_num']}점 -> 조치 후 {after_stats['score_num']}점 (변화량: {delta:+d}점)")
            assert after_stats["score_num"] >= before_stats["score_num"], (
                f"조치 후 보안 점수가 오히려 하락했습니다: "
                f"{before_stats['score_num']}점 -> {after_stats['score_num']}점"
            )

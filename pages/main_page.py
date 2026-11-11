"""
보안점검 프로그램 메인 페이지 Object
- 크롬 임베디드 웹 뷰(Chrome_WidgetWin_1) 정밀 탐색
- '▶ 점검 시작' 버튼 정밀 좌표 및 PostMessage 클릭
- 점검 상태 모니터링 및 탭 전환('메인' -> '점검' -> '점검결과') 검증
- 메인 대시보드 '점검 정보' 카드 텍스트/방패 색상/종료 경고 팝업 검증
"""

import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import ctypes
import win32gui
import win32con
from PIL import ImageGrab
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

    def _connect_window(self):
        """타깃 크롬 웹뷰 HWND 및 pywinauto 윈도우 객체 반환"""
        target_h = self._get_target_hwnd()
        app = Application(backend="uia").connect(handle=target_h)
        return target_h, app.window(handle=target_h)

    def bring_to_front(self) -> None:
        """보안점검 창을 복원하고 최상단 포커스로 활성화"""
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

    def is_window_visible(self) -> bool:
        """보안점검 메인 창이 현재 화면에 표시 중인지 확인"""
        return bool(self.hwnd and win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd))

    def get_active_tab_name(self) -> Optional[str]:
        """좌측 사이드바에서 현재 활성화된 탭 이름('메인', '점검', '점검결과' 등) 반환"""
        _, win = self._connect_window()
        for link in win.descendants(control_type="Hyperlink"):
            cls = link.element_info.class_name or ""
            if "current" in cls or "router-link-active" in cls:
                name = (link.element_info.name or "").strip()
                if name:
                    return name
        return None

    def navigate_to_tab(self, tab_name: str, timeout: float = 8.0) -> None:
        """사이드바 탭 링크 클릭 후 해당 탭 활성화 대기"""
        target_h, win = self._connect_window()
        clicked = False
        for link in win.descendants(control_type="Hyperlink"):
            if (link.element_info.name or "").strip() == tab_name:
                print(f">>> [MainPage] '{tab_name}' 탭 이동 클릭...")
                try:
                    link.invoke()
                except Exception:
                    self._click_element(link, target_h)
                clicked = True
                break

        if not clicked:
            raise RuntimeError(f"사이드바에서 '{tab_name}' 탭을 찾을 수 없습니다.")

        start = time.time()
        while time.time() - start < timeout:
            if self.get_active_tab_name() == tab_name:
                time.sleep(0.5)
                return
            time.sleep(0.25)
        raise TimeoutError(f"'{tab_name}' 탭으로 전환되지 않았습니다. (현재: {self.get_active_tab_name()})")

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

        # 웹뷰 DOM 렌더링 대기 및 '메인' 탭 / '▶ 점검 시작' 버튼 탐색 (최대 8초)
        start_btn = None
        clicked_main_tab = False
        for _ in range(16):
            for b in win.descendants(control_type="Button"):
                b_name = b.element_info.name or ""
                if "점검 시작" in b_name or "점검시작" in b_name:
                    start_btn = b
                    break
            if start_btn:
                break

            if not clicked_main_tab:
                for link in win.descendants(control_type="Hyperlink"):
                    if link.element_info.name == "메인":
                        print(">>> [MainPage] '메인' 탭 링크 클릭...")
                        try:
                            link.invoke()
                        except Exception:
                            self._click_element(link, target_h)
                        clicked_main_tab = True
                        time.sleep(1.0)
                        break

            time.sleep(0.5)

        if not start_btn:
            raise RuntimeError("화면에서 '▶ 점검 시작' 버튼을 찾을 수 없습니다.")

        print(f">>> [MainPage] '▶ 점검 시작' 버튼 발견: Screen={start_btn.rectangle()}")
        self._click_element(start_btn, target_h)
        print(">>> [MainPage] '▶ 점검 시작' 클릭 메시지 전송 완료!")
        return True

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

    def wait_for_inspection_and_result_tab(self, timeout: float = 25.0) -> Dict[str, Any]:
        """
        '▶ 점검 시작' 클릭 후 '점검' 탭 진행을 거쳐 '점검결과' 탭으로 자동 이동할 때까지 폴링 대기합니다.
        """
        start = time.time()
        tabs_seen: List[str] = []
        reached_result = False

        while time.time() - start < timeout:
            active = self.get_active_tab_name()
            if active and (not tabs_seen or tabs_seen[-1] != active):
                tabs_seen.append(active)
                print(f">>> [MainPage] 활성 탭 전환 감지: {active}")
            if active == "점검결과":
                reached_result = True
                time.sleep(1.0)
                break
            time.sleep(0.15)

        elapsed = round(time.time() - start, 2)
        return {
            "tabs_seen": tabs_seen,
            "entered_inspection_tab": "점검" in tabs_seen,
            "reached_result_tab": reached_result,
            "elapsed": elapsed,
        }

    def _get_inspection_card_geometry(self, timeout: float = 10.0) -> Tuple[Any, Any, List[Any]]:
        """'점검 정보' 카드 내부의 main 영역, '▶ 점검 시작' 버튼 및 카드 텍스트 요소 목록 반환 (DOM 렌더링 대기 포함)"""
        deadline = time.time() + timeout
        while True:
            _, win = self._connect_window()
            start_btn = None
            for b in win.descendants(control_type="Button"):
                b_name = b.element_info.name or ""
                if "점검 시작" in b_name or "점검시작" in b_name:
                    start_btn = b
                    break

            if start_btn is not None:
                main_rect = win.rectangle()
                for grp in win.descendants(control_type="Group"):
                    if (grp.element_info.class_name or "") == "main":
                        main_rect = grp.rectangle()
                        break

                start_rect = start_btn.rectangle()
                card_texts: List[Any] = []
                for elem in win.descendants(control_type="Text"):
                    name = elem.element_info.name
                    if not name:
                        continue
                    r = elem.rectangle()
                    if (
                        r.top >= main_rect.top
                        and r.bottom <= start_rect.top + 5
                        and r.left >= start_rect.left - 150
                        and r.right <= start_rect.right + 150
                    ):
                        card_texts.append(elem)

                if card_texts:
                    return main_rect, start_btn, card_texts

            if time.time() >= deadline:
                raise RuntimeError("메인 화면에서 '▶ 점검 시작' 버튼 및 점검 정보 텍스트를 찾을 수 없습니다.")
            time.sleep(0.4)

    def wait_for_main_ready(self, timeout: float = 12.0) -> Dict[str, Any]:
        """메인 화면 웹뷰 DOM('▶ 점검 시작', 안전기준점수, 상태 텍스트)이 완전히 렌더링될 때까지 대기"""
        deadline = time.time() + timeout
        last_info: Dict[str, Any] = {}
        while True:
            try:
                remaining = max(1.0, deadline - time.time())
                self._get_inspection_card_geometry(timeout=min(remaining, 3.0))
                last_info = self.get_inspection_info()
                if last_info.get("status") != "알수없음" and last_info.get("safety_score") is not None:
                    time.sleep(0.4)
                    return last_info
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError(f"메인 화면 DOM 로딩 대기 시간 초과: 마지막 파싱={last_info}")
            time.sleep(0.4)

    def get_inspection_info(self) -> Dict[str, Any]:
        """
        메인 화면 좌상단 '점검 정보' 카드의 상태/점수/취약 건수/안전기준점수 텍스트를 파싱하여 반환합니다.
        """
        _, _, card_texts = self._get_inspection_card_geometry()
        raw_texts = [t.element_info.name for t in card_texts]
        joined = "".join(raw_texts)

        need_scan = "취약점" in joined and "검사 필요" in joined and "검사를 진행해 주십시오" in joined
        score_m = re.search(r"점검결과\s*(\d+)\s*점", joined)
        counts_m = re.search(r"(\d+)\s*개\s*항목\s*중\s*(\d+)\s*개\s*취약", joined)
        safety_m = re.search(r"안전기준점수\s*(\d+)\s*점", joined)

        score = int(score_m.group(1)) if score_m else None
        total_count = int(counts_m.group(1)) if counts_m else None
        vulnerable_count = int(counts_m.group(2)) if counts_m else None
        safety_score = int(safety_m.group(1)) if safety_m else None

        if need_scan:
            status = "대기"
        elif score is not None and safety_score is not None:
            status = "안전" if score >= safety_score else "취약"
        else:
            status = "알수없음"

        return {
            "status": status,
            "need_scan_text": need_scan,
            "score": score,
            "total_count": total_count,
            "vulnerable_count": vulnerable_count,
            "safety_score": safety_score,
            "raw_texts": raw_texts,
            "joined_text": joined,
        }

    def get_shield_visual_state(self) -> Dict[str, Any]:
        """
        '점검 정보' 카드 상단 방패 아이콘 영역을 화면 캡처하여 색상 기반으로 상태('대기'/'양호'/'위험')를 판별합니다.
        """
        self.bring_to_front()
        main_rect, start_btn, card_texts = self._get_inspection_card_geometry()
        start_rect = start_btn.rectangle()
        text_top = min(t.rectangle().top for t in card_texts) if card_texts else (start_rect.top - 115)

        cx = (start_rect.left + start_rect.right) // 2
        top_y = main_rect.top + 15
        bot_y = max(top_y + 40, text_top - 10)
        bbox = (cx - 85, top_y, cx + 85, bot_y)

        crop = ImageGrab.grab(bbox=bbox).convert("RGB")
        pixels = crop.get_flattened_data()

        red = sum(1 for r, g, b in pixels if r > 150 and g < 90 and b < 90)
        blue = sum(1 for r, g, b in pixels if b > 170 and r < 100)
        gray = sum(1 for r, g, b in pixels if abs(r - g) < 20 and abs(g - b) < 20 and 80 < r < 230)

        if red > 800 and red > blue * 2:
            state = "위험"
        elif blue > 800 and blue > red * 2:
            state = "양호"
        elif gray > 800 and red < 150 and blue < 150:
            state = "대기"
        else:
            state = "알수없음"

        return {"state": state, "red": red, "blue": blue, "gray": gray, "bbox": bbox}

    def get_user_info(self) -> Dict[str, str]:
        """
        메인 화면 우측 상단의 '사용자 정보' 카드 정보를 딕셔너리로 추출:
        {
            "os": "Windows 11 Pro 25H2",
            "department": "t1",
            "username": "KYC",
            "ip": "192.168.2.28",
            "last_inspection_time": "2026-11-11 13:23:04"
        }
        """
        target_h, win = self._connect_window()
        texts = [(el.element_info.name or "").strip() for el in win.descendants(control_type="Text")]
        info: Dict[str, str] = {}
        for i, t in enumerate(texts):
            if t == "OS 정보" and i + 1 < len(texts):
                info["os"] = texts[i + 1]
            elif t == "부서명" and i + 1 < len(texts):
                info["department"] = texts[i + 1]
            elif t == "사용자명" and i + 1 < len(texts):
                info["username"] = texts[i + 1]
            elif t == "사용자 IP" and i + 1 < len(texts):
                info["ip"] = texts[i + 1]
            elif t == "최근점검일시" and i + 1 < len(texts):
                info["last_inspection_time"] = texts[i + 1]
        return info

    RADAR_SPOKE_ANGLES = {
        "바이러스백신": -90,
        "소프트웨어": -18,
        "보안패치": 54,
        "계정&패스워드": 126,
        "Windows 설정": 198,
    }

    def get_radar_chart_element(self) -> Any:
        """좌하단 PC보안지표 레이더 차트 Image 컨트롤 반환"""
        _, win = self._connect_window()
        for elem in win.descendants(control_type="Image"):
            r = elem.rectangle()
            if r.width() > 300 and r.left < 500:
                return elem
        raise RuntimeError("메인 화면에서 PC보안지표 레이더 차트 요소를 찾을 수 없습니다.")

    def hover_and_get_radar_tooltip(self, category: str, score: int, timeout: float = 3.0) -> Optional[int]:
        """
        지정된 지표 카테고리(예: '바이러스백신')의 점수(0~100)에 해당하는
        레이더 차트 다각형 꼭짓점 좌표로 마우스를 호버하고, 표시되는 툴팁 점수(int)를 반환합니다.
        """
        if category not in self.RADAR_SPOKE_ANGLES:
            raise ValueError(f"지원하지 않는 보안지표 항목입니다: {category}")

        self.bring_to_front()
        chart = self.get_radar_chart_element()
        cr = chart.rectangle()
        cx = (cr.left + cr.right) // 2
        cy = (cr.top + cr.bottom) // 2
        r_max = int(cr.height() * 0.387)

        deg = self.RADAR_SPOKE_ANGLES[category]
        r_val = r_max * (max(0, min(100, score)) / 100.0)
        vx = int(round(cx + math.cos(math.radians(deg)) * r_val))
        vy = int(round(cy + math.sin(math.radians(deg)) * r_val))

        user32 = ctypes.windll.user32
        _, win = self._connect_window()

        start = time.time()
        while time.time() - start < timeout:
            user32.SetCursorPos(vx, vy)
            time.sleep(0.4)

            for d in win.descendants(control_type="Text"):
                name = (d.element_info.name or "").strip()
                tr = d.rectangle()
                if cr.left <= tr.left <= cr.right and cr.top <= tr.top <= cr.bottom:
                    if name.isdigit() and name not in ("0", "53", "89", "90"):
                        return int(name)

            # 약간의 미세 지터(±2px) 재시도
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                user32.SetCursorPos(vx + dx, vy + dy)
                time.sleep(0.2)
                for d in win.descendants(control_type="Text"):
                    name = (d.element_info.name or "").strip()
                    tr = d.rectangle()
                    if cr.left <= tr.left <= cr.right and cr.top <= tr.top <= cr.bottom:
                        if name.isdigit() and name not in ("0", "53", "89", "90"):
                            return int(name)

        return None

    def read_all_radar_tooltips(self, expected_scores: Dict[str, int]) -> Dict[str, Optional[int]]:
        """5개 지표 항목에 대해 순차적으로 꼭짓점 호버 툴팁 점수를 수집하여 반환"""
        results = {}
        for cat in self.RADAR_SPOKE_ANGLES:
            score = expected_scores.get(cat, 0)
            val = self.hover_and_get_radar_tooltip(category=cat, score=score)
            results[cat] = val
            print(f">>> [MainPage] 보안지표 '{cat}' 호버 점수 툴팁: {val} (기대치: {score})")
        return results

    def click_close_button(self) -> None:
        """창 우상단 닫기(X) 버튼 클릭"""
        self.bring_to_front()
        target_h, win = self._connect_window()
        win_rect = win.rectangle()
        top_bar_bottom = win_rect.top + 70

        candidate_btns = []
        for b in win.descendants(control_type="Button"):
            r = b.rectangle()
            if r.top < top_bar_bottom and r.right > win_rect.right - 150:
                candidate_btns.append(b)

        if not candidate_btns:
            raise RuntimeError("우상단 닫기(X) 버튼을 찾을 수 없습니다.")

        close_btn = max(candidate_btns, key=lambda btn: btn.rectangle().right)
        print(f">>> [MainPage] 우상단 닫기(X) 버튼 클릭: {close_btn.rectangle()}")
        self._click_element(close_btn, target_h)
        time.sleep(0.5)

    def wait_for_close_warning_popup(self, timeout: float = 3.5) -> Optional[Dict[str, Any]]:
        """
        안전 기준 점수 미만 상태에서 닫기(X) 클릭 시 노출되는 경고 팝업을 감지하여 정보 반환.
        미노출 시 None 반환.
        """
        start = time.time()
        while time.time() - start < timeout:
            if not self.is_window_visible():
                return None

            _, win = self._connect_window()
            texts = [
                (d.element_info.name or "").strip()
                for d in win.descendants(control_type="Text")
                if d.element_info.name
            ]
            buttons = {
                (b.element_info.name or "").strip(): b
                for b in win.descendants(control_type="Button")
                if b.element_info.name
            }

            if any("안전 기준 점수 미만" in t or "종료하시겠습니까" in t for t in texts):
                relevant_texts = [
                    t for t in texts if "안전 기준 점수" in t or "종료하시겠습니까" in t
                ]
                return {
                    "message": "\n".join(relevant_texts),
                    "buttons": list(buttons.keys()),
                }
            time.sleep(0.3)
        return None

    def click_popup_button(self, button_name: str, timeout: float = 3.0) -> bool:
        """종료 경고 팝업의 지정 버튼('취소' 또는 '종료') 클릭"""
        start = time.time()
        while time.time() - start < timeout:
            target_h, win = self._connect_window()
            for b in win.descendants(control_type="Button"):
                if (b.element_info.name or "").strip() == button_name:
                    print(f">>> [MainPage] 팝업 '{button_name}' 버튼 클릭: {b.rectangle()}")
                    self._click_element(b, target_h)
                    time.sleep(0.6)
                    return True
            time.sleep(0.25)
        return False

    def click_help_card(self) -> None:
        """메인 대시보드 우측 '도움말 안내' 카드 클릭"""
        self.bring_to_front()
        target_h, win = self._connect_window()
        for d in win.descendants():
            name = (d.element_info.name or "").strip()
            if name == "도움말 안내":
                print(f">>> [MainPage] '도움말 안내' 카드 클릭: {d.rectangle()}")
                self._click_element(d, target_h)
                time.sleep(0.5)
                return
        raise RuntimeError("메인 화면에서 '도움말 안내' 카드를 찾을 수 없습니다.")

    def click_password_safety_card(self) -> None:
        """메인 대시보드 우측 '암호 안전성 검사' 카드 클릭"""
        self.bring_to_front()
        target_h, win = self._connect_window()
        for d in win.descendants():
            name = (d.element_info.name or "").strip()
            if name == "암호 안전성 검사":
                print(f">>> [MainPage] '암호 안전성 검사' 카드 클릭: {d.rectangle()}")
                self._click_element(d, target_h)
                time.sleep(0.5)
                return
        raise RuntimeError("메인 화면에서 '암호 안전성 검사' 카드를 찾을 수 없습니다.")

    def get_past_history_bars(self) -> List[Any]:
        """
        메인 화면 우하단 '지난 검사내역' 차트의 6개 막대(bar) UIA 요소 반환
        - x좌표 오름차순 정렬 (좌측 -> 우측 = 과거 -> 최신)
        """
        _, win = self._connect_window()
        bars = []
        for d in win.descendants():
            cls = d.element_info.class_name or ""
            if cls == "bar":
                bars.append(d)
        return sorted(bars, key=lambda b: b.rectangle().left)

    def hover_and_get_past_history_score(self, bar_index: int, timeout: float = 3.0) -> Optional[int]:
        """
        '지난 검사내역' 지정 막대(0~5, 5가 가장 최신)로 마우스 커서를 호버하고 표시되는 점수(int) 반환
        """
        bars = self.get_past_history_bars()
        if not bars:
            raise RuntimeError("메인 화면에서 '지난 검사내역' 막대 그래프 요소를 찾을 수 없습니다.")
        if not (0 <= bar_index < len(bars)):
            raise IndexError(f"막대 인덱스 범위 초과 (0~{len(bars)-1}): {bar_index}")

        target_bar = bars[bar_index]
        rect = target_bar.rectangle()
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2

        self.bring_to_front()
        user32 = ctypes.windll.user32
        user32.SetCursorPos(cx, cy)
        time.sleep(0.3)

        start = time.time()
        while time.time() - start < timeout:
            _, win = self._connect_window()
            for d in win.descendants(control_type="Text"):
                dr = d.rectangle()
                name = (d.element_info.name or "").strip()
                # 막대 상단 근처에 표시되는 숫자 점수 텍스트
                if abs(dr.left - cx) < 35 and abs(dr.top - rect.top) < 35 and name.isdigit():
                    return int(name)
            time.sleep(0.2)
        return None

    def click_past_history_bar(self, bar_index: int) -> None:
        """'지난 검사내역' 지정 막대 클릭하여 '점검이력' 상세 페이지로 이동"""
        bars = self.get_past_history_bars()
        if not bars:
            raise RuntimeError("메인 화면에서 '지난 검사내역' 막대 그래프 요소를 찾을 수 없습니다.")
        if not (0 <= bar_index < len(bars)):
            raise IndexError(f"막대 인덱스 범위 초과: {bar_index}")

        target_bar = bars[bar_index]
        target_h, _ = self._connect_window()
        print(f">>> [MainPage] 지난 검사내역 {bar_index+1}번째 막대 클릭: {target_bar.rectangle()}")
        self._click_element(target_bar, target_h)
        time.sleep(1.5)

    def get_history_detail_info(self) -> Dict[str, Any]:
        """
        점검 상세 내역 화면에서 점검일시, 점수 파싱하여 반환
        """
        _, win = self._connect_window()
        info: Dict[str, Any] = {}
        for d in win.descendants(control_type="DataItem"):
            name = (d.element_info.name or "").strip()
            if name.endswith("점") and name[:-1].isdigit():
                info["score"] = int(name[:-1])
            elif re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", name):
                info["inspection_time"] = name
        return info

    def get_history_tab_records(self, limit: int = 6) -> List[Dict[str, Any]]:
        """
        '점검이력' 목록 화면에서 상위 N건의 점검 이력 레코드 반환
        """
        _, win = self._connect_window()
        items = [
            (d.element_info.name or "").strip()
            for d in win.descendants(control_type="DataItem")
            if d.element_info.name
        ]
        # 헤더 건너뛰고 레코드 파싱 (번호, 점검 일시, 결과 점수, 안전, 취약, 점검불가, 미점검 7열 구성)
        records = []
        for i, text in enumerate(items):
            if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", text):
                score_str = items[i + 1] if i + 1 < len(items) else ""
                score = int(score_str.replace("점", "")) if "점" in score_str and score_str.replace("점", "").isdigit() else None
                records.append({
                    "inspection_time": text,
                    "score": score,
                })
                if len(records) >= limit:
                    break
        return records




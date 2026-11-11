"""
보안점검 메인 화면 > 암호 안전성 검사 모달(PasswordSafetyModalPage) Page Object
- 메인 화면 우측 '암호 안전성 검사' 카드 클릭으로 모달 팝업 호출 및 닫기
- 입력 필드(pw-input) 텍스트 입력 및 지우기
- 눈 아이콘(pw-toggle) 클릭에 따른 암호 표시/숨김(Show/Hide password) 토글
- 5가지 기준(9자 이상, 대문자, 소문자, 숫자, 특수문자) 충족 상태(✓/✕) 및 등급(약함/보통/강함) 검증
- 일자 바(게이지 바) 픽셀 분석을 통한 채워진 비율(20%~100%) 및 색상(orange/green) 검증
- 한글 입력 시 "입력할 수 없는 문자가 포함되어 있습니다." 경고 감지
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import win32gui
import win32con
import win32clipboard
from PIL import ImageGrab
from pywinauto import Application
import pywinauto.keyboard as keyboard
from pywinauto import mouse


# 5가지 암호 안전성 기준 정규 명칭
PASSWORD_CRITERIA_NAMES = [
    "9자 이상",
    "대문자 포함",
    "소문자 포함",
    "숫자 포함",
    "특수문자 포함",
]


class PasswordSafetyModalPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def _get_target_hwnd(self) -> int:
        """메인 윈도우 내부 크롬 웹뷰 핸들 탐색"""
        target_h = None
        def cb_child(ch, _):
            nonlocal target_h
            cls_name = win32gui.GetClassName(ch)
            if "Chrome_WidgetWin_1" in cls_name or "Chrome_Render" in cls_name:
                target_h = ch
        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return target_h or self.hwnd

    def _connect_window(self):
        """pywinauto UIA 윈도우 객체 및 내부 크롬 HWND 반환"""
        target_h = self._get_target_hwnd()
        app = Application(backend="uia").connect(handle=target_h)
        return target_h, app.window(handle=target_h)

    def _safe_descendants(self, win, control_type: Optional[str] = None, retries: int = 4) -> List[Any]:
        """크롬 웹뷰 UIA control_type=None 일시 에러(KeyError) 방어 안전 조회"""
        for _ in range(retries):
            try:
                if control_type:
                    return win.descendants(control_type=control_type)
                return win.descendants()
            except (KeyError, Exception):
                time.sleep(0.25)
        return []

    def bring_to_front(self) -> None:
        """메인 창 활성화"""
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

    @classmethod
    def open_from_main(cls, main_page, timeout: float = 8.0) -> "PasswordSafetyModalPage":
        """
        메인 화면 우측 '암호 안전성 검사' 카드를 클릭하여 모달을 오픈합니다.
        """
        main_page.bring_to_front()
        target_h, win = main_page._connect_window()

        instance = cls(main_page.hwnd)

        # 이미 열려있는지 확인
        for d in instance._safe_descendants(win):
            if "pw-input" in (d.element_info.class_name or ""):
                return instance

        clicked = False
        for d in instance._safe_descendants(win):
            name = (d.element_info.name or "").strip()
            if name == "암호 안전성 검사":
                print(f">>> [PasswordSafetyModal] '암호 안전성 검사' 카드 클릭: {d.rectangle()}")
                main_page._click_element(d, target_h)
                clicked = True
                break

        if not clicked:
            raise RuntimeError("메인 화면에서 '암호 안전성 검사' 카드를 찾을 수 없습니다.")

        start = time.time()
        while time.time() - start < timeout:
            target_h, win = main_page._connect_window()
            for d in instance._safe_descendants(win):
                if "pw-input" in (d.element_info.class_name or ""):
                    time.sleep(0.5)
                    return instance
            time.sleep(0.3)

        raise TimeoutError("암호 안전성 검사 모달이 제한 시간 내에 열리지 않았습니다.")

    def is_open(self) -> bool:
        """암호 안전성 검사 모달이 현재 열려 있는지 확인"""
        if not win32gui.IsWindow(self.hwnd) or not win32gui.IsWindowVisible(self.hwnd):
            return False
        try:
            _, win = self._connect_window()
            for d in self._safe_descendants(win):
                if "pw-input" in (d.element_info.class_name or ""):
                    return True
        except Exception:
            pass
        return False

    def close(self, timeout: float = 4.0) -> bool:
        """모달 하단의 '닫기' 버튼을 클릭하여 모달 종료"""
        target_h, win = self._connect_window()
        close_btn = None
        for b in self._safe_descendants(win, control_type="Button"):
            if (b.element_info.name or "").strip() == "닫기":
                close_btn = b
                break

        if not close_btn:
            raise RuntimeError("암호 안전성 검사 모달의 '닫기' 버튼을 찾을 수 없습니다.")

        print(f">>> [PasswordSafetyModal] '닫기' 버튼 클릭: {close_btn.rectangle()}")
        try:
            close_btn.invoke()
        except Exception:
            close_btn.click_input()

        start = time.time()
        while time.time() - start < timeout:
            if not self.is_open():
                print(">>> [PasswordSafetyModal] 모달이 정상 종료되었습니다.")
                return True
            time.sleep(0.25)
        return False

    def get_title(self) -> str:
        """모달 상단 타이틀 반환"""
        _, win = self._connect_window()
        for d in self._safe_descendants(win, control_type="Text"):
            r = d.rectangle()
            # 모달 헤더 영역
            if 390 <= r.top <= 460 and 700 <= r.left <= 1200:
                name = (d.element_info.name or "").strip()
                if "암호" in name:
                    return name
        return ""

    def _get_edit_control(self):
        """암호 입력 필드(Edit) UIA 요소 반환"""
        _, win = self._connect_window()
        for d in self._safe_descendants(win):
            if "pw-input" in (d.element_info.class_name or "") or d.element_info.control_type == "Edit":
                return d
        raise RuntimeError("암호 입력 필드(pw-input)를 찾을 수 없습니다.")

    def _get_eye_button(self):
        """눈 아이콘(pw-toggle) Button UIA 요소 반환"""
        _, win = self._connect_window()
        for d in self._safe_descendants(win, control_type="Button"):
            cls_name = d.element_info.class_name or ""
            name = d.element_info.name or ""
            if "pw-toggle" in cls_name or name in ("Show password", "Hide password"):
                return d
        raise RuntimeError("눈 아이콘(pw-toggle) 버튼을 찾을 수 없습니다.")

    def clear_password(self) -> None:
        """입력창 텍스트 전체 삭제"""
        edit = self._get_edit_control()
        r = edit.rectangle()
        mouse.click(coords=(r.left + 50, r.top + 20))
        time.sleep(0.2)
        keyboard.send_keys("^a{BACKSPACE}")
        time.sleep(0.3)

    def type_password(self, pwd: str) -> None:
        """암호 입력 필드에 키보드로 텍스트 입력"""
        self.clear_password()
        if pwd:
            keyboard.send_keys(pwd, with_spaces=True)
            time.sleep(0.4)

    def paste_text(self, text: str) -> None:
        """클립보드를 통해 한글 또는 특수 텍스트 붙여넣기"""
        self.clear_password()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        keyboard.send_keys("^v")
        time.sleep(0.4)

    def is_password_visible(self) -> bool:
        """
        비밀번호가 화면에 보이는 상태인지 확인.
        - 보이는 상태: 눈 아이콘 버튼의 텍스트가 'Hide password'
        - 마스킹된 상태: 눈 아이콘 버튼의 텍스트가 'Show password'
        """
        eye_btn = self._get_eye_button()
        return (eye_btn.element_info.name or "").strip() == "Hide password"

    def toggle_password_visibility(self) -> bool:
        """
        눈 아이콘 버튼을 클릭하여 보임/숨김 토글 후, 변경된 상태(보임: True / 숨김: False) 반환
        """
        eye_btn = self._get_eye_button()
        before_state = self.is_password_visible()
        print(f">>> [PasswordSafetyModal] 눈 아이콘 클릭 (현재 보이는 상태: {before_state})")
        eye_btn.click_input()
        time.sleep(0.3)
        after_state = self.is_password_visible()
        print(f">>> [PasswordSafetyModal] 눈 아이콘 클릭 후 보이는 상태: {after_state}")
        return after_state

    def get_strength_grade(self) -> str:
        """우측 등급 텍스트 반환 ('약함', '보통', '강함')"""
        _, win = self._connect_window()
        for d in self._safe_descendants(win, control_type="Text"):
            name = (d.element_info.name or "").strip()
            if name in ("약함", "보통", "강함"):
                return name
        return ""

    def get_checklist_status(self) -> Dict[str, bool]:
        """
        5가지 기준 항목별 충족(True: ✓/pass) / 미충족(False: ✕) 상태 딕셔너리 반환
        예: {'9자 이상': False, '대문자 포함': True, ...}
        """
        _, win = self._connect_window()
        results = {}
        for d in self._safe_descendants(win, control_type="ListItem"):
            name = (d.element_info.name or "").strip()
            cls_name = d.element_info.class_name or ""
            is_pass = "pass" in cls_name or "✓" in name
            for crit in PASSWORD_CRITERIA_NAMES:
                if crit in name:
                    results[crit] = is_pass
                    break
        return results

    def get_gauge_bar_info(self) -> Dict[str, Any]:
        """
        인풋 바로 밑 일자 바(게이지 바) 픽셀을 분석하여 채워진 너비 비율(%) 및 색상 정보 반환
        - fill_ratio: 0.0 ~ 100.0 (%)
        - color: 'gray' | 'orange' | 'green'
        """
        edit = self._get_edit_control()
        r = edit.rectangle()
        # 게이지 바 영역 캡처: 인풋 바로 아래 높이 약 25px
        bar_bbox = (r.left, r.bottom + 2, r.right, r.bottom + 25)
        img = ImageGrab.grab(bbox=bar_bbox)
        bw, bh = img.size

        colored_x = []
        dominant_color = "gray"
        orange_count = 0
        green_count = 0

        for x in range(bw):
            for y in range(bh):
                pr, pg, pb = img.getpixel((x, y))[:3]
                # 주황색: R > 200, 80 < G < 180, B < 80
                if pr > 200 and 80 < pg < 180 and pb < 80:
                    colored_x.append(x)
                    orange_count += 1
                # 초록색: G > 150, 녹색이 지배적
                elif pg > 150 and pg > pr + 50 and pg > pb + 30:
                    colored_x.append(x)
                    green_count += 1

        fill_ratio = (len(set(colored_x)) / bw * 100.0) if bw > 0 else 0.0

        if green_count > orange_count and green_count > 50:
            dominant_color = "green"
        elif orange_count > 50:
            dominant_color = "orange"
        else:
            dominant_color = "gray"

        return {
            "fill_ratio": fill_ratio,
            "color": dominant_color,
            "orange_pixels": orange_count,
            "green_pixels": green_count,
        }

    def has_invalid_char_error(self) -> bool:
        """
        한글 등 비허용 문자 입력 시 표시되는 '입력할 수 없는 문자가 포함되어 있습니다.'
        빨간색 경고 문구가 화면에 표시되어 있는지 픽셀 분석을 통해 확인
        """
        edit = self._get_edit_control()
        r = edit.rectangle()
        # 인풋 아래 빨간 텍스트 영역: L: r.left, T: r.bottom + 5, R: r.right, B: r.bottom + 35
        error_bbox = (r.left, r.bottom + 5, r.right, r.bottom + 35)
        img = ImageGrab.grab(bbox=error_bbox)
        w, h = img.size

        red_pixels = 0
        for y in range(h):
            for x in range(w):
                pr, pg, pb = img.getpixel((x, y))[:3]
                # 밝은 빨간색: R > 180, G < 100, B < 100
                if pr > 180 and pg < 100 and pb < 100:
                    red_pixels += 1

        print(f">>> [PasswordSafetyModal] 빨간색 에러 문구 픽셀 수: {red_pixels}개")
        return red_pixels >= 40

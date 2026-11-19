"""
보안점검 프로그램 'PC정리' 탭 페이지 Object
- 상단 시스템 정보 카드: OS VERSION, ANTIVIRUS(새로고침 포함), FIREWALL(새로고침 포함)
- 하단 '내 PC 정리': 트리 체크박스 선택/해제, '정리하기' -> 확인 모달('정리 진행') -> 완료 모달('확인')
"""

import time
from typing import Dict, List, Optional, Tuple

from pages.client.main_page import MainPage


class CleanPage(MainPage):
    """'PC정리' 탭 전용 Page Object (MainPage 공통 기능 상속)"""

    WINDOWS_ITEMS = [
        "윈도우 임시 파일",
        "휴지통 비우기",
    ]

    BROWSER_ITEMS = [
        "방문 기록",
        "다운로드 기록",
        "쿠키 및 기타 사이트 데이터",
        "캐시된 이미지 및 파일",
        "자동 완성 양식 데이터",
    ]

    ALL_LEAF_ITEMS = WINDOWS_ITEMS + BROWSER_ITEMS

    def wait_for_clean_ready(self, timeout: float = 10.0) -> None:
        """'PC정리' 탭 DOM(OS VERSION, ANTIVIRUS, FIREWALL, 정리하기 버튼) 렌더링 완료 대기"""
        deadline = time.time() + timeout
        while True:
            try:
                if self.get_active_tab_name() == "PC정리":
                    _, win = self._connect_window()
                    texts = {(t.element_info.name or "").strip() for t in win.descendants(control_type="Text")}
                    buttons = {(b.element_info.name or "").strip() for b in win.descendants(control_type="Button")}
                    if {"OS VERSION", "ANTIVIRUS", "FIREWALL"}.issubset(texts) and "정리하기" in buttons:
                        time.sleep(0.3)
                        return
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError("'PC정리' 탭 DOM 로딩 대기 시간 초과")
            time.sleep(0.3)

    def _get_header_x_bounds(self) -> Dict[str, Tuple[int, int]]:
        """OS VERSION / ANTIVIRUS / FIREWALL 카드의 가로 영역(left, right)을 헤더 위치 기반으로 계산"""
        _, win = self._connect_window()
        headers: Dict[str, int] = {}
        for t in win.descendants(control_type="Text"):
            name = (t.element_info.name or "").strip()
            if name in ("OS VERSION", "ANTIVIRUS", "FIREWALL"):
                rect = t.rectangle()
                headers[name] = (rect.left + rect.right) // 2

        if len(headers) < 3:
            raise RuntimeError(f"시스템 정보 카드 헤더를 모두 찾지 못했습니다: {list(headers.keys())}")

        os_x = headers["OS VERSION"]
        av_x = headers["ANTIVIRUS"]
        fw_x = headers["FIREWALL"]

        os_av_mid = (os_x + av_x) // 2
        av_fw_mid = (av_x + fw_x) // 2

        return {
            "OS VERSION": (0, os_av_mid),
            "ANTIVIRUS": (os_av_mid, av_fw_mid),
            "FIREWALL": (av_fw_mid, 99999),
        }

    def _get_card_list_items(self, card_name: str) -> List[str]:
        """지정된 시스템 정보 카드('OS VERSION', 'ANTIVIRUS', 'FIREWALL') 내 ListItem 텍스트 목록 반환"""
        bounds = self._get_header_x_bounds()
        left_bound, right_bound = bounds[card_name]
        _, win = self._connect_window()

        items: List[Tuple[int, str]] = []
        for item in win.descendants(control_type="ListItem"):
            raw = (item.element_info.name or "").strip()
            if not raw.startswith("·"):
                continue
            rect = item.rectangle()
            cx = (rect.left + rect.right) // 2
            # 상단 카드 영역(네비게이션 및 하단 '내 PC 정리' 안내문 제외)
            if left_bound <= cx < right_bound and rect.top < 410:
                cleaned = raw.lstrip("·").strip()
                if cleaned:
                    items.append((rect.top, cleaned))

        items.sort(key=lambda x: x[0])
        return [text for _, text in items]

    @staticmethod
    def _parse_status_items(raw_items: List[str]) -> List[Dict[str, str]]:
        """'Windows Defender OFF', '알약 ON' 등의 문자열을 [{'name': ..., 'state': 'ON'|'OFF', 'raw': ...}]로 파싱"""
        parsed: List[Dict[str, str]] = []
        for text in raw_items:
            parts = text.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].upper() in ("ON", "OFF"):
                parsed.append({
                    "name": parts[0].strip(),
                    "state": parts[1].upper(),
                    "raw": text,
                })
            else:
                parsed.append({
                    "name": text,
                    "state": "",
                    "raw": text,
                })
        return parsed

    def get_os_version_text(self) -> str:
        """OS VERSION 카드에 표시된 OS 버전 문자열 반환 (예: 'Windows 11 Pro 25H2')"""
        items = self._get_card_list_items("OS VERSION")
        if not items:
            raise RuntimeError("OS VERSION 카드에서 버전 텍스트를 찾지 못했습니다.")
        return items[0]

    def get_antivirus_items(self) -> List[Dict[str, str]]:
        """ANTIVIRUS 카드의 백신 목록 및 ON/OFF 상태 반환"""
        return self._parse_status_items(self._get_card_list_items("ANTIVIRUS"))

    def get_firewall_items(self) -> List[Dict[str, str]]:
        """FIREWALL 카드의 방화벽 목록 및 ON/OFF 상태 반환"""
        return self._parse_status_items(self._get_card_list_items("FIREWALL"))

    def _click_card_refresh_button(self, card_index: int) -> None:
        """
        시스템 정보 카드의 새로고침(⭮) 버튼 클릭.
        card_index: 0 -> ANTIVIRUS(좌측), 1 -> FIREWALL(우측)
        """
        target_h, win = self._connect_window()
        refresh_btns = []
        for b in win.descendants(control_type="Button"):
            cls = b.element_info.class_name or ""
            name = (b.element_info.name or "").strip()
            if "refresh-button" in cls or name == "⭮":
                refresh_btns.append((b.rectangle().left, b))

        refresh_btns.sort(key=lambda x: x[0])
        if len(refresh_btns) <= card_index:
            raise RuntimeError(
                f"새로고침 버튼을 찾지 못했습니다. (발견 개수={len(refresh_btns)}, 요청 인덱스={card_index})"
            )

        btn = refresh_btns[card_index][1]
        try:
            btn.invoke()
        except Exception:
            self._click_element(btn, target_h)
        time.sleep(0.8)

    def click_antivirus_refresh(self) -> None:
        """ANTIVIRUS 카드 우측 상단 새로고침 버튼 클릭"""
        self._click_card_refresh_button(0)

    def click_firewall_refresh(self) -> None:
        """FIREWALL 카드 우측 상단 새로고침 버튼 클릭"""
        self._click_card_refresh_button(1)

    def _find_checkbox(self, name: str):
        """지정된 이름의 CheckBox UIA 요소 반환"""
        target_h, win = self._connect_window()
        for cb in win.descendants(control_type="CheckBox"):
            if (cb.element_info.name or "").strip() == name:
                return target_h, cb
        raise RuntimeError(f"'PC정리' 탭에서 '{name}' 체크박스를 찾을 수 없습니다.")

    def get_checkbox_state(self, name: str) -> int:
        """체크박스의 현재 상태(0=해제, 1=선택, 2=일부선택) 반환"""
        _, cb = self._find_checkbox(name)
        return int(cb.get_toggle_state())

    def set_checkbox(self, name: str, checked: bool, timeout: float = 4.0) -> None:
        """체크박스를 원하는 선택 상태(True/False)로 설정하고 반영까지 대기"""
        current = self.get_checkbox_state(name)
        target_state = 1 if checked else 0
        if current == target_state:
            return

        target_h, cb = self._find_checkbox(name)
        self._click_element(cb, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self.get_checkbox_state(name)
            if state == target_state:
                return
            # 일부선택(2) 상태에서 클릭했을 때 전체선택(1)이 되는 경우 한 번 더 클릭하여 해제
            if not checked and state == 1 and current == 2:
                target_h, cb = self._find_checkbox(name)
                self._click_element(cb, target_h)
                current = 1
            time.sleep(0.15)

        raise TimeoutError(f"'{name}' 체크박스 상태 변경({target_state}) 대기 시간 초과 (현재: {self.get_checkbox_state(name)})")

    def get_visible_checkbox_names(self) -> List[str]:
        """현재 'PC정리' 탭에 표시된 모든 체크박스 이름 목록 반환"""
        _, win = self._connect_window()
        names: List[str] = []
        for cb in win.descendants(control_type="CheckBox"):
            name = (cb.element_info.name or "").strip()
            if name:
                names.append(name)
        return names

    def uncheck_all(self) -> None:
        """모든 정리 항목 체크박스를 해제 상태로 초기화"""
        visible = self.get_visible_checkbox_names()
        if "전체" in visible and self.get_checkbox_state("전체") != 0:
            self.set_checkbox("전체", False)
        for item in visible:
            if item in ("전체", "Windows", "웹 브라우저"):
                continue
            if self.get_checkbox_state(item) != 0:
                self.set_checkbox(item, False)

    def click_clean_button(self) -> None:
        """'정리하기' 버튼 클릭"""
        target_h, win = self._connect_window()
        for b in win.descendants(control_type="Button"):
            if (b.element_info.name or "").strip() == "정리하기":
                try:
                    b.invoke()
                except Exception:
                    self._click_element(b, target_h)
                time.sleep(0.3)
                return
        raise RuntimeError("'PC정리' 탭에서 '정리하기' 버튼을 찾을 수 없습니다.")

    def wait_for_confirm_modal(self, timeout: float = 5.0) -> None:
        """'정리 확인' 모달('정리 진행'/'정리하기' / '취소' 버튼) 노출 대기"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win = self._connect_window()
            texts = {(t.element_info.name or "").strip() for t in win.descendants(control_type="Text")}
            buttons = {(b.element_info.name or "").strip() for b in win.descendants(control_type="Button")}
            if "정리 확인" in texts and ("정리 진행" in buttons or "정리하기" in buttons):
                return
            time.sleep(0.2)
        raise TimeoutError("'정리 확인' 모달이 표시되지 않았습니다.")

    def confirm_clean(self, timeout: float = 5.0) -> None:
        """'정리 확인' 모달에서 확인('정리 진행' 또는 '정리하기') 버튼 클릭"""
        self.wait_for_confirm_modal(timeout=timeout)
        target_h, win = self._connect_window()
        candidates = [
            b for b in win.descendants(control_type="Button")
            if (b.element_info.name or "").strip() in ("정리 진행", "정리하기")
        ]
        if candidates:
            # 모달이 열린 상태에서는 모달 내부 버튼(마지막 요소)을 우선 선택
            btn = candidates[-1]
            try:
                btn.invoke()
            except Exception:
                self._click_element(btn, target_h)
            time.sleep(0.3)
            return
        raise RuntimeError("'정리 확인' 모달에서 '정리 진행'/'정리하기' 버튼을 찾을 수 없습니다.")

    @staticmethod
    def _is_complete_modal_visible(win) -> bool:
        """정리 완료/결과 모달 노출 여부 판별 (구버전 '정리가 완료되었습니다!' + 신버전 '내 PC 정리' 결과 모달 모두 지원)"""
        texts = [(t.element_info.name or "").strip() for t in win.descendants(control_type="Text") if t.element_info.name]
        buttons = list(win.descendants(control_type="Button"))
        has_ok_btn = any((b.element_info.name or "").strip() == "확인" for b in buttons)
        if not has_ok_btn:
            return False
        if "정리가 완료되었습니다!" in texts:
            return True
        if any("처리 완료" in t for t in texts):
            return True
        if "내 PC 정리" in texts and any("close-button" in (b.element_info.class_name or "") for b in buttons):
            return True
        return False

    def wait_for_complete_modal(self, timeout: float = 15.0) -> None:
        """정리 완료/결과 모달('정리가 완료되었습니다!' 또는 '내 PC 정리' 결과 모달) 노출 대기"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win = self._connect_window()
            if self._is_complete_modal_visible(win):
                return
            time.sleep(0.25)
        raise TimeoutError("정리 완료 모달('정리가 완료되었습니다!' / '내 PC 정리')이 표시되지 않았습니다.")

    def close_complete_modal(self, timeout: float = 5.0) -> None:
        """완료 모달에서 '확인' 버튼 클릭 및 모달 닫힘 대기"""
        deadline = time.time() + timeout
        clicked = False
        while time.time() < deadline:
            target_h, win = self._connect_window()
            if not clicked:
                for b in win.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() == "확인":
                        try:
                            b.invoke()
                        except Exception:
                            self._click_element(b, target_h)
                        clicked = True
                        break
            else:
                if not self._is_complete_modal_visible(win):
                    return
            time.sleep(0.15)
        if not clicked:
            raise TimeoutError("완료 모달에서 '확인' 버튼을 찾을 수 없습니다.")
        raise TimeoutError("완료 모달이 '확인' 클릭 후 닫히지 않았습니다.")

    def run_clean_for_items(self, item_names: List[str], timeout: float = 15.0) -> None:
        """지정한 항목들만 체크한 뒤 '정리하기' -> '정리 진행' -> 완료 '확인'까지 일괄 실행"""
        self.uncheck_all()
        for name in item_names:
            self.set_checkbox(name, True)
        self.click_clean_button()
        self.confirm_clean(timeout=5.0)
        self.wait_for_complete_modal(timeout=timeout)
        self.close_complete_modal(timeout=5.0)

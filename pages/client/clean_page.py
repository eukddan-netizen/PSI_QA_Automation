"""
보안점검 프로그램 'PC정리' 탭 페이지 Object
- 상단 시스템 정보 카드: OS VERSION, ANTIVIRUS(새로고침 포함), FIREWALL(새로고침 포함)
- 하단 '내 PC 정리': 트리 체크박스 선택/해제, '정리하기' -> 확인 모달('정리 진행') -> 완료 모달('확인')
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

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

    RESULT_STATUSES = (
        "완료",
        "정리할 데이터 없음",
        "부분 완료",
        "실패",
        "진행하지 않음",
    )

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

    def get_clean_notice_items(self) -> List[str]:
        """하단 '내 PC 정리' 영역의 안내 문구 목록 반환"""
        _, win = self._connect_window()
        notices: List[Tuple[int, str]] = []
        for item in win.descendants(control_type="ListItem"):
            raw = (item.element_info.name or "").strip()
            if not raw.startswith("·"):
                continue
            rect = item.rectangle()
            if rect.top >= 410:
                cleaned = raw.lstrip("·").strip()
                if cleaned:
                    notices.append((rect.top, cleaned))
        notices.sort(key=lambda x: x[0])
        return [text for _, text in notices]

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

    def get_confirm_modal_info(self) -> Dict[str, Any]:
        """
        열려 있는 '정리 확인' 모달의 텍스트, 선택 항목, 브라우저별 프로필 목록,
        '정리하기' 버튼 활성화 여부, 실행 중 브라우저 종료 경고 여부를 반환합니다.
        """
        _, win = self._connect_window()
        texts = [
            (t.element_info.name or "").strip()
            for t in win.descendants(control_type="Text")
            if t.element_info.name
        ]
        selected_items = [
            (li.element_info.name or "").strip()
            for li in win.descendants(control_type="ListItem")
            if (li.element_info.name or "").strip()
        ]

        profiles: Dict[str, List[Dict[str, Any]]] = {}
        browser_all_states: Dict[str, int] = {}
        for grp in win.descendants(control_type="Group"):
            if "profile-group" not in (grp.element_info.class_name or ""):
                continue
            browser_name = (grp.element_info.name or "").strip()
            if not browser_name:
                continue
            prof_list: List[Dict[str, Any]] = []
            for cb in grp.descendants(control_type="CheckBox"):
                cb_name = (cb.element_info.name or "").strip()
                state = int(cb.get_toggle_state())
                if "프로필 전체 선택" in cb_name:
                    browser_all_states[browser_name] = state
                    continue
                m = re.search(r"\(([^()]+)\)\s*$", cb_name)
                folder = m.group(1).strip() if m else cb_name
                prof_list.append({
                    "label": cb_name,
                    "folder": folder,
                    "checked": state,
                })
            profiles[browser_name] = prof_list

        confirm_enabled = False
        confirm_btns = [
            b for b in win.descendants(control_type="Button")
            if (b.element_info.name or "").strip() in ("정리 진행", "정리하기")
        ]
        if confirm_btns:
            try:
                confirm_enabled = bool(confirm_btns[-1].is_enabled())
            except Exception:
                confirm_enabled = True

        running_warnings = [
            t for t in texts
            if "백그라운드 프로세스를 종료합니다" in t or "모든 창과 백그라운드 프로세스를 종료" in t
        ]

        return {
            "texts": texts,
            "selected_items": selected_items,
            "profiles": profiles,
            "browser_all_states": browser_all_states,
            "confirm_enabled": confirm_enabled,
            "running_browser_warnings": running_warnings,
            "has_running_browser_warning": bool(running_warnings),
        }

    def select_profiles_in_confirm_modal(
        self,
        targets: Dict[str, List[str]],
        timeout: float = 4.0,
    ) -> None:
        """
        '정리 확인' 모달에서 브라우저별 지정 프로필 폴더들을 선택합니다.
        예: targets={"Chrome": ["Profile 99"], "Edge": ["Profile 99"]}
        """
        self.wait_for_confirm_modal(timeout=timeout)
        for browser_name, folders in targets.items():
            for folder in folders:
                target_h, win = self._connect_window()
                found = False
                for grp in win.descendants(control_type="Group"):
                    if "profile-group" not in (grp.element_info.class_name or ""):
                        continue
                    if (grp.element_info.name or "").strip() != browser_name:
                        continue
                    for cb in grp.descendants(control_type="CheckBox"):
                        cb_name = (cb.element_info.name or "").strip()
                        if "프로필 전체 선택" in cb_name:
                            continue
                        if cb_name.endswith(f"({folder})"):
                            found = True
                            if int(cb.get_toggle_state()) != 1:
                                self._click_element(cb, target_h)
                                deadline = time.time() + timeout
                                while time.time() < deadline:
                                    info = self.get_confirm_modal_info()
                                    matched = [
                                        p for p in info["profiles"].get(browser_name, [])
                                        if p["folder"] == folder
                                    ]
                                    if matched and matched[0]["checked"] == 1:
                                        break
                                    time.sleep(0.15)
                            break
                    if found:
                        break
                if not found:
                    raise RuntimeError(
                        f"'정리 확인' 모달에서 {browser_name} 프로필 '({folder})' 체크박스를 찾을 수 없습니다."
                    )

    def cancel_confirm_modal(self, timeout: float = 5.0) -> None:
        """'정리 확인' 모달에서 '취소' 버튼 클릭 및 닫힘 대기"""
        deadline = time.time() + timeout
        clicked = False
        while time.time() < deadline:
            target_h, win = self._connect_window()
            if not clicked:
                for b in win.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() == "취소":
                        try:
                            b.invoke()
                        except Exception:
                            self._click_element(b, target_h)
                        clicked = True
                        break
            else:
                texts = {(t.element_info.name or "").strip() for t in win.descendants(control_type="Text")}
                if "정리 확인" not in texts:
                    return
            time.sleep(0.15)
        raise TimeoutError("'정리 확인' 모달이 '취소' 클릭 후 닫히지 않았습니다.")

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
            if not btn.is_enabled():
                raise RuntimeError("'정리 확인' 모달의 '정리하기' 버튼이 비활성화 상태입니다. (프로필 미선택 등)")
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

    def get_complete_modal_result(self) -> Dict[str, Any]:
        """
        현재 표시된 정리 완료/결과 모달의 텍스트, 처리 완료/미완료 건수,
        프로필/대상별 상태('완료', '정리할 데이터 없음', '부분 완료', '실패', '진행하지 않음')를 파싱해 반환합니다.
        """
        _, win = self._connect_window()
        texts = [
            (t.element_info.name or "").strip()
            for t in win.descendants(control_type="Text")
            if t.element_info.name
        ]
        summary_text = next((t for t in texts if "처리 완료" in t), "")
        completed_count = None
        incomplete_count = None
        m = re.search(r"처리\s*완료\s*(\d+)\s*개.*?미완료\s*(\d+)\s*개", summary_text)
        if m:
            completed_count = int(m.group(1))
            incomplete_count = int(m.group(2))

        profile_results: Dict[str, str] = {}
        for idx, txt in enumerate(texts):
            if txt in self.RESULT_STATUSES and idx > 0:
                target_label = texts[idx - 1]
                if target_label and target_label not in self.RESULT_STATUSES:
                    profile_results[target_label] = txt

        return {
            "texts": texts,
            "summary_text": summary_text,
            "completed_count": completed_count,
            "incomplete_count": incomplete_count,
            "profile_results": profile_results,
        }

    def wait_for_complete_modal(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        정리 진행 상태를 거쳐 최종 완료/결과 모달이 표시될 때까지 대기하고,
        관찰된 진행 문구(progress_texts)와 최종 결과(result)를 반환합니다.
        """
        deadline = time.time() + timeout
        progress_texts: List[str] = []
        while time.time() < deadline:
            _, win = self._connect_window()
            if self._is_complete_modal_visible(win):
                res = self.get_complete_modal_result()
                res["progress_texts"] = progress_texts
                return res
            cur_texts = [
                (t.element_info.name or "").strip()
                for t in win.descendants(control_type="Text")
                if t.element_info.name
            ]
            for ct in cur_texts:
                if any(k in ct for k in ("경과 시간", "개 항목 처리", "종료를 기다리고 있습니다")) and ct not in progress_texts:
                    progress_texts.append(ct)
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

    def run_clean_for_items(
        self,
        item_names: List[str],
        browser_profiles: Optional[Dict[str, List[str]]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        지정한 항목들만 체크한 뒤 '정리하기' -> (브라우저 프로필 선택) -> 확인 -> 완료 모달 파싱 -> '확인' 닫기까지 일괄 실행.
        """
        self.uncheck_all()
        for name in item_names:
            self.set_checkbox(name, True)
        self.click_clean_button()
        self.wait_for_confirm_modal(timeout=5.0)
        if browser_profiles:
            self.select_profiles_in_confirm_modal(browser_profiles, timeout=5.0)
        self.confirm_clean(timeout=5.0)
        result = self.wait_for_complete_modal(timeout=timeout)
        self.close_complete_modal(timeout=5.0)
        return result

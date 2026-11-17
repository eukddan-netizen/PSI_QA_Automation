"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) 공통 Playwright Base Page Object
"""

import re
import time
from typing import List, Optional, Tuple
from playwright.sync_api import Locator, Page

from core.desktop_utils import bring_chrome_to_front, dismiss_chrome_bubbles


class AdminBasePage:
    """PSI 웹 관리자 콘솔 공통 로그인, URL 및 IP 기반 사용자 검색 관리"""

    BASE_URL = "https://192.168.4.151"
    LOGIN_URL = f"{BASE_URL}/"
    _LOADING_KEYWORDS = ("서버의 응답을 기다리는 중입니다", "기다리는 중입니다", "로딩 중")

    def __init__(self, page: Page):
        self.page = page

    def dismiss_browser_popups(self, timeout: float = 1.2) -> int:
        """
        크롬 우측 상단에 노출될 수 있는 '비밀번호 저장' / '페이지 복구' 브라우저 버블을
        UIA로 감지하여('사용 안 함'/'취소'/'닫기') 화면을 가리지 않도록 자동으로 닫습니다.
        """
        try:
            return dismiss_chrome_bubbles(timeout=timeout)
        except Exception:
            return 0

    def _is_loading_text(self, text: str) -> bool:
        return any(kw in (text or "") for kw in self._LOADING_KEYWORDS)

    def _describe_visible_overlays(self) -> List[str]:
        """디버깅용: 현재 화면에 표시된 div.fixed / dialog 요소 요약 반환"""
        overlays = self.page.locator("div.fixed, div[role='dialog']")
        desc: List[str] = []
        try:
            for i in range(overlays.count()):
                ov = overlays.nth(i)
                if not ov.is_visible():
                    continue
                txt = ov.inner_text().strip().replace("\n", " | ")
                btns = [b.inner_text().strip() for b in ov.locator("button").all()]
                desc.append(f"[{i}] text={txt!r}, buttons={btns}")
        except Exception:
            pass
        return desc

    def wait_for_loading_clear(self, timeout: float = 12.0) -> None:
        """관리자 웹의 로딩 오버레이('서버의 응답을 기다리는 중입니다.' 등)가 사라질 때까지 대기"""
        deadline = time.time() + timeout
        overlays = self.page.locator("div.fixed, div[role='dialog']")
        while time.time() < deadline:
            loading_visible = False
            try:
                count = overlays.count()
                for i in range(count):
                    ov = overlays.nth(i)
                    if not ov.is_visible():
                        continue
                    txt = ov.inner_text().strip()
                    if self._is_loading_text(txt) and ov.locator("button").count() == 0:
                        loading_visible = True
                        break
            except Exception:
                pass
            if not loading_visible:
                return
            self.page.wait_for_timeout(150)
        raise TimeoutError(
            f"로딩 오버레이가 {timeout}초 내에 사라지지 않았습니다. "
            f"(현재 오버레이: {self._describe_visible_overlays()})"
        )

    def _find_visible_modal_and_button(self, button_text: str) -> Optional[Tuple[Locator, Locator, str]]:
        """지정된 버튼이 실제로 표시되어 있고 로딩 문구가 아닌 활성 모달을 탐색합니다."""
        overlays = self.page.locator("div.fixed, div[role='dialog']")
        count = overlays.count()
        # 중첩 모달이 있을 수 있으므로 뒤쪽(최상단) 요소부터 확인
        for i in range(count - 1, -1, -1):
            modal = overlays.nth(i)
            try:
                if not modal.is_visible():
                    continue
                modal_text = modal.inner_text().strip()
                if not modal_text or self._is_loading_text(modal_text):
                    continue
                btn = modal.locator(f"button:text-is('{button_text}')").first
                if btn.count() == 0:
                    btn = modal.locator(f"button:has-text('{button_text}')").first
                if btn.count() > 0 and btn.is_visible() and btn.is_enabled():
                    return modal, btn, modal_text
            except Exception:
                continue
        return None

    def _click_modal_button(self, button_text: str, timeout: float = 10.0) -> str:
        """
        로딩 오버레이('서버의 응답을 기다리는 중입니다.' 등)를 건너뛰고
        실제 버튼이 표시된 확인/선택 모달이 뜰 때까지 대기한 뒤 버튼을 클릭하고,
        해당 모달/버튼이 닫히고 후속 로딩이 끝날 때까지 대기한 후 모달 본문 텍스트를 반환합니다.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = self._find_visible_modal_and_button(button_text)
            if found is None:
                self.page.wait_for_timeout(150)
                continue

            modal, btn, modal_text = found
            try:
                latest_text = modal.inner_text().strip()
                if not latest_text or self._is_loading_text(latest_text):
                    self.page.wait_for_timeout(150)
                    continue
                modal_text = latest_text
                btn.click(timeout=2000)
            except Exception:
                # 클릭 직전 모달 DOM이 교체(로딩 전환 등)된 경우 루프 재탐색
                self.page.wait_for_timeout(150)
                continue

            # 클릭한 버튼/모달이 사라질 때까지 대기 (같은 컨테이너가 다음 모달로 재사용되는 경우도 텍스트 변화로 감지)
            close_deadline = time.time() + timeout
            while time.time() < close_deadline:
                try:
                    if not btn.is_visible():
                        break
                    cur_text = modal.inner_text().strip()
                    if cur_text != modal_text:
                        break
                except Exception:
                    break
                self.page.wait_for_timeout(120)

            self.wait_for_loading_clear(timeout=timeout)
            return modal_text

        raise TimeoutError(
            f"'{button_text}' 버튼이 포함된 모달이 {timeout}초 내에 처리되지 않았습니다. "
            f"(현재 오버레이: {self._describe_visible_overlays()})"
        )

    def login(self, username: str = "admin", password: str = "Qwe123!@#") -> None:
        """관리자 페이지 접속 및 로그인 (브라우저 복구/암호저장 팝업 자동 정리 포함)"""
        self.bring_to_front()
        print(f"\n>>> [관리자 웹] {self.LOGIN_URL} 접속 중...")
        self.page.goto(self.LOGIN_URL, timeout=15000)

        id_input = self.page.locator("input[type='text']").first
        pw_input = self.page.locator("input[type='password']").first
        id_input.wait_for(state="visible", timeout=10000)
        pw_input.wait_for(state="visible", timeout=10000)
        self.dismiss_browser_popups(timeout=0.6)

        print(f">>> [관리자 웹] 아이디({username}) 및 비밀번호 입력 중...")
        id_input.fill(username)
        pw_input.fill(password)
        print(">>> [관리자 웹] [로그인] 버튼 클릭...")
        self.page.locator("button:has-text('로그인')").first.click()

        # 로그인 완료(비밀번호 입력창 사라짐) 및 로딩 종료까지 대기
        pw_input.wait_for(state="hidden", timeout=15000)
        self.wait_for_loading_clear(timeout=10.0)
        self.dismiss_browser_popups(timeout=1.5)

    def bring_to_front(self) -> None:
        """관리자 웹 브라우저 창 및 탭을 최상단으로 활성화 (사용자 개인 브라우저는 건드리지 않음)"""
        title_hint = ""
        try:
            title_hint = self.page.title() or ""
        except Exception:
            pass
        bring_chrome_to_front(title_hint=title_hint)
        try:
            self.page.bring_to_front()
        except Exception:
            pass

    def find_user_row_by_ip(self, ip: str, table_header_text: str = "접속/단말 IP") -> Optional[Locator]:
        """사용자 테이블에서 정확한 IP 토큰을 포함하는 행 반환"""
        table = self.page.locator("table", has_text=table_header_text).first
        rows = table.locator("tbody tr")
        ip_pattern = re.compile(rf"(?<![0-9.]){re.escape(ip)}(?![0-9.])")

        for i in range(rows.count()):
            row = rows.nth(i)
            if row.locator("td").count() < 5:
                continue
            if ip_pattern.search(row.inner_text()):
                return row
        return None

    def search_user_by_ip(
        self,
        ip_candidates: List[str],
        table_header_text: str = "접속/단말 IP",
    ) -> Tuple[str, Locator]:
        """
        후보 IP 목록을 순차 검색하여 사용자 테이블에서 현재 PC 행을 찾습니다.
        반환값: (매칭된 IP 문자열, 해당 테이블 행 Locator)
        """
        if not ip_candidates:
            raise ValueError("검색할 로컬 IPv4 주소 후보가 없습니다.")

        self.bring_to_front()
        search_input = self.page.locator("input[placeholder='검색어 입력']")
        search_btn = self.page.locator("button:text-is('검색')").first

        table = self.page.locator("table", has_text=table_header_text).first
        for ip in ip_candidates:
            print(f">>> [관리자 웹] 사용자 IP 검색 시도: {ip}")
            try:
                prev_tbody = table.locator("tbody").inner_text().strip()
            except Exception:
                prev_tbody = ""

            search_input.fill(ip)
            search_btn.click()
            self.page.wait_for_timeout(200)
            self.wait_for_loading_clear(timeout=8.0)

            deadline = time.time() + 3.5
            while time.time() < deadline:
                row = self.find_user_row_by_ip(ip, table_header_text=table_header_text)
                if row is not None:
                    print(f">>> [관리자 웹] 사용자 행 탐색 성공 (IP: {ip})")
                    return ip, row

                try:
                    cur_tbody = table.locator("tbody").inner_text().strip()
                except Exception:
                    cur_tbody = ""
                if cur_tbody != prev_tbody and ("없습니다" in cur_tbody or table.locator("tbody tr").count() == 0):
                    break
                if not cur_tbody and time.time() + 2.5 < deadline:
                    pass
                elif "없습니다" in cur_tbody and time.time() > deadline - 2.3:
                    break
                self.page.wait_for_timeout(150)

        raise AssertionError(
            f"관리자 웹({self.page.url})에서 현재 PC IP({ip_candidates})에 해당하는 사용자를 찾을 수 없습니다."
        )


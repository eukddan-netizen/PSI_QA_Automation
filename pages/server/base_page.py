"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) 공통 Playwright Base Page Object
"""

import re
import time
from typing import List, Optional, Tuple
from playwright.sync_api import Locator, Page

from core.desktop_utils import dismiss_chrome_bubbles


class AdminBasePage:
    """PSI 웹 관리자 콘솔 공통 로그인, URL 및 IP 기반 사용자 검색 관리"""

    BASE_URL = "https://192.168.4.151"
    LOGIN_URL = f"{BASE_URL}/"

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

    def login(self, username: str = "admin", password: str = "Qwe123!@#") -> None:
        """관리자 페이지 접속 및 로그인 (브라우저 복구/암호저장 팝업 자동 정리 포함)"""
        print(f"\n>>> [관리자 웹] {self.LOGIN_URL} 접속 중...")
        self.page.goto(self.LOGIN_URL, timeout=15000)
        time.sleep(1.5)
        self.dismiss_browser_popups(timeout=0.6)

        print(f">>> [관리자 웹] 아이디({username}) 및 비밀번호 입력 중...")
        self.page.locator("input[type='text']").fill(username)
        time.sleep(0.5)
        self.page.locator("input[type='password']").fill(password)
        time.sleep(1.0)
        print(">>> [관리자 웹] [로그인] 버튼 클릭...")
        self.page.locator("button:has-text('로그인')").click()
        self.page.wait_for_timeout(1800)
        self.dismiss_browser_popups(timeout=1.5)

    def bring_to_front(self) -> None:
        """관리자 웹 브라우저 탭 활성화 (사용자 개인 브라우저는 일절 건드리지 않음)"""
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

        search_input = self.page.locator("input[placeholder='검색어 입력']")
        search_btn = self.page.locator("button:text-is('검색')").first

        for ip in ip_candidates:
            print(f">>> [관리자 웹] 사용자 IP 검색 시도: {ip}")
            search_input.fill(ip)
            search_btn.click()
            self.page.wait_for_timeout(1500)

            row = self.find_user_row_by_ip(ip, table_header_text=table_header_text)
            if row is not None:
                print(f">>> [관리자 웹] 사용자 행 탐색 성공 (IP: {ip})")
                return ip, row

        raise AssertionError(
            f"관리자 웹({self.page.url})에서 현재 PC IP({ip_candidates})에 해당하는 사용자를 찾을 수 없습니다."
        )


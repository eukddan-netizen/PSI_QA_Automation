"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) 공통 Playwright Base Page Object
"""

import time
from playwright.sync_api import Page


class AdminBasePage:
    """PSI 웹 관리자 콘솔 공통 로그인 및 기본 URL 관리"""

    BASE_URL = "https://192.168.4.151"
    LOGIN_URL = f"{BASE_URL}/"

    def __init__(self, page: Page):
        self.page = page

    def login(self, username: str = "admin", password: str = "Qwe123!@#") -> None:
        """관리자 페이지 접속 및 로그인"""
        print(f"\n>>> [관리자 웹] {self.LOGIN_URL} 접속 중...")
        self.page.goto(self.LOGIN_URL, timeout=15000)
        time.sleep(1.5)
        print(f">>> [관리자 웹] 아이디({username}) 및 비밀번호 입력 중...")
        self.page.locator("input[type='text']").fill(username)
        time.sleep(0.5)
        self.page.locator("input[type='password']").fill(password)
        time.sleep(1.0)
        print(">>> [관리자 웹] [로그인] 버튼 클릭...")
        self.page.locator("button:has-text('로그인')").click()
        self.page.wait_for_timeout(2500)


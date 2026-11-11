"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) Playwright 제어 Page Object
- 관리자 로그인
- /pcsafe 페이지 이동
- 부서 트리 탐색 및 사용자별 정책 제어 (인사 UI 출력 등)
"""

import time
from typing import Optional
from playwright.sync_api import Page, Browser, sync_playwright


class AdminPcsafePage:
    BASE_URL = "https://192.168.4.151"
    LOGIN_URL = f"{BASE_URL}/"
    PCDAFE_URL = f"{BASE_URL}/pcsafe"

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

    def goto_pcsafe(self) -> None:
        """PC보안점검 관리(/pcsafe) 페이지로 이동"""
        if "/pcsafe" not in self.page.url:
            print(">>> [관리자 웹] /pcsafe 메뉴로 이동 중...")
            self.page.goto(self.PCDAFE_URL, timeout=15000)
            self.page.wait_for_timeout(2500)

    def select_department(self, dept_name: str = "t1") -> None:
        """좌측 부서트리에서 부서 클릭"""
        print(f">>> [관리자 웹] 좌측 부서트리에서 '{dept_name}' 부서 선택...")
        dept_locator = self.page.locator(f"text='{dept_name}'").first
        dept_locator.wait_for(state="visible", timeout=10000)
        dept_locator.click()
        self.page.wait_for_timeout(2000)

    def _get_user_row(self, username: str):
        """특정 사용자의 테이블 행(tr) 탐색"""
        user_cell = self.page.locator("text='" + username + "'")
        user_cell.wait_for(state="visible", timeout=10000)
        return self.page.locator("tr", has=user_cell).first

    def get_hr_ui_status(self, username: str = "KYC") -> str:
        """
        사용자의 '인사 UI 출력' 상태 반환 ('ON' 또는 'OFF')
        테이블 컬럼 순서상 7번째 TD가 '인사 UI 출력'
        """
        row = self._get_user_row(username)
        hr_ui_td = row.locator("td").nth(7)
        return hr_ui_td.inner_text().strip()

    def set_hr_ui_status(self, username: str = "KYC", target_state: str = "ON") -> str:
        """
        사용자의 '인사 UI 출력' 상태를 target_state('ON' 또는 'OFF')로 변경.
        확인 모달 및 완료 모달까지 자동 처리.
        """
        target_state = target_state.upper()
        if target_state not in ("ON", "OFF"):
            raise ValueError(f"올바르지 않은 상태 값: {target_state} (ON 또는 OFF여야 함)")

        current_state = self.get_hr_ui_status(username)
        print(f">>> [관리자 웹] '{username}' 사용자의 현재 인사 UI 출력 상태: {current_state} (목표: {target_state})")
        if current_state == target_state:
            return current_state

        row = self._get_user_row(username)
        hr_ui_td = row.locator("td").nth(7)
        slider = hr_ui_td.locator("span.slider")
        print(f">>> [관리자 웹] '{username}'의 인사 UI 출력 스위치 클릭...")
        slider.click()
        time.sleep(1.5)

        # 1차 모달: "인사 UI 출력 정책을 적용하시겠습니까?" -> '예'
        modal1 = self.page.locator("div.fixed.z-50")
        modal1.wait_for(state="visible", timeout=5000)
        print(">>> [관리자 웹] 정책 적용 확인 팝업에서 [예] 클릭...")
        time.sleep(1.0)
        modal1.locator("button:has-text('예')").click()
        time.sleep(1.5)

        # 2차 모달: "정상 처리되었습니다." -> '확인'
        modal2 = self.page.locator("div.fixed.z-50")
        if modal2.is_visible():
            confirm_btn = modal2.locator("button:has-text('확인')")
            if confirm_btn.is_visible():
                print(">>> [관리자 웹] 처리 완료 팝업에서 [확인] 클릭...")
                time.sleep(1.0)
                confirm_btn.click()
                time.sleep(1.5)

        new_state = self.get_hr_ui_status(username)
        print(f">>> [관리자 웹] 최종 변경된 상태: {new_state}")
        return new_state


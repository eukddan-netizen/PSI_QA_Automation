"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) Playwright 제어 Page Object
- 관리자 로그인
- /pcsafe 페이지 이동
- 현재 PC IP(ipconfig) 기반 사용자 검색 및 정책 제어 (인사 UI 출력 등)
"""

import time
from typing import List, Optional, Tuple
from playwright.sync_api import Locator, Page

from common.os_utils import get_current_machine_ips
from pages.admin_base_page import AdminBasePage


class AdminPcsafePage(AdminBasePage):
    PCDAFE_URL = f"{AdminBasePage.BASE_URL}/pcsafe"

    def __init__(self, page: Page):
        super().__init__(page)
        self.target_ip: Optional[str] = None

    def goto_pcsafe(self) -> None:
        """PC보안점검 관리(/pcsafe) 페이지로 이동"""
        if "/pcsafe" not in self.page.url:
            print(">>> [관리자 웹] /pcsafe 메뉴로 이동 중...")
            self.page.goto(self.PCDAFE_URL, timeout=15000)
        self.page.locator("input[placeholder='검색어 입력']").wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(1000)

    def select_department(self, dept_name: str = "t1") -> None:
        """좌측 부서트리에서 부서 클릭"""
        print(f">>> [관리자 웹] 좌측 부서트리에서 '{dept_name}' 부서 선택...")
        dept_locator = self.page.locator(f"text='{dept_name}'").first
        dept_locator.wait_for(state="visible", timeout=10000)
        dept_locator.click()
        self.page.wait_for_timeout(2000)

    def search_current_user_by_ip(self, ip_candidates: Optional[List[str]] = None) -> str:
        """현재 PC의 ipconfig/라우팅 IP 후보로 /pcsafe 사용자를 검색하고 매칭된 IP를 저장"""
        candidates = ip_candidates or get_current_machine_ips()
        print(f">>> [관리자 웹] /pcsafe 현재 PC IP 후보: {candidates}")
        matched_ip, _ = self.search_user_by_ip(candidates)
        self.target_ip = matched_ip
        return matched_ip

    def _get_hr_ui_col_index(self) -> int:
        """사용자 테이블 헤더에서 '인사 UI 출력' 컬럼 인덱스 조회 (기본값 7)"""
        table = self.page.locator("table", has_text="접속/단말 IP").first
        headers = table.locator("thead th, thead td")
        for idx in range(headers.count()):
            if "인사 UI 출력" in headers.nth(idx).inner_text():
                return idx
        return 7

    def _get_user_row(
        self,
        user_ip: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Tuple[str, Locator]:
        """IP 검색(기본) 또는 사용자명 기반으로 /pcsafe 사용자 테이블 행(tr) 반환"""
        if username and not user_ip:
            user_cell = self.page.locator(f"text='{username}'")
            user_cell.wait_for(state="visible", timeout=10000)
            return username, self.page.locator("tr", has=user_cell).first

        target_ip = user_ip or self.target_ip or self.search_current_user_by_ip()
        row = self.find_user_row_by_ip(target_ip)
        if row is None:
            _, row = self.search_user_by_ip([target_ip])
        self.target_ip = target_ip
        return target_ip, row

    def get_hr_ui_status(self, username: Optional[str] = None, user_ip: Optional[str] = None) -> str:
        """
        사용자의 '인사 UI 출력' 상태 반환 ('ON' 또는 'OFF')
        """
        _, row = self._get_user_row(user_ip=user_ip, username=username)
        hr_ui_td = row.locator("td").nth(self._get_hr_ui_col_index())
        return hr_ui_td.inner_text().strip()

    def set_hr_ui_status(
        self,
        username: Optional[str] = None,
        target_state: str = "ON",
        user_ip: Optional[str] = None,
    ) -> str:
        """
        현재 PC IP(또는 지정된 사용자)의 '인사 UI 출력' 상태를 target_state('ON' 또는 'OFF')로 변경.
        확인 모달 및 완료 모달까지 자동 처리.
        """
        target_state = target_state.upper()
        if target_state not in ("ON", "OFF"):
            raise ValueError(f"올바르지 않은 상태 값: {target_state} (ON 또는 OFF여야 함)")

        target_label, row = self._get_user_row(user_ip=user_ip, username=username)
        col_idx = self._get_hr_ui_col_index()
        current_state = row.locator("td").nth(col_idx).inner_text().strip()
        print(f">>> [관리자 웹] '{target_label}' 사용자의 현재 인사 UI 출력 상태: {current_state} (목표: {target_state})")
        if current_state == target_state:
            return current_state

        hr_ui_td = row.locator("td").nth(col_idx)
        slider = hr_ui_td.locator("span.slider")
        print(f">>> [관리자 웹] '{target_label}'의 인사 UI 출력 스위치 클릭...")
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

        new_state = self.get_hr_ui_status(username=username, user_ip=user_ip)
        print(f">>> [관리자 웹] 최종 변경된 상태: {new_state}")
        return new_state


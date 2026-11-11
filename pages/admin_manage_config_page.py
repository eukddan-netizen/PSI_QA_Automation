"""
PSI 관리자 웹 콘솔 환경설정 (/manageConfig) Playwright Page Object
- /manageConfig 접속
- 5개 탭(에이전트, 보안점검, 패치, 다운로드, 배포서버) 전환 제어
- 보안점검 탭 내 하단 '문의처' 입력 및 조회
- 하단 '저장' 버튼 클릭 및 완료 모달 확인
"""

import time
from typing import Optional
from playwright.sync_api import Locator, Page

from pages.admin_base_page import AdminBasePage


class AdminManageConfigPage(AdminBasePage):
    """PSI 웹 관리자 콘솔 /manageConfig 환경설정 Page Object"""

    MANAGE_CONFIG_URL = f"{AdminBasePage.BASE_URL}/manageConfig"

    # 탭 이름 매핑
    TAB_VALUES = {
        "에이전트": "agent",
        "보안점검": "pcsafe",
        "패치": "patch",
        "다운로드": "download",
        "배포서버": "distribute",
    }

    def __init__(self, page: Page):
        super().__init__(page)

    def goto_manage_config(self) -> None:
        """환경설정(/manageConfig) 페이지로 이동"""
        if "/manageConfig" not in self.page.url:
            print(f"\n>>> [관리자 웹] {self.MANAGE_CONFIG_URL} 이동 중...")
            self.page.goto(self.MANAGE_CONFIG_URL, timeout=15000)
        # 탭 바 로딩 대기
        self.page.locator("button[data-value='agent']").wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(800)

    def select_tab(self, tab_name: str = "보안점검") -> None:
        """
        상단 5개 탭 중 하나 선택 ('에이전트', '보안점검', '패치', '다운로드', '배포서버')
        """
        tab_value = self.TAB_VALUES.get(tab_name, tab_name)
        print(f">>> [관리자 웹] 환경설정 '{tab_name}'(value={tab_value}) 탭 선택...")

        btn = self.page.locator(f"button[data-value='{tab_value}']").first
        btn.wait_for(state="visible", timeout=10000)
        btn.click()
        self.page.wait_for_timeout(1000)

        # 탭 활성화 확인 (data-state="active")
        active_tab = self.page.locator(f"button[data-value='{tab_value}'][data-state='active']")
        if active_tab.count() == 0:
            # 1회 재클릭
            btn.click()
            self.page.wait_for_timeout(1000)

    def _get_contact_row(self) -> Locator:
        """보안점검 탭 내 '문의처' 행(tr) Locator 반환"""
        row = self.page.locator("tr", has_text="문의처").first
        row.wait_for(state="visible", timeout=10000)
        return row

    def get_contact_text(self) -> str:
        """'문의처' 행의 현재 input 텍스트 값 반환"""
        row = self._get_contact_row()
        inp = row.locator("input[type='text']").first
        inp.wait_for(state="visible", timeout=5000)
        return inp.input_value().strip()

    def set_contact_text(self, text: str) -> None:
        """'문의처' 행의 input 텍스트 변경"""
        row = self._get_contact_row()
        inp = row.locator("input[type='text']").first
        inp.scroll_into_view_if_needed()
        inp.wait_for(state="visible", timeout=5000)
        inp.fill(text)
        self.page.wait_for_timeout(300)
        actual = inp.input_value().strip()
        assert actual == text, f"문의처 입력값 불일치: 기대={text!r}, 실제={actual!r}"
        print(f">>> [관리자 웹] 문의처 입력값 변경 -> '{text}'")

    def _click_modal_button(self, button_text: str = "확인", timeout: float = 6.0) -> str:
        """저장 확인 모달(div.fixed 또는 role='dialog') 내 지정 버튼 클릭"""
        # 다이얼로그나 모달 컨테이너 탐색
        modal = self.page.locator("div.fixed, div[role='dialog']").filter(has_text=button_text).first
        modal.wait_for(state="visible", timeout=int(timeout * 1000))
        modal_text = modal.inner_text().strip()

        btn = modal.locator(f"button:has-text('{button_text}')").first
        btn.click()
        self.page.wait_for_timeout(800)
        return modal_text

    def save_config(self) -> None:
        """가장 하단의 '저장' 버튼 클릭 및 완료 모달('정상 처리되었습니다.') 확인"""
        print(">>> [관리자 웹] 하단 [저장] 버튼 클릭...")
        save_btn = self.page.locator("button[type='submit']:has-text('저장')").first
        save_btn.scroll_into_view_if_needed()
        save_btn.click()

        # 완료 모달 확인
        modal_text = self._click_modal_button("확인", timeout=8.0)
        assert "정상" in modal_text or "완료" in modal_text or "처리" in modal_text, (
            f"환경설정 저장 후 예상치 못한 모달 응답: {modal_text!r}"
        )
        print(">>> [관리자 웹] 환경설정 저장 및 확인 모달 처리 완료!")
        self.page.wait_for_timeout(1000)


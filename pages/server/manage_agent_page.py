"""
PSI 관리자 웹 콘솔 에이전트 관리 (/manageAgent) Playwright Page Object
- /manageAgent 접속
- '최근 등록 정보' 행에서 모듈명 및 버전 정보 파싱 (예: taKeeper.exe (5.1.70.3))
"""

import re
from typing import Dict
from playwright.sync_api import Locator, Page

from pages.server.base_page import AdminBasePage


class AdminManageAgentPage(AdminBasePage):
    """PSI 웹 관리자 콘솔 /manageAgent 에이전트/모듈 관리 Page Object"""

    MANAGE_AGENT_URL = f"{AdminBasePage.BASE_URL}/manageAgent"
    _MODULE_VERSION_RE = re.compile(r"([A-Za-z0-9_.-]+\.exe)\s*\(([^)]+)\)")

    def __init__(self, page: Page):
        super().__init__(page)

    def goto_manage_agent(self) -> None:
        """에이전트 관리(/manageAgent) 페이지로 이동 및 테이블 렌더링 대기"""
        self.bring_to_front()
        if "/manageAgent" not in self.page.url:
            print(f"\n>>> [관리자 웹] {self.MANAGE_AGENT_URL} 이동 중...")
            self.page.goto(self.MANAGE_AGENT_URL, timeout=15000)
        self.page.locator("tr", has_text="최근 등록 정보").first.wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(600)

    def _get_recent_registration_row(self) -> Locator:
        """'최근 등록 정보' 행(tr) Locator 반환"""
        row = self.page.locator("tr", has_text="최근 등록 정보").first
        row.wait_for(state="visible", timeout=10000)
        return row

    def get_recent_registration_text(self) -> str:
        """'최근 등록 정보' 행의 모듈/버전 목록 문자열 반환"""
        row = self._get_recent_registration_row()
        tds = row.locator("td")
        if tds.count() >= 2:
            return tds.nth(1).inner_text().strip()
        return row.inner_text().strip()

    def get_registered_module_versions(self) -> Dict[str, str]:
        """
        '최근 등록 정보' 행에서 {모듈명: 버전} 딕셔너리 추출
        예: {'taPrsAgentV5.exe': '5.1.70.0', 'taKeeper.exe': '5.1.70.3', ...}
        """
        raw_text = self.get_recent_registration_text()
        versions: Dict[str, str] = {}
        for module_name, version in self._MODULE_VERSION_RE.findall(raw_text):
            versions[module_name.strip()] = version.strip()
        return versions

    def get_module_version(self, module_name: str = "taKeeper.exe") -> str:
        """'최근 등록 정보'에서 지정 모듈(기본: taKeeper.exe)의 버전 문자열 반환"""
        versions = self.get_registered_module_versions()
        if module_name in versions:
            return versions[module_name]
        for name, ver in versions.items():
            if name.lower() == module_name.lower():
                return ver
        raise ValueError(
            f"/manageAgent '최근 등록 정보'에서 '{module_name}' 버전을 찾을 수 없습니다. "
            f"(파싱된 모듈: {versions}, 원문: {self.get_recent_registration_text()!r})"
        )

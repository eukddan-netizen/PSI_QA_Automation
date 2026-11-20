"""
PSI 관리자 웹 콘솔 에이전트 관리 (/manageAgent) Playwright Page Object
- /manageAgent 접속
- '최근 등록 정보' 행에서 모듈명 및 버전 정보 파싱 (예: taKeeper.exe (5.1.70.3))
"""

import re
import time
from typing import Dict
from playwright.sync_api import Locator, Page

from pages.server.base_page import AdminBasePage


class AdminManageAgentPage(AdminBasePage):
    """PSI 웹 관리자 콘솔 /manageAgent 에이전트/모듈 관리 Page Object"""

    MANAGE_AGENT_URL = f"{AdminBasePage.BASE_URL}/manageAgent"
    _MODULE_VERSION_RE = re.compile(r"([A-Za-z0-9_.-]+\.exe)\s*\(([^)]+)\)")

    _PLACEHOLDER_KEYWORDS = ("등록 정보가 없습니다", "없습니다")

    def __init__(self, page: Page):
        super().__init__(page)

    @classmethod
    def _is_placeholder_text(cls, text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return True
        return any(kw in cleaned for kw in cls._PLACEHOLDER_KEYWORDS)

    def goto_manage_agent(self, timeout: float = 12.0) -> None:
        """에이전트 관리(/manageAgent) 페이지로 이동 및 '최근 등록 정보' 비동기 데이터 로드 완료 대기"""
        self.bring_to_front()
        if "/manageAgent" not in self.page.url:
            print(f"\n>>> [관리자 웹] {self.MANAGE_AGENT_URL} 이동 중...")
            self.page.goto(self.MANAGE_AGENT_URL, timeout=15000)
        row = self.page.locator("tr", has_text="최근 등록 정보").first
        row.wait_for(state="visible", timeout=10000)
        self.wait_for_loading_clear(timeout=10.0)

        # 초기 렌더링 직후에는 비동기 API 응답 전 기본 문구('등록 정보가 없습니다.')가 표시될 수 있으므로
        # 실제 모듈 버전 정보(*.exe (x.y.z))가 채워질 때까지 충분히 대기하고, 지연 시 1회 새로고침 재시도
        deadline = time.time() + max(5.0, timeout)
        reloaded = False
        reload_at = time.time() + min(6.0, max(3.5, timeout * 0.5))

        while time.time() < deadline:
            raw_text = self.get_recent_registration_text()
            if not self._is_placeholder_text(raw_text) and self._MODULE_VERSION_RE.search(raw_text):
                return

            if not reloaded and time.time() >= reload_at:
                reloaded = True
                print(">>> [관리자 웹 /manageAgent] '최근 등록 정보' 로드 지연 감지 -> 페이지 1회 새로고침 후 재대기...")
                try:
                    self.page.reload(wait_until="domcontentloaded", timeout=15000)
                    row = self.page.locator("tr", has_text="최근 등록 정보").first
                    row.wait_for(state="visible", timeout=10000)
                    self.wait_for_loading_clear(timeout=10.0)
                except Exception:
                    pass
                continue

            self.page.wait_for_timeout(200)

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

    def get_module_version(self, module_name: str = "taKeeper.exe", timeout: float = 5.0) -> str:
        """'최근 등록 정보'에서 지정 모듈(기본: taKeeper.exe)의 버전 문자열 반환"""
        deadline = time.time() + max(0.5, timeout)
        versions: Dict[str, str] = {}
        while True:
            versions = self.get_registered_module_versions()
            if module_name in versions:
                return versions[module_name]
            for name, ver in versions.items():
                if name.lower() == module_name.lower():
                    return ver
            if time.time() >= deadline:
                break
            self.page.wait_for_timeout(200)

        raise ValueError(
            f"/manageAgent '최근 등록 정보'에서 '{module_name}' 버전을 찾을 수 없습니다. "
            f"(파싱된 모듈: {versions}, 원문: {self.get_recent_registration_text()!r})"
        )

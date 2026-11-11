"""
PSI 관리자 웹 콘솔 패치 관리 (/patch, /patch/client) Playwright Page Object
- /patch 페이지 이동 및 사용자 IP(ipconfig) 검색
- 대상 사용자의 '권고' 패치 개수(설치/전체) 확인 및 상세 페이지(/patch/client) 진입
- 권고 패치 목록(유형, 패치 이름, 상태 현황) 및 패치 정보 모달 내 '발표일' 수집
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import Locator

from pages.admin_base_page import AdminBasePage


class AdminPatchPage(AdminBasePage):
    PATCH_URL = f"{AdminBasePage.BASE_URL}/patch"

    def goto_patch(self) -> None:
        """패치 관리(/patch) 페이지로 이동"""
        if not self.page.url.rstrip("/").endswith("/patch"):
            print(f">>> [관리자 웹] {self.PATCH_URL} 이동 중...")
            self.page.goto(self.PATCH_URL, timeout=15000)
        self.page.locator("input[placeholder='검색어 입력']").wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(1000)

    def _find_user_row_by_ip(self, ip: str) -> Optional[Locator]:
        """사용자 패치 테이블에서 정확한 IP 토큰을 포함하는 행 반환"""
        table = self.page.locator("table", has_text="패치 정보").first
        rows = table.locator("tbody tr")
        ip_pattern = re.compile(rf"(?<![0-9.]){re.escape(ip)}(?![0-9.])")

        for i in range(rows.count()):
            row = rows.nth(i)
            cells = row.locator("td")
            if cells.count() < 17:
                continue
            # '접속/단말 IP' 셀 또는 행 내 정확한 IP 일치 확인
            row_text = row.inner_text()
            if ip_pattern.search(row_text):
                return row
        return None

    def search_user_by_ip(self, ip_candidates: List[str]) -> Tuple[str, Locator]:
        """
        후보 IP 목록을 순차 검색하여 /patch 사용자 테이블에서 현재 PC 행을 찾습니다.
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

            row = self._find_user_row_by_ip(ip)
            if row is not None:
                print(f">>> [관리자 웹] 사용자 행 탐색 성공 (IP: {ip})")
                return ip, row

        raise AssertionError(
            f"관리자 웹(/patch)에서 현재 PC IP({ip_candidates})에 해당하는 사용자를 찾을 수 없습니다."
        )

    def _get_recommended_button(self, row: Locator) -> Locator:
        """사용자 행의 '패치 정보' 컬럼에서 '권고' 개수 버튼 Locator 반환 ('미권고' 제외)"""
        return row.locator("div", has_text=re.compile(r"^권고\s")).locator("button").first

    def get_user_recommended_counts(self, row: Locator) -> Tuple[int, int]:
        """'권고 12/12개' 버튼 텍스트에서 (설치 수, 전체 수) 추출"""
        btn_text = self._get_recommended_button(row).inner_text().strip()
        match = re.search(r"(\d+)\s*/\s*(\d+)", btn_text)
        if not match:
            raise ValueError(f"권고 패치 개수 형식을 파싱할 수 없습니다: {btn_text!r}")
        return int(match.group(1)), int(match.group(2))

    def click_user_recommended_count(self, row: Locator) -> None:
        """'권고' 개수 버튼을 클릭하여 사용자 패치 상세(/patch/client) 페이지로 이동"""
        btn = self._get_recommended_button(row)
        print(f">>> [관리자 웹] '권고' 개수 버튼 클릭: {btn.inner_text().strip()}")
        btn.click()
        self.page.locator("table", has_text="패치 이름").first.wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(1000)

    def _set_max_page_size(self) -> None:
        """페이지당 표시 개수(select.w-20)를 최대치(100개)로 설정"""
        size_select = self.page.locator("select.w-20").last
        if size_select.count() > 0 and size_select.is_visible():
            if size_select.input_value() != "100":
                size_select.select_option("100")
                self.page.wait_for_timeout(1200)

    def _get_total_count(self) -> Optional[int]:
        """상단 'Total N' 텍스트에서 전체 패치 건수 파싱"""
        total_loc = self.page.locator("text=/^Total\\s+\\d+/").first
        if total_loc.count() > 0 and total_loc.is_visible():
            m = re.search(r"Total\s+(\d+)", total_loc.inner_text())
            if m:
                return int(m.group(1))
        return None

    def _read_release_date_from_modal(self, patch_btn: Locator, expected_patch_name: str) -> str:
        """패치 이름 클릭 -> 패치 정보 모달(PatchInfoModal) 데이터 로딩 대기 후 '발표일' 추출 및 닫기"""
        patch_btn.click()
        modal = self.page.locator("[data-testid='PatchInfoModal']")
        modal.wait_for(state="visible", timeout=5000)

        handle = self.page.wait_for_function(
            """(expectedName) => {
                const el = document.querySelector("[data-testid='PatchInfoModal']");
                if (!el) return null;
                let modalName = '';
                let releaseDate = '';
                for (const row of el.querySelectorAll('div.flex.w-full')) {
                    const kids = row.children;
                    if (kids.length < 2) continue;
                    const label = kids[0].innerText.trim();
                    const val = kids[1].innerText.trim();
                    if (label === '패치 이름') modalName = val;
                    if (label === '발표일') releaseDate = val;
                }
                if (modalName === expectedName && releaseDate) {
                    return releaseDate;
                }
                return null;
            }""",
            arg=expected_patch_name,
            timeout=5000,
        )
        release_date = handle.json_value() or ""

        modal.locator("button[title='닫기']").click()
        modal.wait_for(state="hidden", timeout=5000)
        return release_date

    def collect_recommended_patches(self) -> List[Dict[str, Any]]:
        """
        /patch/client 페이지의 권고 패치 전체 행을 수집합니다.
        설치 완료('패치 완료' 포함) 패치는 패치 이름 클릭 후 패치 정보 모달의 '발표일'까지 수집합니다.
        """
        self._set_max_page_size()
        total_expected = self._get_total_count()
        patches: List[Dict[str, Any]] = []
        current_page = 1

        while True:
            patch_table = self.page.locator("table", has_text="패치 이름").first
            rows = patch_table.locator("tbody tr")
            row_count = rows.count()

            for i in range(row_count):
                row = rows.nth(i)
                tds = row.locator("td")
                if tds.count() < 7:
                    continue

                patch_type = tds.nth(2).inner_text().strip()
                name_btn = tds.nth(5).locator("button").first
                patch_name = (name_btn.inner_text() if name_btn.count() > 0 else tds.nth(5).inner_text()).strip()
                status_text = tds.nth(6).inner_text().strip()
                is_installed = "패치 완료" in status_text

                release_date = ""
                if is_installed:
                    click_target = name_btn if name_btn.count() > 0 else tds.nth(5)
                    release_date = self._read_release_date_from_modal(click_target, patch_name)

                patches.append(
                    {
                        "type": patch_type,
                        "name": patch_name,
                        "status": status_text,
                        "installed": is_installed,
                        "release_date": release_date,
                    }
                )

            if total_expected is not None and len(patches) >= total_expected:
                break

            next_page = current_page + 1
            next_btn = self.page.locator(f"button:text-is('{next_page}')")
            if next_btn.count() == 0 or not next_btn.first.is_visible():
                break

            next_btn.first.click()
            self.page.wait_for_timeout(1200)
            current_page = next_page

        return patches


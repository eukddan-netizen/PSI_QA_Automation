"""
PSI 관리자 웹 콘솔 (https://192.168.4.151) Playwright 제어 Page Object
- 관리자 로그인
- /pcsafe 페이지 이동
- 현재 PC IP(ipconfig) 기반 사용자 검색 및 정책 제어 (인사 UI 출력 등)
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import Locator, Page

from common.os_utils import get_current_machine_ips
from pages.server.base_page import AdminBasePage


class AdminPcsafePage(AdminBasePage):
    PCDAFE_URL = f"{AdminBasePage.BASE_URL}/pcsafe"

    def __init__(self, page: Page):
        super().__init__(page)
        self.target_ip: Optional[str] = None

    def goto_pcsafe(self) -> None:
        """PC보안점검 관리(/pcsafe) 페이지로 이동"""
        self.bring_to_front()
        if not self.page.url.rstrip("/").endswith("/pcsafe"):
            print(">>> [관리자 웹] /pcsafe 메뉴로 이동 중...")
            self.page.goto(self.PCDAFE_URL, timeout=15000)
        self.page.locator("input[placeholder='검색어 입력']").wait_for(state="visible", timeout=10000)
        self.wait_for_loading_clear(timeout=10.0)

    def select_department(self, dept_name: str = "t1") -> None:
        """좌측 부서트리에서 부서 클릭"""
        print(f">>> [관리자 웹] 좌측 부서트리에서 '{dept_name}' 부서 선택...")
        dept_locator = self.page.locator(f"text='{dept_name}'").first
        dept_locator.wait_for(state="visible", timeout=10000)
        dept_locator.click()
        self.page.wait_for_timeout(200)
        self.wait_for_loading_clear(timeout=10.0)
        self.page.locator("table", has_text="접속/단말 IP").first.wait_for(state="visible", timeout=10000)

    def search_current_user_by_ip(self, ip_candidates: Optional[List[str]] = None) -> str:
        """현재 PC의 ipconfig/라우팅 IP 후보로 /pcsafe 사용자를 검색하고 매칭된 IP를 저장"""
        candidates = ip_candidates or get_current_machine_ips()
        print(f">>> [관리자 웹] /pcsafe 현재 PC IP 후보: {candidates}")
        matched_ip, _ = self.search_user_by_ip(candidates)
        self.target_ip = matched_ip
        return matched_ip

    def _get_col_index(self, header_keyword: str, default: int) -> int:
        """사용자 테이블 헤더에서 지정 키워드를 포함하는 컬럼 인덱스 조회"""
        table = self.page.locator("table", has_text="접속/단말 IP").first
        headers = table.locator("thead th, thead td")
        for idx in range(headers.count()):
            if header_keyword in headers.nth(idx).inner_text():
                return idx
        return default

    def _get_hr_ui_col_index(self) -> int:
        """사용자 테이블 헤더에서 '인사 UI 출력' 컬럼 인덱스 조회 (기본값 7)"""
        return self._get_col_index("인사 UI 출력", default=7)

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

        self.bring_to_front()
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

        # 1차 모달: "인사 UI 출력 정책을 적용하시겠습니까?" -> '예'
        print(">>> [관리자 웹] 정책 적용 확인 팝업에서 [예] 클릭...")
        self._click_modal_button("예", timeout=10.0)

        # 2차 모달: "정상 처리되었습니다." -> '확인' (로딩 오버레이 자동 대기 후 클릭)
        print(">>> [관리자 웹] 처리 완료 팝업에서 [확인] 클릭...")
        done_text = self._click_modal_button("확인", timeout=10.0)
        assert "정상" in done_text or "완료" in done_text or "처리" in done_text, (
            f"인사 UI 정책 적용 후 예상치 못한 모달 응답: {done_text!r}"
        )

        # 테이블 상태가 목표값으로 반영될 때까지 폴링 대기
        deadline = time.time() + 6.0
        new_state = self.get_hr_ui_status(username=username, user_ip=user_ip)
        while new_state != target_state and time.time() < deadline:
            self.page.wait_for_timeout(200)
            new_state = self.get_hr_ui_status(username=username, user_ip=user_ip)

        print(f">>> [관리자 웹] 최종 변경된 상태: {new_state}")
        assert new_state == target_state, f"인사 UI 상태 변경 실패: 기대={target_state}, 실제={new_state}"
        return new_state

    def refresh_user_search(self, user_ip: Optional[str] = None) -> None:
        """사용자 검색어를 다시 입력/검색하여 최신 데이터를 반영"""
        self.bring_to_front()
        target_ip = user_ip or self.target_ip or self.search_current_user_by_ip()
        _, _ = self.search_user_by_ip([target_ip])

    def get_user_details(self, user_ip: Optional[str] = None) -> dict:
        """
        /pcsafe 사용자 목록 테이블에서 해당 IP 사용자의 행 상세 정보 추출:
        {
            'department': 't1',
            'username': 'KYC',
            'os': '11 Pro',
            'bit': '64',
            'sp': '25H2',
            'ip': '192.168.2.28',
            'mac': 'F44EB419E6AF',
            'score': '89점',
            'last_inspection_time': '2026-11-11 13:55:15',
            'status': '접속'
        }
        """
        target_ip, row = self._get_user_row(user_ip=user_ip)
        table = self.page.locator("table", has_text="접속/단말 IP").first
        headers = [th.inner_text().strip() for th in table.locator("thead th, thead td").all()]
        cells = [td.inner_text().strip() for td in row.locator("td").all()]

        def get_val(header_kw: str) -> str:
            for idx, h in enumerate(headers):
                if header_kw in h and idx < len(cells):
                    return cells[idx]
            return ""

        return {
            "department": get_val("부서"),
            "username": get_val("사용자"),
            "os": get_val("OS"),
            "bit": get_val("Bit"),
            "sp": get_val("SP"),
            "ip": get_val("접속/단말 IP"),
            "mac": get_val("MAC 주소"),
            "score": get_val("점검 점수"),
            "last_inspection_time": get_val("최종 점검일"),
            "status": get_val("접속 상태"),
        }

    def get_user_modal_info(self, user_ip: Optional[str] = None) -> Dict[str, str]:
        """
        /pcsafe 사용자 목록에서 해당 IP 행의 '사용자' 컬럼 버튼을 클릭해
        사용자 정보 모달(ClientFormModal)을 열고 사번/사용자명/갱신일을 추출한 뒤 모달을 닫습니다.
        반환값: {'emp_no': '...', 'username': '...', 'updated_at': 'YYYY-MM-DD HH:MM:SS'}
        """
        self.bring_to_front()
        target_ip, row = self._get_user_row(user_ip=user_ip)
        user_col_idx = self._get_col_index("사용자", default=9)
        user_btn = row.locator("td").nth(user_col_idx).locator("button, a").first
        user_btn.wait_for(state="visible", timeout=5000)
        print(f">>> [관리자 웹] '{target_ip}' 행의 사용자명 버튼 클릭 -> 사용자 정보 모달 오픈...")
        user_btn.click()

        modal = self.page.locator("[data-testid='ClientFormModal']")
        modal.wait_for(state="visible", timeout=5000)

        emp_no = ""
        username = ""
        updated_at = ""
        try:
            emp_input = (
                modal.locator("div.flex.w-full")
                .filter(has=self.page.locator("div.font-semibold", has_text=re.compile(r"^\s*사번\s*$")))
                .locator("input")
                .first
            )
            name_input = (
                modal.locator("div.flex.w-full")
                .filter(has=self.page.locator("div.font-semibold", has_text=re.compile(r"^\s*사용자\s*$")))
                .locator("input")
                .first
            )
            updated_row = (
                modal.locator("div.flex.w-full")
                .filter(has=self.page.locator("div.font-semibold", has_text=re.compile(r"^\s*갱신일\s*$")))
                .first
            )

            deadline = time.time() + 3.0
            while time.time() < deadline:
                emp_no = emp_input.input_value().strip()
                username = name_input.input_value().strip()
                try:
                    updated_text = updated_row.inner_text().strip()
                    m = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", updated_text)
                    if m:
                        updated_at = re.sub(r"\s+", " ", m.group(0)).strip()
                except Exception:
                    pass
                if emp_no and username and updated_at:
                    break
                self.page.wait_for_timeout(200)
        finally:
            close_btn = modal.locator("button[title='닫기']").first
            if close_btn.is_visible():
                close_btn.click()
                modal.wait_for(state="hidden", timeout=5000)

        print(
            f">>> [관리자 웹] 모달 조회 결과 -> 사번: {emp_no!r}, "
            f"사용자명: {username!r}, 갱신일: {updated_at!r}"
        )
        return {"emp_no": emp_no, "username": username, "updated_at": updated_at}



"""
PSI 관리자 웹 콘솔 보안점검 항목 관리 (/pcsafeManage) Playwright Page Object
- 정책 선택 드롭다운 선택 (예: 't1')
- 점검 항목별 점수(점) 조회/수정
- 우측 하단 '안전 기준 점수' 드롭다운 조회/수정
- 하단 '수정' 및 좌측 상단 '정책 적용' 버튼 처리 및 확인 모달 응답
"""

import time
from typing import Any, Dict, Optional, Tuple
from playwright.sync_api import Locator, Page

from pages.server.base_page import AdminBasePage


class AdminPcsafeManagePage(AdminBasePage):
    """PSI 웹 관리자 콘솔 /pcsafeManage 정책 관리 Page Object"""

    PCSAFE_MANAGE_URL = f"{AdminBasePage.BASE_URL}/pcsafeManage"

    def __init__(self, page: Page):
        super().__init__(page)

    def goto_pcsafe_manage(self) -> None:
        """보안점검 항목 관리(/pcsafeManage) 페이지로 이동"""
        if "/pcsafeManage" not in self.page.url:
            print(f">>> [관리자 웹] {self.PCSAFE_MANAGE_URL} 이동 중...")
            self.page.goto(self.PCSAFE_MANAGE_URL, timeout=15000)
        self.page.locator("select").first.wait_for(state="visible", timeout=10000)
        self.page.locator("table tbody tr").first.wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(800)

    def _get_policy_select(self) -> Locator:
        return self.page.locator("select").first

    def _get_safety_score_select(self) -> Locator:
        return self.page.locator("td:has-text('안전 기준 점수') select").first

    def select_policy(self, policy_name: str = "t1") -> None:
        """좌측 '정책 선택' 드롭다운에서 지정된 정책(예: 't1') 선택"""
        sel = self._get_policy_select()
        sel.wait_for(state="visible", timeout=10000)

        target_value = sel.evaluate(
            """(el, name) => {
                for (const opt of el.options) {
                    if (opt.text.trim() === name && !opt.disabled) {
                        return opt.value;
                    }
                }
                return null;
            }""",
            policy_name,
        )
        if target_value is None:
            raise ValueError(f"'정책 선택' 드롭다운에서 '{policy_name}' 정책을 찾을 수 없습니다.")

        print(f">>> [관리자 웹] 정책 선택: '{policy_name}' (value={target_value})")
        sel.select_option(value=target_value)
        self.page.wait_for_timeout(1200)

    def _get_item_row(self, item_no: int, item_name: Optional[str] = None) -> Locator:
        """우측 정책 관리 테이블에서 No.(및 선택적 항목명)로 해당 행 반환"""
        rows = self.page.locator("table").first.locator("tbody tr")
        target_no = str(item_no)
        for i in range(rows.count()):
            row = rows.nth(i)
            tds = row.locator("td")
            if tds.count() < 3:
                continue
            no_text = tds.nth(0).inner_text().strip()
            if no_text != target_no:
                continue
            name_text = tds.nth(1).inner_text().strip()
            if item_name and item_name not in name_text:
                raise AssertionError(
                    f"{item_no}번 항목명이 기대와 다릅니다. 기대 포함='{item_name}', 실제='{name_text}'"
                )
            return row
        raise ValueError(f"정책 관리 테이블에서 {item_no}번 항목을 찾을 수 없습니다.")

    def get_item_score(self, item_no: int, item_name: Optional[str] = None) -> int:
        """특정 점검 항목의 현재 점수(int) 조회"""
        row = self._get_item_row(item_no=item_no, item_name=item_name)
        val = row.locator("input[type='number']").first.input_value().strip()
        return int(val)

    def set_item_score(self, item_no: int, score: int, item_name: Optional[str] = None) -> None:
        """특정 점검 항목의 점수 컬럼 입력값 변경"""
        row = self._get_item_row(item_no=item_no, item_name=item_name)
        inp = row.locator("input[type='number']").first
        inp.wait_for(state="visible", timeout=5000)
        inp.fill(str(score))
        self.page.wait_for_timeout(200)
        actual = inp.input_value().strip()
        assert actual == str(score), f"{item_no}번 항목 점수 입력 실패: 기대={score}, 실제={actual}"
        print(f">>> [관리자 웹] {item_no}번 항목 점수 변경 -> {score}점")

    def get_safety_score(self) -> int:
        """우측 하단 '안전 기준 점수' 드롭다운의 현재 선택값(int) 조회"""
        sel = self._get_safety_score_select()
        sel.wait_for(state="visible", timeout=5000)
        return int(sel.input_value().strip())

    def set_safety_score(self, score: int) -> None:
        """우측 하단 '안전 기준 점수' 드롭다운 값 변경 (예: 10, 100)"""
        sel = self._get_safety_score_select()
        sel.wait_for(state="visible", timeout=5000)
        sel.select_option(value=str(score))
        self.page.wait_for_timeout(300)
        actual = sel.input_value().strip()
        assert actual == str(score), f"안전 기준 점수 변경 실패: 기대={score}, 실제={actual}"
        print(f">>> [관리자 웹] 안전 기준 점수 변경 -> {score}점")

    def _click_modal_button(self, button_text: str, timeout: float = 5.0) -> str:
        """확인/선택 모달(div.fixed.z-50) 대기 후 지정 버튼 클릭 및 본문 텍스트 반환"""
        modal = self.page.locator("div.fixed.z-50").first
        modal.wait_for(state="visible", timeout=int(timeout * 1000))
        modal_text = modal.inner_text().strip()
        btn = modal.locator(f"button:text-is('{button_text}')").first
        if btn.count() == 0:
            btn = modal.locator(f"button:has-text('{button_text}')").first
        btn.click()
        self.page.wait_for_timeout(800)
        return modal_text

    def save_policy(self) -> None:
        """하단 '수정' 버튼 클릭 및 '정상 처리되었습니다.' 모달 확인"""
        print(">>> [관리자 웹] 하단 [수정] 버튼 클릭...")
        edit_btn = self.page.locator("button:text-is('수정')").first
        edit_btn.scroll_into_view_if_needed()
        edit_btn.click()

        modal_text = self._click_modal_button("확인", timeout=8.0)
        assert "정상" in modal_text or "완료" in modal_text or "수정" in modal_text, (
            f"정책 수정 후 예상하지 못한 모달 응답입니다: {modal_text!r}"
        )
        print(">>> [관리자 웹] 정책 수정 완료 확인!")

    def apply_policy(self) -> None:
        """좌측 상단 '정책 적용' 버튼 클릭 -> [예] -> [확인] 처리"""
        print(">>> [관리자 웹] 좌측 상단 [정책 적용] 버튼 클릭...")
        apply_btn = self.page.locator("button:text-is('정책 적용')").first
        apply_btn.scroll_into_view_if_needed()
        apply_btn.click()

        confirm_text = self._click_modal_button("예", timeout=8.0)
        assert "적용" in confirm_text, f"정책 적용 확인 모달 문구가 예상과 다릅니다: {confirm_text!r}"

        done_text = self._click_modal_button("확인", timeout=8.0)
        assert "정상" in done_text or "완료" in done_text, (
            f"정책 적용 완료 모달 문구가 예상과 다릅니다: {done_text!r}"
        )
        # 서버 DB 및 에이전트 정책 동기화 여유 대기
        time.sleep(1.5)
        print(">>> [관리자 웹] 정책 적용 완료!")

    def save_and_apply_policy(self) -> None:
        """수정 버튼 클릭 후 정책 적용 버튼 클릭까지 일괄 수행"""
        self.save_policy()
        self.apply_policy()

    def get_policy_snapshot(self, item_nos: Tuple[int, ...] = (1, 2)) -> Dict[str, Any]:
        """현재 선택된 정책의 지정 항목 점수들과 안전 기준 점수를 스냅샷으로 저장"""
        return {
            "item_scores": {no: self.get_item_score(no) for no in item_nos},
            "safety_score": self.get_safety_score(),
        }

    def restore_policy_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """
        스냅샷과 현재 값이 다를 경우 원래 값으로 되돌리고 수정/정책 적용을 수행합니다.
        이미 동일한 상태라면 불필요한 정책 변경을 건너뛰고 False를 반환합니다.
        """
        changed = False
        for no, orig_val in snapshot.get("item_scores", {}).items():
            if self.get_item_score(no) != orig_val:
                self.set_item_score(no, orig_val)
                changed = True

        orig_safety = snapshot.get("safety_score")
        if orig_safety is not None and self.get_safety_score() != orig_safety:
            self.set_safety_score(orig_safety)
            changed = True

        if changed:
            print(f">>> [관리자 웹] 정책 스냅샷 원복 실행: {snapshot}")
            self.save_and_apply_policy()
        else:
            print(">>> [관리자 웹] 정책 스냅샷과 동일하여 원복 수정/적용 생략")
        return changed


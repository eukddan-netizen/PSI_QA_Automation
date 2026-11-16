"""
보안점검 프로그램 '점검' 탭 페이지 Object
- 점검 탭 렌더링 대기 및 상태(진행률 %, 진행 시간, 전체/안전/취약/점검불가 건수) 파싱
- 점검 탭 내 '▶ 점검 시작' 버튼 클릭 및 실시간 진행 모니터링 / '점검결과' 탭 자동 전환 검증
"""

import re
import time
from typing import Any, Dict, List, Optional

from pages.client.main_page import MainPage


class InspectionPage(MainPage):
    """'점검' 탭 전용 Page Object (MainPage 공통 기능 상속)"""

    def wait_for_inspection_ready(self, timeout: float = 10.0) -> Dict[str, Any]:
        """'점검' 탭 화면 DOM('▶ 점검 시작' 버튼, 진행 시간, 사용자 정보) 렌더링 대기"""
        deadline = time.time() + timeout
        last_status: Dict[str, Any] = {}
        while True:
            try:
                if self.get_active_tab_name() == "점검":
                    _, win = self._connect_window()
                    has_start_btn = any(
                        "점검 시작" in (b.element_info.name or "") or "점검시작" in (b.element_info.name or "")
                        for b in win.descendants(control_type="Button")
                    )
                    last_status = self.get_inspection_status()
                    user_info = self.get_user_info()
                    if has_start_btn and last_status.get("elapsed_time") and user_info.get("username"):
                        time.sleep(0.3)
                        return last_status
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError(f"'점검' 탭 DOM 로딩 대기 시간 초과: 마지막 상태={last_status}")
            time.sleep(0.35)

    def get_inspection_status(self) -> Dict[str, Any]:
        """
        '점검' 탭의 실시간 진행률(%), 진행 시간, 점검 항목 카운트(전체/안전/취약/점검불가)를 파싱합니다.
        """
        _, win = self._connect_window()
        texts = [(el.element_info.name or "").strip() for el in win.descendants(control_type="Text")]
        texts = [t for t in texts if t]
        joined = " ".join(texts)

        progress_percent: Optional[int] = None
        elapsed_time: Optional[str] = None

        for i, t in enumerate(texts):
            if progress_percent is None:
                m_pct = re.fullmatch(r"(\d+)\s*%", t)
                if m_pct:
                    progress_percent = int(m_pct.group(1))
            if elapsed_time is None and t == "진행 시간" and i + 1 < len(texts):
                if re.fullmatch(r"\d{2}:\d{2}:\d{2}", texts[i + 1]):
                    elapsed_time = texts[i + 1]

        if elapsed_time is None:
            m_time = re.search(r"\b(\d{2}:\d{2}:\d{2})\b", joined)
            if m_time:
                elapsed_time = m_time.group(1)

        def _extract_count(label: str) -> Optional[int]:
            m = re.search(rf"{label}\s*:\s*(\d+)", joined)
            return int(m.group(1)) if m else None

        return {
            "progress_percent": progress_percent,
            "elapsed_time": elapsed_time,
            "total_count": _extract_count("전체"),
            "safe_count": _extract_count("안전"),
            "vulnerable_count": _extract_count("취약"),
            "unable_count": _extract_count("점검불가"),
        }

    def click_start_inspection_on_tab(self) -> bool:
        """'점검' 탭 화면에 있는 '▶ 점검 시작' 버튼 클릭"""
        self.bring_to_front()
        target_h, win = self._connect_window()

        start_btn = None
        for _ in range(10):
            for b in win.descendants(control_type="Button"):
                b_name = b.element_info.name or ""
                if "점검 시작" in b_name or "점검시작" in b_name:
                    start_btn = b
                    break
            if start_btn is not None:
                break
            time.sleep(0.3)

        if start_btn is None:
            raise RuntimeError("'점검' 탭에서 '▶ 점검 시작' 버튼을 찾을 수 없습니다.")

        print(f">>> [InspectionPage] '▶ 점검 시작' 버튼 클릭: Screen={start_btn.rectangle()}")
        self._click_element(start_btn, target_h)
        return True

    def monitor_inspection_progress(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        점검 시작 후 실시간 진행률/진행 시간 변화를 추적하고,
        '점검결과' 탭으로 자동 이동할 때까지 폴링 대기합니다.
        """
        start = time.time()
        progress_history: List[int] = []
        elapsed_times_seen: List[str] = []
        reached_result_tab = False

        while time.time() - start < timeout:
            active = self.get_active_tab_name()
            if active == "점검결과":
                reached_result_tab = True
                time.sleep(0.8)
                break

            try:
                status = self.get_inspection_status()
                pct = status.get("progress_percent")
                if pct is not None and (not progress_history or progress_history[-1] != pct):
                    progress_history.append(pct)
                    print(f">>> [InspectionPage] 진행률 변화 감지: {pct}%")

                elapsed_t = status.get("elapsed_time")
                if elapsed_t and (not elapsed_times_seen or elapsed_times_seen[-1] != elapsed_t):
                    elapsed_times_seen.append(elapsed_t)
                    print(f">>> [InspectionPage] 진행 시간 변화 감지: {elapsed_t}")
            except Exception:
                pass

            time.sleep(0.25)

        return {
            "progress_history": progress_history,
            "max_progress": max(progress_history) if progress_history else None,
            "elapsed_times_seen": elapsed_times_seen,
            "reached_result_tab": reached_result_tab,
            "elapsed": round(time.time() - start, 2),
        }


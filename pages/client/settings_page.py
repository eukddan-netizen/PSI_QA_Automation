"""
보안점검 프로그램 '설정' 탭 페이지 Object
- 좌측 설정 하위 탭('일반', '외형', '정보') 전환
- '정보' 탭 내 '앱 버전' 문자열 조회
"""

import time
from typing import Optional

from pages.client.main_page import MainPage


class SettingsPage(MainPage):
    """'설정' 탭 전용 Page Object (MainPage 공통 기능 상속)"""

    def wait_for_settings_ready(self, timeout: float = 10.0) -> None:
        """'설정' 탭 DOM(하위 메뉴 '일반', '외형', '정보') 렌더링 완료 대기"""
        deadline = time.time() + timeout
        while True:
            try:
                if self.get_active_tab_name() == "설정":
                    _, win = self._connect_window()
                    items = {(d.element_info.name or "").strip() for d in win.descendants(control_type="ListItem")}
                    if "일반" in items and "정보" in items:
                        time.sleep(0.3)
                        return
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError("'설정' 탭 DOM 로딩 대기 시간 초과")
            time.sleep(0.3)

    def select_sub_tab(self, tab_name: str, timeout: float = 6.0) -> None:
        """'설정' 탭 좌측 하위 탭('일반', '외형', '정보') 클릭 및 활성화 대기"""
        self.wait_for_settings_ready(timeout=timeout)
        target_h, win = self._connect_window()

        target_item = None
        for item in win.descendants(control_type="ListItem"):
            if (item.element_info.name or "").strip() == tab_name:
                target_item = item
                break

        if target_item is None:
            raise RuntimeError(f"'설정' 탭에서 '{tab_name}' 하위 메뉴를 찾을 수 없습니다.")

        try:
            target_item.invoke()
        except Exception:
            self._click_element(target_item, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win_chk = self._connect_window()
            for item in win_chk.descendants(control_type="ListItem"):
                if (item.element_info.name or "").strip() == tab_name:
                    if "active" in (item.element_info.class_name or ""):
                        time.sleep(0.3)
                        return
            time.sleep(0.25)

        raise TimeoutError(f"'설정 > {tab_name}' 하위 탭 활성화 대기 시간 초과")

    def get_app_version(self, timeout: float = 8.0) -> str:
        """'설정 > 정보' 탭으로 이동하여 '앱 버전' 값을 반환 (예: '5.1.70.3')"""
        self.navigate_to_tab("설정", timeout=timeout)
        self.select_sub_tab("정보", timeout=timeout)

        deadline = time.time() + timeout
        while time.time() < deadline:
            _, win = self._connect_window()
            texts = [
                (t.element_info.name or "").strip()
                for t in win.descendants(control_type="Text")
                if t.element_info.name
            ]
            for idx, txt in enumerate(texts):
                if txt == "앱 버전" and idx + 1 < len(texts):
                    version = texts[idx + 1]
                    if version:
                        return version
            time.sleep(0.25)

        raise RuntimeError("'설정 > 정보' 탭에서 '앱 버전' 값을 찾을 수 없습니다.")


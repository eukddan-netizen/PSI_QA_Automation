"""
보안점검 프로그램 점검결과 페이지 Object
- 크롬 임베디드 렌더러 기반 UIA 정밀 제어
- 특정 점검 항목(점검 번호 또는 항목 이름 키워드) 상태('안전' / '취약' / '점검불가') 조회
- 특정 항목의 '조치' 버튼 클릭 및 실시간 안전 반영 검증
- 상단 취약 개수, 안전 개수 및 점수 조회 및 조치 전후 가감 검증
- 하단 '재점검' 버튼 제어
"""

import re
import time
import win32gui
import win32con
from typing import Any, Dict, List, Optional, Tuple
from PIL import ImageGrab
from pywinauto import Application


class InspectionResultPage:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def _get_target_window(self):
        """UIA 요소들이 존재하는 Chrome_WidgetWin_1 윈도우 핸들 탐색"""
        target_h = None

        def cb_child(ch, extra):
            nonlocal target_h
            cls = win32gui.GetClassName(ch)
            if "Chrome_WidgetWin_1" in cls:
                target_h = ch

        win32gui.EnumChildWindows(self.hwnd, cb_child, None)
        return target_h or self.hwnd

    def _get_app_window(self):
        h = self._get_target_window()
        app = Application(backend="uia").connect(handle=h)
        return app.window(handle=h)

    def bring_to_front(self) -> None:
        """보안점검 창을 복원하고 최상단 포커스로 활성화"""
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
        except Exception:
            pass

    def get_active_tab_name(self) -> Optional[str]:
        """좌측 사이드바에서 현재 활성화된 탭 이름 반환"""
        win = self._get_app_window()
        for link in win.descendants(control_type="Hyperlink"):
            cls = link.element_info.class_name or ""
            if "current" in cls or "router-link-active" in cls:
                name = (link.element_info.name or "").strip()
                if name:
                    return name
        return None

    def wait_for_result_ready(self, timeout: float = 12.0) -> Dict[str, Any]:
        """'점검결과' 탭 DOM(요약 점수, 사용자 정보, 결과 테이블) 렌더링 완료까지 대기"""
        deadline = time.time() + timeout
        last_stats: Dict[str, Any] = {}
        while True:
            try:
                if self.get_active_tab_name() == "점검결과":
                    last_stats = self.get_summary_stats()
                    user_info = self.get_user_info()
                    rows = self.get_all_result_rows()
                    if (
                        last_stats.get("score_num") is not None
                        and last_stats.get("total_num") is not None
                        and user_info.get("username")
                        and len(rows) > 0
                    ):
                        time.sleep(0.3)
                        return last_stats
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError(f"'점검결과' 탭 DOM 로딩 대기 시간 초과: 마지막 요약={last_stats}")
            time.sleep(0.35)

    def get_user_info(self) -> Dict[str, str]:
        """'점검결과' 탭 우측 상단 '사용자 정보' 카드 데이터 추출"""
        win = self._get_app_window()
        texts = [(el.element_info.name or "").strip() for el in win.descendants(control_type="Text")]
        info: Dict[str, str] = {}
        for i, t in enumerate(texts):
            if t == "OS 정보" and i + 1 < len(texts):
                info["os"] = texts[i + 1]
            elif t == "부서명" and i + 1 < len(texts):
                info["department"] = texts[i + 1]
            elif t == "사용자명" and i + 1 < len(texts):
                info["username"] = texts[i + 1]
            elif t == "사용자 IP" and i + 1 < len(texts):
                info["ip"] = texts[i + 1]
            elif t == "최근점검일시" and i + 1 < len(texts):
                info["last_inspection_time"] = texts[i + 1]
        return info

    def get_shield_visual_state(self) -> Dict[str, Any]:
        """
        '점검결과' 탭 좌측 상단 방패 아이콘 영역을 화면 캡처하여
        색상 기반으로 상태('양호'=파랑 / '위험'=빨강 / '대기'=회색)를 판별합니다.
        """
        self.bring_to_front()
        win = self._get_app_window()
        main_rect = win.rectangle()
        for grp in win.descendants(control_type="Group"):
            if (grp.element_info.class_name or "") == "main":
                main_rect = grp.rectangle()
                break

        score_label = None
        score_right = None
        texts = list(win.descendants(control_type="Text"))
        for idx, elem in enumerate(texts):
            name = (elem.element_info.name or "").strip()
            if name == "점검결과":
                score_label = elem
                score_right = elem.rectangle().right
                # 바로 뒤의 점수 숫자/단위('88', '점')까지 포함해 중앙 X 계산
                for k in range(idx + 1, min(len(texts), idx + 4)):
                    nxt_name = (texts[k].element_info.name or "").strip()
                    if nxt_name.isdigit() or nxt_name == "점":
                        score_right = max(score_right, texts[k].rectangle().right)
                break

        if score_label is None:
            raise RuntimeError("점검결과 탭에서 '점검결과' 점수 라벨을 찾을 수 없습니다.")

        label_rect = score_label.rectangle()
        cx = (label_rect.left + (score_right or label_rect.right)) // 2
        top_y = main_rect.top + 12
        bot_y = max(top_y + 40, label_rect.top - 8)
        bbox = (cx - 105, top_y, cx + 105, bot_y)

        crop = ImageGrab.grab(bbox=bbox).convert("RGB")
        pixels = crop.get_flattened_data()

        red = sum(1 for r, g, b in pixels if r > 150 and g < 90 and b < 90)
        blue = sum(1 for r, g, b in pixels if b > 170 and r < 100)
        gray = sum(1 for r, g, b in pixels if abs(r - g) < 20 and abs(g - b) < 20 and 80 < r < 230)

        if red > 800 and red > blue * 2:
            state = "위험"
        elif blue > 800 and blue > red * 2:
            state = "양호"
        elif gray > 800 and red < 150 and blue < 150:
            state = "대기"
        else:
            state = "알수없음"

        return {"state": state, "red": red, "blue": blue, "gray": gray, "bbox": bbox}

    def get_all_result_rows(self) -> List[Dict[str, Any]]:
        """점검결과 테이블의 전체 행(번호, 점검 항목, 결과, 조치/상세보기 버튼 여부)을 파싱하여 반환"""
        win = self._get_app_window()
        desc = list(win.descendants())
        rows: List[Dict[str, Any]] = []

        for i, elem in enumerate(desc):
            if elem.element_info.control_type == "DataItem" and (elem.element_info.class_name or "") == "col-number":
                no_text = (elem.element_info.name or "").strip()
                if not no_text.isdigit():
                    continue

                title = ""
                status = ""
                has_action_btn = False
                has_detail_btn = False

                for j in range(i + 1, min(len(desc), i + 14)):
                    nxt = desc[j]
                    nxt_ct = nxt.element_info.control_type
                    nxt_cls = nxt.element_info.class_name or ""
                    nxt_name = (nxt.element_info.name or "").strip()

                    if nxt_ct == "DataItem" and nxt_cls == "col-number":
                        break
                    if nxt_ct == "DataItem" and nxt_cls == "col-title" and not title:
                        title = nxt_name
                    elif nxt_ct == "DataItem" and nxt_cls == "col-button" and nxt_name in ("안전", "취약", "점검불가") and not status:
                        status = nxt_name
                    elif nxt_ct == "Button":
                        if nxt_name == "조치":
                            has_action_btn = True
                        elif nxt_name == "상세보기":
                            has_detail_btn = True

                rows.append({
                    "no": int(no_text),
                    "title": title,
                    "status": status,
                    "has_action_button": has_action_btn,
                    "has_detail_button": has_detail_btn,
                })

        return rows

    def click_table_header(self, header_name: str) -> None:
        """점검결과 테이블의 정렬 가능 컬럼 헤더('번호', '점검 항목', '결과') 클릭"""
        self.bring_to_front()
        win = self._get_app_window()
        for d in win.descendants(control_type="DataItem"):
            cls = d.element_info.class_name or ""
            name = (d.element_info.name or "").strip()
            if name == header_name and "sortable" in cls:
                print(f">>> [ResultPage] 테이블 '{header_name}' 헤더 클릭")
                self._click_element(d)
                time.sleep(0.6)
                return

        raise RuntimeError(f"점검결과 테이블에서 '{header_name}' 정렬 헤더를 찾을 수 없습니다.")

    def navigate_to_results(self):
        """사이드바의 '점검결과' 메뉴 클릭"""
        win = self._get_app_window()
        for link in win.descendants(control_type="Hyperlink"):
            if link.element_info.name == "점검결과":
                print(">>> [ResultPage] '점검결과' 메뉴 클릭")
                try:
                    link.invoke()
                except Exception:
                    self._click_element(link)
                time.sleep(2.0)
                break

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        상단의 점검 결과 요약 정보(점수, 전체/안전/취약/점검불가 항목 수)를 조회합니다.
        기존 문자열 키('vulnerable_count' 등)와 정수형 키('score_num', 'vulnerable_num' 등)를 함께 반환합니다.
        """
        win = self._get_app_window()
        stats: Dict[str, Any] = {}
        texts = [d.element_info.name.strip() for d in win.descendants(control_type="Text") if d.element_info.name]

        for idx, name in enumerate(texts):
            if name == "점검결과" and idx + 1 < len(texts):
                next_val = texts[idx + 1]
                if next_val.isdigit():
                    stats["score_num"] = int(next_val)
                    stats["score_text"] = f"{next_val}점"
            elif name.startswith("전체:"):
                stats["total_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["total_num"] = int(m.group(1))
            elif name.startswith("안전:"):
                stats["safe_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["safe_num"] = int(m.group(1))
            elif name.startswith("취약:"):
                stats["vulnerable_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["vulnerable_num"] = int(m.group(1))
            elif name.startswith("점검불가:"):
                stats["cannot_check_count"] = name
                m = re.search(r"(\d+)", name)
                if m:
                    stats["cannot_check_num"] = int(m.group(1))

        return stats

    def _find_item_Anchor_index(self, desc, item_name: str = "", check_num: Optional[int] = None) -> int:
        """
        결과 테이블에서 점검 번호(DataItem name == str(check_num)) 또는
        항목 이름 부분 문자열로 해당 행의 시작 인덱스를 탐색합니다.
        점검 개편으로 이름이나 번호 중 하나가 바뀌어도 유연하게 찾을 수 있습니다.
        """
        if check_num is not None:
            num_str = str(check_num)
            for i, d in enumerate(desc):
                if d.element_info.control_type == "DataItem" and d.element_info.name.strip() == num_str:
                    # 번호 셀 뒤쪽(i+1 ~ i+3)에 점검 제목 셀이 위치함
                    return i

        if item_name:
            for i, d in enumerate(desc):
                name = d.element_info.name or ""
                if item_name in name:
                    return i

        return -1

    def get_item_info(
        self, item_name: str = "화면 보호기", check_num: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[object]]:
        """
        점검 결과 테이블에서 특정 항목의 (진단상태 문자열, 조치/상세보기 버튼) 반환
        - 상태: "안전", "취약", "점검불가"
        - 버튼: "조치" 버튼이 있으면 최우선 반환, 없으면 "상세보기" 반환
        """
        win = self._get_app_window()
        desc = win.descendants()

        target_idx = self._find_item_Anchor_index(desc, item_name=item_name, check_num=check_num)
        if target_idx == -1:
            return None, None

        status = None
        action_btn = None
        detail_btn = None

        # 해당 항목 인덱스 주변(번호 셀부터 최대 12개 요소)에서 상태 및 버튼 정밀 탐색
        for j in range(target_idx, min(len(desc), target_idx + 12)):
            elem_name = (desc[j].element_info.name or "").strip()
            ctrl_type = desc[j].element_info.control_type

            # 다음 행의 점검 번호(숫자 DataItem)를 만나면 탐색 종료
            if j > target_idx + 2 and ctrl_type == "DataItem" and elem_name.isdigit():
                break

            if elem_name in ["안전", "취약", "점검불가"] and status is None:
                status = elem_name

            if ctrl_type == "Button":
                if elem_name == "조치" and action_btn is None:
                    action_btn = desc[j]
                elif elem_name == "상세보기" and detail_btn is None:
                    detail_btn = desc[j]

        chosen_btn = action_btn or detail_btn
        return status, chosen_btn

    def _click_element(self, elem):
        """UIA 요소의 좌표를 계산하여 PostMessage 클릭"""
        rect = elem.rectangle()
        target_h = self._get_target_window()
        r_rect = win32gui.GetWindowRect(target_h)
        local_x = (rect.left + rect.right) // 2 - r_rect[0]
        local_y = (rect.top + rect.bottom) // 2 - r_rect[1]

        lParam = (local_y << 16) | (local_x & 0xFFFF)
        win32gui.PostMessage(target_h, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.08)
        win32gui.PostMessage(target_h, win32con.WM_LBUTTONUP, 0, lParam)

    def click_remediate_button_for_item(
        self, item_name: str = "화면 보호기", check_num: Optional[int] = None
    ) -> bool:
        """특정 항목의 '조치' 버튼 클릭"""
        status, btn = self.get_item_info(item_name=item_name, check_num=check_num)
        label = f"{check_num}번({item_name})" if check_num else item_name
        print(f">>> [ResultPage] '{label}' 현재 진단 상태: {status}")
        if btn and btn.element_info.name == "조치":
            print(f">>> [ResultPage] '{label}' '조치' 버튼 발견! 클릭 실행: {btn.rectangle()}")
            self._click_element(btn)
            time.sleep(2.5)  # 조치 적용 및 UI 실시간 반영 대기
            return True
        else:
            print(
                f">>> [ResultPage] '{label}' 조치 버튼이 없습니다. "
                f"(현재 버튼: '{btn.element_info.name if btn else 'None'}')"
            )
            return False

    def get_item_detail_description(self, check_num: int, timeout: float = 4.0) -> Optional[str]:
        """
        특정 점검 번호 행의 '상세보기' 버튼을 클릭하여 상세 모달의 '・진단결과' 본문 텍스트를 반환하고 모달을 닫습니다.
        """
        win = self._get_app_window()
        desc = list(win.descendants())
        target_idx = self._find_item_Anchor_index(desc, check_num=check_num)
        if target_idx == -1:
            return None

        detail_btn = None
        for j in range(target_idx, min(len(desc), target_idx + 14)):
            elem = desc[j]
            elem_name = (elem.element_info.name or "").strip()
            ctrl_type = elem.element_info.control_type
            cls_name = elem.element_info.class_name or ""
            if j > target_idx + 2 and ctrl_type == "DataItem" and cls_name == "col-number":
                break
            if ctrl_type == "Button" and elem_name == "상세보기":
                detail_btn = elem
                break

        if detail_btn is None:
            return None

        try:
            detail_btn.invoke()
        except Exception:
            self._click_element(detail_btn)

        diag_text: Optional[str] = None
        deadline = time.time() + timeout
        while time.time() < deadline:
            win_modal = self._get_app_window()
            texts = [
                (t.element_info.name or "").strip()
                for t in win_modal.descendants(control_type="Text")
                if t.element_info.name
            ]
            if "・진단결과" in texts:
                idx = texts.index("・진단결과")
                collected = []
                for k in range(idx + 1, len(texts)):
                    if texts[k].startswith("・"):
                        break
                    collected.append(texts[k])
                diag_text = "\n".join(collected).strip()
                for b in win_modal.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() in ("확인", "닫기"):
                        try:
                            b.invoke()
                        except Exception:
                            self._click_element(b)
                        time.sleep(0.25)
                        break
                break
            time.sleep(0.2)

        return diag_text

    def click_reinspect(self):
        """결과 화면 하단의 '재점검' 버튼 클릭"""
        win = self._get_app_window()
        for btn in win.descendants(control_type="Button"):
            if "재점검" in (btn.element_info.name or ""):
                print(">>> [ResultPage] '재점검' 버튼 클릭!")
                self._click_element(btn)
                time.sleep(10.0)  # 재점검 수행 대기
                break

    @staticmethod
    def verify_common_remediation_metrics(before_stats: Dict[str, Any], after_stats: Dict[str, Any]) -> None:
        """
        53개 점검 공통 검증 시나리오:
        1) 조치 후 상단 '취약' 카운트가 조치 전보다 감소했는지 검증
        2) 조치 후 상단 '안전' 카운트가 증가하고, 점수가 서버 배점 설정에 따라 가감(상승 또는 유지)되었는지 확인
        """
        print(f">>> [공통 요약 검증] 조치 전: {before_stats} -> 조치 후: {after_stats}")

        if "vulnerable_num" in before_stats and "vulnerable_num" in after_stats:
            assert after_stats["vulnerable_num"] < before_stats["vulnerable_num"], (
                f"조치 후 취약 건수가 감소하지 않았습니다: "
                f"조치 전 {before_stats['vulnerable_num']}건 -> 조치 후 {after_stats['vulnerable_num']}건"
            )

        if "safe_num" in before_stats and "safe_num" in after_stats:
            assert after_stats["safe_num"] > before_stats["safe_num"], (
                f"조치 후 안전 건수가 증가하지 않았습니다: "
                f"조치 전 {before_stats['safe_num']}건 -> 조치 후 {after_stats['safe_num']}건"
            )

        if "score_num" in before_stats and "score_num" in after_stats:
            delta = after_stats["score_num"] - before_stats["score_num"]
            print(f">>> [점수 가감 확인] 조치 전 {before_stats['score_num']}점 -> 조치 후 {after_stats['score_num']}점 (변화량: {delta:+d}점)")
            assert after_stats["score_num"] >= before_stats["score_num"], (
                f"조치 후 보안 점수가 오히려 하락했습니다: "
                f"{before_stats['score_num']}점 -> {after_stats['score_num']}점"
            )
